# CURRICULUM.md — NW 単元カバレッジ台帳(紙面×ラボ)

**役割**: 4 資格(CCNA 200-301 v1.1 / ENCOR 350-401 v1.2 / ENARSI 300-410 v1.1 / CCIE EI v1.1 Lab)の
ブループリントを**単元(unit)** に再編し、単元ごとに「紙面」「ラボ」の作り込み状態を持つ台帳。
`BACKLOG.md` は雑多 TODO(課題単位)、**本台帳は単元単位の到達度**。両者は `BL-` 番号と `U-` 番号で相互リンクする。

制定: 2026-09-21(ユーザ指示「ブループリントで抜けている単元を紙面・ラボ両方で洗い出し、単元ごとに作り込む」)。
ブループリント原典(Cisco 公開 PDF の抽出テキスト)は `private/blueprints/` に保管(取得 2026-09-21)。
ENCOR は **v1.2(2025)** を正とする(v1.1 との差= 無線が全面削除・PTP 追加・MSDP/bidir 追加・
Catalyst Center の AI ワークフロー追加・ハードウェア/ソフトウェアスイッチング項の削除)。

## 運用ルール

1. **更新タイミング**: 紙面ファミリ・ラボ生成器・固定問題が「実機検証済・出題可」になった時
   (= `problems/CATALOG.md` へ追記するのと同じタイミング)に、該当単元の紙面/ラボ欄と「資産」欄を更新し、
   §5 の作り込み記録に 1 行追記する。
2. **着手時**: 単元を作り込み始めたら、まず BACKLOG に `BL-` を起票(または既存行を更新)し、
   本台帳の該当行「関連BL」に番号を書く。台帳の行に作業ログは書かない(BACKLOG/design.md へ)。
3. **段階**(2026-09-21 ユーザ合意・単元ごとにこの順で埋める):
   - 紙面 **P1**= 網羅的な解説穴埋め(shape=cloze・単元の知識項目表 `curriculum/<U>-<名>.md` を全セクション被覆して初めて ◎)
     → **P2**= 試験形式の選択問(問題集/Cisco 調・既存の shape 群)
   - ラボ **L1**= 最小限の基本形の構築(難 2・2〜4 台) → **L2**= 実務規模の構築(要件書駆動・難 4) → **L3**= 実務規模の TS(生成器・難 4〜5)
     → **L4**= 他単元との組合せ・応用(連鎖 TS・キャンパス等)
   - **対象の絞り**: P1/P2 と L1 は全単元。L2/L3 はブループリントが configure/verify/troubleshoot 級の単元だけ
     (describe 級・実機不可は `—`)。L4 は機会があれば。L2 と L3 は同じ盤面を共有してよい(構築問と `--broken` TS を 1 生成器から)。
4. **判定の物差し**(段階ごと):
   - `◎` 厚い= 生成器または複数ファミリがあり、故障種/kind が 6 以上・seed で盤面が変わる
   - `○` ある= 出題可の資産が 1 本以上あるが kind/故障種が少ない、または固定問題のみ
   - `△` 薄い= 他単元の副産物・1 kind・PoC 止まり・設計書のみ
   - `✗` 空白= 資産なし
   - `—` 対象外/実機不可(紙面のみ受け皿、または本 PJ の範囲外と決めたもの)
5. **範囲**: 4 資格のブループリント外でも、掲載単元に関連するものは範囲内(例: IS-IS の AD、
   VyOS/FRR/Junos での同一単元、Linux 側 DNS/DHCP/RADIUS)。「周辺」列に書く。
6. **PVT 系**は本台帳に出自を書かない(`private/CATALOG.md` 参照とだけ書く)。
7. **機械可読の対応表**: 単元→紙面 shape/kind・ラボ genre/ID は `topologies/units.yml`(BL-213)。
   パックは `scripts/pack.sh new --profile ccna|encor|enarsi|ccie|vendor|U-xx,…` でこの表から範囲を絞る。
   資産を足したら units.yml の該当単元にも 1 行足す(台帳の「資産」欄と同時)。
8. **年次見直し**: ブループリント改版時に `private/blueprints/` を更新し、§4 の対応表を差し替える。

凡例(段階列)= P1 穴埋め / P2 選択問 / L1 最小構築 / L2 実務構築 / L3 実務 TS / L4 複合。凡例(資格列)= 該当項番。`(d)`= describe/explain 級(知識のみ・紙面が主戦場)、無印= configure/verify/troubleshoot 級。

## 1. 単元カバレッジ表

### A. L2 / キャンパススイッチング

| U | 単元 | CCNA | ENCOR | ENARSI | CCIE | P1 | P2 | L1 | L2 | L3 | L4 | 資産(現状) | 抜け・薄い点 | 関連BL |
|---|------|------|-------|--------|------|----|----|----|----|----|----|-----------|-------------|--------|
| U-A1 | VLAN/トランク(802.1Q・native・DTP・VTP・pruning・voice VLAN) | 2.1 2.2 | 3.1.a | — | 1.1.c | ✗ | ✗ | ✗ | ✗ | △ | ○ | CAMPUS-TS-01 内(vtp transparent)・**L4= gen_enterprise.py(GEN-ENT・拠点構築)** | 専用問なし。DTP/native 不一致・VTP 事故・allowed vlan 絞りの TS が空白 | BL-225 |
| U-A2 | EtherChannel(LACP/PAgP/static・L2/L3・負荷分散・misconfig guard) | 2.4 | 3.1.b | — | 1.1.d | ✗ | ✗ | ○ | ✗ | ○ | ○ | ENCOR-LAG-01/LAG-TS-01・gen_l2_troubleshoot・**L4= gen_enterprise.py(GEN-ENT・拠点構築)** | 紙面ゼロ。L3 EtherChannel・load-balance 方式・misconfig guard 未 | BL-003 BL-225 |
| U-A3 | STP(PVST+/RSTP/MST・root/port priority・cost・timers・PortFast/BPDU guard/filter・loop/root guard) | 2.5 | 3.1.c | — | 1.1.e | ◎ | ◎ | ◎ | ◎ | ◎ | ◎ | **L1〜L4= gen_stp.py(build L1・build L2・ts・--world mst= MST+旧機境界・**--world 3tier= 3 層キャンパス 構築/TS(難5・BL-221)・保護機構の記述方式 port/global/any(BL-222)**)**・**L3= gen_stp.py(GEN-STP・故障 10 種・E2E 済)**・**P1= cloze_kb_stp.py 6 セクション(t_basics/t_rstp/t_modes/t_tuning/t_guard/t_read 世界)・知識項目表 curriculum/U-A3-stp.md 47+5 項目**・**P2= gen_paper_stp.py 10 kind(瞬発 s_basic/s_rstp/s_modes・思考 s_elect/s_read/s_mst/s_tuning/s_guard/s_ts/s_rolemap=全ポート記入・計算器 stp_model.py)**・照合表 curriculum/U-A3-stp.sources.md・CAMPUS-TS-01 内・PoC 済(poc/stp 第1・2回) | ラボは L1〜L4 完了(2026-09-22)。実行中の pvst→rapid 移行は IOL が不安定で出題しない。P2 未被覆= #10 TCN・#51 誤接続・summary 読解。構築の要件構成が固定(BL-220)・盤面が DS2+AS2 の 1 系のみ=難2 と難5 の段が無い(BL-221) | BL-076 BL-214 BL-216 BL-220 BL-221 BL-226 BL-227 |
| U-A4 | スイッチ管理(MAC テーブル・errdisable recovery・L2 MTU・CDP/LLDP・UDLD) | 1.13 2.3 | — | — | 1.1.a 1.1.b | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | なし | errdisable 復旧・UDLD・CDP/LLDP 読解はすべて空白 | — |
| U-A5 | L2 セキュリティ(DHCP snooping/option 82・DAI・IPSG・port security・storm control・PVLAN・VACL/PACL) | 5.7 | — | — | 4.2.a | ✗ | ✗ | ○ | △ | ✗ | ✗ | ENCOR-VACL-01/02 | VACL 以外空白。**ioll2 のデータプレーン遮断が不発の前例**(IPv6 FHS)→ DHCP snooping/DAI/IPSG は PoC で可否を先に確認 | — |
| U-A6 | FHRP(HSRP/VRRP/GLBP・IPv6 RS/RA 冗長・track 連携) | 3.5 | 3.3.c | — | 4.5.a | ✗ | ○ | ○ | ○ | ✗ | ○ | ENCOR-FHRP-01・UM2-BUILD・CAMPUS-TS・**P2= gen_paper_fhrp.py(h_path 往路/復路の全記入・h_acl SVI ACL 込み)**・**L4= gen_enterprise.py(GEN-ENT・拠点構築)** | P1(穴埋め)無し。VRRP/GLBP・IPv6 HSRP・track が未 | BL-228 BL-225 |
| U-A7 | トラフィックキャプチャ(SPAN/RSPAN/ERSPAN・Embedded Packet Capture) | — | 4.3 | — | 4.7.a | ✗ | ✗ | ○ | ✗ | ✗ | ✗ | ENCOR-SPAN-01/RSPAN-01 | ERSPAN・EPC 未。「答えが pcap の中にしかない」TS は構想のみ | BL-062 |

