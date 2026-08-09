# OSPFv3 ⇄ EIGRPv6 相互再配送「C1↔C2 を通すには」紙面ファミリ — 設計メモ (BL-098)

作成: 2026-08-08 / 発端: ユーザ手組みラボ **「IPv6redistribute01」**(CML, 5×IOL, 温存・読み取りのみ)

## 出題意図(ユーザ要望の整理)

> ラボの状態から「クライアント C1, C2 同士で通信を行えるようにするには？」を問い、
> **その時々の要件によって正解が変わる**(デフォルトルートを置く / route-map を外す・改変する 等)。
> 紙面希望。ただし**認知負荷が高く、技術理解の深さを試す**形式であること。

→ `gen_paper_pbr` / `gen_paper_leakmap`(BL-081/095)で確立した**被覆エンジン方式**に載せる。
すなわち「複数の手段が物理的には直る」状態を作り、**制約(要件世界)が適合解を1つに絞る**。

## 盤面 — ユーザラボの構造(実測で確定)

```
      OSPFv3 544 area 0                              EIGRP named AS 5400
 C1 ────────── RA ────────────── RT-C ────────────── RB ────────── C2
    2001:DB8:2:1::/64   2001:DB8:1:1::/64  ASBR  2001:DB8:A:A::/64  2001:DB8:1A:A::/64
    (C1 LAN)            (Oトランジット)         (Eトランジット)      (C2 LAN)
 RID 6.6.6.6      4.4.4.4      OSPF 2.2.2.2 / EIGRP 1.1.1.1     3.3.3.3      5.5.5.5
```

- C1 は OSPFv3 544 area 0 の一員、C2 は EIGRP named AS5400 の一員(どちらも IOL ルータ)。
- **RT-C だけが ASBR**(単独)。よって古典的な二点相互再配送ループは起きない。
- RT-C の EIGRP は `af-interface Ethernet0/0 shutdown`(= OSPF 側リンクで EIGRP を喋らない)。
  named mode の IPv6 AF は **`network` 文を使わず全 IPv6 IF が既定参加**するため、この明示 shutdown が必要。

### RT-C の再配送(ユーザラボ原文)

```
router eigrp NAMED
 address-family ipv6 unicast autonomous-system 5400
  topology base
   redistribute ospf 544 match internal metric 10000 100 255 1 1500 route-map OMAP01 include-connected
router ospfv3 544
 address-family ipv6 unicast
  redistribute eigrp 5400 route-map EMAP01 include-connected
!
ipv6 prefix-list O544  seq 5 permit 2001:DB8:1:1::/64    ← O トランジット
ipv6 prefix-list E5400 seq 5 permit 2001:DB8:A:A::/64    ← E トランジット
route-map OMAP01 permit 10 / match ipv6 address prefix-list O544
route-map EMAP01 permit 10 / match ipv6 address prefix-list E5400
```

### ★この盤面の核心 — 「動いているのに届かない」

| 方向 | 相手ドメインに届いている経路 | 届いていない経路 |
|---|---|---|
| OSPF → EIGRP | `2001:DB8:1:1::/64` = **EX [170]**(Oトランジット・RT-C にとって **connected**) | `2001:DB8:2:1::/64`(C1 LAN・RT-C にとって本物の `O` 経路) |
| EIGRP → OSPF | `2001:DB8:A:A::/64` = **OE2 [110/20]**(Eトランジット・RT-C にとって **connected**) | `2001:DB8:1A:A::/64`(C2 LAN・RT-C にとって本物の `D` 経路) |

**両方向とも、通っているのは `include-connected` が拾った自分の足元のリンクだけ**で、
本来届けたい学習経路は prefix-list に落ちている。結果 **C1↔C2 は双方向とも全断**。

