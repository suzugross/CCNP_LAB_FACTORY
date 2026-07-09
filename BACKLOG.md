# BACKLOG — 実装したい課題の管理台帳

「今は見送るが、あとで実装したい」ものをここで一元管理する。

## 運用ルール

- 1行1件をテーブルに追記。詳細な設計メモがあるものは `problems/_drafts/*.design.md` に置きリンクする。
- **状態**: `未着手` → `PoC中` → `実装中` → `完了`（完了したら「完了アーカイブ」表へ移動）
- **優先**: `高` / `中` / `低`（着手したい順の目安）
- 着手時はこの表の状態を更新してから作業を始める。

## 課題一覧

| ID | 題名 | 分野 | 優先 | 状態 | 概要 / 詳細リンク |
|----|------|------|------|------|-------------------|
| BL-001 | GEN-AAAGRP: IOS AAA サーバグループ構築問（難4） | ENCOR/AAA | 高 | 未着手 | FreeRADIUS 2台を自動構築し、IOS側の named サーバグループ・非標準ポート・サーバ別キー・ローカルDBフォールバックを3フェーズ挙動採点（正常/片系断/全断）。→ [problems/_drafts/GEN-AAAGRP.design.md](problems/_drafts/GEN-AAAGRP.design.md) |
| BL-002 | BGP 残強化（confederation / IPv6 AF 等 Phase3 候補） | ENARSI/BGP | 中 | 未着手 | gen_bgp_complex_ts.py の Phase3 拡張候補。既存メモリ(ccnp-bgp-complex-gen)参照。★IPv6 AF は 2026-07-09 の IPv6 棚卸しで「BGP 全13問＋生成器が v4 のみ」と判明した ENARSI 直撃の空白（activate 忘れ・IPv4ピア上の v6 next-hop 罠が故障ネタ） |
| BL-003 | LAG（EtherChannel）問題 | ENCOR/L2 | 中 | 未着手 | 問題バックログ既知分。IOSvL2 前提 |
| BL-004 | 既存BGP問の AF 方式化バックログ | ENARSI/BGP | 低 | 未着手 | BGP は以後 AF 方式が標準（規約化済）。旧問の順次改修 |
| BL-005 | ENCOR-EIGRP-BUILD-01 要件7フィルタ強化 | ENCOR/EIGRP | 低 | 未着手 | RT03 のみ到達可へ絞る宿題 |
| BL-006 | DMVPN + IPsec 合体問 | ENARSI/VPN | 中 | 未着手 | sVTI×IKEv1/v2・crypto map 版は完成済。残りは DMVPN との合体 |
| BL-007 | Linuxサーバラボ次候補（BINDマスター/スレーブ・chrony+rsyslog・FRR） | Linux×NW | 低 | 未着手 | ゾーン転送/serial、EEM連携運用複合、FRRでLinuxをBGPピア化 |
| BL-008 | NETAUTO-04-NETCONF: ncclient で get-config/edit-config（難2-3） | 自動化/NETCONF | 高 | 未着手 | N3(RESTCONF)と同じ題材をXML+SSH(830)で対比。cat8000v×1。netconf-yang起動待ち・VRF越し830要実機確認 → [problems/_drafts/NETAUTO-DOJO.design.md](problems/_drafts/NETAUTO-DOJO.design.md) |
| BL-009 | NETAUTO-01-NETMIKO: Python+netmiko で show収集→設定投入（難1-2） | 自動化/Python | 中 | 未着手 | IOL 3台で軽い。★.venv に netmiko の pip 追加が前提作業 → 同設計メモ |
| BL-010 | NETAUTO-02-DATA: JSON/YAML/Jinja2 の読み書き（難1-2） | 自動化/データ | 中 | 未着手 | ラボ不要（オフライン・隙間時間向け）。生成物diff方式の採点は要設計 → 同設計メモ |
| BL-011 | NETAUTO-05-PYATS: pyATS/Genie で状態取得・差分検知（難3） | 自動化/検証 | 低 | 未着手 | 採点系のGenieを学習者側に降ろす。IOLで可 → 同設計メモ |
| BL-012 | GEN-DOJO-PREFIX: ip prefix-list 道場（ドリル型・Phase1） | ENARSI/filter | 高 | 未着手 | 2台(feeder+target)・1出題K課題を意味的突き合わせで採点（`show ip bgp prefix-list` オンボックス採点・定義のみで適用不要）→ [problems/_drafts/DOJO-LISTS.design.md](problems/_drafts/DOJO-LISTS.design.md) |
| BL-013 | GEN-DOJO-ASPATH: as-path access-list 道場（Phase2） | ENARSI/filter | 高 | 未着手 | feeder流用＋local-as replace-as/prepend で AS_PATH合成、`show ip bgp filter-list` 採点。local-as の IOL 挙動は先行PoC → 同 design.md |
| BL-014 | GEN-DOJO-ACL: ACL 道場（Phase3） | ENCOR/ACL | 高 | 未着手 | acl_model.py（テストパケットベクタ意味評価器）＋grade.py 新チェック種 `acl_vectors:`。TGENルータのヒットカウンタは自己確認専用 → 同 design.md |
| BL-015 | MPLS: PE-CE eBGP 化（応用問03 → gen `--pece ebgp` 軸） | ENARSI/MPLS | 高 | 未着手 | vrf 内 eBGP で再配布レス化（02 との対比が核心）。同一AS変種で as-override/allowas-in。手組み03→gen移植の順 → [problems/_drafts/MPLS-SERIES.design.md](problems/_drafts/MPLS-SERIES.design.md) |
| BL-016 | MPLS: RT 非対称ハブ&スポーク構築問 | ENARSI/MPLS | 中 | 未着手 | export/import 独立の威力（spoke間はhub経由のみ）。hub CE 折返しの IOL 挙動は要 PoC → 同 design.md |
| BL-017 | MPLS: RT 混線 TS 故障（l4_rt_cross_import）追加 | ENARSI/MPLS | 中 | 未着手 | 重複prefixだと症状が非決定的→redistribute connected を base v2 軸で足し PE-CE リンク漏えいで決定的に検出 → 同 design.md |
| BL-018 | MPLS: VPNv4 RR 軸（gen `--ibgp rr`, 専用RRノード13台） | ENARSI/MPLS | 中 | 未着手 | フルメッシュ→RR。故障=client旗/RR activate/cluster-id。chainTS の「client旗1つでは壊れない」教訓の VPNv4 版確認 → 同 design.md |
| BL-019 | chainTS swap モード l3_subnets_missing 再検証 | ENARSI/再配送 | 高 | 未着手 | iol-xe 17.15 の subnets 暗黙定発見の波及。故障として不成立の疑い→90秒以上待って単体検証、不成立なら差替え → 同 design.md |
| BL-020 | gen_mpls_ts --faults 3 の実機1サイクル | ENARSI/MPLS | 中 | 未着手 | 3層連鎖（下位が上位を隠す）の組合せ未検証。seed 7200 相当で注入→切り分け→100点まで → 同 design.md |
| BL-021 | MPLS 小粒（LDP MD5 / 01・02 params 化 / MSS 効果採点 / 遠期: InterAS・6PE） | ENARSI/MPLS | 低 | 未着手 | 詳細は design.md の BL-021 節 → 同 design.md |
| BL-025 | gen_qos_ts.py: QoS TS 生成器（効果が出ない QoS を数値で切り分け） | ENCOR/QoS | 中 | 未着手 | dir_wrong/match_dscp_wrong/priority_missing 等 7 故障候補。3問完成後に知見をカタログ化 → 同 design.md |
| BL-026 | QoS: MQC 入門ドリル（難2・設定手順ガイドつき） | ENCOR/QoS | 低 | 未着手 | 概念のみの学習者向けに class-map/policy-map 文法を手順ガイドつきで練習する前々段。BL-023 で足りるかを見てから要否判断（2026-07-09 見送り） |
| BL-029 | OSPF: forwarding address 罠の TS 故障ネタ（E2 が FA 経由で ECMP 化） | ENARSI/OSPF | 低 | 未着手 | uRPF PoC で実機発見: redistribute static の次ホップIFが OSPF 有効だと Type-5 に FA が立ち E2 経路が意図せず ECMP/別経路化。gen_ospf_complex_ts への故障追加 or 単問。詳細= [poc/urpf/README.md](poc/urpf/README.md) の★2 |
| BL-031 | IPv6 ルータセキュリティ問（IPv6 uRPF + traffic-filter 合体） | ENARSI/IPv6 | 中 | 未着手 | ENARSI 3.0 の未カバー2技術を1問で回収。OSPFv3 土台([[ccnp-ospfv3-syntax]])上に `ipv6 verify unicast source reachable-via`。IOL の ipv6 verify 対応・カウンタ書式の PoC が前提（半日規模） |
| BL-032 | ENARSI-URPF-01 params 変種2本（acl 変種・allow-default 変種） | ENARSI/security | 低 | 未着手 | acl=E0/1 strict維持+番号ACL例外を強制(難4-5)。★実機知見(2026-07-09 GEN-URPF-4242): ACL例外通過は suppressed に計上されず **ACL matches カウンタ**で追跡→採点は `show ip access-lists` の matches 非0 で / allow-default=default route追加で loose素通し体感。既存 params 機構で低コスト。設計詳細= [problems/_drafts/URPF-01.design.md](problems/_drafts/URPF-01.design.md) 変種節 |
| BL-033 | IPv6 相互再配送 TS 生成器（OSPFv3⇄EIGRPv6） | ENARSI/IPv6 | 高 | 未着手 | ENARSI 1.x は再配送を v4/v6 両方で明記するがリポの再配送資産は全て v4。gen_redist_mutual_ts.py（AD95<110 次善誘発・タグ+distribute-list）の v6 焼き直し。部品= gen_ospfv3/gen_eigrpv6 両生成器の構文知見。★netmodel 採点は IPv4 前提→v6 は raw プレフィクス判定に置換が前提 |
| BL-034 | DHCPv6 シリーズ（stateless O-flag / stateful M-flag / リレー / PD） | ENARSI/IPv6 | 中 | PoC中 | ブループリント 4.x「IPv4/IPv6 DHCP」の v6 半分が完全空白（SLAAC は既出）。詳細設計済: PoC半日→ENARSI-DHCPV6-01（3方式使い分け・4 IOL・難4-5）→PD 問（3 IOL・難4）の3フェーズ＋将来TS故障カタログ。★最大の不確実点= IOL クライアントの O-flag 応答（要PoC）→ [problems/_drafts/DHCPV6-SERIES.design.md](problems/_drafts/DHCPV6-SERIES.design.md) |
| BL-035 | OSPFv3 系 2問の bfd 変種（`ospfv3 bfd` 構文プローブ込み） | ENARSI/BFD | 中 | 未着手 | BFD シリーズの明示的な残作業（[[ccnp-bfd-variants]]）。`ospfv3 bfd` の実機プローブ1回＋ENCOR-OSPFV3-01/AREA-01 への変種追加で完結する小粒 |
| BL-036 | IPv6 First Hop Security（RA Guard / DHCPv6 Guard / ND inspection） | ENARSI/IPv6 | 低 | 未着手 | ブループリント 3.x 明記だが「Describe」レベルの出題深度。L2 スイッチ（IOL L2 / IOSvL2）の FHS 対応が不明で PoC リスク大→登録のみ |
| BL-037 | IPv6 小ネタ変種（IPv6 PBR / EIGRPv6 named 集約 / DMVPN IPv6 オーバーレイ） | ENARSI/IPv6 | 低 | 未着手 | いずれも既存問題への変種軸で回収可: PBR は既存 PBR 問の v6 版、集約は af-interface `summary-address`、DMVPN は既存3問へのオーバーレイ v6 軸 |

