#!/usr/bin/env python3
"""自動化ラボの穴埋め生成器（どこを穴にするかを seed でランダム化）。

problems/<ID>/controller_solution/ (完成形 tasks/handlers) ＋ controller/ (配布の土台:
ansible.cfg/hosts.ini/host_vars/site.yml 等) ＋ blanks.yml (穴候補) から、
--seed で --count 個の候補を選び、その箇所だけ __FILL_n__ にした配布物を生成する。

採点は最終状態のみ(手段非依存)なので、どこを穴にしても正解は不変。
つまり「同じ問題・同じ採点」のまま、穴の位置と数だけを seed で変えられる。

使い方:
  gen_blanks.py --repo . --problem ENCOR-AUTO-OSPF-ROLE-01 --seed 42 [--count 4] --out lab/<ID>
出力:
  <out>/...            完成形を土台に、選ばれた箇所だけ __FILL_i__ に置換した workspace
  <out>/穴.md          穴のヒント一覧(番号→ファイル→ヒント)
  <out>/_answers.json  穴の答え(解説・確認用)
"""
import argparse
import json
import os
import random
import shutil

import yaml


def replace_nth(text, find, repl, occurrence):
    """text 中の find の occurrence 番目(1始まり)だけを repl に置換。"""
    parts = text.split(find)
    if len(parts) - 1 < occurrence:
        raise SystemExit(f"[gen_blanks] '{find}' が {occurrence} 回見つかりません")
    left = find.join(parts[:occurrence])
    right = find.join(parts[occurrence:])
    return left + repl + right


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--problem", required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--count", type=int, default=0, help="穴の数(0=全候補)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    pdir = f"{a.repo}/problems/{a.problem}"
    sol = f"{pdir}/controller_solution"
    doc = yaml.safe_load(open(f"{pdir}/blanks.yml", encoding="utf-8"))
    spec = doc["blanks"]
    default_count = int(doc.get("default_count", 0))

    # 1) 土台: controller/ をコピー → solution(完成形 tasks/handlers)で上書き = 完成 workspace
    if os.path.exists(a.out):
        shutil.rmtree(a.out)
    shutil.copytree(f"{pdir}/controller", a.out)
    for root, _, files in os.walk(sol):
        for fn in files:
            rel = os.path.relpath(os.path.join(root, fn), sol)
            dst = os.path.join(a.out, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy(os.path.join(root, fn), dst)

    # 2) seed で穴にする候補を選ぶ
    rng = random.Random(a.seed)
    n = len(spec)
    k = a.count if a.count > 0 else (default_count if default_count > 0 else n)
    k = max(1, min(k, n))
    chosen = sorted(rng.sample(range(n), k))

    # 3) 選ばれた箇所を __FILL_i__ に置換（番号は出現順=ファイル内の位置順で振り直す）
    #    まず (file, occurrence, ...) を解決してから、ファイル/行頭位置でソートして採番。
    picks = [spec[i] for i in chosen]

    answers = []
    # ファイルごとに処理（同一ファイル内の複数置換に対応）
    by_file = {}
    for b in picks:
        by_file.setdefault(b["file"], []).append(b)

    # 仮番号で全置換 → 最後に登場順で振り直すのは複雑なので、
    # ここでは「候補定義(blanks.yml)の順序」で番号を振る（安定・分かりやすい）。
    numbered = sorted(picks, key=lambda b: spec.index(b))
    fill_no = {id(b): i + 1 for i, b in enumerate(numbered)}

    for fpath, items in by_file.items():
        full = os.path.join(a.out, fpath)
        text = open(full, encoding="utf-8").read()
        # 同じ find を複数 occurrence 穴にする場合、先に小さい occurrence を置換すると
        # 後続(大きい occurrence)がずれる → occurrence の大きい順に置換して衝突回避。
        for b in sorted(items, key=lambda b: -b.get("occurrence", 1)):
            i = fill_no[id(b)]
            blank = b["blank"].replace("____", f"__FILL_{i}__")
            text = replace_nth(text, b["find"], blank, b.get("occurrence", 1))
        open(full, "w", encoding="utf-8").write(text)

    for b in numbered:
        i = fill_no[id(b)]
        answers.append({"n": i, "file": b["file"],
                        "answer": b["answer"], "hint": b["hint"]})

    # 4) 穴.md（ヒント一覧）と _answers.json を書く
    md = [f"# 穴の一覧（seed={a.seed} / {len(answers)}個）\n",
          "下の `__FILL_n__` を埋めてください（答えは見ないこと）。\n",
          "| 穴 | ファイル | ヒント |", "|----|----------|--------|"]
    for ans in answers:
        md.append(f"| __FILL_{ans['n']}__ | `{ans['file']}` | {ans['hint']} |")
    md.append("")
    open(os.path.join(a.out, "穴.md"), "w", encoding="utf-8").write("\n".join(md))
    json.dump({"seed": a.seed, "answers": answers},
              open(os.path.join(a.out, "_answers.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    print(f"[gen_blanks] {a.problem} seed={a.seed}: {len(answers)}個の穴 "
          f"({', '.join('FILL_%d=%s' % (x['n'], x['answer']) for x in answers)})")


if __name__ == "__main__":
    main()
