#!/usr/bin/env bash
# ============================================================
# 教材コース(読み物+実践)のビルドと持ち出し(BL-246)。読み物の道具(read.sh / gen_reading.py)の薄い前段。
#
#   scripts/course.sh <コース> build          # 実践ページを課題文から起こして、各言語をビルド
#   scripts/course.sh <コース> sync           # ビルドして章ごとに束ね、Drive へ同期(各言語の book.yml の drive:)
#   scripts/course.sh <コース> serve          # ビルドしてポータル(8899 の Study Materials)で読む
#
# コース= courses/<名前>/。book.yml は 1 つ(lang: / alt_lang: の 2 言語の本)で、単元のページは言語ごとのフォルダ
# (en/・ja/)に同じファイル名で置く。ポータルでは 1 冊として載り、ページの中のボタンで言語が切り替わる(BL-248)。
# 実践ページ(課題文)は二重に持たない: 正本は problems/<ラボ ID>/task.en.md(英語)と task.md(日本語)。
# courses/<名前>/practice.yml の対応表に従って「## 単元の見出し」ごとに切り出し、読み物のページにする。
# ============================================================
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$REPO/.venv/bin/python3"
course="${1:-}"; cmd="${2:-}"
[ -n "$course" ] && [ -d "$REPO/courses/$course" ] && [ -n "$cmd" ] || { sed -n '2,12p' "${BASH_SOURCE[0]}"; exit 1; }
src="$REPO/courses/$course"

gen_practice() {
  "$PY" - "$REPO" "$src" <<'PYEOF'
import os, re, sys, yaml
repo, src = sys.argv[1], sys.argv[2]
spec = yaml.safe_load(open(os.path.join(src, "practice.yml"), encoding="utf-8"))
TASK = {"en": "task.en.md", "ja": "task.md"}
for lang, head in spec["intro"].items():
    for page in spec["pages"]:
        text = open(os.path.join(repo, "problems", page["problem"], TASK[lang]), encoding="utf-8").read()
        # 「## 見出し」で節に分ける(先頭の # 題名は捨てる)
        parts = re.split(r"(?m)^(?=## )", text)
        secs = {re.match(r"## (.+)", p).group(1).strip(): p for p in parts if p.startswith("## ")}
        want = [k for k in secs if any(k.startswith(pre) for pre in page["sections"][lang])]
        missing = [pre for pre in page["sections"][lang] if not any(k.startswith(pre) for k in secs)]
        if missing:
            sys.exit(f"{page['problem']} {TASK[lang]}: 節が見つからない {missing}")
        body = "\n".join(secs[k].rstrip() + "\n" for k in want)
        out = f"# {page['title'][lang]}\n\n{head.format(problem=page['problem']).strip()}\n\n{body}"
        with open(os.path.join(src, lang, page["file"]), "w", encoding="utf-8") as fh:
            fh.write(out)
        print(f"practice: {lang}/{page['file']} <- problems/{page['problem']}/{TASK[lang]} {want}")
PYEOF
}

case "$cmd" in
  build) gen_practice; "$REPO/scripts/read.sh" build "$src" ;;
  sync)  gen_practice; exec "$REPO/scripts/read.sh" sync "$src" ;;
  serve) gen_practice; "$REPO/scripts/read.sh" build "$src"; exec "$REPO/scripts/read.sh" serve ;;
  *) sed -n '2,12p' "${BASH_SOURCE[0]}"; exit 1 ;;
esac
