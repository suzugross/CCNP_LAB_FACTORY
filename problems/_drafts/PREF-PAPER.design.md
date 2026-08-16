# BL-127 紙面 経路選好ファミリ (shape=pref) 実装設計 — 2026-08-16

計画の親= [PAPER-3FAM-COPP-DMVPN-PREF.design.md](PAPER-3FAM-COPP-DMVPN-PREF.design.md) §0(共通原則)・§3。
本メモは **shape=pref の実装正典**。ENARSI v1.1 の **1.10.d(OSPF パス選好)** と
**1.9.c(EIGRP FD/FS/variance)** を1つの shape に統合する。

## 0. 着手時のユーザ判断(2026-08-16)

- **① shape は1本**: `--shape pref` に統合。OSPF系/EIGRP系は **kinds で分岐**する
  (モデル実装は `ospfpref_model.py` / `eigrpfs_model.py` の2ファイルに分けてよいが、
  shape・生成器・selftest・quota ジャンルは1本)。
- **③ mixed 配分**: 暫定枠でねじ込み、全体の再配分は後日まとめて検討する
  (= 本実装では「どこから削ったか」を最小限の注記に留め、配分の最適化はしない)。
- 進め方= 適宜ユーザに確認しながら段階実装。

## 1. 知識境界(§0-1 に従う)

| 範囲内(選択肢の正誤に使う) | 範囲外(解答 md の裏話のみ) |
|---|---|
| OSPF: intra > inter > E1 > E2 の**型優先**(コストより先) | LSA の詳細フォーマット・SPF タイマ |
| OSPF: E1 = 外部メトリック + ASBR までの内部コスト(累積) | Type-7→5 変換の P ビット詳細 |
| OSPF: E2 = 外部メトリック固定・同値時は **forward metric** で比較 | forwarding address が非0 の場合の再帰解決 |
| OSPF: N1/N2 の位置づけ(NSSA 内から見た型) | NSSA の no-summary/translator 選挙 |
| EIGRP: FD/RD/successor・**FC= RD < 現 successor の FD**(等号は不成立) | 複合メトリック K 値の変更・wide metric |
| EIGRP: FS の定義・variance は **FS のみ**を乗せる・倍率条件 | SIA・query スコープ(cause の裏話に留める) |
| 表示: `show ip route <pfx>` detail / `show ip eigrp topology (all-links)` の読解 | `traffic-share` の詳細配分アルゴリズム |

## 2. モデル(純関数・bgpbest 方式)

### 2.1 `ospfpref_model.py`

候補経路 dict のキー:

```
key      識別子("via RT02" 等)
kind     "intra" | "inter" | "e1" | "e2" | "n1" | "n2"
metric   int  表に出るメトリック(E2 は外部メトリックそのもの)
fwd      int  ASBR/ABR までの内部コスト(E2 の第2段・E1 では metric に既に含む)
ext      int  外部メトリック(E1 の内訳表示用・E2 では metric と同値)
rid      str  広告元 RID(最終タイブレークの決定化に使う)
```

決定リスト `STEPS = ["type", "metric", "fwd", "rid"]`。
- `type`: TYPE_RANK = intra(0) < inter(1) < e1(2) < n1(2) < e2(3) < n2(3)
  (N1/N2 は E1/E2 と同順位=NSSA 内から見た表示違い。同順位同士が同一盤面に
  混在する盤面は draw で排除する)
- `metric`: 小さいほう。E1 は累積後の値。
- `fwd`: **E2/N2 のみ**適用(forward metric 小)。
- `rid`: ECMP を避けるための決定化。**タイが `rid` まで落ちた盤面は
  `best(strict=True)` が ValueError**(実機は ECMP になり「1本を選ぶ」設問が壊れるため
  生成器が draw を捨てる。bgpbest の strict 拒否の踏襲)。

返り値= `{"winner": key, "step": 決め手の段, "elim": [(key, step), ...]}`。

### 2.2 `eigrpfs_model.py`

```
key   識別子("via RT02")
rd    Reported Distance(隣接が申告する距離)
cost  自分から隣接までのリンクコスト(= FD候補 = rd + cost)
```

