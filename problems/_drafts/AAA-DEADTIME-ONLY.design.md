# BL-105 実装計画 — 紙面 `shape=aaa` に故障種 `deadtime_only` を追加する

状態: **完了(2026-08-10)。S0〜S3 実施済み・出題可。**
上位= [AAA-BASE.design.md](AAA-BASE.design.md) / 実測の正典= [poc/aaa/README.md](../../poc/aaa/README.md) §19.3・§19.8

## 1. 作るもの

故障種 `deadtime_only`（15 → 16 種目）。

**`deadtime` は書いてあるが `radius-server dead-criteria` が無い構成。**
サーバが応答しなくなっても「死んだ」と判定されないため、`deadtime` の出番が永久に来ない。

実測(§19.3・片系断のまま連続ログイン):

| dead-criteria | 1回目 | 2回目 | 3回目 |
|---|---|---|---|
| 無し | 6.3s | 6.3s | 6.4s（**永久に速くならない**） |
| `time 5 tries 1` | 6.4s | 3.3s | **0.3s** |

このファミリが既に持つ「**書いたのに効かない**」型の一員（`list_undefined` = 未定義リスト参照は
default へ落ちる no-op、`authz_if_authenticated` = 認可は通るが属性が降りない、と同族）。

## 2. 設計上の中心問題

**`aaa_model.py` は意図的に時間を持たない**（AAA-BASE §6 のレビュー決定。4 値＋理由のみ、
秒数は `delay_seconds()` の式で出す）。ところが本故障種の症状は**時間の推移**そのもの。
「1 回目は遅い」だけでは健全な片系断と区別できず、**「2 回目以降も遅いまま」**が指紋になる。

→ モデルに状態機械（DEAD の記録・deadtime の経過）を持ち込むのは方針違反かつ危険。
**式を 2 本にするだけで表現できる**ので、そうする。

```
1 回目   = timeout × (retransmit+1) × 到達不能サーバ数        （現行の delay_seconds）
2 回目以降 = dead_criteria が有る  → 0（当該サーバを飛ばす）
             dead_criteria が無い → 1 回目と同じ
```

状態を持たず、boolean 1 個で分岐する。**モデルは時間を持たないままでいられる。**

## 3. ★前提として直すもの 2 件（本題より先）— **実施済み 2026-08-10**

裏取り= [poc/aaa/README.md](../../poc/aaa/README.md) §19.9 / `results-deadstate.md`。
片系断のまま連続 4 回ログインして毎回 State を採り、**判定条件が無ければ 4 回とも
`current UP` のまま**・有れば 1 回目の直後に DEAD、を確認した。両件とも修正済み。

### 3.1 健全な盤面が `dead-criteria` を持っていない

現行モデルには dead-criteria の概念が無い＝**すべての既存盤面が実質「dead-criteria 無し」**。
このまま故障種だけ足すと、健全盤面と `deadtime_only` が同一になり成立しない。

→ `_base()` / `build()` の健全側に `dev["dead_criteria"] = True` を持たせ、
構成描画にも `radius-server dead-criteria time <t> tries <n>` を出す。
**既存の全 aaa 問題の設定抜粋のテキストが 1 行増える**（影響範囲はここが最大）。

### 3.2 `show aaa servers` の UP/DEAD 表示が実測と逆

`aaa_servers_block()` は「到達不能なら DEAD」と描いている(gen_paper_aaa.py 内)。
しかし実測では、**応答が無くなっただけではサーバは UP のまま**で、
dead-criteria を満たして初めて DEAD になる(§19.8 / P0 §5「RAD1 は UP のまま」)。

→ `DEAD` の条件を「到達不能 **かつ** dead_criteria」に改める。
**これは本故障種とは独立した既存の誤り**なので、単独でも直す価値がある。
直した結果、`show aaa servers` が本故障種の**第 2 の指紋**になる（下記 4.2）。

## 4. 観測チャネル

### 4.1 遅延の 2 値化（主）

trace 形の 1 行を 1 値から 2 値へ。

```
現行: 横浜: User was successfully authenticated. (約 6 秒)
新:   横浜: User was successfully authenticated. (1 回目 約 6 秒 / 2 回目 即時)
      横浜: User was successfully authenticated. (1 回目 約 6 秒 / 2 回目 約 6 秒)  ← deadtime_only
```

**全故障種で一律に 2 値にする**。片方の故障種でだけ表示形式が変わると、それ自体が道標になる
（`authz_no_fallback` の全断表を常設にしたときと同じ理由 = BL-103 の教訓）。

### 4.2 `show aaa servers` の状態（従）

3.2 を直すと、片系断のとき

- 健全: 応答しないサーバが **DEAD**
- `deadtime_only`: 応答しないのに **UP のまま**

evidence / dbgread 形で使える独立した指紋になる。

## 5. 載せる出題形・載せない出題形

