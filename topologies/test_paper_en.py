#!/usr/bin/env python3
"""紙面の英語版(BL-236 ③)のオフライン自己テスト。

リポの問題にも CML にも触らず、合成した原文と訳文で次を検証する:
  ・英語の目印(## Choices / (Choose two.) / Items to Match)を解答欄の部品が読める
  ・照合(paper_en.check)が、正しい訳文を通し、解けなくなる・誤採点になる食い違いを落とす
  ・照合を通らない訳文は描画に使われない(paper_en.presented が原文を返す)

実行: .venv/bin/python3 topologies/test_paper_en.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paper_en  # noqa: E402
import render_html as R  # noqa: E402

JA = """# 問題 20990101-001

> **本問は機器に接続せずに解答すること。追加の show 実行は認めない。**

## シナリオ

RT1 は 10.1.1.0/24 への経路を 2 台の隣接から学習しています。ホールド時間は 30 秒です。

```mermaid
graph LR
  A["RT1<br/>観測点"]
  A --- B["RT2"]
```

| 区間 | ネットワーク |
|---|---|
| RT1 ⇔ RT2（本線） | 10.0.12.0/30 |

```
RT1# show ip route 10.1.1.0
(出力なし)
 via 10.0.12.2, Ethernet0/0
```

1. `variance 2` を変更してはなりません。
2. 既存の隣接関係は維持されます。

## 設問

正しく述べられているものを、次のうちから 2 つ選択してください。

## 選択肢

A. RT2(10.0.12.2)経由の 1 本が搭載される

B. 経路は搭載されない

C. メトリックは 409600 である
"""

EN = """# Question 20990101-001

> **Answer this question without connecting to any device. No additional show commands may be run.**

## Scenario

RT1 learns the route to 10.1.1.0/24 from two neighbors. The hold time is 30 seconds.

```mermaid
graph LR
  A["RT1<br/>Observation point"]
  A --- B["RT2"]
```

| Link | Network |
|---|---|
| RT1 ⇔ RT2 (primary) | 10.0.12.0/30 |

```
RT1# show ip route 10.1.1.0
(no output)
 via 10.0.12.2, Ethernet0/0
```

1. Do not change `variance 2`.
2. The existing adjacencies are maintained.

## Question

Which two statements are true? (Choose two.)

## Choices

A. One route is installed: through RT2 (10.0.12.2).

B. No route is installed.

C. The metric is 409600.
"""

CLOZE_JA = """# 問題 20990101-002

## 設問

空欄 ①〜② に入る語句を、語群から 1 つずつ選択してください。

```
interface Tunnel0
 ［①］
```

この構成は Phase ［②］である。

## 選択肢

A. ip nhrp redirect

B. 3
"""

CLOZE_EN = """# Question 20990101-002

## Question

For each of the blanks ① through ②, select one term from the choices.

```
interface Tunnel0
 ［①］
```

This configuration is Phase ［②］.

## Choices

A. ip nhrp redirect

B. 3
"""

MATCH_JA = """# 問題 20990101-003

## 設問

左側の①〜②を、右側の A〜B から選択してください。

### 対応させる項目

| # | コマンド |
|---|------|
| ① | `maximum-paths 2` |
| ② | `metric weights 0 1 0 1 0 0` |

## 選択肢

A. ルータ コンフィギュレーション モード
B. アドレス ファミリ コンフィギュレーション モード
"""

MATCH_EN = """# Question 20990101-003

## Question

Match each of the commands ① through ② on the left with one of A through B on the right.

### Items to Match

| # | Command |
|---|------|
| ① | `maximum-paths 2` |
| ② | `metric weights 0 1 0 1 0 0` |

## Choices