これが認知負荷の源泉:
- `show ipv6 protocols` には両方向の Redistribution 行が正常に出る。
- 経路表にも相手ドメインの経路が **1本ずつ入っている**(=「再配送が壊れている」ようには見えない)。
- prefix-list 名(`O544` / `E5400`)は**方向を表しているのか対象を表しているのか字面から判別できない**。
  実際は「OSPF *から* 出す方向のフィルタ」なのに、許可しているのは **OSPF 側のリンク**。

### ★症状の非対称(実測・紙面素材として一級)

| ping | 結果 | 意味 |
|---|---|---|
| C1 → `2001:DB8:1A:A::2`(C2) | `% No valid route for destination` | C1 に経路が無い |
| C1 → `2001:DB8:A:A::2`(RB の E 側) | `..`(タイムアウト) | **往路はある・復路が無い**(RB は C1 LAN を知らない) |
| C1 → `2001:DB8:1:1::1` | `!!` | 同一ドメイン内なので疎通 |
| C2 → `2001:DB8:1:1::1` / `A:A::1` | `!!` | EX 経路で到達 |

★さらに **`ping <dst> source <src>` を付けると `% No valid route` が出ず `..` になる**(実測)。
「source を指定した瞬間に経路欠落の証拠が消える」——TS 実務の落とし穴そのもの。

## PoC 項目(poc/v6redist/sweep.py) — ★**全 17 シナリオ実測完了(2026-08-08)**

実測値の確定表は [poc/v6redist/README.md](../../poc/v6redist/README.md) を正典とする。
以下は各検証の**狙い**(結果は確定表を参照)。

| # | 検証 | 何のために要るか |
|---|---|---|
| B0 | 基線がユーザラボ実測と一致 | ✅ 済(経路表4ノード完全一致) |
| E1 | route-map を両方向とも外す | 「一番荒い解」の成否 |
| E2 | prefix-list に客先 LAN を**追記** | 最小改変解 |
| E3 | ★prefix-list を客先 LAN のみに**置換** | **include-connected 由来の経路に route-map は効くか**(効くなら「トランジット秘匿」要件が成立) |
| E4 | include-connected を外す | トランジットが消えるかの確認 |
| E5 | ★EIGRP 側 redistribute の **metric 省略** | 「route-map を外す」時に metric を落とすと**何も広告されない**罠 |
| E6 | `default-metric` で救えるか | 上の代替解 |
| E7 | ★参照 prefix-list を**未定義**に | 全許可か全拒否か(leakmap では「全許可」) |
| E8 | ★**未定義 route-map** を参照 | 全拒否か全許可か(leakmap では「全拒否」)→ **非対称の確認** |
| E9 | af-interface E0/0 の shutdown 解除 | `1:1::/64` が EX[170] → D[90] に化けるか(「内部で受けたい」要件) |
| E10 | ★`match internal` は OSPF 外部(OE2)を落とすか | `match internal external` 要求の要件世界 |
| E11 | ★OSPFv3 `default-information originate` の **always 要否** | デフォルト解の成立条件(RT-C 自身は ::/0 を持たない) |
| E12 | ★EIGRP `af-interface summary-address ::/0` | EIGRP 側デフォルト配布の成否と Null0 ブラックホール副作用 |
| E13 | ★RA/RB に**静的のみ**(IGP 再配送なし) | 「中継は知るがクライアントは知らない」= 静的解の落とし穴 |
| E14 | E13 + C1/C2 にデフォルト | フィルタ無改変の最小静的解 |
| E15 | `metric-type 1` / metric 指定 | 「E1 で受けたい」要件世界 |
| E16 | ★`redistribute` 再発行のマージ挙動 | 下記(確定済) |

### ★確定済の知見(2026-08-08 実測・IOL iol-xe 17.15)

**`redistribute` は再発行でマージされる — `route-map` 節を書かずに打ち直しても route-map は外れない。**

```
(基線)  redistribute eigrp 5400 route-map EMAP01 include-connected
(A) 「  redistribute eigrp 5400 include-connected 」を投入
     → 結果: redistribute eigrp 5400 route-map EMAP01 include-connected  ← 変化なし
(B) 「no redistribute eigrp 5400」→「redistribute eigrp 5400 include-connected」
     → 結果: redistribute eigrp 5400 include-connected                    ← 外れる
```

