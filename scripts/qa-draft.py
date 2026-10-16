#!/usr/bin/env python3
"""
短文助手 · 单条草稿质检脚本
用法：python3 scripts/qa-draft.py outputs/<MMDD-slot>/<topic>/
退出码：0 = 全部通过，1 = 有红线命中
"""
import re, sys, pathlib, yaml

if len(sys.argv) != 2:
    print("usage: python3 qa-draft.py outputs/<dir>/")
    sys.exit(2)

d = pathlib.Path(sys.argv[1])
if not d.is_dir():
    print(f"ERR: {d} 不是目录"); sys.exit(2)

state = pathlib.Path("state")
fr = yaml.safe_load((state / "forbidden.yaml").read_text())
sx  = yaml.safe_load((state / "style-x.yaml").read_text())
sh  = yaml.safe_load((state / "style-xhs.yaml").read_text())

x_path  = d / "x.txt"
xh_path = d / "xhs.txt"
m_path  = d / "material.yaml"

problems = []

def check(label, ok, hint=""):
    mark = "✓" if ok else "✗"
    print(f"  {mark} {label}" + (f"  ({hint})" if hint else ""))
    if not ok: problems.append(label)

if m_path.exists():
    m = yaml.safe_load(m_path.read_text())
    print(f"━━━ material: {m.get('material_id', '?')} ━━━")
    print(f"  author: @{m['author']['handle']}  ·  post_id: {m['original'].get('post_id')}")
    print(f"  views: {m['metrics']['views']:,}")
    print(f"  treatment: {m.get('treatment_hint', '?')}")

print()

if x_path.exists():
    x_text = x_path.read_text()
    x_body = "\n".join(l for l in x_text.splitlines() if not l.startswith("#")).strip()
    print("━━━ x.txt 自检 ━━━")
    check("字数 ≥80", len(x_body) >= 80, f"实际 {len(x_body)}")
    check("字数 ≤500", len(x_body) <= 500, f"实际 {len(x_body)}")
    check("含数字", bool(re.search(r'\d', x_body)))
    check("含链接", 'x.com' in x_body or 'http' in x_body)
    n_hash = len(re.findall(r'#[^#\s]+', x_body))
    check("hashtag ≤1", n_hash <= 1, f"实际 {n_hash}")
    for phrase in sx['forbidden_phrases']:
        check(f"无「{phrase}」", phrase not in x_body)
    for c in fr['forbidden_content']:
        if c['scope'] and 'x' in c['scope']:
            keyword = c['id'].replace('no_', '').replace('_', ' ')
            check(f"无 {c['id']}", keyword.lower() not in x_body.lower())

print()

if xh_path.exists():
    xh_text = xh_path.read_text()
    lines = xh_text.splitlines()
    if not lines:
        print("ERR: xhs.txt 为空"); sys.exit(1)
    title = lines[0].strip()
    body = "\n".join(lines[1:]).strip()
    tags_line = lines[-1] if lines[-1].startswith('#') else ''
    tags = re.findall(r'#\s*[^\s#]+', tags_line) if tags_line else []

    print("━━━ xhs.txt 自检 ━━━")
    units = sum(1 if ord(c) > 0x4e00 else 0.5 for c in title if not c.isspace())
    check("标题 ≤20 单位", units <= 20, f"实际 {units}")
    check("正文 ≥300", len(body) >= 300, f"实际 {len(body)}")
    check("正文 ≤700", len(body) <= 700, f"实际 {len(body)}")
    check("标签 3~8 个", 3 <= len(tags) <= 8, f"实际 {len(tags)}")
    for phrase in sx['forbidden_phrases']:
        check(f"无「{phrase}」", phrase not in body)
    for c in fr['forbidden_content']:
        if c['scope'] and 'xhs' in c['scope']:
            keyword = c['id'].replace('no_', '').replace('_', ' ')
            check(f"无 {c['id']}", keyword.lower() not in body.lower())
    for term in sh['voice'].get('avoid_terms', []):
        check(f"无「{term}」", term not in body)

print()
shots = d / "screenshots"
if shots.is_dir():
    n = len(list(shots.glob("*.png")) + list(shots.glob("*.jpg")))
    check(f"≥2 张截图", n >= 2, f"实际 {n}")

print()
if problems:
    print(f"━━━ {len(problems)} 项失败 ━━━")
    sys.exit(1)
print("━━━ 全部 PASS ━━━")