A. router configuration mode
B. address family configuration mode
"""

FAILS = []


def expect(name, cond, detail=""):
    print(f"  {'ok  ' if cond else 'FAIL'} {name}{(' — ' + str(detail)) if detail and not cond else ''}")
    if not cond:
        FAILS.append(name)


def breaks(name, en, needle):
    """訳文を 1 か所壊したら、照合が needle を含む食い違いを出すこと。"""
    got = paper_en.check(JA, en)
    expect(f"落とす: {name}", any(needle in g for g in got), got)


def main():
    print("[英語の目印を解答欄の部品が読める]")
    expect("選択肢の記号", R.choice_letters(EN) == ["A", "B", "C"], R.choice_letters(EN))
    expect("選ぶ個数 (Choose two.)", R.pick_count(EN) == 2, R.pick_count(EN))
    expect("選ぶ個数 既定 1", R.pick_count(EN.replace(" (Choose two.)", "")) == 1)
    expect("数非明示 (Choose all that apply.)",
           R.pick_count(EN.replace("(Choose two.)", "(Choose all that apply.)")) == -1)
    expect("本文の Select 2 を拾わない",
           R.pick_count(EN.replace(" (Choose two.)", "").replace("30 seconds", "30 seconds. Select 2 paths")) == 1)
    expect("選択肢の本文", dict(R.choice_texts(EN))["B"] == "No route is installed.")
    expect("選択肢のカード化", 'class="choice"' in R.md_to_body(EN)[0])
    expect("## DHCP Options を選択肢の節と見なさない", not R.is_choices_head("## DHCP Options"))
    expect("空欄", [k for k, _ in R.blank_terms(CLOZE_EN)] == ["①", "②"])
    expect("対応付けの項目", [k for k, _ in R.match_terms(MATCH_EN)] == ["①", "②"])
    expect("対応付けの見出し", any(R.MATCH_HEAD_RE.match(l) for l in MATCH_EN.split("\n")))

    print("[正しい訳文は照合を通る]")
    for name, ja, en in (("選択形", JA, EN), ("穴埋め形", CLOZE_JA, CLOZE_EN), ("組合せ形", MATCH_JA, MATCH_EN)):
        got = paper_en.check(ja, en)
        expect(name, not got, got)

    print("[食い違いは落とす]")
    breaks("選択肢が 1 つ足りない", EN.replace("\nC. The metric is 409600.\n", "\n"), "選択肢の記号")
    breaks("選択肢の見出しが違う", EN.replace("## Choices", "## Options"), "選択肢の記号")
    breaks("選ぶ個数が落ちた", EN.replace(" (Choose two.)", ""), "選ぶ個数")
    breaks("アドレスの打ち間違い", EN.replace("10.1.1.0/24", "10.1.2.0/24"), "識別子")
    breaks("タイマ値を綴った", EN.replace("30 seconds", "thirty seconds"), "識別子")
    breaks("選択肢のアドレスが落ちた", EN.replace(" (10.0.12.2).", "."), "識別子")
    breaks("show 出力を書き換えた", EN.replace("via 10.0.12.2, Ethernet0/0", "via 10.0.12.2, Et0/0"), "原文どおり")
    breaks("コードブロックの行が減った", EN.replace("(no output)\n", ""), "行数")
    breaks("インラインコードを外した", EN.replace("`variance 2`", "the variance of 2"), "インラインコード")
    breaks("要件が 1 つ減った", EN.replace("2. The existing adjacencies are maintained.\n", ""), "番号付き項目")
    breaks("表の行が減った", EN.replace("| RT1 ⇔ RT2 (primary) | 10.0.12.0/30 |\n", ""), "表の行")
    breaks("日本語が残った", EN.replace("Observation point", "観測点"), "日本語")
    breaks("全角の括弧が残った", EN.replace("(primary)", "（primary）"), "日本語")
    got = paper_en.check(CLOZE_JA, CLOZE_EN.replace("Phase ［②］", "Phase 3"))
    expect("落とす: 空欄を埋めてしまった", any("空欄" in g for g in got), got)
    got = paper_en.check(MATCH_JA, MATCH_EN.replace("### Items to Match", "### Commands"))
    expect("落とす: 対応付けの見出しが違う", any("対応付け" in g for g in got), got)

    print("[1 桁の数は綴ってよい・20 ビット → 20-bit]")
    expect("2 台 → two neighbors", not paper_en.check(JA, EN))
    ja = JA.replace("ホールド時間は 30 秒です。", "ラベルは 20 ビットです。")
    en = EN.replace("The hold time is 30 seconds.", "The label is a 20-bit field.")
    expect("20-bit", not paper_en.check(ja, en), paper_en.check(ja, en))

    print("[照合を通らない訳文は使われない]")
    with tempfile.TemporaryDirectory() as repo:
        os.makedirs(os.path.join(repo, "questions", "en"))
        src = "questions/20990101-001.md"
        with open(os.path.join(repo, src), "w", encoding="utf-8") as fh:
            fh.write(JA)
        expect("未訳 → 原文", paper_en.presented(repo, src) == src and paper_en.status(repo, src)[0] == "missing")
        enp = os.path.join(repo, paper_en.en_path(src))
        with open(enp, "w", encoding="utf-8") as fh:
            fh.write(EN.replace("10.1.1.0/24", "10.1.2.0/24"))
        expect("食い違い → 原文", paper_en.presented(repo, src) == src and paper_en.status(repo, src)[0] == "ng")
        with open(enp, "w", encoding="utf-8") as fh:
            fh.write(EN)
        expect("OK → 英語版", paper_en.presented(repo, src) == "questions/en/20990101-001.md")
        expect("日本語指定 → 原文", paper_en.presented(repo, src, "ja") == src)

    print(f"\n{'全部 ok' if not FAILS else 'FAIL: ' + ', '.join(FAILS)}")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