`metric` / `match internal` も同様に、`no` を前置しない限り残る。
→ **「route-map を外す」設問の CLI 選択肢は `no redistribute ...` を含む状態収束形でなければ不正解**。
これはユーザ要望の「ルートマップを外す」を*正しく*問うための必須知見であり、
かつ **fix(CLI) 形の最有力ディストラクタ**(route-map 節を省いた再発行=見た目は正しいが効かない)。
PoC 手順自体もこの罠を踏んだ(初回スイープで E1 が「変化なし」となり発覚)。

**`no router ospfv3 <pid>` はインタフェースの `ipv6 ospf <pid> area <n>` も道連れに消す。**
プロセスを作り直したら IF 側も焼き直しが要る(スイープの restore で対処済)。

> 実測結果は [poc/v6redist/results-raw.md](../../poc/v6redist/results-raw.md) に追記型で記録し、
> 確定表を本メモと [poc/v6redist/README.md](../../poc/v6redist/README.md) に反映する。

## 要件世界(制約)→ 正解反転 の設計案

「C1↔C2 を通す」手段は物理的には多数あるが、制約が適合解を1つに絞る。

| 世界 | 制約(問題文に書く) | 死ぬ手段 | 生きる手段 | 実測根拠 |
|---|---|---|---|---|
| `free` | 制約なし・最小の変更で | — | prefix-list 追記(2行) | E2 ✅ |
| `filter_frozen` | 監査により route-map / prefix-list は変更禁止 | フィルタ改変系すべて(E1/E2/E3/E7)・**中継だけの静的**(E13=半正解) | 静的+クライアント既定GW(E14) / `default-information originate always` + EIGRP `summary-address ::/0`(E12) | E11 E12 E13 E14 ✅ |
| `no_static` | 静的経路は使わない(全て動的に) | 静的解・Null0 | prefix-list 改変 / route-map 外し | E1 E2 E3 ✅ |
| `hide_transit` | トランジット 2 本は相手ドメインへ広告しない | route-map 外し(E1)・prefix-list **追記**(E2)・PL 削除(E7) | prefix-list **置換** / include-connected 削除 + PL 置換 | **E3 ✅**(include-connected も route-map に従う) |
| `rtc_only` | RT-C 以外の機器は構成変更しない | 静的解(RA/RB/C1/C2 を触る) | RT-C 上の手段すべて | E13/E14 との対比 |
| `default_only` | 相手ドメインの明細は持たず `::/0` のみで届かせる | 明細を通す全手段(E1/E2/E3/E7)・静的解(E14=明細が入る) | `default-information originate always` + EIGRP `summary-address ::/0` | **E12 ✅**(明細ゼロで 100%/100%) |
| `internal_ad` | EIGRP 側は `1:1::/64` を**内部(D / AD 90)**で受けること | 再配送のみ(必ず `EX [170]`) | af-interface `shutdown` 解除 **＋** 客先 LAN を通す手段 | **E9 ✅** |
| `pass_external` | OSPF 側の**外部経路**も EIGRP へ渡すこと | `match internal` のまま | `match internal external` へ変更(★`no redistribute` 前置が要る) | **E10 ✅** |
| `e1_type` | C1 側は C2 LAN を **OE1** で受け、コストが経路上で累積すること | 既定(`OE2`=全ノード `[110/20]` 固定) | `metric ... metric-type 1` | **E15 ✅**(RA 510 → C1 520) |

★ `hide_transit` と `internal_ad` は**2手が必要**(通す手段 + 形を整える手段)なので、
選択肢のうち片方しか含まないものが自然な誤答になる。
★ 等価な最終状態(例: `hide_transit` の PL 置換 と include-connected 削除+PL 置換)は
**意味シグネチャで畳む**(BL-084 の dedupe 方式)——同時提示しない。