### B. ルーティング基礎・経路制御

| U | 単元 | CCNA | ENCOR | ENARSI | CCIE | P1 | P2 | L1 | L2 | L3 | L4 | 資産(現状) | 抜け・薄い点 | 関連BL |
|---|------|------|-------|--------|------|----|----|----|----|----|----|-----------|-------------|--------|
| U-B1 | 経路表/転送判断(AD・最長一致・メトリック・GW of last resort・static/floating・v4/v6) | 3.1 3.2 3.3 | — | 1.1 | 1.2.a 1.2.b | △ | ○ | ○ | — | ✗ | — | rtbasic・ring AD 世界・cloze order(AD 表)・各ラボ | IPv6 static/floating の紙面・「static のマルチキャスト」は周辺 | — |
| U-B2 | ルートフィルタ/route-map/prefix-list/distribute-list/offset-list | — | 3.2.b | 1.2 | 1.2.g | ✗ | ◎ | ○ | ◎ | ◎ | ◎ | chain/ring/ospfv3pl/name_clash・RTCTL・道場 | 飽和 | — |
| U-B3 | 再配送(全プロトコル・ループ防止・タグ・seed metric) | — | — | 1.3 1.4 | 1.2.h | ✗ | ◎ | ○ | ○ | ◎ | ◎ | 7 shape・gen_redist_field ほか | 飽和(**主役でない=現状維持**) | BL-117 |
| U-B4 | 集約(EIGRP summary/leak-map・OSPF range/summary-address・BGP aggregate/as-set/suppress-map・auto-summary) | — | 3.2.b | 1.5 | 1.3.e 1.5.e | ✗ | ○ | ○ | ✗ | △ | ✗ | leakmap・eigrpkb autosum・ospfv3pl summarize・GEN-AGG・BGP-AGGREGATE-01 | BGP aggregate の as-set/suppress-map/attribute-map・OSPF summary-address(ASBR 側)の紙面 | BL-096 BL-117① |
| U-B5 | PBR(IPv4/IPv6・local policy・set ip next-hop verify-availability) | — | 3.2.d(d) | 1.6 | 1.2.c | ✗ | ○ | ○ | ○ | ✗ | ✗ | pbr 紙面・ENCOR-PBR-01/02 | IPv6 PBR・track 連携 PBR | BL-037 BL-082 |
| U-B6 | VRF-Lite / VRF-aware ルーティング / VRF 間リーク(route-map・VASI) | 1.12(d) | 2.2.a | 1.7 1.9 1.11 | 1.2.d 1.2.e 1.2.f | ✗ | ✗ | ○ | ○ | ◎ | ○ | VRF-LEAK/VRF-TS/VRF-NAT・EIGRP-VRF・H 型(private)・VRFMAZE | **紙面ゼロ**(1.7 明示)。VASI・BGP 版 H 型未 | BL-117④ BL-102② |
| U-B7 | BFD(各プロトコル・timers・echo) | — | — | 1.8(d) | 1.2.j | ✗ | △ | ○ | — | ✗ | — | bfd variant(12 問)・svc bfd kind(1) | 紙面ゼロ(describe 級=紙面向き)。OSPFv3/BGP の bfd 変種 | BL-035 |
| U-B8 | ルーティング認証(OSPF/EIGRP/BGP/RIP・key chain・SHA) | — | — | 1.9.b 1.10.b 1.11.b | 1.2.i | ✗ | ○ | ○ | — | ○ | ✗ | ospfdbg auth_*・bgpdbg pw_*・OSPF-AUTH-01・複合 TS | EIGRP 認証の紙面・key chain ローテーション・OSPFv3 IPsec 認証の紙面 | — |
| U-B9 | L3 MTU / パス MTU(OSPF MTU・GRE/IPsec・MPLS コア) | — | — | — | 1.2.k | △ | △ | ✗ | — | △ | ✗ | ospfdbg mtu・cloze d_ MTU | MPLS コア MTU ブラックホール TS・tcp adjust-mss の効果採点 | BL-053 |

### C. EIGRP

| U | 単元 | CCNA | ENCOR | ENARSI | CCIE | P1 | P2 | L1 | L2 | L3 | L4 | 資産(現状) | 抜け・薄い点 | 関連BL |
|---|------|------|-------|--------|------|----|----|----|----|----|----|-----------|-------------|--------|
| U-C1 | 隣接/認証/K 値/AS/パッシブ(EIGRP 版 debug 読解) | — | 3.2.a | 1.9.b | 1.3.a | ✗ | ✗ | ○ | — | ◎ | ✗ | gen_eigrp_complex_ts・H 型 | **ospfdbg/bgpdbg はあるのに eigrpdbg が無い** | — |
| U-C2 | ベストパス(RD/FD/FC/successor/FS・classic/wide metrics) | — | 3.2.a | 1.9.c 1.9.f | 1.3.b | ✗ | ○ | ○ | — | ✗ | ✗ | pref(fc/fs/variance 4 kind)・ENCOR-EIGRP-VARIANCE-01 | wide metrics(named mode 64bit・`metric rib-scale`)・トポロジ表読解 | — |
| U-C3 | stub / leak-map / query 境界 / SIA / graceful shutdown | — | — | 1.9.d | 1.3.c 1.3.e | ✗ | △ | ✗ | ✗ | ○ | ✗ | leakmap 紙面・ENARSI-EIGRP-SIA-01 | stub の紙面(receive-only/connected/summary)・SIA 紙面・graceful shutdown | BL-096 |
| U-C4 | named mode / AF / VRF / PE-CE | — | — | 1.9 | 1.3.d | ✗ | ○ | ○ | ✗ | ◎ | ✗ | eigrpkb named_mode・EIGRP-VRF-01・gen_eigrp_vrf_ts・H 型 | PE-CE(MPLS 内 EIGRP・SoO) | BL-070③ BL-052 |
| U-C5 | 負荷分散(ECMP/variance/maximum-paths) | — | 3.2.a | 1.9.e | 1.3.b | ✗ | ○ | ○ | — | ✗ | — | pref variance_*・VARIANCE-01 | — | — |
| U-C6 | EIGRPv6 | — | — | 1.9.a | — | ✗ | △ | ✗ | ✗ | ○ | ✗ | v6redist・gen_eigrpv6_complex_ts | 紙面は再配送文脈のみ | BL-033 |