| 形 | 可否 | 備考 |
|---|---|---|
| `trace` | ◎ | 本命。2 値の推移がそのまま設問になる |
| `read` | ◎ | 観測表 ＋ 構成から読ませる |
| `cause` | ◎ | 錯乱肢に「サーバが停止している」「タイマが長すぎる」を置ける |
| `evidence` | ◎ | **1 回目だけでは健全な片系断と区別できない** → 「次に取るべき観測」が本当に効く |
| `fix` | ○ | 正解= 判定条件の追加。錯乱肢= `deadtime` を伸ばす / `timeout` を縮める / サーバを直す |
| `dbgread` | △ | debug 上はタイムアウトの繰り返しで、他の無応答系と差が出にくい |
| `dbgconf` | △ | 同上。無理に載せない |
| `authread` | × | enable の遍歴とは無関係 |
| `patch` | × | 移行順序の話ではない |

## 6. 盤面の制約

**症状は「片系断のとき」にしか出ない**（両系生存なら誰も待たされない／全断なら local に落ちて
やはり推移が見えない）。

→ `deadtime_only` を引いたら `d["srv1_down"] = True` を強制する。
`authz_no_fallback` が `all_down` を必要としたのと同じ型の制約。
**全断の常設表とは矛盾しない**（常設表は別の仮定として出しているため）が、
「現在の稼働状態」欄と `srv1_down` が必ず連動していることを検算で担保する。

## 7. 区別不能ペアが 3 組目になる

既存 2 組（`key_mismatch` ↔ `src_iface_missing` / `list_not_applied` ↔ `list_undefined`）に加え、

**`deadtime_only` ↔ 健全 × 片系断** が「1 回のログインだけでは区別できない」ペアになる。

これは欠点ではなく **evidence 形の一等地**。ただし
「提示した選択肢の中で一意」の規約(P1a 知見③)を守るため、
2 回目の観測と `show aaa servers` を**同時に選択肢へ出さない**こと（どちらも決定的なので）。

## 8. 実装ステップ

| 段 | 内容 | 実機 |
|---|---|---|
| **S0** | `dev["dead_criteria"]` ／ `delay_pair()` を新設(`delay_seconds` は据え置き) → **完了** | 不要 |
| **S1** | ①健全盤面に dead-criteria ②DEAD 条件是正 ③**所要時間の行を `site_rows()` に常設**(trace だけでなく観測表そのものに入れた) → **完了** | 不要 |
| **S2** | `KINDS`(16) ／ `build()` 分岐 ／ `CLAIMS` ／ `FIXES`(`set_dead_criteria`) ／ `NEEDS_OUTAGE` に追加 → **完了** | 不要 |
| **S3** | 家族 3720/3720・authread 640/640・既出題4seed 不変・決定性 OK・全11shape OK → **完了** | 不要 |
| **S4** | 実機再確認（任意）: dead-criteria 有無での `show aaa servers` UP/DEAD を 1 回だけ撮り直す。§19.8 の未確定（`config-sg-radius` の `?`）と同時に取れば 1 セッションで済む → BL-108 と合流 | 要 |

S0〜S3 は実機不要。**S4 だけ BL-108 と束ねる**のが効率的。

## 9. リスク

1. **影響範囲が既存全問に及ぶ**（3.1 の構成 1 行追加・4.1 の trace 2 値化）。
   既出題の問題文とテキストが変わるが、**答えは変わらない**ことを回帰で確認する。
2. **2 値化が他の故障種の難易度を下げる恐れ**。
   「2 回目が即時」＝ dead-criteria が効いている、という情報を全問に配るため、
   無応答系（`key_mismatch` / `src_iface_missing` / `port_mismatch`）で
   「1 回目が遅い」以上の手掛かりを与えていないか、被覆エンジンで確認する。
3. **`dead-criteria` の値そのものを問う設問には踏み込まない**。
   `time` と `tries` の AND 条件・`timeout` との大小関係は実機ラボ（GEN-AAAGRP）側の題材。
   紙面では「有る／無い」の 2 値に留める（モデルを時間で汚さないため）。

## 10. 派生（本計画の対象外）

BL-108 が決着したら、**`timers_in_group`**（`timeout`/`retransmit` をグループ内に書いて効かない）
も同じ「書いたのに効かない」型として故障種にできる。症状は `deadtime_only` と似るが、
`show aaa servers` の実効値と debug の `Started N sec timeout` で分かれる。
ただし**紙面に載せる前に BL-108 の「仕様か parser の事故か」を確定させること**
（事故なら IOS のバージョン依存になり、紙面の恒久教材には向かない）。


---

## 11. 実装後の申し送り(2026-08-10)

- **観測の置き場所は trace 行ではなく `site_rows()` にした**。計画では trace 形だけ 2 値化する
  つもりだったが、それでは read / cause 形に症状が出ない。観測表そのものに常設した。
  結果、**`_obs_sig` にも自動的に入る**ので「提示と判定のずれ」も構造的に起きない。
- **代償**: 1 回目と 2 回目を常に両方見せるため、計画 §7 で期待した
  「1 回のログインだけでは健全な片系断と区別できない」という **evidence 形の一等地は消えた**
  (selftest の「区別できないペア」に `deadtime_only` は現れない)。
  2 値のうち片方だけを伏せる出題は作れるが、**観測の定義を 1 箇所に集約する規約と衝突する**
  ため見送った。必要になったら「観測の粒度」を選べる仕組みごと設計し直すこと。
- `delay_seconds()` は既存の呼び出し(モデルの selftest)のために残し、`delay_pair()` を新設した。