## 完了アーカイブ

| ID | 題名 | 完了日 | 備考 |
|----|------|--------|------|
| BL-030 | gen_urpf_ts.py: uRPF TS 生成器（故障4種・非対称/役割/値ランダム化） | 2026-07-09 | 専用生成器を新設（既存生成器はRIBベース採点のためuRPF=データプレーン故障を検出不能と判明→載せ替え断念が正解）。故障= strict_on_asym(難4)/acl_exempt_wrong(難5)/missing_on_uplink(難3)/loose_on_strict_side(難4)。**全4故障 実機フルサイクル済(2026-07-09)**: acl_exempt_wrong 75→100（役割スワップ構成）/ loose_on_strict_side 65→100 / strict_on_asym 75→100 / missing_on_uplink 70→100。★注意: 故障スコアの採取は起動直後だと OSPF(redistribute) 収束前で経路ガードが一過性FAILする→1〜2分待つか max_attempts≥2 で。検証seedは掃除済（出題時は新seedで生成）。ユーザ実解答: GEN-URPF-7777(loose_on_strict_side)100点クリア |
| BL-028 | ENARSI-OSPF-MADJ-01: OSPF マルチエリア隣接 最適化問（難4・6台） | 2026-07-09 | 実機フルサイクル済（未解答20点/サイレント故障誤答20点/エリア移動チート60点/模範解答100点収束）。核心=RFC3509迂回を制約(virtual-link/エリア変更禁止)下で `ip ospf multi-area` に一意化。★最大の罠=broadcastのままではエラー無しでMA0 DOWN（P2P化が必須）。採点=MADJシグネチャ(neighbor Genie/if brief raw)＋traceroute経路。PoC成果: [poc/ospf-madj/README.md](poc/ospf-madj/README.md) |
| BL-027 | ENARSI-URPF-01: uRPF エッジ anti-spoofing 問（難4・strict/loose 使い分け） | 2026-07-09 | 実機フルサイクル済（未解答35点/両strict誤答75点/模範解答100点/ACL別解100点・フレッシュカウンタでも収束確認）。核心=デュアルホーム顧客の出口非対称で strict 無思慮投入が正規断。★教訓: 偽装pingの成否採点は偽陽性→per-IF verification dropsカウンタ採点＋0点「発射」チェックをカウンタ判定の前に置く順序設計。PoC成果: [poc/urpf/README.md](poc/urpf/README.md)（FA罠→BL-029派生） |
| BL-023 | ENCOR-QOS-CLASS-01 / POLICE-01: 分類マーキング・ポリシング体感問（難3） | 2026-07-09 | 実機フルサイクル済（両問とも未解答10点/模範解答100点収束・POLICE は class-default 誤答65点も実機確認）。★教訓: policing の限定性は ICMP 巻き添えで検出不可（TCP 自制）→構造 ne:any + UDP 素通りで採点。学習順序 CLASS→POLICE→LLQ |
| BL-024 | ENCOR-QOS-LLQ-01: 輻輳→LLQ で救う旗艦体感問（難4） | 2026-07-09 | 実機フルサイクル済（未解答0点/模範解答100点×3回・採点は2試行収束約4分）。効果採点パターン確立: grade.py class:直指定拡張＋「EF無傷AND BE劣化」統合チェック（EF単独採点は偽陽性20点の実機教訓）。規約は conventions.md「QoS効果採点規約」 |
| BL-022 | QoS Phase0 PoC: 実効性マトリクス＋iperf3 測定基盤 | 2026-07-08 | **IOL採用で確定**(shape/police/LLQ全て実効・EF ping 327ms→0.97ms)。fair-queue対比消失・priorityポリサ罠・Genie rv1問題を発見。成果物: [poc/qos/README.md](poc/qos/README.md)＋poc-qos-iol-lab.yaml。次=BL-024(LLQ旗艦問) |
