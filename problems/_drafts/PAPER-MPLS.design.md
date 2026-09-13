# 紙面 MPLS L3VPN ファミリ（shape=mpls・BL-169）設計

起票 2026-09-13。状態= **完了・出題可（同日。P0 PoC→P1/P2→scratch E2E→mixed 暫定 5% 合流）**。残= p_soo(P3)・実パックでの初出題。PoC 実測表= [poc/mpls-paper/README.md](../../poc/mpls-paper/README.md)。
台帳= [BACKLOG.md](../../BACKLOG.md) BL-169。共通原則= [PAPER-3FAM-COPP-DMVPN-PREF.design.md](PAPER-3FAM-COPP-DMVPN-PREF.design.md) §0、
新ファミリ共通チェックリスト= [PAPER-BLUEPRINT-GAP.design.md](PAPER-BLUEPRINT-GAP.design.md) §5（14項目）。

## 0. 位置づけと判断

- ブループリント v1.1 の **2.1（MPLS 動作: LSR/LDP/label switching/LSP）と 2.2（MPLS L3VPN: RD/RT/VPNv4/PE-CE）は
  ともに describe レベル**。ラボ側（ENARSI-MPLS-L3VPN-01〜06・gen_mpls_ts）は範囲を超過達成しているが、
  **紙面はゼロ**（BL-100 の突合せ）。VPN 20% の紙面空白のうち MPLS が 2/3 を占める。
- 2026-09-13 のユーザ判断= 紙面の空白は既存問題の変種化でなく**生成器ファミリで埋める**（費用対効果）。
- 本試験で想定される問われ方（describe 級が中心）:
  1. 用語・役割・仕組みの正誤（P/PE/CE/LER/LSR、ラベル・ヘッダ、LDP、LSP/FEC、PHP、RD/RT/VPNv4、MP-BGP）
  2. 用語と説明の**対応付け**（組合せ形。解答UIは BL-168 で整備済み）
  3. **VRF 構成の読解**（片側 PE の構成を見て対向 PE の正しい構成を選ぶ／到達しない原因を選ぶ／どの VRF に何が載るか）
  4. **表示の読解**（`show mpls forwarding-table`・`show mpls ldp bindings` の imp-null / Pop Label / swap、LDP 隣接）
  5. PE-CE（eBGP の as-override / allowas-in、SoO）の原因と対処
- したがって**器は TS 系（故障を仕込んで直す）ではなく「知識＋読解」系**。それでも正解の一意性は
  モデル層と事実ベースで機械検証する（言葉で担保しない）。

## 1. 器

- `gen_paper_mcq.py --shape mpls`（紙面専用・ラボ展開なし）。素材モジュール= `topologies/gen_paper_mpls.py`。
  モデル= `topologies/rt_model.py`（RT の import/export 集合→VRF 表の到達）＋ `gen_paper_mpls` 内の
  ラベル連鎖モデルと事実ベース。作法は `gen_paper_copp.py`（KINDS / WORLDS / kind_forms / draw /
  build_choices_* / selftest）に揃える。
- 主形は選択式。BL-100 が示唆した記述式（bgpdbg の essay 方式）は P3 の任意項目に回す。
- 種別行は `mpls/<kind>`。`records/genres.yml` の `vpn: [dmvpn, mpls, ...]` に既に載っているので集計側の変更は不要。

## 2. 知識境界

| 扱う（選択肢の正誤に使う） | 裏話のみ（解説の末尾・正誤に使わない） | 扱わない |
|---|---|---|
| ラベル・ヘッダ（20/3/1/8 ビット）、LSR/LER、FEC、LSP、PHP と imp-null、LDP（TCP 646・hello は UDP 646・router-id の選び方・transport address の到達性）、LDP autoconfig（OSPF/IS-IS）、RD（64 ビット・VPNv4 = RD＋IPv4 96 ビット・一意性の目的）、RT（拡張コミュニティ・import/export の制御）、VPNv4 AF と `send-community extended`、`ip vrf forwarding`/`vrf definition`、PE-CE eBGP の as-override / allowas-in / SoO、`show mpls forwarding-table`・`show mpls ldp bindings`・`show bgp vpnv4 unicast all`・`show ip route vrf` の読み方 | 自動 RT フィルタ（import に合わない VPNv4 経路は PE が保持しない・RR は例外）、explicit-null、OSPF PE-CE の sham-link と DN ビット（L3VPN-03 / VRFLITE-DNBIT-01 の知見）、`bgp default route-target filter` | RSVP-TE は名称の問い（「TE に使うのは RSVP」）までで挙動は扱わない、6PE/6VPE、CSC、Inter-AS、MPLS QoS |