### D. OSPF

| U | 単元 | CCNA | ENCOR | ENARSI | CCIE | P1 | P2 | L1 | L2 | L3 | L4 | 資産(現状) | 抜け・薄い点 | 関連BL |
|---|------|------|-------|--------|------|----|----|----|----|----|----|-----------|-------------|--------|
| U-D1 | 隣接/認証(hello/dead・area・MTU・nettype・auth・RID 重複・prio 0・passive・単方向) | 3.4 | 3.2.b | 1.10.b | 1.4.a | ✗ | ◎ | ○ | ○ | ◎ | ○ | ospfdbg 12 変種・GEN-TS・OSPF-MADJ-01・OSPF-AUTH-01 | 飽和 | — |
| U-D2 | ネットワーク種別/エリア種別/ルータ種別/仮想リンク/LSA タイプ | 3.4 | 3.2.a 3.2.b | 1.10.c | 1.4.c | ✗ | △ | ○ | ✗ | △ | ✗ | ospfdbg nettype/stub・OSPF-STUB/NSSA-01・MADJ | **LSA タイプ読解(LSDB)・仮想リンク・totally stubby/NSSA の紙面**が薄い(cloze 次候補) | — |
| U-D3 | パス選好(intra>inter>E1>E2・cost・forward metric・FA) | — | 3.2.a | 1.10.d | 1.4.d | ✗ | ○ | ✗ | ✗ | ○ | ✗ | pref(OSPF 4 kind)・GEN-PATH | forwarding address 罠 | BL-029 |
| U-D4 | OSPFv3 / AF 方式 / IPv6 | — | 3.2.b | 1.10.a | 1.4.b | ✗ | ○ | ○ | ○ | ○ | ✗ | ospfv3pl・v6redist・OSPFV3-01/AREA-01・gen_ospfv3_complex_ts | OSPFv3 AF 方式 vs 従来構文の混在は紙面未 | BL-035 |
| U-D5 | 最適化(default-information originate・stub router max-metric・LSA throttle/SPF tuning・prefix suppression・GTSM・graceful shutdown) | — | — | — | 1.4.e 1.4.f | ✗ | ✗ | ✗ | — | ✗ | ✗ | なし | **CCIE 帯の完全空白** | — |
| U-D6 | 集約・フィルタ(area range・summary-address・filter-list・dl in) | — | 3.2.b | 1.5 | 1.2.g | ✗ | ○ | ○ | ✗ | ○ | ✗ | ospfv3pl・GEN-AGG・GEN-TWIST | — | — |
| U-D7 | OSPF×VRF / PE-CE(sham-link・DN bit・domain-id・capability vrf-lite) | — | — | 1.7 | 1.2.e | ✗ | ✗ | ○ | ✗ | ○ | ✗ | VRFLITE-DNBIT-01・H 型 OSPF 版(private) | sham-link/backdoor 族は設計書のみ | BL-140 |

### E. BGP

| U | 単元 | CCNA | ENCOR | ENARSI | CCIE | P1 | P2 | L1 | L2 | L3 | L4 | 資産(現状) | 抜け・薄い点 | 関連BL |
|---|------|------|-------|--------|------|----|----|----|----|----|----|-----------|-------------|--------|
| U-E1 | 隣接/認証(update-source・multihop・ttl-security・peer group/template・dynamic neighbor・4-byte/private AS・timers・active/passive・states) | — | 3.2.c | 1.11.b | 1.5.a | ✗ | ○ | ○ | ✗ | ◎ | ○ | bgpdbg 6 変種・gen_bgp_complex_ts 26 故障・ENARSI-BGP-01 mh-auth | peer group/template・dynamic neighbor・ttl-security・timers・4-byte AS 表記(asdot)は両方薄い | BL-061 |
| U-E2 | ベストパス/属性(weight/LP/origin/MED/AS-path・multipath・deterministic-med) | — | 3.2.c | 1.11.c | 1.5.b | △ | ○ | ○ | ○ | ◎ | ✗ | bgpbest 10 kind・cloze order・BGP-POLICY-01・ring・GEN-BGPBEST | multipath(iBGP/eBGP)・always-compare-med・deterministic-med | — |
| U-E3 | ポリシー(in/out フィルタ・community std/ext・conditional advertisement・ORF・multihoming) | — | — | 1.11.e | 1.5.c | ✗ | △ | ○ | ✗ | ○ | ✗ | bgppol 2 kind・BGP-COMM-01・ring prefix_steer・道場 | **conditional advertisement・ORF・extended community(MPLS 外)・multihoming 設計**が空白 | BL-060 |
| U-E4 | AS-path 操作(local-as・allowas-in・remove-private-as・prepend・regexp) | — | — | 1.11.e | 1.5.d | ✗ | △ | ○ | ✗ | ✗ | ✗ | 道場 aspath・L3VPN-05 allowas-in・mpls as-override | local-as/remove-private-as 両方空白・regexp は道場のみ | — |
| U-E5 | RR / スケール(cluster・originator・RR 配下の next-hop) | — | — | 1.11.d | 1.5.e | ✗ | ✗ | ✗ | ✗ | ○ | ◎ | GEN-BGPRR・GEN-CHAIN | 紙面ゼロ(1.11.d 明示) | — |
| U-E6 | 集約(aggregate-address・as-set・summary-only・suppress/unsuppress-map) | — | — | 1.5 | 1.5.e | ✗ | ✗ | ○ | ✗ | ✗ | ✗ | BGP-AGGREGATE-01 | 紙面ゼロ | — |
| U-E7 | 運用(soft-reconfig/route refresh・dampening・sync・next-hop-self/tracking・clear の要否) | — | — | 1.11.b | 1.5.f | △ | △ | ✗ | ✗ | ○ | ✗ | BGP-SYNC-01・NHSELF-01・cloze 一部 | soft-reconfig/route refresh・dampening の紙面 | BL-004 |
| U-E8 | BGP AF(IPv6・VPNv4/v6)・BGP×VRF-Lite | — | — | 1.11.a 1.11 | 1.5 | △ | △ | ○ | ✗ | ✗ | ○ | BGP-IPV6-01・MPLS 群・mpls 紙面 | H 型 BGP 版・IPv6 eBGP の紙面 | BL-102② |

### F. マルチキャスト

