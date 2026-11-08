#!/usr/bin/env bash
# 開発コンテナを作った直後に 1 回走る(BL-265)。何度走らせてもよい(状態の確認にも使える)。
#   1. リポの .venv を、イメージの中の仮想環境 /opt/venv へのリンクにする
#   2. git の「持ち主が違う」警告を避ける(Mac のフォルダをマウントしているため)
#   3. 道具と行き先の簡単な確認を表示する(失敗しても止めない)
set -uo pipefail

REPO=/home/suzuki/ansible/CCNP01
cd "$REPO" || { echo "リポが見当たらない: $REPO"; exit 1; }

# 1. .venv
if [ -L .venv ]; then
  :
elif [ -e .venv ]; then
  echo "★ .venv がリンクでなく実体のフォルダになっている(別のマシンから写したもの?)。"
  echo "  mv .venv .venv.old してから、もう一度このスクリプトを走らせる。"
else
  ln -s /opt/venv .venv && echo ".venv → /opt/venv をリンクした"
fi

# 2. git
if [ -d .git ] && [ "$(stat -c %u .)" != "$(id -u)" ]; then
  git config --global --get-all safe.directory 2>/dev/null | grep -qxF "$REPO" \
    || git config --global --add safe.directory "$REPO"
fi

# 3. 確認
ok() { printf '  %-28s %s\n' "$1" "$2"; }
echo "== 道具"
ok "python" "$(/opt/venv/bin/python3 --version 2>&1)"
ok "pyats" "$(/opt/venv/bin/python3 -c 'import pyats, genie, unicon; from importlib.metadata import version; print(version("pyats"))' 2>&1 | tail -1)"
ok "ansible-core" "$(/opt/venv/bin/ansible --version 2>/dev/null | head -1)"
# pip の ansible にも junipernetworks.junos が同梱されている(版が古い)ので、名前を重複なしで数える
ok "collections" "$(/opt/venv/bin/ansible-galaxy collection list 2>/dev/null \
    | awk '{print $1}' | grep -xE 'cisco\.cml|juniper\.device|junipernetworks\.junos' | sort -u | wc -l) / 3"
ok "rclone" "$(rclone version 2>/dev/null | head -1)"

echo "== 行き先"
cml=$(sed -nE 's/^cml_host:[[:space:]]*"?([^"#[:space:]]+)"?.*/\1/p' group_vars/all/local.yml 2>/dev/null | head -1)
if [ -n "$cml" ]; then
  if timeout 5 bash -c "</dev/tcp/$cml/443" 2>/dev/null; then ok "CML $cml:443" "OK"; else ok "CML $cml:443" "届かない"; fi
else
  ok "CML" "group_vars/all/local.yml がまだ無い(pull-from-vm.sh で写す)"
fi
clab=$(sed -nE 's/^clab_host:[[:space:]]*"?([^"#[:space:]]+)"?.*/\1/p' group_vars/all/local.yml 2>/dev/null | head -1)
if [ -n "$clab" ]; then
  if timeout 5 bash -c "</dev/tcp/$clab/22" 2>/dev/null; then ok "containerlab $clab:22" "OK"; else ok "containerlab $clab:22" "届かない(停止中なら問題ない)"; fi
fi
[ -f "$HOME/.ssh/id_ed25519" ] && ok "~/.ssh/id_ed25519" "あり" || ok "~/.ssh/id_ed25519" "なし(pull-from-vm.sh で写す)"
[ -f "$HOME/.config/rclone/rclone.conf" ] && ok "rclone.conf" "あり" || ok "rclone.conf" "なし(pull-from-vm.sh で写す)"
exit 0