## 3. kinds（4群・11種）

| 群 | kind | 主題 | 難 | 決め手／モデル |
|---|---|---|---|---|
| term | `t_roles` | P/PE/CE/LER/LSR の役割（ラベルの付加・交換・除去・非対応） | 2 | 事実ベース |
| term | `t_label` | ラベル・ヘッダのフォーマット、LSP/FEC、PHP・imp-null | 2 | 事実ベース |
| term | `t_ldp` | LDP のトランスポート・router-id・transport address・autoconfig | 3 | 事実ベース |
| term | `t_vpn` | RD/RT/VPNv4/MP-BGP の役割分担（RD は一意化・RT が制御・RT は import≠export でよい） | 3 | 事実ベース |
| vrfcfg | `v_peer` | 片側 PE の VRF 構成から対向 PE の正しい構成を選ぶ（RT の対称性・RD は一致不要） | 3 | rt_model |
| vrfcfg | `v_reach` | どの VRF 表に何が載るか／到達できる組を選ぶ | 3 | rt_model |
| vrfcfg | `v_cause` | 拠点間が到達しない原因（import/export の取り違え・`activate` 欠落・`send-community extended` 欠落・再配送欠落。**RD 不一致は原因でない**という錯乱肢） | 4 | rt_model＋事実ベース |
| label | `l_read` | LFIB/LIB の行から動作を読む（imp-null＝PHP で最終ホップ手前が除去、Pop Label、swap、No Label） | 3 | ラベル連鎖モデル |
| label | `l_cause` | IGP は正常なのに VPN だけ死ぬ（LDP 未起動の IF＝LSP の穴・transport address 不達・MTU） | 4 | ラベル連鎖モデル |
| pece | `p_asoverride` | 同一 AS の拠点間で経路が入らない（`DENIED due to: AS-PATH contains our own AS`）→ as-override / allowas-in を要件で選ぶ | 4 | 事実ベース＋世界 |
| pece | `p_soo` | バックドアを持つ拠点の再流入を SoO で止める | 4 | 事実ベース＋世界 ★**P3 へ保留**（PoC 用ラボにバックドア無し・M12 未実測） |

`gen_mpls_ts` の故障14種のうち RT export/import 取り違え・非標準 RD デコイは `v_cause`/`v_peer` の種、
L3VPN-04 の as-override 指紋（PoC 採取済）は `p_asoverride` の種として流用する。

## 4. worlds（要件世界。fix 系の正解を反転させる）

| 群 | world | 要件文の骨子 | 正解の反転 |
|---|---|---|---|
| vrfcfg | `w_fullmesh` | 全拠点が相互に到達 | 単一 RT を import/export |
| vrfcfg | `w_hubspoke` | 拠点は hub とだけ通信、spoke 同士は不可 | hub 側 export=RT-H/import=RT-S、spoke 側は逆 |
| vrfcfg | `w_extranet` | 顧客 A/B は分離のまま共有サービス VRF にだけ到達 | サービス VRF が両 RT を import、各顧客はサービス RT を追加 import（**additive** の罠は裏話） |
| vrfcfg | `w_isolate` | 同一プレフィックスを使う 2 顧客を混ぜない | RT を分ける（RD を分けるだけでは不足＝錯乱肢） |
| pece | `w_ce_frozen` | CE の構成は変更できない（顧客管理） | PE 側 `neighbor <CE> as-override` |
| pece | `w_pe_frozen` | 事業者は PE のポリシーを変えない | CE 側 `neighbor <PE> allowas-in` |
| pece | `w_backdoor` | 拠点間バックドアあり、MPLS 経由の経路が拠点へ戻らないこと | `set extcommunity soo` を route-map で in 適用 |

