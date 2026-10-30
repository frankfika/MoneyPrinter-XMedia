#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""xb.py — 短文助手浏览器执行层（替代 MiniMax Code 的 mcp_browser 工具）。

单次调用 = 单次 action：

    python3 scripts/browser/xb.py --action '{"action":"navigate","input":{"url":"https://x.com/frankfika"}}'

stdout 只有一行 JSON（日志全部走 stderr），退出码 0/1/2。
契约（action 名 / JSON 形状 / 退出码）由 scripts/browser/README.md 定义，不得擅自改名。

设计要点：
  * 两条传输路径：CDP attach（优先）→ persistent context 启动本机 Chrome。
  * 进程复用（默认开启，--ephemeral 关闭）：Chrome 常驻，跨调用保住登录态与会话；
    反复调用只 attach，不重启浏览器。
  * 绝不使用 Chrome 默认 profile（macOS TCC + Chrome 155 远程调试限制）。
  * 只读优先：本工具不提供发帖/点赞/回复等写操作的快捷封装，
    fill + press 也仅执行「用户明确给出」的键盘/填表动作。
  * 无 TTY 依赖；硬超时（signal）保证 cron 里不会挂死。

Python 3.9+；playwright 缺失时自动用 `uv run --with playwright` 重新执行自己。
"""

from __future__ import annotations

import errno
import fcntl
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# --------------------------------------------------------------------------- #
# 常量
# --------------------------------------------------------------------------- #

SCRIPT = Path(__file__).resolve()
HERE = SCRIPT.parent                 # scripts/browser
ROOT = SCRIPT.parents[2]             # 仓库根：scripts/browser/xb.py -> 短文助手/
# 运行时状态目录（可用 XB_STATE_DIR 覆盖，自检/测试用临时目录避免污染真实状态）
STATE_DIR = Path(os.environ.get("XB_STATE_DIR") or (HERE / ".state"))
REFS_FILE = STATE_DIR / "refs.json"
LAST_PAGE_FILE = STATE_DIR / "last_page.json"
ENDPOINT_FILE = STATE_DIR / "endpoint.json"

EXIT_OK = 0
EXIT_ACTION_FAILED = 1
EXIT_BROWSER_UNAVAILABLE = 2

LOGIN_URL_HINTS = ("/i/jf/onboarding", "/i/flow/login", "/login", "/i/flow/signup")

DEFAULT_CONFIG: Dict[str, Any] = {
    "cdp": "http://127.0.0.1:9222",
    "user_data_dir": "~/.shortbot-browser-profile",
    "locale": "zh-CN",
    "timezone_id": "Asia/Shanghai",
    "action_timeout_ms": 30000,
    "navigate_timeout_ms": 45000,
    "settle_ms": 800,
    "headless": False,
    "proxy_mode": "auto",         # auto | always | never
    "proxy": "http://127.0.0.1:7897",
    "viewport": {"width": 1366, "height": 900},
    "chrome_path": "",
}

ACTION_NAMES = [
    "navigate", "open_tab", "wait", "query", "inspect",
    "click", "fill", "press", "screenshot", "login_state",
]

DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
)

# --------------------------------------------------------------------------- #
# 错误
# --------------------------------------------------------------------------- #


class XBError(Exception):
    """带可判定 error.code 的失败。"""

    def __init__(self, code: str, message: str, exit_code: int = EXIT_ACTION_FAILED):
        super().__init__(message)
        self.code = code
        self.message = message
        self.exit_code = exit_code


class BrowserUnavailable(XBError):
    def __init__(self, message: str):
        super().__init__("BROWSER_UNAVAILABLE", message, EXIT_BROWSER_UNAVAILABLE)


# --------------------------------------------------------------------------- #
# 输出
# --------------------------------------------------------------------------- #

_emitted = False


def log(msg: str) -> None:
    sys.stderr.write("[xb] %s\n" % msg)
    sys.stderr.flush()


def emit(payload: Dict[str, Any], exit_code: int) -> int:
    """stdout 只写这一行 JSON（并立即 flush），返回退出码。

    注意：这里**不**直接 os._exit —— 调用方需要先清理浏览器进程再退出。
    """
    global _emitted
    if _emitted:
        return exit_code
    _emitted = True
    line = json.dumps(payload, ensure_ascii=False, default=str)
    sys.stdout.write(line + "\n")
    sys.stdout.flush()
    sys.stderr.flush()
    return exit_code


def emit_ok(action: str, data: Dict[str, Any]) -> int:
    return emit({"ok": True, "action": action, "data": data}, EXIT_OK)


def emit_err(action: Optional[str], err: XBError) -> int:
    payload: Dict[str, Any] = {"ok": False}
    if action:
        payload["action"] = action
    payload["error"] = {"code": err.code, "message": err.message}
    return emit(payload, err.exit_code)


def emit_and_exit(payload: Dict[str, Any], exit_code: int) -> None:
    """早期退出（help / list-actions / print-config）：没有浏览器进程需要清理。"""
    emit(payload, exit_code)
    os._exit(exit_code)


# --------------------------------------------------------------------------- #
# 硬超时（保证 cron 里不会挂死）
# --------------------------------------------------------------------------- #

_timed_out = False
_deadline_monotonic: Optional[float] = None


def _on_alarm(signum, frame):  # noqa: ANN001
    global _timed_out
    if _timed_out:
        # 清理阶段再次超时：直接退出，避免无限挂
        os._exit(EXIT_ACTION_FAILED)
    _timed_out = True
    raise XBError(
        "TIMEOUT",
        "action 执行超过硬超时上限（%.1fs），已中断。cron 场景请把它当作「本轮浏览器不可用」"
        % (_hard_timeout_ms / 1000.0),
    )


_hard_timeout_ms = 0


def arm_hard_timeout(ms: int) -> None:
    global _hard_timeout_ms, _deadline_monotonic
    _hard_timeout_ms = int(ms)
    _deadline_monotonic = time.monotonic() + ms / 1000.0
    try:
        signal.signal(signal.SIGALRM, _on_alarm)
        signal.setitimer(signal.ITIMER_REAL, ms / 1000.0)
    except Exception as exc:  # pragma: no cover - 非 main thread 才会发生
        log("WARN 无法设置硬超时: %s" % exc)


def remaining_ms() -> int:
    if _deadline_monotonic is None:
        return 10 ** 9
    return max(0, int((_deadline_monotonic - time.monotonic()) * 1000))


def clamp_ms(wanted: int, reserve: int = 800) -> int:
    """把单步等待压进硬超时预算内，留出收尾/输出时间。"""
    return max(500, min(int(wanted), remaining_ms() - reserve))


# --------------------------------------------------------------------------- #
# 配置
# --------------------------------------------------------------------------- #


def _mini_yaml(text: str) -> Dict[str, Any]:
    """极简 YAML 兜底解析：只支持 key: value / 注释 / 简单缩进嵌套。

    正常情况下用 pyyaml（uv run 里已带上），这里是「系统 python3 没装 pyyaml」的保底。
    """
    out: Dict[str, Any] = {}
    stack: List[Tuple[int, Dict[str, Any]]] = [(-1, out)]
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        key, sep, val = line.strip().partition(":")
        if not sep:
            continue
        key = key.strip().strip("'\"")
        val = val.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1] if stack else out
        if val == "":
            child: Dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            # 去掉行尾注释（简单处理：值里有 # 且前面有空格）
            val = re.split(r"\s+#", val, 1)[0].strip()
            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            if val.lower() in ("true", "yes"):
                parsed: Any = True
            elif val.lower() in ("false", "no"):
                parsed = False
            elif val.lower() in ("null", "none", "~"):
                parsed = None
            elif re.fullmatch(r"-?\d+", val):
                parsed = int(val)
            elif re.fullmatch(r"-?\d+\.\d+", val):
                parsed = float(val)
            else:
                parsed = val
            parent[key] = parsed
    return out


def load_config(config_path: Optional[str]) -> Dict[str, Any]:
    cfg = dict(DEFAULT_CONFIG)
    cfg["viewport"] = dict(DEFAULT_CONFIG["viewport"])
    candidates: List[Path] = []
    if config_path:
        candidates.append(Path(config_path).expanduser())
    env_cfg = os.environ.get("XB_CONFIG")
    if env_cfg:
        candidates.append(Path(env_cfg).expanduser())
    candidates.append(ROOT / "private" / "browser.yaml")
    candidates.append(HERE / "browser.yaml")
    path = next((p for p in candidates if p.is_file()), None)
    if path is None:
        log("未找到配置文件，使用默认值（%s）" % (ROOT / "private" / "browser.yaml"))
        return cfg
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text) or {}
        if not isinstance(data, dict):
            raise ValueError("配置不是 mapping")
    except ImportError:
        data = _mini_yaml(text)
    except Exception as exc:
        log("WARN 配置文件解析失败(%s)，改用兜底解析: %s" % (path, exc))
        data = _mini_yaml(text)
    for k, v in data.items():
        if v is None:
            continue
        if k == "viewport" and isinstance(v, dict):
            cfg["viewport"] = {**DEFAULT_CONFIG["viewport"], **v}
        else:
            cfg[k] = v
    cfg["_config_path"] = str(path)
    log("config=%s cdp=%s profile=%s" % (path, cfg.get("cdp"), cfg.get("user_data_dir")))
    return cfg


def expand_dir(value: str) -> Path:
    p = Path(str(value)).expanduser()
    if not p.is_absolute():
        p = (ROOT / p).resolve()
    return p


# --------------------------------------------------------------------------- #
# 跨进程互斥：同一个 Chrome profile 上的动作必须串行（否则两个 cron 会抢同一个 tab）
# --------------------------------------------------------------------------- #

LOCK_FILE = STATE_DIR / "xb.lock"  # 与 STATE_DIR 联动（XB_STATE_DIR 可覆盖）
_lock_fd: Optional[int] = None


def acquire_lock(wait_ms: int) -> None:
    """串行化并发调用；等不到就报 LOCK_TIMEOUT（exit 1，可判定，不是浏览器不可用）。"""
    global _lock_fd
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(LOCK_FILE), os.O_RDWR | os.O_CREAT, 0o644)
    except Exception as exc:
        log("WARN 无法创建锁文件（继续但不串行）: %s" % exc)
        return
    deadline = time.monotonic() + max(0, wait_ms) / 1000.0
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                os.ftruncate(fd, 0)
                os.write(fd, str(os.getpid()).encode())
            except Exception:
                pass
            _lock_fd = fd
            return
        except OSError as exc:
            if exc.errno not in (errno.EAGAIN, errno.EACCES):
                log("WARN flock 异常（继续）: %s" % exc)
                os.close(fd)
                return
            if time.monotonic() >= deadline:
                os.close(fd)
                raise XBError(
                    "LOCK_TIMEOUT",
                    "另一个 xb.py 调用正在使用同一浏览器（锁 %s）。等了 %dms 仍未释放。"
                    "cron 场景请把它当作本轮跳过，不要并发重试。" % (LOCK_FILE, wait_ms),
                )
            time.sleep(0.15)


def release_lock() -> None:
    global _lock_fd
    if _lock_fd is not None:
        try:
            fcntl.flock(_lock_fd, fcntl.LOCK_UN)
            os.close(_lock_fd)
        except Exception:
            pass
        _lock_fd = None


# --------------------------------------------------------------------------- #
# 状态（跨调用：last page / refs）
# --------------------------------------------------------------------------- #


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, data: Any) -> None:
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception as exc:  # 状态写失败不影响 action 结果
        log("WARN 状态落盘失败 %s: %s" % (path, exc))


def remember_last_page(url: str) -> None:
    if not url:
        return
    write_json(LAST_PAGE_FILE, {"url": url, "ts": int(time.time())})


def remember_endpoint(endpoint: str, profile: str, mode: str) -> None:
    """记下「当前在用的 endpoint」——Chrome 用显式 --remote-debugging-port 时不会写
    DevToolsActivePort（那是 port=0 才写），所以自己记一份，方便下一轮/排查。"""
    write_json(ENDPOINT_FILE, {"endpoint": endpoint, "profile": profile,
                               "mode": mode, "ts": int(time.time())})


def remembered_endpoint() -> Optional[str]:
    data = read_json(ENDPOINT_FILE, {})
    ep = data.get("endpoint") if isinstance(data, dict) else None
    return ep or None


def last_page_url() -> Optional[str]:
    data = read_json(LAST_PAGE_FILE, {})
    url = data.get("url") if isinstance(data, dict) else None
    return url or None


def store_ref(selector: str, index: int) -> str:
    refs = read_json(REFS_FILE, {})
    if not isinstance(refs, dict):
        refs = {}
    ref = "ref-" + os.urandom(4).hex()
    refs[ref] = {"selector": selector, "index": index, "ts": int(time.time())}
    if len(refs) > 200:  # 只留最近 200 个
        for k in sorted(refs, key=lambda x: refs[x].get("ts", 0))[: len(refs) - 200]:
            refs.pop(k, None)
    write_json(REFS_FILE, refs)
    return ref


def resolve_ref(ref: str) -> Tuple[str, int]:
    refs = read_json(REFS_FILE, {})
    item = refs.get(ref) if isinstance(refs, dict) else None
    if not item:
        raise XBError(
            "REF_NOT_FOUND",
            "ref %s 不存在或已过期；请先 inspect {selector} 拿新 ref（ref 存储于 %s）" % (ref, REFS_FILE),
        )
    return str(item["selector"]), int(item.get("index", 0))


# --------------------------------------------------------------------------- #
# 浏览器会话
# --------------------------------------------------------------------------- #


def find_chrome(cfg: Dict[str, Any]) -> str:
    explicit = os.environ.get("XB_CHROME") or str(cfg.get("chrome_path") or "")
    cands: List[Path] = []
    if explicit:
        cands.append(Path(explicit).expanduser())
    cands += [
        Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        Path.home() / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
        Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
    ]
    for c in cands:
        if c.is_file():
            return str(c)
    for name in ("google-chrome", "chromium", "chromium-browser", "chrome"):
        found = shutil.which(name)
        if found:
            return found
    raise BrowserUnavailable(
        "找不到本机 Chrome 可执行文件。请安装 Google Chrome，或用环境变量 XB_CHROME / "
        "private/browser.yaml#chrome_path 指定路径。"
    )


def cdp_alive(endpoint: str, timeout: float = 1.5) -> bool:
    import urllib.request

    try:
        with urllib.request.urlopen(endpoint.rstrip("/") + "/json/version", timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def _cdp_http(endpoint: str, path: str, method: str = "GET", timeout: float = 3.0) -> Any:
    import urllib.request

    req = urllib.request.Request(endpoint.rstrip("/") + path, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode("utf-8", "replace")
    return json.loads(raw) if raw.strip() else {}


def ensure_page_target(endpoint: str) -> None:
    """Playwright attach 需要浏览器里至少有一个 type=page 的 target。

    实测（Chrome 155 + Playwright 1.64）：浏览器窗口全关、只剩进程时 /json/list 里
    没有 page target，connect_over_cdp 会报
    "Protocol error (Browser.setDownloadBehavior): Browser context management is not supported"。
    这里先补一个 about:blank，避免 cron 里误判成「浏览器不可用」。
    """
    try:
        targets = _cdp_http(endpoint, "/json/list")
    except Exception as exc:
        log("WARN 读 /json/list 失败: %s" % exc)
        return
    if isinstance(targets, list) and any(t.get("type") == "page" for t in targets):
        return
    try:
        _cdp_http(endpoint, "/json/new?about:blank", method="PUT")
        log("CDP 里没有 page target，已创建 about:blank（attach 必需）")
    except Exception as exc:
        log("WARN 创建 page target 失败: %s" % exc)


def endpoint_port(endpoint: str) -> int:
    m = re.search(r":(\d+)(?:/|$)", endpoint)
    return int(m.group(1)) if m else 9222


def _profile_in_use(profile: Path) -> bool:
    """该 user-data-dir 是否已有 Chrome 进程在使用（不杀进程，只判断）。"""
    try:
        r = subprocess.run(["pgrep", "-f", "user-data-dir=%s" % profile],
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=5)
        return bool(r.stdout.strip())
    except Exception:
        return False


def _read_devtools_port(profile: Path) -> Optional[int]:
    devtools = profile / "DevToolsActivePort"
    if not devtools.is_file():
        return None
    try:
        return int(devtools.read_text(encoding="utf-8").splitlines()[0].strip())
    except Exception:
        return None


class BrowserSession:
    """一次调用内的浏览器连接。"""

    def __init__(self, cfg: Dict[str, Any], *, keepalive: bool, headless: bool,
                 endpoint: Optional[str], proxy: Optional[str], ephemeral: bool):
        self.cfg = cfg
        self.keepalive = keepalive
        self.headless = headless
        self.endpoint = endpoint
        self.proxy = proxy
        self.ephemeral = ephemeral
        self.playwright = None
        self.browser = None
        self.context = None
        self.mode = ""            # "cdp" | "persistent"
        self.owns_browser = False  # persistent-context 由本进程拥有
        self._last_saved_url: Optional[str] = None

    # -- 启动 ---------------------------------------------------------------
    def start(self) -> None:
        from playwright.sync_api import sync_playwright

        self.playwright = sync_playwright().start()
        errors: List[str] = []

        if self.endpoint:
            if cdp_alive(self.endpoint):
                if self._attach(self.endpoint):
                    return
                errors.append("CDP attach 失败: %s" % self.endpoint)
            else:
                errors.append("CDP 未监听: %s" % self.endpoint)
                # 上次 spawn 记录过别的端口（比如换了 cdp 配置）→ 先试它
                prev = remembered_endpoint()
                if prev and prev.rstrip("/") != self.endpoint.rstrip("/") and cdp_alive(prev):
                    if self._attach(prev):
                        log("改用上次记录的 endpoint: %s" % prev)
                        self.endpoint = prev
                        return
                    errors.append("上次记录的 endpoint attach 失败: %s" % prev)

        if self.keepalive and self.endpoint:
            # --ensure 语义：拉起常驻 Chrome 并 attach（跨调用复用，保住登录态）
            try:
                ep = self._spawn_chrome()
                if self._attach(ep):
                    return
                errors.append("拉起 Chrome 后 attach 失败: %s" % ep)
            except XBError as exc:
                errors.append("拉起 Chrome 失败: %s" % exc.message)
            except Exception as exc:
                errors.append("拉起 Chrome 异常: %s" % exc)

        # 兜底/persistent-context 路径（进程随调用退出，profile 仍留在磁盘）
        try:
            self._launch_persistent()
            return
        except Exception as exc:
            errors.append("persistent context 启动失败: %s" % exc)

        # 最后再试一次 attach（上面这些路径可能只是撞上了 Chrome 的瞬时状态）
        if self.endpoint and cdp_alive(self.endpoint):
            time.sleep(1.5)
            if self._attach(self.endpoint):
                log("最终重试 attach 成功")
                return
            errors.append("最终重试 attach 仍失败: %s" % self.endpoint)

        raise BrowserUnavailable(
            "浏览器不可用（BROWSER_UNAVAILABLE）。尝试记录："
            + " | ".join(errors)
            + "。检查项：① Chrome 是否安装 ② private/browser.yaml 的 cdp / user_data_dir "
            "③ user_data_dir 是否被别的 Chrome 进程占用（同一 profile 只能一个实例）"
        )

    def _attach(self, endpoint: str, attempts: int = 3) -> bool:
        last_err = None
        ensure_page_target(endpoint)
        for attempt in range(1, attempts + 1):
            try:
                self.browser = self.playwright.chromium.connect_over_cdp(endpoint, timeout=15000)
                last_err = None
                break
            except Exception as exc:
                last_err = exc
                self.browser = None
                log("connect_over_cdp(%s) 第 %d/%d 次失败: %s"
                    % (endpoint, attempt, attempts, str(exc).splitlines()[0]))
                if attempt < attempts:
                    # 浏览器刚被上一个客户端连过 / 正在收尾时会出现瞬时协议错误，退避重试
                    time.sleep(0.9 * attempt)
                    if "context management" in str(exc):
                        ensure_page_target(endpoint)  # 可能窗口全关导致没有 page target
        if last_err is not None:
            return False
        self.mode = "cdp"
        remember_endpoint(endpoint, str(expand_dir(str(self.cfg["user_data_dir"]))), "cdp")
        contexts = list(self.browser.contexts)
        self.context = contexts[0] if contexts else self.browser.new_context()
        log("attached via CDP %s (contexts=%d pages=%d)"
            % (endpoint, len(contexts), len(self.context.pages)))
        return True

    def _spawn_chrome(self) -> str:
        profile = expand_dir(str(self.cfg["user_data_dir"]))
        if "Library/Application Support/Google/Chrome" in str(profile):
            raise BrowserUnavailable(
                "拒绝使用 Chrome 默认 profile（%s）：macOS TCC 会让进程 Operation not permitted，"
                "且 Chrome 155 在默认 profile 上不监听 --remote-debugging-port。" % profile
            )
        profile.mkdir(parents=True, exist_ok=True)
        chrome = find_chrome(self.cfg)
        port = endpoint_port(self.endpoint or "http://127.0.0.1:9222")

        # 同一个 profile 只能有一个 Chrome 实例。若已有进程占用但这个实例没开调试端口，
        # 再 spawn 只会被 Chrome 的 singleton 转交给老进程（调试端口依旧不监听）→ 明确报错。
        if _profile_in_use(profile):
            raise BrowserUnavailable(
                "profile %s 已被一个 Chrome 实例占用，但它没在 %d 上开调试端口。请先退出那个 Chrome，"
                "或让它带 --remote-debugging-port=%d 重启（本工具不会擅自杀掉用户的浏览器进程）。"
                % (profile, port, port)
            )

        # 该 profile 已有实例在跑（Chrome 会写 DevToolsActivePort）→ 直接 attach
        real_port = _read_devtools_port(profile)
        if real_port:
            cand = "http://127.0.0.1:%d" % real_port
            if cdp_alive(cand):
                log("profile 已有调试实例在跑，attach %s" % cand)
                self.endpoint = cand
                return cand

        args = [
            chrome,
            "--user-data-dir=%s" % profile,
            "--remote-debugging-port=%d" % port,
            "--remote-allow-origins=*",  # CDP WebSocket 握手会因 Origin 被 403
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-blink-features=AutomationControlled",
            "--lang=%s" % str(self.cfg.get("locale") or "zh-CN"),
        ]
        if self.headless:
            args.append("--headless=new")
        if self.proxy:
            args.append("--proxy-server=%s" % self.proxy)
        args.append("about:blank")

        log("spawn chrome: %s (profile=%s port=%d headless=%s)"
            % (chrome, profile, port, self.headless))
        subprocess.Popen(
            args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True, close_fds=True,
        )

        # 等端口就绪（同时兼容 DevToolsActivePort 里是别的端口）
        endpoint = "http://127.0.0.1:%d" % port
        deadline = time.monotonic() + min(25.0, max(8.0, remaining_ms() / 1000.0 - 5))
        while time.monotonic() < deadline:
            if cdp_alive(endpoint, timeout=0.6):
                self.endpoint = endpoint
                remember_endpoint(endpoint, str(profile), "spawned")
                return endpoint
            real_port = _read_devtools_port(profile)
            if real_port:
                cand = "http://127.0.0.1:%d" % real_port
                if cdp_alive(cand, timeout=0.6):
                    self.endpoint = cand
                    return cand
            time.sleep(0.25)
        raise BrowserUnavailable(
            "Chrome 已拉起但 %d 秒内没有监听调试端口（%s）。常见原因：profile 已被另一个 Chrome "
            "实例占用（同一 profile 只能一个实例），或 Chrome 拒绝在默认 profile 开远程调试。"
            % (int(25), endpoint)
        )

    def _launch_persistent(self) -> None:
        profile = expand_dir(str(self.cfg["user_data_dir"]))
        if "Library/Application Support/Google/Chrome" in str(profile):
            raise BrowserUnavailable(
                "拒绝使用 Chrome 默认 profile（%s）：macOS TCC 会拒绝读取。" % profile
            )
        profile.mkdir(parents=True, exist_ok=True)
        if _profile_in_use(profile):
            raise BrowserUnavailable(
                "profile %s 正被另一个 Chrome 进程使用（同一 profile 只能有一个实例）。"
                "请先退出它，或改用 CDP attach 路径。" % profile
            )
        kwargs: Dict[str, Any] = dict(
            user_data_dir=str(profile),
            channel="chrome",
            headless=self.headless,
            locale=str(self.cfg.get("locale") or "zh-CN"),
            timezone_id=str(self.cfg.get("timezone_id") or "Asia/Shanghai"),
            viewport=dict(self.cfg.get("viewport") or DEFAULT_CONFIG["viewport"]),
            user_agent=DEFAULT_UA,
            args=[
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-blink-features=AutomationControlled",
                "--lang=%s" % str(self.cfg.get("locale") or "zh-CN"),
            ],
        )
        if self.proxy:
            kwargs["proxy"] = {"server": self.proxy}
        kwargs["user_data_dir"] = str(profile)
        self.context = self.playwright.chromium.launch_persistent_context(**kwargs)
        self.mode = "persistent"
        self.owns_browser = True
        log("launched persistent context (profile=%s headless=%s)" % (profile, self.headless))

    # -- 页面 ---------------------------------------------------------------
    def pages(self) -> List[Any]:
        try:
            return [p for p in (self.context.pages if self.context else []) if not p.is_closed()]
        except Exception:
            return []

    def get_page(self, *, restore: bool = False) -> Any:
        last = last_page_url()
        pages = self.pages()
        page = None
        if last:
            for p in pages:
                if (p.url or "").split("#")[0] == last.split("#")[0]:
                    page = p
                    break
        if page is None:
            x_pages = [p for p in pages if "x.com" in (p.url or "") or "twitter.com" in (p.url or "")]
            if x_pages:
                page = x_pages[-1]
        if page is None and pages:
            page = pages[0]
        if page is None:
            page = self.context.new_page()
            log("no page target, opened new page")
        page.set_default_timeout(int(self.cfg.get("action_timeout_ms", 30000)))
        page.set_default_navigation_timeout(int(self.cfg.get("navigate_timeout_ms", 45000)))
        if restore and last and self.mode == "persistent" and (page.url or "about:blank") in ("", "about:blank"):
            # persistent context 每次调用都是新进程，恢复上次的 URL 以模拟「同一个 tab」
            try:
                log("restore last page: %s" % last)
                page.goto(last, wait_until="domcontentloaded",
                          timeout=clamp_ms(int(self.cfg.get("navigate_timeout_ms", 45000))))
            except Exception as exc:
                log("WARN 恢复上次页面失败: %s" % exc)
        return page

    def remember(self, page: Any) -> None:
        try:
            url = page.url or ""
        except Exception:
            return
        if url and url != "about:blank" and url != self._last_saved_url:
            remember_last_page(url)
            self._last_saved_url = url

    # -- 收尾 ---------------------------------------------------------------
    def stop(self) -> None:
        if self.playwright is None:
            return
        try:
            if self.owns_browser and self.context is not None:
                self.context.close()
        except Exception as exc:
            log("WARN context.close 失败: %s" % exc)
        try:
            # 只停 driver：connect 来的 Chrome 由外部拥有，断开连接不关浏览器
            self.playwright.stop()
        except Exception as exc:
            log("WARN playwright.stop 失败: %s" % exc)
        self.playwright = None


# --------------------------------------------------------------------------- #
# action 实现
# --------------------------------------------------------------------------- #


def _wait_settle(page: Any, cfg: Dict[str, Any], ms: Optional[int] = None) -> int:
    wait_ms = int(ms if ms is not None else cfg.get("settle_ms", 800))
    if wait_ms > 0:
        page.wait_for_timeout(clamp_ms(wait_ms))
    return wait_ms


def _goto(page: Any, url: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    nav_timeout = clamp_ms(int(cfg.get("navigate_timeout_ms", 45000)))
    try:
        resp = page.goto(url, wait_until="domcontentloaded", timeout=nav_timeout)
    except Exception as exc:
        msg = str(exc)
        hint = ""
        if "ERR_" in msg:
            hint = ("；若为 ERR_CONNECTION/ERR_TIMED_OUT 类错误，可在 private/browser.yaml 里把 "
                    "proxy_mode 改成 always（或 xb.py --proxy http://127.0.0.1:7897）重试")
        raise XBError("NAVIGATION_FAILED", "打开 %s 失败: %s%s" % (url, msg.splitlines()[0], hint))
    return {"status": resp.status if resp is not None else None, "_resp": resp}


def action_navigate(sess: BrowserSession, inp: Dict[str, Any]) -> Dict[str, Any]:
    url = str(inp.get("url") or "").strip()
    if not url:
        raise XBError("BAD_INPUT", "navigate 需要 input.url")
    page = sess.get_page(restore=False)
    info = _goto(page, url, sess.cfg)
    waited = _wait_settle(page, sess.cfg, inp.get("settleMs"))
    if inp.get("waitFor"):
        try:
            page.wait_for_selector(str(inp["waitFor"]), timeout=clamp_ms(8000))
        except Exception:
            log("waitFor 未命中: %s" % inp["waitFor"])
    sess.remember(page)
    return {
        "url": page.url,
        "title": page.title(),
        "status": info["status"],
        "settle_ms": waited,
        "replaced_current_tab": bool(inp.get("replaceCurrentTab", True)),
    }


def action_open_tab(sess: BrowserSession, inp: Dict[str, Any]) -> Dict[str, Any]:
    url = str(inp.get("url") or "").strip()
    if not url:
        raise XBError("BAD_INPUT", "open_tab 需要 input.url")
    page = sess.context.new_page()
    info = _goto(page, url, sess.cfg)
    waited = _wait_settle(page, sess.cfg, inp.get("settleMs"))
    if inp.get("waitFor"):
        try:
            page.wait_for_selector(str(inp["waitFor"]), timeout=clamp_ms(8000))
        except Exception:
            log("waitFor 未命中: %s" % inp["waitFor"])
    sess.remember(page)
    return {
        "url": page.url,
        "title": page.title(),
        "status": info["status"],
        "settle_ms": waited,
        "tab_count": len(sess.pages()),
    }


def action_wait(sess: BrowserSession, inp: Dict[str, Any]) -> Dict[str, Any]:
    kind = str(inp.get("kind") or "timeout").lower()
    page = sess.get_page(restore=True)
    if kind == "timeout":
        ms = int(inp.get("timeout", 3000))
        if ms < 0:
            raise XBError("BAD_INPUT", "wait.timeout 必须 >= 0")
        real = clamp_ms(ms)
        page.wait_for_timeout(real)
        sess.remember(page)
        return {"kind": "timeout", "waited_ms": real, "requested_ms": ms, "url": page.url}
    if kind == "selector":
        selector = inp.get("selector")
        if not selector:
            raise XBError("BAD_INPUT", "wait kind=selector 需要 input.selector")
        timeout = clamp_ms(int(inp.get("timeout", 5000)))
        try:
            page.wait_for_selector(str(selector), timeout=timeout)
            found = True
        except Exception:
            found = False
        sess.remember(page)
        return {"kind": "selector", "selector": selector, "found": found,
                "waited_ms": timeout, "url": page.url}
    raise XBError("BAD_INPUT", "wait.kind 只支持 timeout / selector，收到 %r" % kind)


def _selector_hint(url: str) -> str:
    """选择器没命中时给出「为什么」的可判定提示，避免 cron 把两种原因混写。"""
    if "x.com" in (url or "") or "twitter.com" in (url or ""):
        return ("。X 未登录页面会剥离 data-testid（实测 0 个），likes/replies 必须登录后按手册 §8.5 "
                "读 [data-testid='like'] / [data-testid='reply'] 的 aria-label；"
                "也可能是页面还在加载（先 wait {\"kind\":\"timeout\",\"timeout\":3000} 再 query）")
    return "。可能原因：① 页面还没加载完（先 wait 再 query）② selector 与当前页面不符"


def _extract_first(page: Any, selector: str, timeout_ms: int = 3000) -> Any:
    loc = page.locator(selector)
    try:
        count = loc.count()
    except Exception as exc:
        raise XBError("BAD_INPUT", "selector 无效 %r: %s" % (selector, str(exc).splitlines()[0]))
    if count == 0 and timeout_ms > 0:
        try:
            page.wait_for_selector(selector, timeout=clamp_ms(timeout_ms))
            count = loc.count()
        except Exception:
            pass
    return loc, count


def _truncate(text: str, max_chars: int) -> Tuple[str, bool, int]:
    full_len = len(text)
    if max_chars and full_len > max_chars:
        return text[:max_chars], True, full_len
    return text, False, full_len


def action_query(sess: BrowserSession, inp: Dict[str, Any]) -> Dict[str, Any]:
    kind = str(inp.get("kind") or "text").lower()
    selector = inp.get("selector")
    page = sess.get_page(restore=True)
    max_chars = int(inp.get("maxChars") or (6000 if kind == "text" else 8000))
    max_matches = max(1, min(int(inp.get("maxMatches") or 5), 50))
    want_all = bool(inp.get("all"))

    if kind == "text":
        if not selector:
            body = page.inner_text("body")
            text, truncated, full_len = _truncate(body, max_chars)
            sess.remember(page)
            return {"kind": "text", "selector": None, "url": page.url, "title": page.title(),
                    "text": text, "length": full_len, "truncated": truncated, "match_count": 1}
        loc, count = _extract_first(page, str(selector))
        if count == 0:
            raise XBError(
                "SELECTOR_NOT_FOUND",
                "query kind=text 没匹配到 %r（url=%s）%s" % (selector, page.url, _selector_hint(page.url)),
            )
        if want_all:
            items = []
            for i in range(min(count, max_matches)):
                try:
                    items.append({"index": i, "text": loc.nth(i).inner_text()[:max_chars]})
                except Exception as exc:
                    items.append({"index": i, "error": str(exc).splitlines()[0]})
            sess.remember(page)
            return {"kind": "text", "selector": selector, "url": page.url, "title": page.title(),
                    "match_count": count, "items": items}
        text = loc.first.inner_text()
        text, truncated, full_len = _truncate(text, max_chars)
        sess.remember(page)
        return {"kind": "text", "selector": selector, "url": page.url, "title": page.title(),
                "text": text, "length": full_len, "truncated": truncated, "match_count": count}

    if kind == "dom":
        if not selector:
            raise XBError("BAD_INPUT", "query kind=dom 需要 input.selector")
        loc, count = _extract_first(page, str(selector))
        if count == 0:
            raise XBError(
                "SELECTOR_NOT_FOUND",
                "query kind=dom 没匹配到 %r（url=%s）%s" % (selector, page.url, _selector_hint(page.url)),
            )
        matches = []
        for i in range(min(count, max_matches)):
            el = loc.nth(i)
            try:
                html = el.evaluate("e => e.outerHTML")
                attrs = el.evaluate(
                    "e => Object.fromEntries(Array.from(e.attributes).map(a => [a.name, a.value]))"
                )
                try:
                    txt = el.inner_text()[:300]
                except Exception:
                    txt = ""
            except Exception as exc:
                matches.append({"index": i, "error": str(exc).splitlines()[0]})
                continue
            matches.append({
                "index": i,
                "tag": el.evaluate("e => e.tagName.toLowerCase()"),
                "aria_label": attrs.get("aria-label"),
                "testid": attrs.get("data-testid"),
                "text": txt,
                "attributes": attrs,
                "html": html[:1200],
                "html_length": len(html),
            })
        first_html = matches[0].get("html", "") if matches and "html" in matches[0] else ""
        first_html, truncated, full_len = _truncate(first_html, max_chars)
        sess.remember(page)
        return {
            "kind": "dom",
            "selector": selector,
            "url": page.url,
            "title": page.title(),
            "match_count": count,
            "aria_label": matches[0].get("aria_label") if matches else None,
            "html": first_html,
            "html_length": full_len,
            "truncated": truncated,
            "matches": matches,
        }

    if kind == "semantic":
        # 按可见文字找可点元素的 ref（兼容旧 mcp_browser 的 kind=semantic）
        text = str(inp.get("text") or inp.get("query") or "").strip()
        if not text:
            raise XBError("BAD_INPUT", "query kind=semantic 需要 input.text（可见文字）")
        candidates = []
        try:
            handles = page.get_by_role("button").all()
        except Exception:
            handles = []
        for i, h in enumerate(handles[:200]):
            try:
                label = (h.inner_text() or "").strip()
                aria = h.get_attribute("aria-label") or ""
            except Exception:
                continue
            if text.lower() in (label + " " + aria).lower():
                candidates.append({"index": i, "text": label[:120], "aria_label": aria,
                                   "ref": store_ref("role=button", i)})
                if len(candidates) >= max_matches:
                    break
        sess.remember(page)
        return {"kind": "semantic", "url": page.url, "text": text,
                "match_count": len(candidates), "matches": candidates}

    raise XBError("BAD_INPUT", "query.kind 只支持 text / dom / semantic，收到 %r" % kind)


def action_inspect(sess: BrowserSession, inp: Dict[str, Any]) -> Dict[str, Any]:
    selector = inp.get("selector")
    if not selector:
        raise XBError("BAD_INPUT", "inspect 需要 input.selector")
    page = sess.get_page(restore=True)
    loc, count = _extract_first(page, str(selector))
    if count == 0:
        raise XBError("SELECTOR_NOT_FOUND", "inspect 没匹配到 %r（url=%s）" % (selector, page.url))
    max_items = max(1, min(int(inp.get("maxMatches") or 10), 50))
    elements = []
    for i in range(min(count, max_items)):
        el = loc.nth(i)
        try:
            attrs = el.evaluate(
                "e => Object.fromEntries(Array.from(e.attributes).map(a => [a.name, a.value]))"
            )
            try:
                text = (el.inner_text() or "")[:200]
            except Exception:
                text = ""
            elements.append({
                "ref": store_ref(str(selector), i),
                "tag": el.evaluate("e => e.tagName.toLowerCase()"),
                "text": text,
                "aria_label": attrs.get("aria-label"),
                "attributes": attrs,
                "visible": bool(el.is_visible()),
            })
        except Exception as exc:
            elements.append({"ref": store_ref(str(selector), i), "error": str(exc).splitlines()[0]})
    sess.remember(page)
    return {"url": page.url, "selector": selector, "match_count": count, "elements": elements}


def _locator_for(page: Any, inp: Dict[str, Any]) -> Tuple[Any, Dict[str, Any]]:
    ref = inp.get("ref")
    selector = inp.get("selector")
    if ref:
        sel, idx = resolve_ref(str(ref))
        loc = page.locator(sel).nth(idx)
        return loc, {"selector": sel, "index": idx, "ref": ref}
    if not selector:
        raise XBError("BAD_INPUT", "需要 input.selector 或 input.ref")
    idx = int(inp.get("index") or 0)
    return page.locator(str(selector)).nth(idx), {"selector": str(selector), "index": idx}


def action_click(sess: BrowserSession, inp: Dict[str, Any]) -> Dict[str, Any]:
    page = sess.get_page(restore=True)
    loc, meta = _locator_for(page, inp)
    try:
        count = page.locator(meta["selector"]).count()
    except Exception as exc:
        raise XBError("BAD_INPUT", "selector 无效 %r: %s" % (meta["selector"], exc))
    if count == 0:
        raise XBError("SELECTOR_NOT_FOUND", "click 没匹配到 %r（url=%s）" % (meta["selector"], page.url))
    try:
        loc.scroll_into_view_if_needed(timeout=clamp_ms(5000))
        loc.click(timeout=clamp_ms(int(inp.get("timeout") or 8000)))
    except Exception as exc:
        raise XBError("ACTION_FAILED", "click 失败 %r: %s" % (meta["selector"], str(exc).splitlines()[0]))
    waited = _wait_settle(page, sess.cfg, inp.get("settleMs", 400))
    sess.remember(page)
    return {"url": page.url, "title": page.title(), "clicked": meta, "settle_ms": waited}


def action_fill(sess: BrowserSession, inp: Dict[str, Any]) -> Dict[str, Any]:
    if "text" not in inp:
        raise XBError("BAD_INPUT", "fill 需要 input.text")
    text = inp["text"]
    if not isinstance(text, str):
        text = str(text)
    page = sess.get_page(restore=True)
    loc, meta = _locator_for(page, inp)
    try:
        count = page.locator(meta["selector"]).count()
    except Exception as exc:
        raise XBError("BAD_INPUT", "selector 无效 %r: %s" % (meta["selector"], exc))
    if count == 0:
        raise XBError("SELECTOR_NOT_FOUND", "fill 没匹配到 %r（url=%s）" % (meta["selector"], page.url))
    try:
        loc.scroll_into_view_if_needed(timeout=clamp_ms(5000))
        loc.fill(text, timeout=clamp_ms(int(inp.get("timeout") or 10000)))  # fill 会自动清空
    except Exception as exc:
        raise XBError("ACTION_FAILED", "fill 失败 %r: %s" % (meta["selector"], str(exc).splitlines()[0]))
    try:
        value_len = len(loc.input_value(timeout=clamp_ms(3000)))
    except Exception:
        value_len = -1
    sess.remember(page)
    return {"url": page.url, "target": meta, "filled_chars": len(text),
            "value_len": value_len, "cleared_before_fill": True}


_KEY_MAP = {
    "cmd": "Meta", "command": "Meta", "meta": "Meta", "super": "Meta",
    "ctrl": "Control", "control": "Control",
    "opt": "Alt", "option": "Alt", "alt": "Alt", "shift": "Shift",
    "return": "Enter", "enter": "Enter", "esc": "Escape", "escape": "Escape",
    "backspace": "Backspace", "tab": "Tab", "space": "Space", "spacebar": "Space",
    "delete": "Delete", "del": "Delete", "home": "Home", "end": "End",
    "pageup": "PageUp", "pagedown": "PageDown",
    "up": "ArrowUp", "down": "ArrowDown", "left": "ArrowLeft", "right": "ArrowRight",
    "arrowup": "ArrowUp", "arrowdown": "ArrowDown", "arrowleft": "ArrowLeft",
    "arrowright": "ArrowRight",
}


def normalize_key(key: str) -> str:
    parts = [p for p in re.split(r"\+", str(key).strip()) if p]
    if not parts:
        raise XBError("BAD_INPUT", "press 需要非空 input.key")
    out: List[str] = []
    for i, part in enumerate(parts):
        low = part.strip().lower()
        if low in _KEY_MAP:
            out.append(_KEY_MAP[low])
        elif len(part) == 1:
            out.append(part)          # 单字符（字母/符号）原样
        else:
            out.append(part)          # F1 / Insert 等直接交给 Playwright
    return "+".join(out)


def action_press(sess: BrowserSession, inp: Dict[str, Any]) -> Dict[str, Any]:
    key = inp.get("key")
    if not key:
        raise XBError("BAD_INPUT", "press 需要 input.key（如 \"Meta+Enter\" / \"Enter\"）")
    normalized = normalize_key(str(key))
    page = sess.get_page(restore=True)
    if inp.get("selector"):
        loc, meta = _locator_for(page, inp)
        if page.locator(meta["selector"]).count() == 0:
            raise XBError("SELECTOR_NOT_FOUND", "press 没匹配到 %r（url=%s）" % (meta["selector"], page.url))
        try:
            loc.click(timeout=clamp_ms(5000))  # 聚焦目标元素
        except Exception as exc:
            log("WARN press 前聚焦失败: %s" % str(exc).splitlines()[0])
    try:
        page.keyboard.press(normalized)
    except Exception as exc:
        raise XBError("ACTION_FAILED", "press %r 失败: %s" % (normalized, str(exc).splitlines()[0]))
    waited = _wait_settle(page, sess.cfg, inp.get("settleMs", 300))
    sess.remember(page)
    return {"url": page.url, "key": normalized, "requested_key": str(key), "settle_ms": waited}


def action_screenshot(sess: BrowserSession, inp: Dict[str, Any]) -> Dict[str, Any]:
    page = sess.get_page(restore=True)
    raw = inp.get("path")
    if raw:
        path = Path(str(raw)).expanduser()
        if not path.is_absolute():
            path = (ROOT / path).resolve()
    else:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        path = ROOT / "screenshots" / ("xb-%s.png" % stamp)
    path.parent.mkdir(parents=True, exist_ok=True)
    full_page = bool(inp.get("fullPage", False))
    try:
        page.screenshot(path=str(path), full_page=full_page, timeout=clamp_ms(10000))
    except Exception as exc:
        raise XBError("ACTION_FAILED", "截图失败: %s" % str(exc).splitlines()[0])
    size = path.stat().st_size if path.exists() else 0
    sess.remember(page)
    try:
        rel = str(path.relative_to(ROOT))
    except Exception:
        rel = str(path)
    return {"path": str(path), "rel_path": rel, "bytes": size,
            "url": page.url, "title": page.title(), "full_page": full_page}


LOGIN_DETECT_JS = """
() => {
  const q = sel => document.querySelector(sel);
  const acc = q("[data-testid='SideNav_AccountSwitcher_Button']");
  const prof = q("[data-testid='AppTabBar_Profile_Link']");
  const composer = q("[data-testid='SideNav_NewTweet_Button']");
  const links = Array.from(document.querySelectorAll("a[href^='/']"));
  const profLink = links.find(a => (a.getAttribute('aria-label') || '').toLowerCase() === 'profile');
  const href = (prof && prof.getAttribute('href')) || (profLink && profLink.getAttribute('href')) || null;
  const accText = acc ? acc.innerText : "";
  const hasLoginCta = !!Array.from(document.querySelectorAll("a,span,div"))
      .find(e => /^(log in|sign up|登录|注册)$/i.test((e.innerText || '').trim()));
  return {
    account_switcher: !!acc,
    profile_link: !!prof,
    composer: !!composer,
    profile_href: href,
    account_text: accText,
    login_cta: hasLoginCta,
    body_head: (document.body ? document.body.innerText : "").slice(0, 400)
  };
}
"""


def _detect_login(page: Any, context: Any) -> Dict[str, Any]:
    final_url = page.url or ""
    login_wall = any(h in final_url for h in LOGIN_URL_HINTS)
    cookies = []
    try:
        cookies = context.cookies(["https://x.com", "https://twitter.com"])
    except Exception as exc:
        log("WARN 读 cookie 失败: %s" % exc)
    has_auth = any(c.get("name") == "auth_token" and (c.get("value") or "") for c in cookies)
    has_ct0 = any(c.get("name") == "ct0" and (c.get("value") or "") for c in cookies)
    try:
        dom = page.evaluate(LOGIN_DETECT_JS)
    except Exception as exc:
        log("WARN DOM 探测失败: %s" % exc)
        dom = {}
    dom_signal = bool(dom.get("account_switcher") or dom.get("profile_link") or dom.get("composer"))
    handle = None
    href = dom.get("profile_href") or ""
    if href:
        seg = href.strip("/").split("/")[0].split("?")[0]
        if seg and not seg.startswith("i"):
            handle = "@" + seg
    if not handle:
        m = re.search(r"@([A-Za-z0-9_]{2,20})", dom.get("account_text") or "")
        if m:
            handle = "@" + m.group(1)
    logged_in = (has_auth or dom_signal) and not login_wall
    if logged_in and handle is None:
        log("已登录但没解析出 handle（DOM 里没有 profile 链接）")
    log("login detect: url=%s auth=%s ct0=%s dom=%s wall=%s"
        % (final_url, has_auth, has_ct0, dom_signal, login_wall))
    return {
        "logged_in": bool(logged_in),
        "handle": handle,
        "url": final_url,
        "_debug": {"has_auth_token": has_auth, "has_ct0": has_ct0,
                   "dom_signal": dom_signal, "login_wall": login_wall,
                   "profile_href": href, "cookie_names": sorted({c.get("name", "") for c in cookies})},
    }


XHS_DETECT_JS = """
() => {
  const txt = document.body ? document.body.innerText : "";
  const pwd = !!document.querySelector("input[type='password']");
  const loginWords = ["扫码登录", "手机号登录", "登录后", "请登录", "登录/注册", "Log in", "Sign in"];
  const hitWords = loginWords.filter(w => txt.includes(w));
  const nameEl = document.querySelector(".user-name, .name-box, [class*='user-name']");
  return {
    password_field: pwd,
    login_words: hitWords,
    user_name: nameEl ? nameEl.innerText.trim() : "",
    body_head: txt.slice(0, 300)
  };
}
"""


def _detect_xhs(page: Any) -> Dict[str, Any]:
    """小红书登录态（best-effort）。XHS 自动发布是禁止的，这里只做判定不做任何动作。"""
    url = page.url or ""
    try:
        dom = page.evaluate(XHS_DETECT_JS)
    except Exception as exc:
        log("WARN XHS DOM 探测失败: %s" % exc)
        dom = {}
    wall = bool(dom.get("password_field")) or bool(dom.get("login_words"))
    logged_in = ("creator.xiaohongshu.com" in url) and not wall
    handle = (dom.get("user_name") or "").strip() or None
    log("xhs login detect: url=%s wall=%s words=%s" % (url, wall, dom.get("login_words")))
    return {"logged_in": logged_in, "handle": handle, "url": url,
            "_debug": {"login_wall": wall, "login_words": dom.get("login_words"),
                       "user_name": dom.get("user_name")}}


def _probe_x_login(sess: BrowserSession, url: str) -> Dict[str, Any]:
    """在临时 tab 里探 /home，不动调用方当前页面。"""
    probe = None
    try:
        probe = sess.context.new_page()
        probe.set_default_timeout(int(sess.cfg.get("action_timeout_ms", 30000)))
        probe.set_default_navigation_timeout(int(sess.cfg.get("navigate_timeout_ms", 45000)))
        try:
            probe.goto(url, wait_until="domcontentloaded", timeout=clamp_ms(20000))
        except Exception as exc:
            log("WARN 探测页导航失败（继续用当前 DOM 判断）: %s" % str(exc).splitlines()[0])
        probe.wait_for_timeout(clamp_ms(2000, reserve=1500))
        return _detect_login(probe, sess.context)
    finally:
        if probe is not None:
            try:
                probe.close()
            except Exception:
                pass


def action_login_state(sess: BrowserSession, inp: Dict[str, Any]) -> Dict[str, Any]:
    """检测登录态。不执行任何登录动作。

    判定范围按「当前页面」走（和旧 mcp_browser 的语义一致）：
      * 当前页是 x.com / twitter.com → 用当前页 + cookie 判定
      * 当前页是 xiaohongshu.com       → XHS 分支（best-effort；XHS 自动发布本来就是禁止的）
      * 其它 / about:blank             → 临时 tab 探 https://x.com/home
      * input.url 显式指定             → 临时 tab 探那个 URL
    """
    explicit = str(inp.get("url") or "").strip()
    if explicit:
        result = _probe_x_login(sess, explicit)
    else:
        page = sess.get_page(restore=True)
        cur = page.url or ""
        if "x.com" in cur or "twitter.com" in cur:
            result = _detect_login(page, sess.context)
        elif "xiaohongshu.com" in cur:
            result = _detect_xhs(page)
        else:
            result = _probe_x_login(sess, "https://x.com/home")
    data = {"logged_in": result["logged_in"], "handle": result["handle"], "url": result["url"]}
    if os.environ.get("XB_DEBUG") == "1":
        data["_debug"] = result.get("_debug")
    return data


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

HANDLERS = {
    "navigate": action_navigate,
    "open_tab": action_open_tab,
    "wait": action_wait,
    "query": action_query,
    "inspect": action_inspect,
    "click": action_click,
    "fill": action_fill,
    "press": action_press,
    "screenshot": action_screenshot,
    "login_state": action_login_state,
}

USAGE = """\
用法:
  python3 scripts/browser/xb.py --action '<JSON>'

  --action JSON      单次 action，形状 {"action":"...","input":{...}}
  --action-file PATH 从文件读 action JSON（cron 里引号麻烦时用）
  --ensure           确保浏览器在跑并复用（默认已开启）
  --ephemeral        一次性模式：persistent context 起完就关（不杀已在跑的 CDP Chrome）
  --headless         无头（默认 headed）
  --headed           有头（默认）
  --timeout-ms N     本次调用的硬超时上限（默认取配置 action_timeout_ms=30000）
  --proxy URL        强制走代理，如 http://127.0.0.1:7897
  --no-proxy         本次不走代理
  --cdp URL          覆盖 CDP endpoint（优先于配置）
  --lock-wait-ms N   并发互斥等待上限（默认 min(10000, timeout-3000)）
  --config PATH      覆盖配置文件（默认 private/browser.yaml）
  --print-config     打印解析后的配置（调试用，stdout 为 JSON）
  --list-actions     列出支持的 action
  -h, --help

