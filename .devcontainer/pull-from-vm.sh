#!/usr/bin/env bash
# 旧制御ホスト(VM)の作業環境を、この開発コンテナのホームへ写す(BL-265)。Mac の開発コンテナの中で走らせる。
#
#   .devcontainer/pull-from-vm.sh                 下見(何がどれだけ写るかを表示するだけ)
#   .devcontainer/pull-from-vm.sh --go            写す(1 回目。VM は動かしたままでよい)
#   .devcontainer/pull-from-vm.sh --go --final    切り替え直前の最終の写し。VM 側で消えたファイルはこちらでも消す
#   --with-images                                 ~/cml-images(CML へのイメージ登録用・約 900MB)も写す
#   --list                                        下見で、写るファイルを 1 行ずつ出す
#   --src USER@HOST:/home/suzuki/                 写す元(既定 suzuki@10.1.10.6:/home/suzuki/)
#   --dest DIR                                    写す先(既定 このコンテナのホーム。試しに別の場所へ写す時に使う)
#
# 写すもの:   リポ(ansible/CCNP01。git に入っていない private/・作業フォルダ・MGMT の貸出台帳・生成物も含む)、
#             ~/.ssh、~/.config/rclone、~/.claude と ~/.claude.json(Claude Code のメモリと設定)、シェルの設定
# 写さないもの: リポの .venv(x86 用。コンテナでは /opt/venv)、~/.local(x86 の rclone・claude)、~/.vscode-server、
#             ~/.nvm、Claude Code のログイン情報(.credentials.json。コンテナで改めてログインする)、
#             CCNP01 以外のプロジェクト(同じ VM のほかのフォルダ。移行済みか破棄済み)
#
# ★写している間は VM 側でもこちらでも作業しない。--final の前に VM の配信サーバ(pack.sh serve)を止める。
set -euo pipefail

src="suzuki@10.1.10.6:/home/suzuki/"
dest="$HOME/"
go=0; final=0; images=0; dest_given=0; list=0

usage() { sed -n '2,21p' "${BASH_SOURCE[0]}"; exit "${1:-1}"; }
while [ $# -gt 0 ]; do
  case "$1" in
    --go) go=1 ;;
    --final) final=1 ;;
    --with-images) images=1 ;;
    --list) list=1 ;;
    --src) src="${2:?--src の値がない}"; shift ;;
    --dest) dest="${2:?--dest の値がない}"; dest_given=1; shift ;;
    -h|--help) usage 0 ;;
    *) echo "知らないオプション: $1"; usage ;;
  esac
  shift
done
case "$src" in */) ;; *) src="$src/" ;; esac
case "$dest" in */) ;; *) dest="$dest/" ;; esac

# 旧制御ホストの上で自分のホームへ写す事故を防ぐ(コンテナの中か、--dest を明示した時だけ動く)。
if [ "$dest_given" = 0 ] && [ ! -f /.dockerenv ] && [ ! -f /run/.containerenv ]; then
  echo "コンテナの中ではないようなので止めた(写す先を明示するなら --dest DIR)。"; exit 2
fi

rules=$(mktemp); trap 'rm -f "$rules"' EXIT
{
  echo "- /ansible/CCNP01/.venv"
  echo "- __pycache__/"
  echo "- /.claude/.credentials.json"
  echo "- /.claude/ide/"
  echo "- /.claude/shell-snapshots/"
  echo "- /.claude/session-env/"
  echo "+ /ansible/"
  echo "+ /ansible/CCNP01/***"
  echo "+ /.ssh/***"
  echo "+ /.config/"
  echo "+ /.config/rclone/***"
  echo "+ /.claude/***"
  echo "+ /.claude.json"
  echo "+ /.bashrc"
  echo "+ /.profile"
  echo "+ /.bash_profile"
  echo "+ /.bash_history"
  [ "$images" = 1 ] && echo "+ /cml-images/***"
  echo "- *"
} > "$rules"

# 持ち主・グループは写さない(Mac のフォルダの上では付け替えられないことがある)。権限(600 等)は写す。
opts=(-a --no-o --no-g -h --filter=". $rules"
      -e "ssh -o StrictHostKeyChecking=accept-new")
[ "$final" = 1 ] && opts+=(--delete)
if [ "$go" = 1 ]; then
  opts+=(--info=stats1,progress2)
else
  opts+=(--dry-run --stats)
  [ "$list" = 1 ] && opts+=(--out-format=%n)
  echo "== 下見(まだ何も写していない。写すなら --go)"
fi
echo "   元: $src"
echo "   先: $dest"
[ "$final" = 1 ] && echo "   最終の写し: 元で消えたファイルは先でも消す"

mkdir -p "$dest"
rsync "${opts[@]}" "$src" "$dest"

if [ "$go" = 1 ] && [ "$dest_given" = 0 ]; then
  echo
  bash "$HOME/ansible/CCNP01/.devcontainer/post-create.sh"
  echo
  echo "次: Claude Code にログインし直す → 試運転(problems/_drafts/CTRL-HOST-MAC.design.md の §5)"
fi