kind ごとに成立する world を `KIND_WORLDS` に明示し、非両立は `compatible_worlds()` で除外する（チェックリスト 5）。
曖昧要件（BL-113 の3条件）は vrfcfg で使う: 例=「spoke 間の通信は hub 経由で許可される」を要件に書かず、
盤面の RT 集合から一意に決まる形にする。

## 5. forms

| form | 内容 | 使う群 |
|---|---|---|
| `select` | 正しい記述を 1 つ | term |
| `select2` | 正しい記述を 2 つ（数明示） | term / vrfcfg |
| `allthat` | 該当するものをすべて（**数非明示**・`pick_count=-1`） | term（各ファミリ1形の標準装備） |
| `match` | 用語①〜④ と説明 A〜D の対応付け（`### 対応させる項目` の表＋`## 選択肢`・正解行 `**①－D、②－A…**`） | term |
| `fix` | 要件を満たす構成（CLI 提示）を 1 つ | vrfcfg / pece |
| `cause` | 事象の原因を 1 つ（claim＋反証の事実ベース・排他表） | vrfcfg / label / pece |
| `read` | 表示から帰結を 1 つ（どの VRF に載るか／imp-null の意味／出て行くラベル） | vrfcfg / label / pece |

exam 時の重み（暫定）= term 30 / vrfcfg 35 / label 20 / pece 15。form は kind ごとの `kind_forms()` から抽選、`--forms` で絞れる。

## 6. モデル層（一意性の機械検証）

1. **`rt_model.py`**（純関数・状態なし。`ospfpref_model.py` と同じ位置づけ）
   - 入力: `vrfs = {name: {pe, rd, imp:set, exp:set, nets:[prefix]}}`。
   - `reach(vrfs)` → VRF ごとに「載るプレフィックスと出自 VRF」の集合。規則= 他 VRF の export と自 VRF の import の
     交わりが空でなければ載る（同一 PE 内でも RT で漏れる）。RD は集合の計算に**関与しない**（VPNv4 キーの一意化だけ）。
   - `vpnv4_entries(vrfs, pe)` → その PE の VPNv4 表に並ぶ（RD, prefix）の一覧（同一プレフィックスが RD 違いで 2 本並ぶ表示の再現）。
   - fix 形の判定は copp と同じ `works>=2 / complies==1`（機能的に直る候補が複数あり、要件に適合するのが 1 つ）。
2. **ラベル連鎖モデル**（`gen_paper_mpls` 内）: 経路 PE1→P1→P2→PE2 と各ホップの binding から、ホップごとの動作
   （push / swap / pop）と出て行くラベルを決める。最終ホップ手前は imp-null（PHP）。LDP の無い IF は「LSP の穴」で
   VPN トラフィックだけ落ちる。表示は PoC の byte 写しに値を当てはめる。
3. **事実ベース**（term・cause 用）: `CLAIMS`（真偽つきの記述・タグ・反証文）。`select/select2/allthat` は同一タグ内で
   真偽を混ぜて組み、**タグの排他表**で「同時に真」を防ぐ。「真だが設問に答えていない」肢は別タグの真の記述から供給する。

## 7. 盤面と exhibit

- トポロジ（紙面用の合成・6〜7台）: PE1—P1—P2—PE2 のコアに CE を 2〜4 台。Extranet 世界だけ SVC-PE/SVC-CE を足す。
  値の抽選軸= AS（65000 系）、RD/RT（`AS:100`/`AS:200` 系＋非標準デコイ）、VRF 名（CUST_A/B・Blue/Red・顧客名）、
  プレフィックス（172.16/10.x）、ラベル値（16〜1048575 の帯から抽選・imp-null は固定語）、ホスト名。
- exhibit は **PoC の byte 写し**（チェックリスト 7）: `show vrf` / `show run | section vrf definition` /
  `show bgp vpnv4 unicast all` / `show bgp vpnv4 unicast all summary` / `show ip route vrf` /
  `show mpls forwarding-table` / `show mpls ldp bindings` / `show mpls ldp neighbor` / `show mpls interfaces` /
  `traceroute vrf`（`[MPLS: Label N Exp 0]`）/ CE の `debug ip bgp updates`（DENIED 指紋）/
  `show ip bgp neighbors <PE> received-routes`（AS_PATH `65000 65000`）。