| U | 単元 | CCNA | ENCOR | ENARSI | CCIE | P1 | P2 | L1 | L2 | L3 | L4 | 資産(現状) | 抜け・薄い点 | 関連BL |
|---|------|------|-------|--------|------|----|----|----|----|----|----|-----------|-------------|--------|
| U-F1 | IGMP v2/v3・IGMP snooping/querier/filter・PIM snooping・MLD | — | 3.3.d(d) | — | 1.6.a | ◎ | ✗ | ✗ | ✗ | ✗ | ✗ | **P1= cloze_kb_mcast.py(g_basics/g_igmp/g_l2)**・知識項目表 curriculum/U-F-mcast.md・PoC poc/mcast | P2・ラボが空白。IGMP filter は ioll2 に無い(文書ベース) | BL-077 BL-217 |
| U-F2 | PIM SM/SSM/bidir・RP(static/BSR/Auto-RP)・RPF・boundary・anycast RP(MSDP)・multipath | — | 3.3.d(d) | — | 1.6.b 1.6.c | ◎ | ✗ | ✗ | ✗ | ✗ | ✗ | **P1= cloze_kb_mcast.py(g_pim/g_rp/g_ssm/g_rpf/g_read 世界)**・知識項目表 curriculum/U-F-mcast.md・PoC poc/mcast(PIM-SM/BSR/Auto-RP/SSM/bidir/MSDP 実測) | P2・ラボ L1〜L3 が空白。PIM snooping・PIMv6 anycast・J/P の 3.5 倍は未(資料割れ/未実測) | BL-077 BL-217 |

### G. VPN / トランスポート / オーバーレイ

| U | 単元 | CCNA | ENCOR | ENARSI | CCIE | P1 | P2 | L1 | L2 | L3 | L4 | 資産(現状) | 抜け・薄い点 | 関連BL |
|---|------|------|-------|--------|------|----|----|----|----|----|----|-----------|-------------|--------|
| U-G1 | GRE(p2p・keepalive・MTU/MSS・recursive routing) | — | 2.2.b | — | 3.1 | △ | ✗ | ○ | ✗ | ✗ | ○ | GRE-01/02・WANHA・cloze d_ MTU | 再帰ルーティング(tunnel 自壊)の TS・紙面 | — |
| U-G2 | IPsec(IKEv1/v2・sVTI/crypto map/profile・PSK/証明書・NAT-T) | 5.5(d) | 2.2.b | 2.3.c | 3.3.a | ○ | ✗ | ○ | ◎ | ○ | ○ | cloze d_ IPsec 連鎖/IKE 表・IPSEC-VTI/IKEV2/GREIPSEC-MAP・S2SVPN+D2 | 証明書認証・NAT-T・crypto map hub 折返し | BL-209 |
| U-G3 | DMVPN(Phase 1/2/3・NHRP・spoke-to-spoke・dual hub・IPsec/IKEv2 PSK・EIGRP/OSPF 注意点) | — | — | 2.3 | 3.3 | ○ | ○ | ○ | ○ | ◎ | ○ | dmvpn 紙面 4 kind+cloze d_ 10・PHASE3/DMVPN-BGP/DMVPN-IPSEC・gen_dmvpn_ts 16・wreck | **dual hub**(CCIE 明記)・IPv6 オーバーレイ・per-tunnel QoS が両方空白 | BL-037 |
| U-G4 | MPLS 基礎(label stack・LSR・LSP・LDP・mpls ping/traceroute) | — | — | 2.1(d) | 3.2.a | ○ | ○ | ○ | ✗ | ○ | ✗ | mpls 紙面 t_/l_・cloze m_ 21・L3VPN-01・GEN-MPLSTS | **LDP の中身が薄い**(session/transport/MD5/IGP sync/label filtering/TTL propagate/mpls ping・traceroute) | BL-021 |
| U-G5 | MPLS L3VPN(RD/RT/VPNv4/v6・PE-CE BGP/OSPF/EIGRP/static・as-override/allowas-in/SoO・extranet・RR・hub&spoke) | — | — | 2.2(d) | 3.2.b | ○ | ○ | ○ | ○ | ◎ | ○ | mpls 紙面 v_/p_・L3VPN-01〜06・gen_mpls_ts(--pece ebgp) | **12 台問が主でパックに載りにくい**(CML 20 上限)→ 5〜7 台版が無い。VPNv6/6VPE・PE-CE OSPF/EIGRP・SoO・VPNv4 RR・Inter-AS・CE 視点 TS が空白 | BL-016 BL-017 BL-018 BL-052 BL-053 BL-070③ BL-140 |
| U-G6 | LISP / VXLAN / EVPN(概念・制御/データプレーン) | — | 2.3(d) | — | 2.1.b | ✗ | ✗ | ○ | ✗ | ✗ | ✗ | SDA-LISP-01・EVPN-VXLAN-01 | 紙面ゼロ(ENCOR describe → 紙面必須) | — |
| U-G7 | SD-WAN(vManage/vBond/vSmart・OMP/TLOC・templates・centralized/localized policy・AAR) | — | 1.2(d) | — | 2.2 | ✗ | ✗ | △ | — | — | ✗ | FGT-SDWAN-01(非 Cisco)・BL-050 PoC 退避中 | **ENCOR describe + CCIE 25% 帯の半分が空白**。紙面(用語・OMP 属性・ポリシー読解)から | BL-050 |
| U-G8 | SD-Access(underlay/overlay・LISP/BGP CP・VXLAN・TrustSec/SGT/SGACL・fabric roles・border handoff/fusion・extended node) | — | 1.3(d) | — | 2.1 | ✗ | ✗ | △ | ✗ | ✗ | ✗ | SDA-LISP-01(ガイド付き) | 紙面ゼロ。fusion router handoff・SGT は空白 | — |

### H. セキュリティ