退出码: 0 成功 / 1 action 失败 / 2 浏览器不可用（BROWSER_UNAVAILABLE）
"""


def parse_args(argv: List[str]) -> Dict[str, Any]:
    args: Dict[str, Any] = {
        "action": None, "action_file": None, "ensure": False, "ephemeral": False,
        "headless": None, "timeout_ms": None, "proxy": None, "no_proxy": False,
        "cdp": None, "config": None, "print_config": False, "list_actions": False,
        "lock_wait_ms": None,
    }
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("-h", "--help"):
            sys.stderr.write(USAGE)
            emit_and_exit({"ok": True, "action": "help", "data": {"usage": USAGE}}, EXIT_OK)
        elif a == "--action":
            i += 1
            args["action"] = argv[i] if i < len(argv) else None
        elif a.startswith("--action="):
            args["action"] = a.split("=", 1)[1]
        elif a == "--action-file":
            i += 1
            args["action_file"] = argv[i] if i < len(argv) else None
        elif a.startswith("--action-file="):
            args["action_file"] = a.split("=", 1)[1]
        elif a == "--ensure":
            args["ensure"] = True
        elif a == "--ephemeral":
            args["ephemeral"] = True
        elif a == "--headless":
            args["headless"] = True
        elif a == "--headed":
            args["headless"] = False
        elif a == "--timeout-ms":
            i += 1
            args["timeout_ms"] = int(argv[i])
        elif a.startswith("--timeout-ms="):
            args["timeout_ms"] = int(a.split("=", 1)[1])
        elif a == "--proxy":
            i += 1
            args["proxy"] = argv[i] if i < len(argv) else None
        elif a.startswith("--proxy="):
            args["proxy"] = a.split("=", 1)[1]
        elif a == "--no-proxy":
            args["no_proxy"] = True
        elif a == "--lock-wait-ms":
            i += 1
            args["lock_wait_ms"] = int(argv[i])
        elif a.startswith("--lock-wait-ms="):
            args["lock_wait_ms"] = int(a.split("=", 1)[1])
        elif a == "--cdp":
            i += 1
            args["cdp"] = argv[i] if i < len(argv) else None
        elif a.startswith("--cdp="):
            args["cdp"] = a.split("=", 1)[1]
        elif a == "--config":
            i += 1
            args["config"] = argv[i] if i < len(argv) else None
        elif a.startswith("--config="):
            args["config"] = a.split("=", 1)[1]
        elif a == "--print-config":
            args["print_config"] = True
        elif a == "--list-actions":
            args["list_actions"] = True
        else:
            raise XBError("BAD_INPUT", "未知参数 %r（--help 看用法）" % a)
        i += 1
    return args


def load_request(args: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    raw = args["action"]
    if raw is None and args["action_file"]:
        try:
            raw = Path(args["action_file"]).expanduser().read_text(encoding="utf-8")
        except Exception as exc:
            raise XBError("BAD_INPUT", "读 --action-file 失败: %s" % exc)
    if raw is None:
        raise XBError("BAD_INPUT", "缺少 --action '<JSON>'（--help 看用法）")
    try:
        req = json.loads(raw)
    except Exception as exc:
        raise XBError("BAD_INPUT", "action JSON 解析失败: %s" % exc)
    if not isinstance(req, dict):
        raise XBError("BAD_INPUT", "action JSON 必须是对象，形如 {\"action\":\"...\",\"input\":{...}}")
    unknown = set(req) - {"action", "input"}
    if unknown:
        raise XBError("BAD_INPUT", "action JSON 有未知字段 %s；只支持 action / input" % sorted(unknown))
    name = req.get("action")
    if not name:
        raise XBError("BAD_INPUT", "action JSON 缺少 action 字段")
    if name not in HANDLERS:
        raise XBError("UNKNOWN_ACTION", "不支持的 action %r；支持: %s" % (name, ", ".join(ACTION_NAMES)))
    inp = req.get("input") or {}
    if not isinstance(inp, dict):
        raise XBError("BAD_INPUT", "input 必须是对象")
    return name, inp


# --------------------------------------------------------------------------- #
# 引导：playwright 不在当前解释器里就用 uv run 重新执行自己
# --------------------------------------------------------------------------- #


def _has_playwright(python_bin: str) -> bool:
    try:
        r = subprocess.run([python_bin, "-c", "import playwright.sync_api"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
        return r.returncode == 0
    except Exception:
        return False


def bootstrap_if_needed() -> None:
    if os.environ.get("XB_BOOTSTRAP") == "1":
        return
    try:
        import playwright.sync_api  # noqa: F401
        return
    except Exception:
        pass

    venv_py = HERE / ".venv" / "bin" / "python"
    if venv_py.is_file() and _has_playwright(str(venv_py)):
        os.execve(str(venv_py), [str(venv_py), str(SCRIPT)] + sys.argv[1:],
                  {**os.environ, "XB_BOOTSTRAP": "1"})

    uv = shutil.which("uv") or "/opt/homebrew/bin/uv"
    if Path(uv).is_file():
        argv = [uv, "run", "--no-project", "--quiet",
                "--with", "playwright", "--with", "pyyaml",
                "python3", str(SCRIPT)] + sys.argv[1:]
        os.execvpe(uv, argv, {**os.environ, "XB_BOOTSTRAP": "1"})

    emit_and_exit({"ok": False, "error": {"code": "BROWSER_UNAVAILABLE", "message": (
        "当前 Python 没有 playwright，也没找到 uv。安装：pip install playwright "
        "（无需下载浏览器，用 channel=chrome 复用系统 Chrome）；或用 uv run --with playwright python3 "
        "scripts/browser/xb.py ..."
    )}}, EXIT_BROWSER_UNAVAILABLE)


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #


def _safe_stop(sess: Optional[BrowserSession], exit_code: int) -> None:
    """清理浏览器连接；清理阶段最多再给 6 秒，卡住就直接退出（JSON 已经输出）。"""
    if sess is None:
        return
    try:
        signal.signal(signal.SIGALRM, lambda *_: os._exit(exit_code))
        signal.setitimer(signal.ITIMER_REAL, 6.0)
    except Exception:
        pass
    try:
        sess.stop()
    except Exception as exc:
        log("WARN stop 失败: %s" % exc)


def main(argv: List[str]) -> int:
    action_name: Optional[str] = None
    sess: Optional[BrowserSession] = None
    data: Optional[Dict[str, Any]] = None
    err: Optional[XBError] = None

    try:
        args = parse_args(argv)
        if args["list_actions"]:
            emit_and_exit({"ok": True, "action": "list_actions",
                           "data": {"actions": ACTION_NAMES,
                                    "shape": {"action": "...", "input": {}},
                                    "exit_codes": {"0": "ok", "1": "action_failed",
                                                   "2": "BROWSER_UNAVAILABLE"}}}, EXIT_OK)
        cfg = load_config(args["config"])
        if args["print_config"]:
            printable = {k: v for k, v in cfg.items() if not k.startswith("_")}
            printable["_config_path"] = cfg.get("_config_path")
            printable["headless"] = bool(args["headless"] if args["headless"] is not None
                                         else cfg.get("headless", False))
            emit_and_exit({"ok": True, "action": "print_config", "data": printable}, EXIT_OK)

        action_name, inp = load_request(args)

        headless = bool(args["headless"] if args["headless"] is not None
                        else cfg.get("headless", False))
        endpoint = (args["cdp"] or os.environ.get("XB_CDP") or str(cfg.get("cdp") or "")).strip() or None
        # 代理：--no-proxy > --proxy > 配置 proxy_mode
        proxy: Optional[str] = None
        if not args["no_proxy"]:
            mode = str(cfg.get("proxy_mode") or "auto").lower()
            if args["proxy"]:
                proxy = args["proxy"]
            elif mode == "always":
                proxy = str(cfg.get("proxy") or "") or None
        keepalive = not args["ephemeral"] or args["ensure"]

        timeout_ms = int(args["timeout_ms"] or os.environ.get("XB_TIMEOUT_MS")
                         or cfg.get("action_timeout_ms") or 30000)
        arm_hard_timeout(timeout_ms)

        log("start action=%s keepalive=%s headless=%s endpoint=%s proxy=%s timeout=%dms"
            % (action_name, keepalive, headless, endpoint, proxy, timeout_ms))

        lock_wait = int(args["lock_wait_ms"] if args["lock_wait_ms"] is not None
                        else min(10000, max(0, timeout_ms - 3000)))
        acquire_lock(lock_wait)

        sess = BrowserSession(cfg, keepalive=keepalive, headless=headless,
                              endpoint=endpoint, proxy=proxy, ephemeral=args["ephemeral"])
        sess.start()
        data = HANDLERS[action_name](sess, inp)
        exit_code = EXIT_OK
    except XBError as exc:
        err = exc
        exit_code = exc.exit_code
    except Exception as exc:
        log(traceback.format_exc())
        exit_code = EXIT_ACTION_FAILED
        err = XBError("ACTION_FAILED",
                      "%s: %s" % (type(exc).__name__,
                                  str(exc).splitlines()[0] if str(exc) else "未知异常"))

    # 先输出结果（cron 一定能读到），再清理进程，最后退出
    if err is not None:
        exit_code = emit_err(action_name, err)
    elif data is not None and action_name is not None:
        exit_code = emit_ok(action_name, data)
    else:
        exit_code = emit_err(action_name, XBError("ACTION_FAILED", "未产生结果（异常退出）"))
    _safe_stop(sess, exit_code)
    release_lock()
    return exit_code


if __name__ == "__main__":
    bootstrap_if_needed()
    os._exit(main(sys.argv[1:]))