- `fd(p) = p.rd + p.cost`(topology 表示の左値)
- `successor` = fd 最小(タイは key 順で決定化・タイ盤面は strict で拒否)
- `is_fs(p)` = `p.rd < fd(successor)` — **等号は FS でない**(P0 で実証する軸 E2)
- `variance_installed(paths, v)` = successor ∪ { p | is_fs(p) かつ fd(p) <= v * fd(successor) }
  **FC を満たさない経路は倍率をいくら上げても入らない**(ひっかけ核)

`all_fs(paths)` が **allthat 形(「FS になり得る経路をすべて選べ」)の正解集合**を返す。
FC は整数比較なので正解集合の機械検証が完全にできる= 数非明示形の理想的な導入先。

★**盤面妥当性(P0 で発見・`check_board()`)**: 非 FC の経路は RD が大きいほど、
隣接自身の最良経路が観測点経由に反転し、**スプリット・ホライズンで topology 表から
丸ごと消える**(PoC §11 の実測)。表に見せたい経路は
`FD_succ <= RD < FD_succ + 逆向きコスト` の窓に入っていなければならない。
窓を外れた draw は捨てる(紙面では描けても実機で再現できず E2E 照合が壊れる)。

## 3. kinds(8種・OSPF 4 / EIGRP 4)

| kind | 系 | 論点 | 主な誤答の型 |
|---|---|---|---|
| `type_intra` | OSPF | intra > inter(コスト小の O IA が負ける) | メトリック比較を先にする |
| `type_e1e2` | OSPF | E1 > E2(E2 のメトリックが小さくても) | 表の数値だけ見る |
| `e2_fwd` | OSPF | E2 同値 → forward metric の第2段 | 「E2 は同値なら ECMP」 |
| `e1_accum` | OSPF | E1 は外部+内部の累積(2 ASBR の計算) | 外部メトリックだけで比較 |
| `fc_strict` | EIGRP | FC は RD **<** FD(等号不成立) | RD 同士の比較・等号を可とする |
| `fs_allthat` | EIGRP | FS 集合の列挙(allthat の本体) | successor 自身を FS に数える/数えない |
| `variance_bound` | EIGRP | 倍率が足りず乗らない(FS だが FD 超過) | 倍率だけ見て FC を確認しない |
| `variance_nonfc` | EIGRP | 非 FC は倍率無関係に乗らない | 「variance を上げれば全部乗る」 |

## 4. worlds(要件レバー・正解反転)

要件世界は **制約の束**(`WORLD_RULES`)で表し、候補の属性に対する述語で機械判定する。
要件文(`gen_paper_mcq.PREF_WORLD_TXT`)と `WORLD_RULES` は **1 対 1 に対応させること**
(文面と機械判定がずれると、fix の一意性の保証が嘘になる)。

| world | 制約の束 | 効き方 |
|---|---|---|
| `w_freeze_area` | エリア構成不変 + 1箇所 | エリア移動系の fix 候補を殺す |
| `w_no_e1` | メトリック型不変 + 1箇所 | `metric-type` 化の fix を殺す |
| `w_variance_cap` | 倍率を上げない + 1箇所 | 倍率で解く手を殺し、FC/範囲を作る側へ寄せる |
| `w_single_touch` | 1箇所 + 最良経路を悪化させない | 2箇所解と「サクセサを悪化させて条件を作る」解を殺す |
| `w_local_only` | 1箇所 + 観測点のみ + 悪化させない | 隣接側の変更を殺す |
| `w_target_only` | 1箇所 + 現在の勝者側は触らない | 「勝っている側を劣化させる」解を殺す |

★**`worsens`(最良経路の悪化)は静的属性ではなく `_worsens()` がモデルで実測する**。
「型を変えれば悪化する」といった思い込みで判定すると、選択肢の判定文が盤面の数値と
矛盾する(E1→E2 は実際にはメトリックが下がる。2026-08-16 に実際に踏んだ欠陥)。

**曖昧要件(vague・§0-2)**: fix 形の設問から **対象経路の名指しを落とす**(40%)。
OSPF は「より小さい外部メトリックが広告されている側の ASBR を経由する経路」、
EIGRP は「現在は搭載されていない冗長なパス」という間接指定にし、盤面の事実から
一意に補完させる。BL-113 の3条件(矛盾なし/一意に補完可/一意性維持)は
`_vague_ok()` が機械保証する(外部メトリックが同値の `e2_fwd`、内部系の
`type_intra`、対象が複数ある盤面では vague にしない)。