| U | 単元 | CCNA | ENCOR | ENARSI | CCIE | P1 | P2 | L1 | L2 | L3 | L4 | 資産(現状) | 抜け・薄い点 | 関連BL |
|---|------|------|-------|--------|------|----|----|----|----|----|----|-----------|-------------|--------|
| U-H1 | AAA(RADIUS/TACACS+/local・method list・authorization・accounting・deadtime) | 5.8(d) | 5.1.b | 3.1 | 4.1.b | ○ | ◎ | ○ | ○ | ✗ | ○ | aaa 15 故障 9 形・cloze a_ 9・GEN-AAAGRP/RADIUS・EDGE-HARDEN | **TACACS+ 空白**(ユーザ決定で後回し・tac_plus は Linux で可)・accounting 薄い | BL-103 BL-105 BL-108 |
| U-H2 | IPv4 ACL(standard/extended/named/sequence/**time-based**・object-group・established・適用点) | 5.6 | 5.2.a | 3.2.a | 4.2.b | ✗ | ◎ | ○ | ○ | ✗ | ○ | acl 紙面・ACL 道場・ENCOR-ACL-*・hardmode acl_wall・**L4= gen_enterprise.py(GEN-ENT・拠点構築)** | **time-based ACL 空白**(ENARSI 3.2.a 明記)・適用点主題化 | BL-109 BL-121 BL-225 |
| U-H3 | IPv6 traffic filter | — | — | 3.2.b | 4.2.b | ✗ | ◎ | ✗ | ✗ | ○ | ✗ | aclv6 6 kind・gen_v6addr_ts acl_blocks_ra | — | — |
| U-H4 | uRPF(strict/loose/allow-default/ACL 例外・IPv6 uRPF) | — | — | 3.2.c | 4.2.b | ✗ | ◎ | ○ | ✗ | ○ | ✗ | urpf 紙面・ENARSI-URPF-01・gen_urpf_ts | IPv6 uRPF | BL-031 BL-032 |
| U-H5 | CoPP / CPPr(control plane protection) | — | 5.2.b | 3.3 | 4.1.a | ✗ | ◎ | ○ | ○ | ✗ | ○ | copp 12 kind・COPP-01/02/03 | CPPr(host/transit/cef-exception サブIF)空白 | — |
| U-H6 | IPv6 FHS(RA guard・DHCPv6 guard・binding table・device tracking・ND inspection・source guard) | — | — | 3.4(d) | 4.2.c | ○ | ○ | ○ | ○ | ○ | ✗ | fhs 紙面 3 kind・cloze f_ 9・gen_v6addr_build(fhs) | **source/prefix/destination guard は ioll2 で遮断不発**(文書ベース維持)・IOSvL2 は FHS 非機能 | BL-036 BL-146 |
| U-H7 | デバイスアクセス(line/local user・privilege level・parser view・SSH v2・SCP・HTTP(S)・login block・password 種別) | 2.8 5.3 | 5.1.a | 4.1 | 4.3.a | ✗ | ○ | ○ | ✗ | ✗ | ✗ | svc ssh/copy・aaa line/vty/con/enable・EDGE-HARDEN | privilege level/parser view・login block-for・SCP・HTTPS サーバ・enable secret 種別(type 5/8/9) | — |
| U-H8 | ネットワークセキュリティ設計(NGFW・IPS・endpoint・TrustSec/MACsec・802.1X/MAB/WebAuth) | 1.1.c(d) 5.1 5.2(d) | 5.4(d) | — | — | ✗ | ✗ | △ | — | — | — | ASAv/FGT 問(非 Cisco・周辺) | **ENCOR describe が紙面ゼロ**。802.1X はラボ化候補(FreeRADIUS+ioll2・要 PoC) | BL-041 BL-045 |
| U-H9 | 無線セキュリティ(WPA/2/3・PSK/EAP・WLAN GUI) | 5.9 5.10 | — | — | — | ✗ | ✗ | — | — | — | — | なし | CCNA のみ(ENCOR v1.2 で無線は削除)。実機不可→紙面のみ | — |
| U-H10 | REST API セキュリティ(認証方式・トークン・TLS) | 6.5(d) | 5.3(d) | — | — | ✗ | ✗ | — | — | — | — | なし | 紙面のみの受け皿 | — |

### I. インフラサービス / 運用

| U | 単元 | CCNA | ENCOR | ENARSI | CCIE | P1 | P2 | L1 | L2 | L3 | L4 | 資産(現状) | 抜け・薄い点 | 関連BL |
|---|------|------|-------|--------|------|----|----|----|----|----|----|-----------|-------------|--------|
| U-I1 | NTP(client/server/master/auth/source/stratum)・**PTP** | 4.2 | 3.3.a | — | 4.5.b | ✗ | ○ | ✗ | ✗ | ✗ | △ | svc ntp・EDGE-HARDEN 一部 | NTP 専用 TS ラボ無し・**PTP は ENCOR v1.2 新規で空白**(紙面) | — |
| U-I2 | NAT/PAT(static/dynamic/PAT/policy/VRF-aware/VASI・overlapping) | 4.1 | 3.3.b | — | 4.5.d | ✗ | ✗ | ✗ | ○ | ✗ | ○ | VRF-NAT-01・INTEGRATED-01・S2SVPN D2(overlapping)・**L4= gen_enterprise.py(GEN-ENT・拠点構築)** | **紙面ゼロ**・NAT 専用 TS 生成器無し・VASI 空白 | BL-225 |
| U-I3 | DHCPv4(server/relay/options/client・helper・conflict) | 4.3 4.6 | — | 4.4 | 4.5.c | ✗ | △ | ○ | ✗ | ◎ | ○ | svc light dhcp_helper・DHCP-01・gen_dhcp_ts・(private) リレー連鎖・**L4= gen_enterprise.py(GEN-ENT・拠点構築)** | **紙面が 1 kind のみ**(4.4 は 25% 帯)。ラボ資産の紙面転用が未 | BL-069 BL-225 |
| U-I4 | DHCPv6/SLAAC(stateless/stateful・M/O flag・relay・**PD**) | — | — | 4.4 | 4.5.c | ✗ | ○ | ○ | ○ | ◎ | ✗ | dhcp6 紙面・DHCPV6-01・gen_v6addr_ts/build | PD は両方空白 | BL-034 |
| U-I5 | SNMP v2c/v3(view/group/user・trap/inform・ACL・engineID) | 4.4(d) | 4.1 | 4.2 | 4.3.b | ○ | ○ | ○ | ✗ | ○ | ✗ | svc snmp・cloze s_・gen_snmpv3_ts・Zabbix 構築 | v2c community/ACL の TS・engineID 変更で user 消失の罠 | — |
| U-I6 | ロギング/デバッグ(local/buffered/syslog・severity・timestamps・conditional debug・config change notification・archive) | 4.5(d) | 4.1 | 4.3 | 4.3.c | △ | ○ | ✗ | ✗ | ✗ | ✗ | svc log/archive・ospfdbg/bgpdbg 読解・cloze order syslog | **conditional debug(`debug condition`/`debug platform condition`)** 両方空白・config change logging 空白 | — |
| U-I7 | IP SLA / track / track list(ICMP/UDP jitter/TCP/HTTP・responder・boolean list・threshold) | — | 4.4 | 4.5 | 4.6.a 4.6.b | ✗ | △ | ○ | ○ | ◎ | ○ | svc ipsla_sched/light・IPSLA-01/02・gen_ipsla_ts・WANHA・**L4= gen_enterprise.py(GEN-ENT・拠点構築)** | 紙面が薄い(4.5 は 25% 帯)。track list・jitter/UDP プローブ(responder)空白 | BL-148 BL-225 |
| U-I8 | NetFlow v5/v9 / FNF(record/exporter/monitor/sampler・top-talkers) | — | 4.2 | 4.6 | 4.6.c | ○ | △ | ○ | ✗ | ◎ | ✗ | cloze s_ FNF 4・svc light・FNF-01・gen_fnf_ts | sampler・IPv6 FNF | — |
| U-I9 | EEM(applet・event syslog/cli/timer/track・action) | — | 6.6 | — | 5.2.a | ✗ | ✗ | ○ | ✗ | ✗ | ✗ | ENCOR-EEM-01 | **紙面ゼロ**(ENCOR「applet を構成せよ」→ fix/read 形が要る) | — |
| U-I10 | Catalyst Center(assurance・device 360・path trace・PnP/LAN automation・AI ワークフロー) | — | 4.5(d) | 4.7 | 2.1.a | ✗ | △ | — | — | — | — | svc dnac 1 kind | 実機不可→**紙面が唯一の受け皿なのに 1 kind** | — |
| U-I11 | QoS MQC(classification/marking・trust boundary・NBAR・policing/shaping・LLQ/CBWFQ/WRED・HQoS・DSCP/CoS map・PHB) | 4.7(d) | 1.4 | — | 4.4 | △ | ✗ | ○ | ✗ | ✗ | ✗ | QOS-CLASS/POLICE/LLQ-01 | **紙面ゼロ**(ENCOR「QoS 設定を解釈せよ」→ read 形が本命)。shaping/WRED/HQoS/NBAR・生成器 | BL-025 BL-026 |
| U-I12 | ファイル/イメージ管理((T)FTP/SCP・copy/archive・boot system・ROMMON・パスワード復旧・ライセンス) | 4.9(d) | — | 4.1.c | — | ✗ | △ | ✗ | — | ✗ | — | svc copy/archive | ラボ無し(IOL で copy tftp/scp は可) | — |
| U-I13 | CEF/RIB/FIB/隣接・スイッチング概念(MAC 学習/フラッディング) | 1.13 3.2 | — | — | — | ✗ | ○ | — | — | — | — | svc cef 3 形 | CCNA の基礎読解(MAC テーブル・フレーム転送)は空白 | — |
| U-I14 | 診断ツール(ping/traceroute 拡張オプション・packet-trace・EPC・IOS-XE data path) | — | 4.1 | 4.3 | 4.7.b | ✗ | ✗ | ✗ | — | ✗ | ✗ | なし | 完全空白(CCIE 4.7.b・cat8000v で可) | BL-062 |

### J. IPv6 基礎

| U | 単元 | CCNA | ENCOR | ENARSI | CCIE | P1 | P2 | L1 | L2 | L3 | L4 | 資産(現状) | 抜け・薄い点 | 関連BL |
|---|------|------|-------|--------|------|----|----|----|----|----|----|-----------|-------------|--------|
| U-J1 | IPv6 アドレス種別/EUI-64/LL/anycast/multicast/prefix/計算 | 1.8 1.9 | — | — | — | ✗ | ✗ | ○ | — | ✗ | — | IPV6-STATIC-01・SLAAC-STATIC-01 | 紙面ゼロ(CCNA 基礎・瞬発枠向き) | — |
| U-J2 | ND/RS/RA/DAD/RA フラグ(M/O/A)・RA 冗長 | — | — | 4.4 | 4.5.a | ○ | ○ | ○ | — | ○ | ✗ | aclv6 nd・fhs・dhcp6 mode・v6addr | — | — |
| U-J3 | IPv6 トンネリング/6PE/6VPE/NAT64(周辺) | — | — | — | — | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | なし | 範囲外寄り(遠期) | BL-021 |

### K. 自動化 / プログラマビリティ / AI

| U | 単元 | CCNA | ENCOR | ENARSI | CCIE | P1 | P2 | L1 | L2 | L3 | L4 | 資産(現状) | 抜け・薄い点 | 関連BL |
|---|------|------|-------|--------|------|----|----|----|----|----|----|-----------|-------------|--------|
| U-K1 | データ形式(JSON/XML/YAML/Jinja)・Python 基礎読解 | 6.7 | 6.1 6.2 | — | 5.1 | ✗ | ✗ | △ | — | — | — | ANSIBLE-04-VARS | 紙面ゼロ(JSON 読解・Python スクリプト読解は ENCOR 明示) | BL-010 |
| U-K2 | REST API(CRUD/verbs/status code/認証)・Catalyst Center API・SD-WAN Manager API | 6.5(d) | 6.4 6.5 | — | 5.3.a 5.3.b | ✗ | ✗ | △ | — | — | — | NETAUTO-03-RESTCONF | **紙面ゼロ**。DNAC/vManage は実機無し→紙面 or DevNet sandbox | — |
| U-K3 | NETCONF/RESTCONF/YANG | — | 4.6 6.3 | — | 4.3.a 5.3 | ✗ | ✗ | ○ | ✗ | — | — | NETAUTO-03-RESTCONF | NETCONF ラボ・YANG 読解紙面 | BL-008 |
| U-K4 | オンボックス自動化(EEM Python・guest shell・CLI Python module) | — | — | — | 5.2.b | ✗ | ✗ | ✗ | — | — | — | なし | cat8000v family で可・IOL 不可 | — |
| U-K5 | 構成管理ツール(Ansible 実技・agent vs agentless 比較・Terraform/Puppet/Chef) | 6.6(d) | 6.7(d) | — | — | ✗ | ✗ | ◎ | ○ | — | ○ | ANSIBLE-01〜05・AUTO-OSPF/BGP | 比較紙面ゼロ・netmiko/pyATS | BL-009 BL-011 |
| U-K6 | モデル駆動テレメトリ(gRPC dial-out・on-change subscription) | — | — | — | 5.3.c | ✗ | ✗ | ✗ | ✗ | — | — | なし | 完全空白(cat8000v+telegraf/gNMI で可) | — |
| U-K7 | SDN 概念(overlay/underlay/fabric・CP/DP 分離・NB/SB API)・AI/ML in NetOps | 6.2 6.3 6.4 | 4.5(d) | — | — | ✗ | ✗ | — | — | — | — | なし | 紙面のみ受け皿・CCNA v1.1 で AI 項が新設 | — |

### L. 基礎概念(主に CCNA・紙面のみ)

| U | 単元 | CCNA | ENCOR | ENARSI | CCIE | P1 | P2 | L1 | L2 | L3 | L4 | 資産(現状) | 抜け・薄い点 | 関連BL |
|---|------|------|-------|--------|------|----|----|----|----|----|----|-----------|-------------|--------|
| U-L1 | 構成要素/トポロジ/ケーブル/PoE/インタフェース障害(collision・duplex/speed) | 1.1〜1.4 | 1.1(d) | — | — | ✗ | ✗ | △ | — | — | — | (duplex 不一致は IOSvL2 で再現可・未作問) | 紙面ゼロ | — |
| U-L2 | TCP/UDP・IPv4 サブネッティング/VLSM・private 空間 | 1.5〜1.7 | — | — | — | ✗ | ✗ | — | — | — | — | なし | **サブネット計算ドリル**(瞬発枠の素材) | — |
| U-L3 | 仮想化(hypervisor 1/2・VM・vSwitch・コンテナ)・クラウド/オンプレ | 1.2.f 1.12 | 2.1(d) | — | — | ✗ | ✗ | — | — | — | — | なし | 紙面のみ | — |
| U-L4 | 無線基礎(RF/チャネル/SSID・AP モード/WLC・roaming・GUI) | 1.11 2.6〜2.9 | — | — | — | ✗ | ✗ | — | — | — | — | なし | CCNA のみ・実機不可・紙面のみ | — |
| U-L5 | 高可用設計(2/3 tier・SSO/NSF・冗長)・アーキテクチャ比較 | 1.2 | 1.1(d) | — | — | ✗ | ✗ | — | — | — | — | なし | 紙面のみ | — |
| U-L6 | クライアント OS の IP 確認(Windows/Mac/Linux) | 1.10 | — | — | — | ✗ | ✗ | — | — | — | — | alpine/ubuntu ノードを含むラボ | 紙面のみ | — |

## 2. 空白・薄層の一覧(優先順の提案・2026-09-21)

判断軸= ①複数資格にまたがる ②配点帯が大きい ③本人の弱点(2026-08-01 不合格の内訳= Security 36%・VPN 67%・Services 80%)
④既存資産で初速が出る。**A 群= 完全空白で複数資格が要求、B 群= 資産はあるが片翼(紙面 or ラボ)が無い、
C 群= 既存単元の薄い層。**

### A 群: 完全空白(紙面もラボも無い)

| 順 | U | 単元 | 要求資格 | 所見 |
|----|---|------|----------|------|
| A1 | U-A3 | STP(RSTP/MST・guard 系) | CCNA/ENCOR/CCIE | **P1 完了(2026-09-21)・P2 完了(2026-09-22)・L1〜L4 完了(2026-09-22)**。旧記述: L1〜L3(PoC 済 poc/stp・設計書 STP-SERIES.design.md) |
| A2 | U-F1/F2 | マルチキャスト(IGMP/PIM/RP/RPF) | ENCOR(d)/CCIE | **P1 完了(2026-09-22)**・PoC 済(poc/mcast: PIM-SM/BSR/Auto-RP/SSM/bidir/MSDP すべて IOL で可)。残= P2・L1〜L3 |
| A3 | U-I11 | QoS 設定読解(MQC) | CCNA(d)/ENCOR/CCIE | ラボ 3 問あり→紙面 read 形(policy-map を読んで挙動を答える)。ENCOR 1.4 は「解釈せよ」 |
| A4 | U-G7 | SD-WAN(OMP/TLOC/policy) | ENCOR(d)/CCIE 25%帯 | 実機は BL-050 停滞→まず紙面(用語・OMP 属性・ポリシー読解・cloze 向き) |
| A5 | U-D5 | OSPF 最適化(stub router/LSA throttle/prefix suppression/GTSM) | CCIE | IOL で全部可。ospfdbg の変種追加+ラボ故障種追加で安く埋まる |
| A6 | U-A5 | L2 セキュリティ(DHCP snooping/DAI/IPSG/port security/storm control) | CCNA/CCIE | **ioll2 の可否 PoC が先**(FHS の前例)。可なら構築+TS 生成器 |
| A7 | U-A4 | スイッチ管理(errdisable/UDLD/CDP・LLDP/L2 MTU) | CCNA/CCIE | A1/A6 と同じ盤面に故障種として同居させる |
| A8 | U-I14 | 診断ツール(EPC/packet-trace/debug platform condition) | ENCOR/CCIE | cat8000v 必要。BL-062 と合流 |
| A9 | U-K6/K4 | テレメトリ・guest shell | CCIE | cat8000v。優先低(CCIE 着手時) |
| A10 | U-H9/L4 | 無線 | CCNA のみ | 実機不可。CCNA 受験を決めた時に紙面のみ |

### B 群: 片翼が空白(資産の転用で初速が出る)

| 順 | U | 単元 | 空白側 | 所見 |
|----|---|------|--------|------|
| B1 | U-I3 | DHCPv4 | 紙面 | gen_dhcp_ts の 8 故障を紙面 cause/fix/read に転用(4.4・25% 帯) |
| B2 | U-I7 | IP SLA/track | 紙面 | gen_ipsla_ts 13 故障を転用+track list の知識形(4.5) |
| B3 | U-B6 | VRF-Lite | 紙面 | 1.7 明示。VRF-LEAK/H 型の盤面で read/fix(route leak・vrf forwarding で IP 剥がれ) |
| B4 | U-I2 | NAT/PAT | 紙面+専用ラボ | overlapping/policy NAT の read 形・NAT TS 生成器 |
| B5 | U-E5/E6 | BGP RR・集約 | 紙面 | 1.11.d 明示。GEN-BGPRR の故障を紙面化・aggregate as-set/summary-only 読解 |
| B6 | U-I9 | EEM | 紙面 | applet の fix/read(ENCOR 6.6) |
| B7 | U-A2/A6/A7 | EtherChannel・FHRP・SPAN | 紙面 | ラボあり→show 出力読解の read 形 |
| B8 | U-G6/G8 | LISP/VXLAN/SD-Access | 紙面 | ENCOR describe。SDA-LISP/EVPN の実測 show を素材に cloze |
| B9 | U-C1 | EIGRP 隣接 debug 読解 | 紙面 | ospfdbg の EIGRP 版(K 値/AS/認証/passive) |
| B10 | U-B7 | BFD | 紙面 | describe 級・cloze 向き |
| B11 | U-I10/K2 | Catalyst Center・REST API | 紙面 | 実機無し・紙面が唯一の受け皿 |
| B12 | U-K1/K7/L2/L3/L5/J1 | JSON/Python 読解・SDN 概念・サブネット計算・仮想化・IPv6 アドレス | 紙面 | CCNA/ENCOR の知識帯。瞬発枠(speed)の素材に向く |

### C 群: 既存単元の薄い層(層を厚くする)

| 順 | U | 単元 | 薄い層 |
|----|---|------|--------|
| C1 | U-G4/G5 | **MPLS** | LDP の中身(session/transport/MD5/IGP sync/label filter/TTL)・mpls ping/traceroute・**5〜7 台版でパックに載る形**・VPNv6/6VPE・PE-CE OSPF(sham-link)/EIGRP(SoO)・VPNv4 RR・Inter-AS Option A・CE 視点 TS |
| C2 | U-G3 | DMVPN | dual hub(CCIE 明記)・IPv6 オーバーレイ・per-tunnel QoS |
| C3 | U-H2 | ACL | time-based(ENARSI 明記)・object-group・適用点主題化(BL-109) |
| C4 | U-H1 | AAA | TACACS+(tac_plus)・accounting |
| C5 | U-E1/E3/E4 | BGP | peer group/template・dynamic neighbor・ttl-security・conditional advertisement・ORF・local-as/remove-private-as・multipath |
| C6 | U-H7 | デバイスアクセス | privilege level/parser view・login block-for・SCP/HTTPS・secret 種別 |
| C7 | U-H5 | CoPP | CPPr |
| C8 | U-I6 | ロギング | conditional debug・config change notification |
| C9 | U-D2 | OSPF | LSA タイプ/LSDB 読解・仮想リンク・totally stubby/NSSA 紙面 |
| C10 | U-C3 | EIGRP | stub 種別・SIA 紙面・graceful shutdown・wide metrics |
| C11 | U-I4 | DHCPv6 | PD |
| C12 | U-H6 | IPv6 FHS | ハード制約の記録済(source/prefix/dest guard 不発)。紙面で補う |

## 3. 紙面 shape / ラボ生成器 → 単元 逆引き

| 紙面 shape | 単元 | | ラボ生成器/固定問 | 単元 |
|-----------|------|-|------------------|------|
| chain/ring/mploop/riploop/ospfbgp | U-B3 | | gen_redist_field/arena/mp/loop/ripospf/mutual | U-B3 |
| leakmap / eigrpkb | U-B4 U-C3 U-C4 | | gen_route_ctrl・gen_list_dojo | U-B2 |
| ospfv3pl / v6redist | U-D4 U-D6 U-C6 | | gen_troubleshoot/ospf_complex/ospfv3_complex | U-D1 U-D4 |
| ospfdbg / pref(OSPF) | U-D1 U-D3 | | gen_aggregate/pathctrl/twist | U-B4 U-D3 U-D6 |
| pref(EIGRP) | U-C2 U-C5 | | gen_eigrp_complex/eigrpv6_complex/eigrp_vrf | U-C1 U-C4 U-C6 |
| bgpdbg / bgpbest / bgppol | U-E1 U-E2 U-E3 | | gen_bgp_*(troubleshoot/pathts/ring/rrts/complex/bgpbest) | U-E1〜E5 |
| pbr | U-B5 | | gen_chain_ts | U-B3 U-E5 |
| rtbasic / cloze order | U-B1 | | gen_mpls_ts・L3VPN-01〜06 | U-G4 U-G5 |
| mpls / cloze m_ | U-G4 U-G5 | | gen_dmvpn_ts/wreck・DMVPN-* | U-G3 |
| dmvpn / cloze d_ | U-G3 U-G2 | | gen_s2svpn・IPSEC-* | U-G2 |
| aaa / cloze a_ | U-H1 | | gen_aaa_build/radius_build | U-H1 |
| acl / aclv6 / urpf / copp | U-H2 U-H3 U-H4 U-H5 | | gen_urpf_ts・COPP-* | U-H4 U-H5 |
| fhs / cloze f_ / dhcp6 | U-H6 U-I4 U-J2 | | gen_v6addr_ts/build・DHCPV6-01 | U-I4 U-H6 U-J2 |
| svc / cloze s_ | U-I1 U-I5 U-I6 U-I8 U-I13 U-H7 | | gen_snmpv3_ts/fnf_ts/ipsla_ts/dhcp_ts | U-I5 U-I8 U-I7 U-I3 |
| cloze g_ | U-F1 U-F2 | | (マルチキャストのラボは未・PoC 盤面 _POC-MCAST) | U-F1 U-F2 |
| stp / fhrp / cloze t_ | U-A3 U-A6 | | gen_stp(build L1/L2・ts・--world mst・--world 3tier)・CAMPUS-TS-01 | U-A3 |
| speed(型プール 26) | 横断 | | gen_l2_troubleshoot・LAG/FHRP/SPAN/VACL | U-A2 U-A6 U-A7 U-A5 |
| (private) shimen | 横断 | | SDA-LISP/EVPN-VXLAN/UM2/CAMPUS/FGT/ASAv | U-G6 U-G8 U-A6 U-H8 |
| | | | ANSIBLE-*/NETAUTO-03 | U-K5 U-K3 |

## 4. ブループリント原典と改版メモ

| 資格 | 版 | 取得日 | 保管 | 備考 |
|------|----|--------|------|------|
| CCNA 200-301 | v1.1 | 2026-09-21 | private/blueprints/200-301-CCNA-v1.1.txt | 6.4 に AI/ML 項。無線は残る |
| ENCOR 350-401 | **v1.2** | 2026-09-21 | private/blueprints/350-401-ENCOR-v1.2.txt | 無線全削除・PTP 追加(3.3.a)・MSDP/bidir(3.3.d)・Catalyst Center AI(4.5)・HW/SW スイッチング項削除 |
| ENARSI 300-410 | v1.1 | 2026-09-21 | private/blueprints/300-410-ENARSI-v1.1.txt | 1.0 35% / 2.0 20% / 3.0 20% / 4.0 25%(v1.2 は未公開・要再確認) |
| CCIE EI Lab | v1.1 | 2026-09-21 | private/blueprints/CCIE-EI-v1.1-lab.txt | 1.0 30% / 2.0 SD 25% / 3.0 15% / 4.0 15% / 5.0 15% |

## 5. 作り込み記録(単元ごとの履歴・新しい順)

| 日付 | U | 段階 | 成果物 | 備考 |
|------|---|------|--------|------|
| 2026-09-27 | U-A1 U-A2 U-A6 U-H2 U-I2 U-I3 U-I7 | L4 | `gen_enterprise.py`(GEN-ENT・エンタープライズ拠点構築・難5・20 ノード)＋`ent_ops.py`(採点前フック=回線切替試験) | BL-225。U-H2 は ACL の実務構築(SVI×送信元 VLAN・境界 WAN/LAN・命名規約)として L2 も ○。E2E 3→100・誤解法 63。残り(ハード・TS・世界 B・パック)= BL-229 |
| 2026-09-27 | U-A6 | P2 | `gen_paper_fhrp.py`(shape fhrp・h_path/h_acl)= U-A6 初の紙面 | BL-228。STP の盤面＋HSRP で往路・復路を全記入・ハードは SVI ACL。実機 PoC(poc/fhrp)で選出・preempt・非対称・ACL の効き方を確定 |
| 2026-09-27 | U-A3 | P2 | `gen_paper_stp.py` に `s_rolemap`(ラボと同じ盤面で全ポートの役割を記入・全空欄一致で正答) | BL-226。表内プルダウン(穴埋め形の UI)・正解は stp_model。試用= PACK-TEST-ROLEMAP。派生案は BL-227 |
| 2026-09-27 | U-A3 | L4 | `gen_stp.py --world 3tier --mode ts`(故障 12 種)＋`--guard-style {port,global,any}`＋パック `stp3ts` | BL-221(T4 TS)・BL-222。PoC 第6回(guard 行の書式・既定と明示の優先関係・3 故障の実挙動)。採点を実効状態へ移行。E2E 4 バッチ＋day0 全て 100 に復帰・方式の取り違えは 90 |
| 2026-09-26 | U-A3 | L4 | `gen_stp.py --world 3tier`(`gen_stp_3tier.py`・3 層キャンパス構築・難5)＋パック `stp3build` | BL-221 の T4。層が 3 つ・保護は方針で与えポートを列挙しない・分配の 36864 で 2 段の負荷分散。実機 E2E 16→100、誤解法 78(MAC 任せ)/82(guard 上下逆) |
| 2026-09-22 | U-A3 | L4 | `gen_stp.py --world mst`(`gen_stp_mst.py`・ts 故障 13 種・build)＋パック `stpts`(pvst/mst 抽選) | BL-076 完了。PoC 第4回(MST 境界・PVST シミュレーション・region 不一致・移行の向き)。全故障 E2E 済 |
| 2026-09-22 | U-A3 | L1 L2 | `gen_stp.py --mode build --level 1/2`＋パック構築ジャンル `stpbuild` | BL-076。E2E L1 23→100・L2 19→100・誤解法降格。持ち込み機器は駐車 VLAN・初期は全台 rapid(IOL の移行不安定を回避) |
| 2026-09-22 | U-A3 | L3 | `gen_stp.py`(GEN-STP・ts モード・故障 10 種・selftest 2200 NG0)＋`stp_ops.py`＋PoC 第3回(poc/stp・4 台盤面) | BL-076。全故障 実機 E2E 済・誤解法降格確認。build(L1/L2)・MST(L4)は同じ生成器の次段 |
| 2026-09-22 | U-F1 U-F2 | P1 | `cloze_kb_mcast.py`(8 kind・selftest 4800 NG0)＋`curriculum/U-F-mcast.md`(41 項目)＋照合表 `U-F-mcast.sources.md`＋PoC `poc/mcast`(IOL 8+ioll2) | BL-217。問題集(Drive)に教材なし= 置かれたら照合追加。実パック初出題は未 |
| 2026-09-22 | U-A3 | P2 | `gen_paper_stp.py`(9 kind・selftest 1280 NG0)＋`stp_model.py`(選出の計算器・実機一致を含む selftest)＋照合表 `curriculum/U-A3-stp.sources.md` | BL-216。作問の裏どりルールの初適用(3 ソース+実機 PoC 第2回)。実パック初出題= 2026-09-22 |
| 2026-09-21 | U-A3 | P1 | `cloze_kb_stp.py`(6 kind・selftest 4320 NG0)＋`curriculum/U-A3-stp.md`(47 項目) | BL-214。初の「知識項目表→穴埋め」型。実パック初出題= 2026-09-22 |
| 2026-09-21 | (台帳) | — | CURRICULUM.md 制定・全単元の初期判定・段階列(P1/P2/L1〜L4)化・units.yml・--profile | BL-212/213。初期判定は CATALOG/生成器/メモリからの棚卸し |
