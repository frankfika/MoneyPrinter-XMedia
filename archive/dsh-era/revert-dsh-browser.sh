#!/bin/bash
# 一键回滚「给 desktop profile 挂内置浏览器」这一步改动。
#
# 什么时候用：重启 DSH 后如果起不来 / 报错 / 浏览器工具异常，在**终端**里跑这个，然后再开 DSH。
#   bash /Users/fangchen/shortbot/scripts/revert-dsh-browser.sh
#
# 它做的事：把 desktop profile 的 package.json 和 cordis.patch.yml 还原成挂浏览器之前的版本。
set -euo pipefail

P="$HOME/.dsh/profiles/desktop"
ok=0

# 2026-10-29 起优先用 .bak-20261029-before-browser3：
# 它是「去掉浏览器条目、但保留此后新增配置」的快照（例如 volces-agent-plan provider），
# 回滚语义不变（仍然移除内置浏览器），但不会再把后来加的 provider 一起冲掉。
# 旧的 .bak-20261026-before-browser2 保留作兜底。
for f in package.json cordis.patch.yml; do
  restored=""
  for bak in ".bak-20261029-before-browser3" ".bak-20261026-before-browser2"; do
    src="$P/$f$bak"
    if [ -f "$src" ]; then
      cp "$src" "$P/$f"
      echo "restored $f  <- $(basename "$src")"
      restored=1
      break
    fi
  done
  if [ -z "$restored" ]; then
    echo "WARN: 备份不存在: $P/$f.bak-20261029-before-browser3 (及旧备份)" >&2
  else
    ok=1
  fi
done

if [ "$ok" = "1" ]; then
  echo
  echo "已回滚。现在重开 DSH："
  echo "  osascript -e 'quit app \"DeepSeek Harness\"' ; open -a 'DeepSeek Harness'"
else
  echo "没有可用的备份，未做任何修改。" >&2
  exit 1
fi
