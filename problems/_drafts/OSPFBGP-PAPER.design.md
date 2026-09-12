# OSPF→BGP 再配送の範囲(match オプション) 紙面ファミリ (BL-163)

定番題材派生。2026-09-12 実装・出題可。実装= `topologies/gen_paper_ospfbgp.py`
＋ `gen_paper_mcq.py --shape ospfbgp`。実測台帳= [poc/ospfbgp/README.md](../../poc/ospfbgp/README.md)。

## 1. 核心

**OSPF から BGP への再配送は、既定ではエリア内(O)とエリア間(O IA)だけが対象**で、
外部(O E1 / O E2)は `match external 1 external 2` を明示しないと入らない。
「結果の BGP テーブルから設定を逆算させる」形と相性が良い
（match 付きのコマンドを選ぶと、提示されたテーブルと矛盾する）。

既存の紙面 shape は BGP を **読解**(bgpdbg/bgpbest)と**選好**(pref)でしか扱っておらず、
**BGP への再配送**は空白だった。

## 2. 盤面（固定 4 ルータ・値は seed 抽選）

```
RCV(BGP のみ) ─ DUT(BGP + OSPF) ─ ABR(OSPF・ABR 兼 ASBR) ─ EDGE(RIP)
```
DUT の OSPF テーブルに 4 種が揃う: `O` / `O IA` / `O E1` / `O E2`
（＋ OSPF 区間の接続セグメントもエリア内経路として再配送対象になる）。

## 3. 状態モデル（実測の遷移規則をそのまま実装）

状態 = 集合 S ⊆ {internal, external 1, external 2}（空にならない）。

| 操作 | 結果 |
|---|---|
| `redistribute ospf P`（match 無し） | **S = {internal} にリセット**（★マージではない） |
| `redistribute ospf P match <集合>` | **S = S ∪ 指定**（★マージ・置換ではない） |
| `no redistribute ospf P match <集合>` | S = S − 指定（空なら {internal}） |

表示形は S == {internal} のときだけ素の `redistribute ospf P`。それ以外は
`match internal external 1 external 2` の順で並び、**既定だった internal も明示化**される。

4 状態 × 8 コマンド = 32 本を実機で全数計測して確定（PoC の遷移表）。
★このモデルがあるので、**fix 形の正解は「候補を適用して要件集合と一致するか」で
機械判定**でき、一意性が構成で保証される（正解が複数成立する場合は最短のみを残し、
他は選択肢に出さない）。

## 4. 要件世界（正解の反転）

| world | 要件 | 例（現状 → 正解） |
|---|---|---|
| `all` | 内部も外部も全部届ける | 既定 → `match external 1 external 2`（マージで internal は残る） |
| `internal_only` | 内部だけ（外部を注入しない） | `match internal external 1` → `no ... match external 1` |
| `ext1_only` | 外部タイプ 1 だけ | 既定 → **`no redistribute` してから** `match external 1`（★マージ回避） |

kind（現状）= `default_only` / `ext_only` / `int_ext1` / `ext2_only`。
既に要件を満たしている組合せは `draw` が弾く。

## 5. 出題形

- **fix**: 要件を満たす構成を選ぶ（選択肢は全て設定コマンド＝提示は常に cli 体裁）。
  ★最良のディストラクタ = **`redistribute ospf P`（match 無し）を出す**形。
  出典の「正解コマンド」に見えるが、**実機ではリセットされて外部が消える**。
- **cause**: 「なぜこの結果になるのか」。誤答には
  「既定では外部だけが対象」（逆）・「`subnets` が無い」（OSPF への再配送の話）・
  「`default-metric` が無い」（BGP では必須でない）を置く。
- **read**: 「この設定なら受信側の BGP テーブルはどうなるか」（表そのものを選ぶ）。
  要件は**出さない**（出すと「要件を満たす表」を選ぶ別の設問に化ける）。

## 6. 実装上の注意（詰まった点）

- 節の見出しは不親切化(BL-088)が拾う正規名でなければならない。
  独自の「## 提示された出力」に置くとフェンスが再構成で落ち、
  `_assert_no_loss` が発火する → **「## 現在の状態」**に置く。
- read 形の選択肢に自前でコードフェンスを付けると `render_options` が
  二重にフェンスして壊れる → 生のテキストを返す。
- mixed の配分は chain の 5% を割って **ospfbgp 3% / chain 2%** とした
  （chain は実機展開を伴い重い・ospfbgp は紙面専用で軽い）。全体の再配分はユーザ判断。

## 7. 検証

- fix 形の一意性: 全 kind × world × 5 seed で「正解ちょうど1つ」を機械検査。
- 生成: 12 本（fix 9 / cause 3）＋ exam 8 本（read 形の描画も確認）→
  正解の重複ゼロ・不親切化の不変条件 PASS。生成物は削除済み。
- ★盤面の数値は**すべて実機実測の写像**（メトリック・`* i`/`*>i` の別・表示形）。