## 5. forms(5形)

| form | 設問 | 正解数 |
|---|---|---|
| `read` | 「この宛先に対して RIB に載るのはどれか」 | 1 |
| `why` | 「その経路が選ばれた決め手はどの段か」 | 1 |
| `fix` | 「この経路を選ばせるにはどの1手か」 | 1 |
| `cause` | 「なぜ期待した経路が使われないのか」 | 1 |
| `allthat` | ★「FS になり得る経路をすべて選べ」(数非明示) | 1〜n(機械検証) |

`allthat` は `pick_count` -1 経路(BL-125 で新設)にそのまま乗る。
成立形は 2 段で決まる:
- `kind_forms(kind)`= 原理的な上限。**`type_intra` は fix を持たない**
  (型優先は構造で決まり 1 手で反転させられず、候補が 2 本立たない)。
  **`allthat` は `fs_allthat` のみ**(選択肢=盤面の経路なので 4 経路必要)。
- `forms_for(d)`= その盤面で実際に成立する形(fix は一意性検証に通ったときだけ)。
  なお fix を持つ kind は draw が一意性を強制するので、実質 `kind_forms` と一致する。

## 6. ひっかけ(§0-2 の3類型を各形に最低1つ)

1. **真だが答えていない**: 「O IA のほうがコストが小さい」(事実だが選好の理由にならない)
2. **近似値**: E1 の累積を片側だけ足した値・FD と RD の取り違え値
3. **意味論の取り違え**: 「FC は RD 同士の比較」「variance は全経路に効く」
   「E2 のメトリックは経路上で加算される」

## 7. P0 PoC(`poc/pref/` ・実機1回)★2026-08-16 完了(o7 のみ未実施)

**実測結果は [poc/pref/README.md](../../poc/pref/README.md)**(確定挙動12点)。
全12軸のうち o1〜o6・e1〜e4 が PASS、モデルの修正は不要だった。
唯一の設計変更= §2.2 の `check_board()`(スプリット・ホライズン窓)の新設。


盤面= CML `_POC-PREF`(IOL)。OSPF ブロックと EIGRP ブロックを1ラボに同居させる
(アドレス空間は分離・相互接続なし)。probe は bgpbest 方式の **console 直駆動**
(mgmt/SSH 不使用・CVAC 罠回避)。

| # | 観測 | 目的 |
|---|---|---|
| O1 | `O` / `O IA` / `O E1` / `O E2` の表行と `show ip route <pfx>` detail | **書式 byte 採取**(type extern 1/2・forward metric 句の有無) |
| O2 | intra(高コスト) vs inter(低コスト) | 型優先の実証 |
| O3 | E1(高) vs E2(低) 同一プレフィックス | 型優先の実証 |
| O4 | E2 同値・ASBR 内部コスト差 | forward metric 段の実証+書式 |
| O5 | E1 の metric 値 | 累積の算術確認 |
| O6 | `show ip ospf database external` | LSA 断片の書式採取 |
| O7 | NSSA 内から見た `O N1`/`O N2`(任意・落としてよい) | 書式採取 |
| E1 | `show ip eigrp topology` / `all-links` / route detail | **書式 byte 採取** |
| E2 | ★**RD == FD の経路が FS になるか** | 等号不成立の実証(モデルの核) |
| E3 | variance で FS のみ乗る | 非 FC が乗らないことの実証 |
| E4 | variance 倍率不足 | 境界条件の実証 |

## 8. フェーズ