- 図は mermaid（`messy_mermaid` 適用）。散文は Cisco 語＋`obfuscate_md`（keep_ask= read/cause は設問が情報の担い手）。

## 8. 認知負荷の装置（§0 共通原則の当てはめ）

- 複数選択: `select2` を主形、`allthat` を term に標準装備。正解集合は selftest で機械検証。
- ひっかけ: ①真だが設問外（LDP の事実を RSVP の設問に）②近似値（ラベル 20 ビット vs 32、RD 64 vs 32）
  ③意味論の取り違え（RD を「制御」・RT を「一意化」と入れ替えた文、`imp-null` を「付加」と読む文）。
- 曖昧要件: vrfcfg の世界で「hub 経由」「共有サービス」を明文化せず、盤面の RT 集合で一意化。

## 9. PoC（`poc/mpls-paper/README.md`・実測してから実装）

使うラボ= 既存問題を provision して流用（新規トポロジは作らない）。**CML の空きが要るので採点完了後**。

| # | 項目 | ラボ | 目的 |
|---|---|---|---|
| M1 | `show mpls forwarding-table` の byte 書式（Local/Outgoing/Prefix/Bytes/Outgoing interface/Next Hop、Pop Label、No Label、imp-null の出方） | L3VPN-01 | `l_read` の表 |
| M2 | `show mpls ldp bindings` / `show mpls ldp neighbor` / `show mpls ldp discovery` の書式（transport address・TCP 646・router-id） | L3VPN-01 | `t_ldp`/`l_read` |
| M3 | `traceroute vrf` のラベル表示 | L3VPN-01 | read 形の証拠 |
| M4 | ある IF の `mpls ip` を落としたときの症状（IGP 正常・VPN だけ断・LFIB の行の変化） | L3VPN-01 | `l_cause` |
| M5 | LDP router-id が到達不能なときの隣接（`Passive/Active`・確立しない指紋） | L3VPN-01 | `t_ldp`/`l_cause` |
| M6 | `show bgp vpnv4 unicast all` で同一プレフィックスが RD 違いで 2 本並ぶ表示（重複プレフィックス顧客） | L3VPN-01 | `v_reach` |
| M7 | RT import を外した／export を変えたときの `show ip route vrf` と VPNv4 表（自動 RT フィルタの実挙動＝裏話の根拠） | L3VPN-01 | `v_cause`/裏話 |
| M8 | 2 つの VRF に同じ RD を入れたときの IOS の応答（拒否か受理か） | L3VPN-01 | `w_isolate` の錯乱肢の根拠 |
| M9 | `send-community extended` 欠落／`activate` 欠落の指紋（PfxRcd 0・Established のまま） | L3VPN-01 | `v_cause` |
| M10 | as-override 前後の CE 受信 AS_PATH と DENIED 指紋（採取済の再確認） | L3VPN-04 | `p_asoverride` |
| M11 | allowas-in を CE 側に入れたときの受信と経路表 | L3VPN-04 | `w_pe_frozen` |
| M12 | SoO を in で付けたときの再流入抑止（バックドア拠点） | L3VPN-04＋1 リンク | `p_soo`（成立しなければ P3 へ） |
| M13 | Extranet の import 追加で `additive` の有無による差（L3VPN-06 の知見の再確認） | L3VPN-06 | `w_extranet` の裏話 |
| M14 | LDP autoconfig（`mpls ldp autoconfig` は OSPF/IS-IS のみ）の受理／拒否 | L3VPN-01 | `t_ldp` |

「定説と違う」結論が出たら、まずそれを疑う（チェックリスト 12）。M8・M12 は結果次第で kind を落とす。

## 10. selftest