★世界は**問題文の要件節**として提示し、選択肢には因果を書かない(gen_paper_mcq 恒久規約)。

## 認知負荷を上げる装置(ユーザ要望の中核)

1. **デコイ乱立**: 未参照の prefix-list / route-map / ACL を 3〜6 個。似た名前(`O544`/`O5440`/`OSPF544`)。
   タイポ参照・seq 影(`deny` が先に来る)・`ge/le` の空振り。
2. **名前が方向を語らない**: `OMAP01`/`O544` は「OSPF から」なのか「OSPF へ」なのか読み手に判断させる。
   ユーザラボが偶然そうなっている構造をそのまま教材化する。
3. **`include-connected` の主語**: 「その connected は誰のものか」= ASBR 自身の IF のみ。
   RA/RB の connected は含まれない、という理解を問う。
4. **2つの `router-id`**(OSPF 2.2.2.2 / EIGRP 1.1.1.1)と `af-interface shutdown` で
   「EIGRP が動いていないのか / IF が落ちているのか / 意図的に喋らせていないのか」を切り分けさせる。
5. **症状の3値**(`% No valid route` / `..` / `!!`)と `source` 指定による症状の化け。

## 出題形状

- **S1 fix**: 現状 config エキシビット + 要件世界 → 「どの設定変更が要件を満たすか」4択(prose / CLI 状態収束形)
- **S2 cause**: 経路表 + ping 出力 → 「C1↔C2 が通らない理由はどれか」4択
- **S3 read**: エキシビット → 「C1(または C2)の `show ipv6 route` はどれか」4択 ← 認知負荷最大
- **S4 trace**(★この盤面固有の新形): 3 本の ping 結果の組合せを与え、**どの方向のどの経路が欠けているか**を問う。
  `% No valid route` と `..` の読み分けを直接試す。他 shape に無い強い形。

## サンプル問題(P1 の目標像・**選択肢はすべて実測済みの挙動**)

`shape=v6redist` / `form=fix` / `world=hide_transit`。文体は Cisco 語規約([[ccnp-cisco-japanese-style]])。

> ### 要件
> 1. C1 と C2 は、相互に通信できなければなりません。
> 2. いずれのドメインのルータの経路テーブルにも、対向するドメインのトランジット リンクの
>    ネットワーク(`2001:DB8:1:1::/64` および `2001:DB8:A:A::/64`)が、現れてはなりません。
> 3. 静的ルートの使用は、認められていません。
> 4. RT-C 以外のデバイスに対する構成の変更は、許可されていません。
>
> ### 設問
> 要件を満たすところの構成は、次のうちどれですか。

| 選択肢 | 内容 | ★実測される結果 | 判定 |
|---|---|---|---|
| A | `ipv6 prefix-list O544 seq 10 permit 2001:DB8:2:1::/64` / `E5400 seq 10 permit 2001:DB8:1A:A::/64` を**追記** | 開通する(ping 100%)が**トランジットも残る** (E2) | 要件2違反 |
| **B** | 両 prefix-list を **客先 LAN のみに置換**(既存 seq 5 を削除) | 開通し、**トランジットが消える** (E3) | **正解** |
| C | `redistribute ... include-connected` を **route-map 節を書かずに再発行** | ★**何も変わらない**(行がマージされ route-map が残る) (E16) | 開通しない |
| D | `no ipv6 prefix-list O544` / `no ipv6 prefix-list E5400` | ★**全許可**になり全開通するが**トランジットも通る** (E7) | 要件2違反 |

4案すべてが「もっともらしい」うえ、**C は一見正しい CLI なのに no-op**、**D は絞る操作なのに全開**という
反直感を含む。同じエキシビットで `world` を差し替えるだけで正解が A/B/D に移る(被覆エンジン)。

## 実装計画