- **P0**: 上記 PoC → `poc/pref/README.md` に確定挙動+書式を残す。★完了(2026-08-16)
- **P1**: 2モデル+レンダラ(表・detail・topology)+`read`/`why`+selftest。
  ★**完了(2026-08-16)**= `topologies/gen_paper_pref.py`+`gen_paper_mcq.py --shape pref`。
  - kinds 8種すべてで盤面が成立(selftest 836 checks NG=0)・byte 決定性 OK・
    mixed に **暫定 5%** で合流(pbr/urpf/leakmap/ospfv3pl/bgpbest から 1% ずつ)。
  - ★実装中に踏んだ欠陥2件(いずれも修正済・selftest で恒久検出):
    ① **正解肢だけ助詞前の空白が無い**= 文面の作り方が違い、正解が形から割れた
       → 選択肢の文面は `_o_opt()` 1関数に集約し、read 形の書式を selftest で検査。
    ② topology 表を **variance 適用後**で描いており `N successors` が答え(本数)を
       漏らしていた → 既定は**適用前**を描き(`applied=False`)、設問は
       「variance を構成した場合」を問う形にした。
  - ★`keep_ask` 登録必須(既知の罠): pref は**壊れていない**盤面なので汎用の
    症状文が存在しない障害を参照してしまい、設問文も対象(プレフィックス・経路・
    倍率)の担い手。全形 keep_ask にした。
  - quota ジャンル= `records/genres.yml` の `shapes.igp` に `pref` を追加済。
- **P2**: `fix`/`cause`/`allthat`+曖昧要件世界+ひっかけ3類型。
  ★**完了(2026-08-16)**= 全5形。selftest 715 checks NG=0。
  - **fix**= 候補(OSPF 7 / EIGRP 6)をモデルに適用して works を機械判定し、
    要件世界で complies を絞る。**complies==1 かつ works>=2 を draw で強制**
    (満たさない盤面は捨てて引き直す= copp と同じ「一意性は生命線」方針)。
  - **allthat**= `fs_allthat` 盤面(4経路)のみ。選択肢=盤面の実在の経路、
    正解集合= FC の整数比較。`pick_count` -1(数非明示・checkbox)で確認済。
  - **cause**= 機構の記述を選ばせる。錯乱肢は同系の他 kind の機構(この盤面では
    成り立たない)+ AD/ホップ数/帯域の一般則。同義文(fc_strict と
    variance_nonfc)は重複するので除外する。
  - **曖昧要件(vague・40%)**= 対象経路を名指ししない。OSPF は「より小さい外部
    メトリックが広告されている側」、EIGRP は「搭載されていない冗長なパス」で
    一意に補完させ、`_vague_ok()` が一意性を機械保証する(外部メトリックが同値の
    `e2_fwd` や内部系の `type_intra` では成立しないので出さない)。
  - ★実装中に踏んだ欠陥2件(修正済):
    ① **判定文が盤面の数値と矛盾**(上記 `worsens` の実測化で解消。
       併せて「勝者側を触るな」という別軸の世界 `w_target_only` を新設)。
    ② **本題の錯乱肢が抽選で落ちる**(fc_strict で「variance を上げれば載る」肢が
       出ないことがあった)→ `FORCED_DISTRACTORS` で kind ごとに必ず提示。
  - ★要件ダミーの除外: 汎用ダミー「対象外であるところのデバイスの変更は不可」は
    `w_local_only` と同義になり、他の世界で remote 候補を機械判定の外から
    禁止して一意性を壊すため、この shape では使わない。
- **E2E**: 紙面盤面を実機に流し込み、レンダラ出力と実機 show の **行一致**照合。
  ★**完了(2026-08-16)= 24/24 PASS**(`poc/pref/e2e.py`・結果は
  [poc/pref/README.md](../../poc/pref/README.md) の「E2E 実機照合」)。
  EIGRP 4 ケース(fc_strict/variance_bound/variance_nonfc/**fs_allthat=4経路**)×
  3 項目 + OSPF 3 ケース × 4 項目。**メトリックの算術が 1 の位まで一致**。
  4 経路盤面の再現のため PoC ラボへ **RE6 を追加**(11 台)。
  ★E2E 特有の落とし穴3点(README に収録)= FD は前回 Active 以降の最小値なので
  `clear ip eigrp <AS> neighbors` が要る / 収束は本数でなく**出力の安定**で待つ /
  17.15 は `subnets` を暗黙化するため完全形の `no redistribute` が当たらない。
- **mixed 合流**: ★完了= 暫定 5%(§0-③)。quota ジャンルは `records/genres.yml` の
  `shapes.igp` に `pref` を追加済(確認済み)。