- `rt_model.selftest()`= PoC の M6〜M9 の実測表と一致（aaa_model 方式）。
- `gen_paper_mpls.selftest(seeds=40)`= kinds×worlds×forms の全組合せ× N seed で
  fix= works≥2・complies=1、cause= 真 claim ちょうど1、read= モデルの答えが 1 つ、
  select/select2/allthat= 正解集合が事実ベースと一致しタグ排他を満たす、match= 全単射。
- `PYTHONHASHSEED` 1/999 で byte 同一（zlib.crc32 のみ）。`render_html --selftest` で選択肢の分割と組合せ項目の検出。
- 機械検証は自モデルの誤りを検出できない（チェックリスト 10）→ PoC 実測との突合が生命線。

## 11. 段階と工数

| 段 | 内容 | 目安 |
|---|---|---|
| P0 | PoC M1〜M14（L3VPN-01/04/06 を provision して採取・README に実測表） | 0.5 日 |
| P1 | `rt_model.py`＋ term/vrfcfg（select/select2/allthat/match/fix/cause/read）＋ selftest | 1 日 |
| P2 | label/pece（ラベル連鎖モデル・DENIED 指紋・SoO）＋ selftest | 1 日 |
| E2E | 紙面の描画確認・パック1本に混ぜてユーザ試行・講評 | 0.5 日 |
| 合流 | mixed に暫定 5%（捻出元は urpf/pbr/leakmap/ospfv3pl/v6redist から 1% ずつ・全体再配分はユーザ判断） | 0.5 日 |
| P3（任意） | 記述式（bgpdbg の essay 方式）・SoO が成立しない場合の代替 | 別途 |

## 11-b. 実装記録（2026-09-13・P1）

- `topologies/rt_model.py`（純関数・selftest 6 ケース）と `topologies/gen_paper_mpls.py`（term 4 種＋vrfcfg 3 種・7 形・selftest= kinds×worlds×forms×30 seed= 900 件 NG 0）。
- `gen_paper_mcq.py --shape mpls` を組み込み（shape 登録・kinds プール・`--forms`/`--worlds`・draw/形抽選/選択肢・md 組み立て・mixed 暫定 5%・紙面専用リスト・`assign_sites` 除外）。
  scratch 複製リポで 7 種 1 問ずつ生成→`choice_letters`/`pick_count`/`match_terms`/`key_of`/バッジ数を全件確認、mixed 40 問(--no-lab)で mpls 3 問混入、`--forms match`/`--worlds w_hubspoke` 動作、PYTHONHASHSEED 1/999 で byte 同一、dry-run パックで 6 形の解答UI（ラジオ/チェックボックス/組合せ 4 行）を確認。
- ★設計からの変更点:
  - `obfuscate_md` は **essay モード（タイトルの無機質化のみ）**で通す。本ファミリの md は標準 5 節（トポロジ/要件/現在の状態/設定抜粋/設問）でなく「シナリオ/設問/対応させる項目/選択肢」なので、節の再構成は当てはまらない（§7 の「obfuscate 適用」を訂正）。
  - `rebalance_position`/`choice_style` は組合せ形（(項目, 説明, 対応) の組）を素通しにするガードを追加。
  - **v_cause の一意性**: 「import が誤り」と「対向の export が誤り」は同じ不一致の両面なので、壊していない側の値が**第三の VRF によって裏付けられる**組だけを盤面に採る（例: 対向の export を他の VRF も import して到達できている→誤りは被疑側の import）。全 PE の VRF 節を提示し、症状文に「なお、X の拠点は Y と正常に通信できています」を添える。裏付けの無い組は draw で捨てる。
  - v_reach の read 形は宛先を「PE の VRF の拠点(プレフィックス)」で表す（顧客間でプレフィックスが重複する世界があるため）。
  - term 群の「真だが設問外」肢は select/select2 と allthat(正解 2 以下)に 1 つだけ入れ、判定欄で「記述は正しいが設問の主題ではない」と明示する。