- **P0 ✅ 完了(2026-08-08)**: `problems/_POC-V6REDIST`(ユーザラボ複製・基線一致 ✅)で
  **B0 + E1〜E16 の全 17 シナリオを実測**。確定表 → [poc/v6redist/README.md](../../poc/v6redist/README.md)。
  全 9 要件世界の「生きる手段/死ぬ手段」に実測根拠が付いた(上表)。
- **P1 ✅ 完了(2026-08-08)**: `topologies/gen_paper_v6redist.py` +
  `gen_paper_mcq.py --shape v6redist`(mixed ルーレット合流済)。
  故障種 5 種 × 要件世界 8 種の被覆エンジン。検証= `--selftest`
  (world 明示 1505/1600・**world 未指定 600/600**)＋ E2E 24 問の機械検分(漏えい/選択肢数/
  判定行数)＋ 他 shape の回帰(ospfv3pl/leakmap/urpf/pbr/mixed)。
- **P2 ✅ 完了(2026-08-08)**: 出題形 4 種 S1〜S4 を実装(fix/cause/read/**trace**)。
  read の経路表・trace の ping 出力は実測書式に忠実(コード・AD・メトリック)。

### P1/P2 の実装で確定した設計上の判断(重要)

1. **候補は「現在状態からの差分」で持つ**(絶対状態ではない)。絶対状態にすると、
   「フィルタに触らない」はずの手段(静的・デフォルト)の最終状態が壊れた route-map を
   暗黙に修復してしまい、**提示する CLI と要件適合の判定がずれる**。
   候補の性質(filt/other/static/igp_default)も宣言せず**差分から導出**する。
2. **fix 形は常に CLI 提示**にした。手段の散文表現では「参照やメトリックの是正も
   含むのか」が曖昧になるため。CLI は状態収束形で完全に explicit
   (★`no redistribute` の前置を含む=実測 E16 の写像)。
3. **`no_incl` は故障種にしない**。客先 LAN は*学習経路*であって connected ではないので、
   `include-connected` の有無はトランジットの見え方しか変えられず、
   単独では C1↔C2 を落とせない(実測 E4 の「全滅」は PL がトランジットのみ許可
   していたこととの合わせ技)。**cause 形の錯乱肢としてのみ使う**。
4. **cause 形の錯乱肢は claim を機械判定して選ぶ**(`claim_true()`)。事実として
   偽の claim だけを錯乱肢にすることで、正解の一意性を構造的に保証する
   (手書きの排他表は故障種を足したときに破綻する)。
5. **`default_only` は一部の故障種と両立しない**。デフォルトの配布は OSPF 側の
   既存の明細を消さないため(実測 E12: EIGRP 側は summary-address が more-specific を
   全抑止するが、OSPF 側は残る)。`draw()` は `compatible_worlds()` で
   成立する世界だけを選ぶ。
6. **trace 形の代替状態は明示的に作る**。候補の写像から採ると到達性の組合せが
   重複して選択肢が畳まれるため、5 通り(双方向開通/片側のみ×2/双方向不通/
   クライアントのみ既定 GW)を直接構成する。
- **P3**: **実機 TS 版**(`gen_v6redist_ts.py`)。★この盤面は紙面だけで終わらせるには惜しい:
  症状の非対称(NOROUTE / タイムアウト)は実機で触ってこそ身につく。紙面 P1/P2 完了後に分離登録。

## 紙面 vs ラボ の判断(ユーザ問いへの回答)

**紙面ファミリを主軸に据える**。理由: 「要件で正解が反転する」は候補どうしの**比較**が本質で、
選択肢を並べられる紙面が最も高密度に試せる(1問あたり4案 × 要件世界)。実機ラボだと 1 回の
解答で 1 つの手段しか観測できず、被覆効率が落ちる。
ただし本盤面は**ラボ問としても強い**ため P3 で実機 TS 版を作る(紙面で手段の地図を作り、
実機でその中の 1 本を歩かせる、という二段構え)。

公開可否: 定番題材の自作問のため公開系(PVT 不要)。