- **P2（同日）**: `l_read`（4 副形= Pop Label の意味／送出時のラベル・スタック／traceroute の PHP／imp-null の意味）と `l_cause`（lsp_hole／transport_unreach）を実装。exhibit は poc/mpls-paper/results-raw.md の M1〜M5 の byte 写し（LFIB の列幅と折り返し・bindings・neighbor・discovery detail の `no route to transport addr`・traceroute の `Labels 17/20`→`Label 20`）で、行書式は selftest で実測行と一致を検査。`p_soo` は P3。
- **P2（同日）**: `p_asoverride`（cause/fix/read・worlds= w_ce_frozen/w_pe_frozen）を実装。exhibit は poc/mpls-paper/results-raw-04.md の byte 写し（`show bgp vpnv4 unicast vrf`・`advertised-routes`・CE の `show ip bgp`/`summary`）で、行の書式は selftest で実測行と一致を検査。fix は「機能する 2 候補（PE の as-override / CE の allowas-in）のうち、要件（どちら側を変えられないか）に適合する 1 つ」= works≥2・complies==1。remove-private-as は機能してしまう（顧客 AS が私設のとき）ため錯乱肢に使わない。DENIED の debug 行は先行 PoC の記録を流用（本日は soft out 構文誤りで再採取不可）。

## 12. `gen_paper_mcq.py` への組み込み点

1. `import gen_paper_mpls as gpm`（他ファミリと同じ位置）
2. `--shape` の choices と help に `mpls` を追加、`--forms` の help に `shape=mpls: select,select2,allthat,match,fix,cause,read`
3. kinds プール辞書（3 か所: 単一 shape・--forms 絞り・mixed）に `"mpls": gpm.KINDS`
4. `--forms`/`--worlds` の対応 shape に `mpls` を追加（`kind_forms` / `worlds_for` を実装）
5. `pick_draw_mpls(qseed, kind, forms, worlds)`（copp と同じ seed 探索）
6. draw/render の dispatch（`shape_i == "mpls"`）: 形の抽選→`build_choices_<form>`→`question_md_mpls`/`answer_md_mpls`
7. mixed の重み表（§11 の暫定 5%）と keep_ask（read/cause/match/select 系は設問が情報の担い手）
8. `answer_md` の種別行 `mpls/<kind>`、`gen_pack.py` の紙面既定ジャンル抽選への追加は **不要**（`--require-shape` は既定 redist,aaa,acl,bgp のまま。vpn 枠は BL-158 の設計に従う）

## 13. リスク

- 知識問は暗記されやすい → claim プールを選択肢数の 3 倍以上持ち、極性反転（「誤っているもの」）と数非明示で摩耗を遅らせる。
- IOL の表示が物理 IOS-XE と異なる可能性（imp-null / Pop Label / explicit-null の出方）→ PoC の byte 写しを正典にし、解説で「表示は IOL 17.15」と明記。
- 範囲超過の誘惑（TE・6PE・Inter-AS）→ §2 の境界で止める。
- 紙面 shape は実機フルサイクルの安全網が無い（チェックリスト 13）→ read/cause の証拠は必ず PoC 由来にする。

## 14. 参照

- ラボ資産: ENARSI-MPLS-L3VPN-01〜06、`topologies/gen_mpls_ts.py`（`--pece ebgp`）、[MPLS-SERIES.design.md](MPLS-SERIES.design.md)、[OSPF-PECE-SHAMLINK.design.md](OSPF-PECE-SHAMLINK.design.md)
- 手本: `topologies/gen_paper_copp.py`（事実ベースの cause・allthat・selftest）、`topologies/ospfpref_model.py`（純関数モデル）、[BGPBEST-PAPER.design.md](BGPBEST-PAPER.design.md)（PoC 表の書き方）
- 組合せ形の解答UI: BACKLOG BL-168（完了アーカイブ）
- 規約: [PAPER-3FAM-COPP-DMVPN-PREF.design.md](PAPER-3FAM-COPP-DMVPN-PREF.design.md) §0、[PAPER-BLUEPRINT-GAP.design.md](PAPER-BLUEPRINT-GAP.design.md) §5

## 15. 台帳

- 着手時: BACKLOG BL-169 を `PoC中`→`実装中` に更新。PoC の実測表は `poc/mpls-paper/README.md`。
- 完了時: 完了アーカイブへ移動、`problems/CATALOG.md` に紙面ファミリ行を追記、memory を更新。
