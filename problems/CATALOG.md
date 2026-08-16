# 問題カタログ — 出題可問題の正準台帳

出題フロー(`.claude/skills/quiz/SKILL.md`)が問題選定に使う一覧。**問題完成(実機検証済)時に1行追記する。**
出題の記録は [problems/_history.md](_history.md) に付ける(このファイルには書かない)。

- 掲載問題は**原則すべて実機フルサイクル検証済・出題可**。例外・注意のみ備考に記す。
- 難易度は 1〜6(出題の基本レンジは 3〜4)。台数は target_nodes 数(≒必要ノード数の目安)。
- **CML Personal は同時起動 20 ノード上限**。台数の大きい問題は他ラボの teardown を先に。
- variant 列: `base`=既定 / `bfd`=BFD 要件付き / `sNNNN`=seed 値違い。`-e variant=<名>` で切替。

## 通常問題(scripts/lab.sh で provision/teardown)

### ENCOR 系

| ID | 難 | 分野 | 台数 | access | variant | 備考 |
|----|----|------|------|--------|---------|------|
| ENCOR-ACL-EXTENDED-01 | 4 | acl,security,filtering | 3 | ssh |  |  |
| ENCOR-ACL-NAMED-01 | 4 | acl,named-acl,sequence | 3 | ssh |  |  |
| ENCOR-COPP-01 | 3 | copp,security | 1 | ssh |  |  |
| ENCOR-COPP-02 | 4 | copp,security | 1 | ssh |  |  |
| ENCOR-COPP-03 | 4 | copp,security,qos | 2 | ssh | base,s41144,s51234 |  |
| ENCOR-DHCP-01 | 3 | dhcp,dhcp-relay,acl | 5 | ssh |  | DHCPv4一気通貫(配布/MAC固定/リレー/DHCP-only ACL)。★MAC固定は実機調査型(識別子=cisco文字列罠が本題)・採点はrelease/renew実効込み |
| ENCOR-EDGE-HARDEN-01 | 5 | security,aaa,copp | 2 | ssh |  |  |
| ENCOR-EEM-01 | 3 | eem,automation,assurance | 1 | ssh |  |  |
| ENCOR-EIGRP-01 | 2 | eigrp,igp | 3 | ssh | base,bfd,s4242,v2 |  |
| ENCOR-EIGRP-BUILD-01 | 4 | eigrp,igp,summarization | 5 | ssh | base,bfd | 要件7フィルタ強化の宿題あり(BL-005)。出題は可 |
| ENCOR-EIGRP-VARIANCE-01 | 5 | eigrp,variance,feasible-successor | 5 | ssh | base,bfd |  |
| ENCOR-FHRP-01 | 3 | fhrp,hsrp,l2 | 4 | ssh |  |  |
| ENCOR-FNF-01 | 2 | netflow,flexible-netflow,telemetry | 3 | ssh | base,v2 | IOL は flow monitor 配下の cache サブツリー自体が無い(entries/timeout/type 全て不可・2026-07-27 `?` 実測)。★2026-07-25 採点強化(BL-065): exporter source/export-protocol 追加＋cache 同一行判定・base 実機再検証済(10→100) |
| ENCOR-GRE-01 | 3 | tunnel,gre,eigrp | 3 | ssh |  |  |
| ENCOR-GRE-02 | 4 | tunnel,gre,ospf | 4 | ssh |  |  |
| ENCOR-INTEGRATED-01 | 6 | ospf,bgp,nat | 4 | ssh | base,s58207,s72513,v2 |  |
| ENCOR-IPSLA-01 | 4 | ip-sla,track,static-route | 4 | ssh |  |  |
| ENCOR-IPSLA-02 | 5 | ip-sla,track,static-route | 4 | ssh |  |  |
| ENCOR-IPV6-SLAAC-STATIC-01 | 4 | ipv6,addressing,slaac | 3 | ssh |  |  |
| ENCOR-IPV6-STATIC-01 | 4 | ipv6,addressing,link-local | 3 | ssh |  |  |
| ENCOR-LAG-01 | 3 | etherchannel,lag,l2 | 2 | telnet |  |  |
| ENCOR-LAG-TS-01 | 4 | etherchannel,lag,l2 | 2 | telnet |  |  |
| ENCOR-OSPF-01 | 2 | ospf,igp | 3 | ssh | base,bfd |  |
| ENCOR-OSPF-AUTH-01 | 3 | ospf,authentication,md5 | 3 | ssh | base,bfd |  |
| ENCOR-OSPF-IF-01 | 2 | ospf,igp | 3 | ssh | base,bfd |  |
| ENCOR-OSPF-NSSA-01 | 5 | ospf,multi-area,nssa | 3 | ssh | base,bfd |  |
| ENCOR-OSPF-STUB-01 | 4 | ospf,multi-area,stub | 3 | ssh | base,bfd |  |
| ENCOR-OSPFV3-01 | 5 | ipv6,ospfv3,ospf | 3 | ssh |  |  |
| ENCOR-OSPFV3-AREA-01 | 6 | ipv6,ospfv3,ospf | 4 | ssh |  |  |
| ENCOR-PBR-01 | 4 | pbr,routing | 3 | ssh |  |  |
| ENCOR-PBR-02 | 4 | pbr,routing | 4 | ssh |  |  |
| ENCOR-QOS-CLASS-01 | 3 | qos,mqc,classification | 4 | ssh |  | QoS体感シリーズ。効果を実測採点 |
| ENCOR-QOS-LLQ-01 | 4 | qos,mqc,llq | 4 | ssh |  | QoS体感シリーズ。iperf3/ping で効果実測採点 |
| ENCOR-QOS-POLICE-01 | 3 | qos,mqc,policing | 4 | ssh |  | QoS体感シリーズ。効果を実測採点 |
| ENCOR-REDIST-01 | 3 | redistribution,ospf,eigrp | 3 | ssh | base,bfd,s63048 |  |
| ENCOR-RSPAN-01 | 5 | rspan,span,monitor | 2 | console |  | ★IOSvL2: 同上(Vlan999 SVI bounce) |
| ENCOR-SPAN-01 | 4 | span,monitor,l2 | 1 | console |  | ★IOSvL2: ブート後 Vlan999 SVI down固着→shut/no shut |
| ENCOR-VACL-01 | 4 | vacl,acl,l2 | 1 | telnet |  |  |
| ENCOR-VACL-02 | 4 | vacl,acl,l2 | 5 | telnet |  |  |
| ENCOR-VRF-LEAK-01 | 6 | vrf,vrf-lite,route-leaking | 2 | ssh |  |  |
| ENCOR-VRF-NAT-01 | 6 | vrf,nat,pat | 4 | ssh |  |  |
| ENCOR-VRF-TS-01 | 5 | vrf,vrf-lite,route-leaking | 2 | ssh |  |  |
| ENCOR-WANHA-01 | 5 | tunnel,gre,ip-sla | 4 | ssh |  |  |

### ENARSI 系

| ID | 難 | 分野 | 台数 | access | variant | 備考 |
|----|----|------|------|--------|---------|------|
| DMVPN-PHASE3-01 | 5 | dmvpn,mgre,nhrp | 4 | console |  | DMVPN Phase3 |
| DMVPN-POC-01 | 5 | dmvpn,mgre,nhrp | 4 | console |  | 名称は POC だが Phase2 の完成問 |
| ENARSI-BGP-01 | 4 | bgp,path-control | 4 | ssh | base,mh-auth | variant mh-auth=認証/Loopback/multihop(実機済) |
| ENARSI-BGP-AGGREGATE-01 | 4 | bgp,aggregation,summarization | 3 | ssh |  |  |
| ENARSI-BGP-ASPATH-01 | 3 | bgp,filter,as-path | 3 | ssh |  |  |
| ENARSI-BGP-ASPATH-RM-01 | 4 | bgp,as-path,route-map | 2 | ssh |  |  |
| ENARSI-BGP-IPV6-01 | 4 | bgp,ipv6,address-family,dual-stack | 3 | ssh |  | dual-stack TS。v4健全なのにv6全滅。故障=v6 activate欠落/network欠落/ipv6 unicast-routing欠落。★unicast-routing欠落はv6 AF activate受理も壊す→是正後clear要 |
| ENARSI-BGP-COMM-01 | 4 | bgp,attributes,community | 2 | ssh |  |  |
| ENARSI-BGP-MED-01 | 3 | bgp,attributes,med | 2 | ssh |  |  |
| ENARSI-BGP-NHSELF-01 | 4 | bgp,ibgp,next-hop | 3 | ssh |  |  |
| ENARSI-BGP-ORIGIN-01 | 4 | bgp,origin,path-selection | 3 | ssh |  |  |
| ENARSI-BGP-POLICY-01 | 5 | bgp,path-control,community | 6 | ssh | base,bfd,s4242,s7777 |  |
| ENARSI-BGP-PREFIX-01 | 3 | bgp,filter,prefix-list | 2 | ssh | base,bfd |  |
| ENARSI-BGP-ROUTEMAP-01 | 4 | bgp,route-map,prefix-list | 3 | ssh |  |  |
| ENARSI-BGP-SYNC-01 | 5 | bgp,synchronization,ibgp,transit | 5 | ssh |  | レガシー同期残骸×非BGP中継ブラックホールの2段TS(sync除去は要clear) |
| ENARSI-BGP-WEIGHT-01 | 3 | bgp,attributes,weight | 3 | ssh | base,bfd |  |
| ENARSI-DHCPV6-01 | 5 | ipv6,dhcpv6,slaac | 4 | ssh |  |  |
| ENARSI-DMVPN-BGP-01 | 5 | dmvpn,mgre,nhrp | 5 | console |  | DMVPN+BGP再配送 |
| ENARSI-DMVPN-IPSEC-01 | 5 | dmvpn,mgre,nhrp | 4 | console |  | DMVPN+IPsec完全版。★出題済(ユーザ100点) |
| ENARSI-EIGRP-SIA-01 | 5 | eigrp,sia,query | 4 | ssh |  |  |
| ENARSI-EIGRP-VRF-01 | 4 | eigrp,vrf,named-mode | 4 | ssh |  | BL-070①(2026-07-27)。VRF-Lite×named mode SUZUNET・2テナント重複172.16・MD5認証・/23集約。実機0→100検証済。★罠=vrf forwardingでIP剥がれ(taskに明かさない)。値固定(params未対応・再出題は要注意) |
| ENARSI-GREIPSEC-MAP-01 | 4 | ipsec,gre,crypto-map | 4 | console |  |  |
| JUNOS-BUILD-01 | 3 | junos,ospf,routing-policy,commit,multivendor | 2+JUN01 | ssh |  | BL-061初弾(2026-07-29)。★Junos主役シリーズ第1弾: JUN01(vJunos EVO/containerlab)をゼロから組み立て(set/commit confirmed/policy-statement export)・Cisco据え付け対向。実機0→100検証済。解答動線=`ssh admin@172.20.20.2`(CMLコンソール不使用)。provision約5分(EVOブート込)・RAM7.3GiB(szk-cl01) |
| ENARSI-IPSEC-IKEV2-01 | 4 | ipsec,svti,ikev2 | 4 | console |  |  |
| ENARSI-IPSEC-VTI-01 | 3 | ipsec,svti,ikev1 | 3 | console |  |  |
| ENARSI-MPLS-L3VPN-01 | 3 | mpls,ldp,l3vpn | 7 | ssh |  |  |
| ENARSI-MPLS-L3VPN-02 | 4 | mpls,l3vpn,vpnv4 | 7 | ssh |  |  |
| ENARSI-MPLS-L3VPN-03 | 5 | mpls,l3vpn,vpnv4 | 7 | ssh |  |  |
| ENARSI-MPLS-L3VPN-04 | 4 | mpls,l3vpn,vpnv4 | 7 | ssh |  |  |
| ENARSI-MPLS-L3VPN-05 | 4 | mpls,l3vpn,vpnv4 | 12 | ssh |  |  |
| ENARSI-MPLS-L3VPN-06 | 5 | mpls,l3vpn,vpnv4 | 9 | ssh |  |  |
| ENARSI-OSPF-MADJ-01 | 4 | ospf,multi-area,abr | 6 | ssh |  |  |
| ENARSI-REDIST-BGP-LOOP-01 | 5 | redistribution,bgp,eigrp | 4 | ssh | base,s28776 | s28776=実機検証済インスタンス |
| ENARSI-REDIST-LOOP-01 | 5 | redistribution,ospf,eigrp | 4 | ssh | base,s73519 |  |
| ENARSI-REDIST-MUTUAL-01 | 4 | redistribution,ospf,eigrp | 4 | ssh | base |  |
| ENARSI-REDIST-POLICY-01 | 4 | redistribution,route-map,policy | 4 | ssh | base | 選択的再配送・ポリシー制御構築問(BL-068)。仕様書駆動: 選択遮断/E1指定/プレフィックス毎seed metric/出自タグ/監査。出題時は新seed生成 |
| ENARSI-URPF-01 | 4 | urpf,security,anti-spoofing | 3 | ssh |  |  |
| ENARSI-VRFLITE-DNBIT-01 | 4 | vrf-lite,ospf,redistribution | 3 | ssh |  |  |

### 生成済み GEN インスタンス

★既存インスタンスは**ユーザに既出の可能性あり**。GEN 系の出題は原則「生成器で新 seed を切って新インスタンスを作る」(下の生成器一覧)。既存分は復習用。

| ID | 難 | 分野 | 台数 | access | variant | 備考 |
|----|----|------|------|--------|---------|------|
| GEN-AGG-40350 | 3 | ospf,multiarea,summarization | 5 | ssh |  |  |
| GEN-AGG-6203 | 3 | ospf,multiarea,summarization | 5 | ssh |  |  |
| GEN-BGPCX-4127 | 5 | bgp,ospf,mp-bgp | 7 | ssh |  |  |
| GEN-BGPCX-5291 | 5 | bgp,ospf,mp-bgp | 7 | ssh |  |  |
| GEN-BGPCX-6100 | 5 | bgp,ospf,mp-bgp | 8 | ssh |  |  |
| GEN-BGPPATH-4410 | 5 | bgp,path-selection,troubleshooting | 4 | ssh |  |  |
| GEN-BGPRR-4500 | 5 | bgp,route-reflector,ibgp | 4 | ssh |  |  |
| GEN-BGPTS-5800 | 5 | bgp,mp-bgp,troubleshooting | 4 | ssh |  |  |
| GEN-CHAIN-6190 | 5 | ospf,bgp,route-reflector | 12 | ssh |  |  |
| GEN-CHAIN-9000 | 5 | ospf,bgp,route-reflector | 12 | ssh |  |  |
| GEN-CHAIN-9200 | 5 | ospf,bgp,route-reflector | 12 | ssh |  |  |
| GEN-CHAIN-9300 | 5 | ospf,bgp,route-reflector | 12 | ssh |  |  |
| GEN-CHAIN-9301 | 5 | ospf,bgp,route-reflector | 12 | ssh |  |  |
| GEN-CHAIN-9500 | 5 | ospf,bgp,route-reflector | 12 | ssh |  |  |
| GEN-CHAIN-9600 | 5 | ospf,bgp,route-reflector | 12 | ssh |  |  |
| GEN-CHAIN-9700 | 5 | ospf,bgp,route-reflector | 12 | ssh |  |  |
| GEN-CHAIN-9711 | 5 | ospf,bgp,route-reflector | 12 | ssh |  |  |
| GEN-CHAIN-9800 | 5 | ospf,bgp,route-reflector | 12 | ssh |  |  |
| GEN-DNSDHCP-100 | 3 | dns,bind9,dhcp | 4 | ssh |  |  |
| GEN-DNSDHCP-101 | 3 | dns,bind9,dhcp | 4 | ssh |  |  |
| GEN-DNSTS-510 | 4 | dns,bind9,dhcp | 4 | ssh |  |  |
| GEN-DOJO-ASPATH-8802 | 3 | aspath,bgp,filtering | 2 | ssh |  |  |
| GEN-L2TS-6158 | 4 | etherchannel,lag,l2 | 2 | telnet |  |  |
| GEN-LOOPPOC-1 | 1 | bgp,eigrp,redistribution | 4 | ssh |  | ★PoC 検証用。出題しない |
| GEN-MPLSTS-100 | 5 | mpls,ldp,l3vpn | 12 | ssh |  |  |
| GEN-MPLSTS-7100 | 5 | mpls,ldp,l3vpn | 12 | ssh |  |  |
| GEN-OSPF-2348 | 2 | ospf,igp,generated | 4 | ssh |  |  |
| GEN-PATH-14649 | 4 | ospf,path-selection,cost | 4 | ssh |  |  |
| GEN-PATH-4711 | 4 | ospf,path-selection,cost | 4 | ssh |  |  |
| GEN-PATH-57391 | 4 | ospf,path-selection,cost | 4 | ssh |  |  |
| GEN-PATH-77312 | 4 | ospf,path-selection,cost | 4 | ssh |  |  |
| GEN-AAAGRP-51201 | 4 | aaa,radius,security,server | 4 | ssh |  | ★BL-001/BL-101 P2。**サーバ側(FreeRADIUS×2)は完成品**で渡し課題は機器側 AAA のみ。**3フェーズ挙動採点(正常/片系断/全断)**= 採点が実際にサーバを止めて実ログインで確認し自動復旧する(採点中1分ほどログインが不安定)。実機フルサイクル検証に使った初号機(問題パック自体は素の状態・再provision で基線から始まる)。出題は原則**新 seed** |
| GEN-RADIUS-100 | 4 | aaa,radius,security | 3 | ssh |  |  |
| GEN-REDISTLOOP-6601 | 5 | redistribution,bgp,eigrp | 4 | ssh | base |  |
| GEN-REDISTRO-101 | 5 | redistribution,rip,ospf | 6 | ssh |  | seed_loop のみ実機済。他故障は出題前に実機1サイクル推奨 |
| GEN-SNMPTS-100 | 4 | snmp,snmpv3,monitoring | 4 | ssh |  |  |
| GEN-SNMPTS-4201 | 4 | snmp,snmpv3,monitoring | 4 | ssh |  |  |
| GEN-SNMPTS-5301 | 5 | snmp,snmpv3,monitoring | 4 | ssh |  |  |
| GEN-TS-15505 | 4 | ospf,troubleshooting,generated | 5 | ssh |  |  |
| GEN-TS-31337 | 3 | ospf,troubleshooting,generated | 5 | ssh |  |  |
| GEN-TS-43317 | 5 | ospf,troubleshooting,generated | 5 | ssh |  |  |
| GEN-TS-48160 | 4 | ospf,troubleshooting,generated | 5 | ssh |  |  |
| GEN-TS-64436 | 4 | ospf,troubleshooting,generated | 4 | ssh |  |  |
| GEN-TS-729 | 4 | ospf,troubleshooting,generated | 4 | ssh |  |  |
| GEN-TWIST-46822 | 3 | ospf,route-filtering,generated | 5 | ssh |  |  |
| GEN-TWIST-51847 | 3 | ospf,route-filtering,generated | 4 | ssh |  |  |
| GEN-TWIST-58271 | 3 | ospf,route-filtering,generated | 4 | ssh |  |  |
| GEN-TWIST-85186 | 3 | ospf,route-filtering,generated | 4 | ssh |  |  |
| GEN-URPF-4242 | 5 | urpf,security,troubleshooting | 3 | ssh |  |  |
| GEN-URPF-7777 | 4 | urpf,security,troubleshooting | 3 | ssh |  |  |
| GEN-ZBXBUILD-200 | 3 | snmp,snmpv3,monitoring | 4 | ssh |  |  |
| GEN-ZBXBUILD2-810 | 3 | snmp,snmpv3,monitoring | 4 | ssh |  |  |

## 特殊ラボ(lab.sh ではなく専用 ops CLI で運用)

build/grade/teardown を各 ops スクリプトのサブコマンドで行う。使い方は各スクリプト冒頭 docstring 参照。

| ID | 難 | 分野 | 台数 | 運用CLI (topologies/) | 備考 |
|----|----|------|------|----------------------|------|
| CAMPUS-TS-01 | 5 | ospf,hsrp,stp | 11 | `campus_ops.py` | 3層キャンパス障害演習。11VM・ASA含む。build→inject <fault>→grade→destroy |
| EVPN-VXLAN-01 | 3 | evpn,vxlan,spine-leaf | 4 | `evpn_ops.py` | build 約7分。★SDA-LISP-01 と同時稼働不可(リース.37重複+RAM)。採点は P2a 温め必須 |
| SDA-LISP-01 | 3 | sd-access,lisp,vxlan | 6 | `sda_ops.py` | ガイド付き伴走ラボ。build 約6分。★EVPN-VXLAN-01 と同時稼働不可 |
| UM2-BUILD-01 | 5 | vrf-lite,hsrp,track | 6 | `um2_ops.py` | 書籍UM2再現。★出題済(96→100点)。★20ノード上限で 01/02 同時起動不可 |
| UM2-BUILD-02 | 5 | vrf-lite,hsrp,track | 6 | `um2_ops.py` | ワンアームLB変種(build --variant onearm)。★01と同時起動不可 |
| FGT-SDWAN-01 | 3 | sdwan,performance-sla,health-check | 1 | `sdwan_ops.py` | 共用ラボFGT-LAB。★fgt1 wipe禁止(eval ライセンス消失)。destroy なし(stop のみ) |
| FGT-FW-BASIC-01 | 2 | firewall-policy,address-object,snat | 1 | `fgtbasic_ops.py` | 共用ラボFGT-LAB。同上の wipe/stop 制約 |
| FGT-IPSEC-01 | 3 | ipsec,ikev2,svti | 2 | `fgtipsec_ops.py` | FGT×IOS interop。共用ラボFGT-LAB。同上。★Phase 0=管理IF(port3)自己設定から始まる(2026-07-23課題化・buildがport3を白紙化) |
| FGT-REPLACE-01 | 4 | asa-config-reading,firewall-migration,security-level | 1 | `fgtreplace_ops.py` | ASA読替の卒業試験。共用ラボFGT-LAB。同上 |

## 自動化ラボ(lab/<ID>/ の作業コピーを VSCode で編集して解く)

provision は lab.sh(通常問題と同じ)。採点前にユーザの playbook 実行が前提。

| ID | 難 | 分野 | 台数 | access | variant | 備考 |
|----|----|------|------|--------|---------|------|
| ANSIBLE-01-INVENTORY | 1 | automation,ansible,inventory | 3 | ssh | base | 自動化道場L1 |
| ANSIBLE-02-ADHOC | 1 | automation,ansible,adhoc | 3 | ssh | base | 自動化道場L2 |
| ANSIBLE-03-PLAYBOOK | 2 | automation,ansible,playbook | 3 | ssh | base | 自動化道場L3 |
| ANSIBLE-04-VARS | 2 | automation,ansible,variables | 3 | ssh | base | 自動化道場L4 |
| ANSIBLE-05-IDEMPOTENCY | 2 | automation,ansible,idempotency | 3 | ssh | base | 自動化道場L5 |
| ENARSI-AUTO-BGP-01 | 3 | automation,ansible,bgp | 2 | ssh | base |  |
| ENCOR-AUTO-OSPF-FILL-01 | 2 | automation,ansible,ospf | 3 | ssh | base |  |
| ENCOR-AUTO-OSPF-ROLE-01 | 3 | automation,ansible,ospf | 3 | ssh | base |  |
| ENCOR-AUTO-OSPF-SCRATCH-01 | 4 | automation,ansible,ospf | 3 | ssh | base | controller のみ(blanks なし) |
| NETAUTO-03-RESTCONF | 2 | automation,restconf,python | 1 | ssh |  | cat8000v。RESTCONF 起動待ち約1分 |

## 生成器一覧(GEN 問題の新規出題)

共通手順: `.venv/bin/python3 topologies/<生成器> --repo . --seed <新seed>` → `problems/<生成ID>/` ができる → `scripts/lab.sh provision <生成ID>`。
軸・故障種の詳細は各スクリプトの docstring / `--help`。**同 seed = 同問題**(再現可能)。

| 生成器 (topologies/) | 出題ID接頭 | 内容 | 軸・注意 |
|---------------------|-----------|------|----------|
| `gen_topology.py` | GEN-OSPF | ランダムツリー OSPF 構築・到達性 | 難2 |
| `gen_twist.py` | GEN-TWIST | ルートフィルタひねり | |
| `gen_aggregate.py` | GEN-AGG | 経路集約・マルチエリア | |
| `gen_pathctrl.py` | GEN-PATH | 経路制御・冗長 | |
| `gen_troubleshoot.py` | GEN-TS | OSPF 故障TS | `--n` 台数 / `--faults` 多重・おとり・段差 |
| `gen_bgp_troubleshoot.py` | GEN-BGPTS | BGP 到達性TS | |
| `gen_bgp_pathts.py` | GEN-BGPPATH | BGP 経路選択TS | 後継=gen_bgp_ring_ts(shape=path_select)。新規出題はそちら推奨 |
| `gen_bgp_ring_ts.py` | GEN-BGPRING | ★★リングBGP=**AS設計/ポリシー層の統一生成器(BL-093完成形)**: 4台リング固定×AS配置抽選(4AS別/自社対角同一AS+ISP×2/全iBGP)×shape抽選・難4-5・4 IOL | **1つのIDから5形が出る**: ①isp_exchange=ISP越し自社AS交換不能(variant=allowas_full/partial/**override_partial**=ISP側as-override残骸で片側だけ通る) ②no_transit=非トランジット化(`--solution aspath/routemap` 解法強制・監査regex) ③path_select=対角双方向経路指定(LP/prepend欠落・誤適用/weight残骸/**MED異AS比較=always-compare-med**) ④stale=監査是正(実害weight・裏LP×無害allowas-in・as-override混在全撤去) ⑤ibgp_ring=フルメッシュ欠落(全Established対角欠け)/network欠落/OSPF Lo欠落。`--shape`/`--faults 2`指定可。task.mdはCisco語＋論理構成非提示。全shape×全解法軸×複合 実機11サイクル済(2026-08-06)・検証seed掃除済・出題時新seed |
| `gen_bgp_rrts.py` | GEN-BGPRR | RR 伝播TS | |
| `gen_bgp_complex_ts.py` | GEN-BGPCX | BGP 複合TS(7台4AS・26故障・48変種) | `--faults` `--policy-faults` ほか変種軸 |
| `gen_eigrp_complex_ts.py` / `gen_ospf_complex_ts.py` / `gen_ospfv3_complex_ts.py` / `gen_eigrpv6_complex_ts.py` | GEN-EIGRPCX 等 | IGP 複合TS | |
| `gen_redist_mutual_ts.py` | GEN-REDIST系 | 相互再配送TS | |
| `gen_redist_arena.py` | GEN-RDARENA | 再配送ループ・アリーナ=トポロジ抽選型ループ特化(BL-074 Phase1・難5・5〜8台) | **通常出題は gen_redist_field.py 経由(shape=ring)を推奨**(IDから型が割れないため)。単体はループ確定で出したい時のみ。generate()関数化済(prob_id差替可)。実機検証済・提示改修済・出題時新seed |
| `gen_redist_field.py` | GEN-RDFIELD | ★★再配送フィールド=**統一生成器(BL-074完成形)**: shape抽選 chain50%/twoborder25%/ring25%・難4-5・3〜8台 | **1つのIDから3形が出る**(どれが来たかは非自明): ①chain=木構造トラブル(missing/wrong_id/no_seed/filter・全4型実機済・`--hard`=K3+subtle保証) ②twoborder=2点相互再配送(mutual_ts定石移植・no_tag次善/missing両方向/seed_metric・AD95固定・タグ衛生が健全形・no_tag 60→100/seed_metric 20→100実機済) ③ring=ループ(arena委譲・25→100実機済)。`--shape`指定可。★監査regexは表示形/検証seedは掃除済・出題時新seed |
| `gen_redist_ripospf_ts.py` | GEN-REDISTRO | RIP⇄OSPF 再配送ループTS(7故障) | ★seed_loop 以外は出題前に実機1サイクル推奨。★実測(2026-08-13・BL-116)= **wrong_tag_filter は定常ループにならず振動**(境界2台の状態が入れ替わり・経路消失の窓・ping 0%⇄100%。seed 1 の同値タイ×タグ半遮断が原因)。task.md の症状文「ループしている(TTL超過)」は「断続的に到達不能」が実態。**seed 5 に変えると安定した素通り+片境界遠回り**(紙面 shape=riploop はこちらを採用) |
| `gen_redist_loop_ts.py` | GEN-REDISTLOOP | 再配送リング BGP ループTS | `--variant ad_ospf/ad_eigrp/filter_ospf`(3変種とも実機済。filter_ospf は distance 禁止→フィルタ解法強制) |
| `gen_redist_mp_ts.py` | GEN-REDISTMP | 多点相互再配送 定常ループTS(6台・AD無操作) | `--solution acl/prefix/routemap/distance`(要求解法を seed 抽選し監査ポリシーで強制。4モードとも実機フルサイクル済・出題時は新seed) |
| `gen_chain_ts.py` | GEN-CHAIN | 12台レイヤ連鎖故障(17故障) | `--chain-depth 0/2/3/4`・fullmesh/branch×IGP軸 |
| `gen_mpls_ts.py` | GEN-MPLSTS / GEN-MPLSEB | 12台 MPLS L3VPN TS | `--pece ebgp` で PE-CE eBGP 軸 |
| `gen_l2_troubleshoot.py` | GEN-L2TS | EtherChannel 等 L2 TS | access=telnet |
| `gen_urpf_ts.py` | GEN-URPF | uRPF 4故障(データプレーン効果採点) | `--fault` 指定可 |
| `gen_fnf_ts.py` | GEN-FNFTS | Flexible NetFlow 監視標準 適合TS(3台・故障10種・仕様書突き合わせ型) | `--fault` 指定可・`--faults 2` で別レイヤ複合(難+1)。全10故障 実機フルサイクル済(2026-07-25)。難3〜5・ENARSI シム対策 |
| `gen_eigrp_vrf_ts.py` | GEN-EGVRF | VRF-aware EIGRP 収容標準 適合TS(4台・故障9種4レイヤ・仕様書突き合わせ型・BL-070②) | `--fault` 指定可・`--faults 2` で別レイヤ複合(難+1)。全9故障+複合1 実機フルサイクル済(2026-07-27)。難3〜5。★af-interfaceはIF非所属VRFだとday0破棄→vrf_if_swapのfixは認証再投入込み |
| `gen_dhcp_ts.py` | GEN-DHCPTS | DHCPv4 配布標準 適合TS(5台・故障8種3レイヤ・仕様書突き合わせ型) | `--fault` 指定可・`--faults 2` で別レイヤ複合(難+1)。全8故障 実機フルサイクル済(2026-07-26)。難3〜5。★目玉=relay_service_off(リレー機 no service dhcp・helperは完璧に見える)/acl_src_narrow(DISCOVERのみ落ちる) |
| `gen_dmvpn_ts.py` | GEN-DMVPN | DMVPN+IPsec TS(**16故障**・`--faults 2`複合可) | ★**全16種実機フルサイクル済**(2026-08-05 BL-089: 新規i7=profileのset transform-set欠落=既定TSフォールバック/i8=レガシーprofile誤参照＋残8種スイープ)。★**`--faults 2`(BL-091)**=1ルータ1故障で2箇所(hub+spoke/spoke×2・i3/r2は単独専用・中立チケット2枚・難max+1)・複合2型実機済(31002/31001)。IOSv・console採点。★i7/i8のfixはclear不十分→Tunnel0 shut/no shut必須(fix.jsonに組込済)。fix投入はSSH不可(旧kex)→fix.jsonをfix_console形式へ変換しconsole経路で |
| `gen_vrf_maze.py` | GEN-VRFMAZE | ★おまけ枠「VRF迷路」(2台IOL・物理1本×dot1qサブIF折り返し×VRFチェーニング・故障5種+healthy・難2-3) | ★**全5故障実機フルサイクル済**(2026-08-05 BL-092)。**足跡採点**=tracerouteのホップ番号×中継IPで順路を拘束+「ちょうどL歩」。`--rooms 3-5`/`--fault`指定可・SSH採点・出題時新seed。bringup_ifs は生成器が自動出力(手当不要) |
| `gen_s2svpn.py` | GEN-S2SVPN | 複数拠点 IPsec VPN 設計構築(要件書形式・技術選定自由・8台) | 運用=`s2svpn_ops.py`(console・リース不要)。seed軸=支店ごとfull/split×支店間4種×公開静的NAT。svti/cmap両模範解で実機4サイクル済(2026-07-24)・出題時は新seed・難4 |
| `gen_s2svpn.py --day2` | GEN-S2SVPN-\*-D2 | Day2運用チケット3本(支店追加×仕様書食い違い/full→split移行/サブネット重複×NAT overlapping・12台) | 手順=build→`solve --mode base`→`day2init`→受講者→`grade --ticket t1/t2/t3`(各100点・回帰込み)。3チケット実機済(2026-07-25)・難5・BL-063既習前提 |
| `gen_list_dojo.py` | GEN-DOJO-* | フィルタ道場(prefix/aspath/ACL) | `--dojo prefix/aspath/acl` |
| `gen_dnsdhcp_build.py` / `gen_dnsdhcp_ts.py` | GEN-DNSDHCP / GEN-DNSTS | BIND9+DHCP 構築/TS | Linux ノード |
| `gen_radius_build.py` | GEN-RADIUS | FreeRADIUS 構築 | |
| `gen_aaa_build.py` | GEN-AAAGRP | ★冗長 AAA(RADIUS サーバグループ)構築(BL-001/BL-101 P2・難4・4ノード) | 紙面 `shape=aaa` と**同一盤面・同一語彙**の実機側(両刀)。SRV01=標準ポート/SRV02=**非標準ポート**・**サーバ毎に別鍵**・clients は各ルータの **Loopback0 のみ受理**(→`ip radius source-interface` が主罠)。要件= 個別サーバ定義/グループ化(**SRV01 優先**)/`group <G> local`/片系断の遅延≤5秒/**応答不能サーバの切り離し**/exec 課金。★採点の目玉= **3フェーズ挙動採点**(SRV01 上の `/opt/ccnp/aaa_phase.sh` が停止→実ログイン観測→自動復旧を1本で完結。`grade.yml` は ios を全件集めてから shell を回すため、この形以外に順序を作れない)。★**`deadtime` 単独では無効**で `radius-server dead-criteria` が要る(実測 poc/aaa/README.md §19)。実機= 基線6→100/100・連続4回安定・負のテスト2種で降格実証。出題時は**新 seed** |
| `gen_snmpv3_ts.py` | GEN-SNMPTS / GEN-ZBXBUILD(2) | SNMPv3/Zabbix 監視TS・構築 | `--mode build [--level 2]` で構築問 |
| `gen_bgpbest_ts.py` | GEN-BGPBEST | ★BGP ベストパス運用基準 適合ラボ(BL-115・6 IOL・SSH採点・**紙面 shape=bgpbest と故障種名を共有する両刀**) | 運用基準5本(MED合意=acm/戻りはリンク別MED 10-200-300/決定性=crid/境界経路の有効性=NHS/監査=weight・LP上書き禁止)を常設し、**TS**= `--fault` 6種(acm_missing/crid_missing/nh_no_self/weight_remote/lp_ebgp/med_swapped・全種実機 broken→fix→100 済 2026-08-13)・**build**= `--mode build`(ポリシー白紙・実機 20→100 済)。★採点は `show ip bgp <pfx> bestpath` サブコマンド(実測B1)で best を判定(DOTALL横断regexは偽合格の危険で禁止)・受信MEDは「from行→Origin行」の行ペアregex。★境界が広告し返すのは**タイprefix(P2)だけ**(MED合意で境界のPベストはiBGP学習→スプリットホライズン。境界経由チェックはP2で行う)。★crid_missing のbroken時P2チェックはoldest依存で±10揺れる(監査-5は決定的)。出題時は新seed |
| `gen_paper_mcq.py` | (紙面: questions/日付-連番.md) | ★紙面問題 統一生成器(shape= chain/ring/mploop/**riploop**/pbr/urpf/bgpdbg/**leakmap**/**ospfv3pl**/**v6redist**/**aaa**/**acl**/**aclv6**/**bgpbest**/mixed) | 常用=`--shape mixed --exam` 新seed(--hard は chain 用)。**riploop(BL-116・2026-08-13)**= RIP⇄OSPF 二点相互再配送の「対策が効いていない」型(GEN-REDISTRO 盤面流用・実機展開あり)。kinds= wrong_tag_filter(match tag 不一致素通り)/half_fix(distance 片境界のみ)/stale_filter(残骸 distribute-list)/seed_loop(同値ECMPタイ定常ループ・cause専用)・形= fix/cause・症状3型(周回/遠回り/偏り)。★紙面版 wrong_tag は seed 5 で安定化(seed 1 は振動=実測)。urpf/bgpdbg/**leakmap**/**ospfv3pl**/**v6redist**/**aaa**/**acl**/**aclv6** は紙面専用(実機展開なし・挙動は PoC 実測の写像)。**BL-121 P2(2026-08-16)**= 同リーン世界を v4 acl(FILTER_WORLDS)へも移植(std/ext 両対応・one_line の「のみ」潜在矛盾も両家族で解消)。**BL-122(2026-08-16)**= 再配送系(chain/ring/mploop/riploop)の形式抽選を config解決系(fix+select2)~70% へ増量+ring(tag)/mploop(routemap) の fix 形に**方向反転錯乱肢**(set/deny の場所を入れ替えた鏡像の対・why=「守る向きが逆」)。**BL-123(2026-08-16)**= aaa に新形 `patchseq`((順番,操作)ペア6択から2つ選択・①前提作業→②切替・patch枠と50/50)+patch/patchseq に前提文「台帳および構成は示されているものが全てです」常設。**BL-124(2026-08-16)= bgpdbg 選択式化・パック合流**= 記述式(BL-085)を4形の選択式へ= `dbgconf`(逆問題・構成ペア5択。★可視指紋モデルで一意性を機械検証= ebgp の no route to peer は送信元が観測できないので、可視でない軸を動かした錯乱肢を排除)/`select2`(是正2アクション・6択正解2。ebgp は「片側だけの multihop では確立しない」実測が Choose two の必然)/`fix`(asym_up 単一選択・決定的錯乱肢=両側 update-source 無し=Idle)/`read`(asym_up「なぜ UP か」複数選択)。正解組は全組合せ総当たりで機械判定・要件(Lo設計維持/開始側非依存)が是正形の一意性の担い手。mixed 5%(BGP計13%)・パック必須ジャンル `bgp`(bgpbest+bgpdbg)新設。記述式は `--forms essay` 明示時のみ。**aclv6 リーン要件世界(BL-121・2026-08-16)**= WORLDS に `lean_only`(非包含の明文なし・「のみ」+deny禁止から排他を導出)と `lean_hole`(「のみ」も無し・名指し禁止網=4本目が集約の踏み絵)を追加(排他の担い手が世界ごとに違う3段難度系列。`--worlds lean_only/lean_hole` 指定可・mixed でも抽選)。**leakmap(BL-095+096③・2026-08-07)**= EIGRP 集約×リーク手段選択・故障7種(★共用route-map編集副作用=エコ形含む)・要件世界4種(再配送禁止/Lo network禁止/内部限定/IF集約禁止)で正解反転・fix/cause/read の3形・リスト乱立読解。実測表= poc/leakmap/README.md。**ospfv3pl(BL-097 P1・2026-08-08)**= OSPFv3 マルチエリア prefix-list(16進繰り上がり・/44〜47中間マスク・ge/le)・現在状態8種×要件世界5種(エリア限定/全域遮蔽/RIBのみ/最小集約/全停止)で正解反転・fix/read の2形(cause は P2)・実機5ケース突き合わせ済。実測表= poc/ospfv3-pl/README.md。**v6redist(BL-098 P1/P2・2026-08-08)**= OSPFv3⇄EIGRPv6 相互再配送「C1↔C2 を通すには」手段選択(ユーザ手組みラボ発案)・★核心=再配送は動いているが include-connected が拾ったトランジットだけが渡り客先LANは prefix-list に落ちている(壊れて見えない)・故障5種×要件世界8種で正解反転・**形4種= fix(常にCLI提示)/cause/read/★trace(ping3値 `% No valid route`・`..`・`!!` の読み分け)**・selftest= world未指定 600/600。実測表= poc/v6redist/README.md。**aaa(BL-101 P1a・2026-08-08)**= IOS AAA(RADIUS)の読解(紙面 shape と実機ラボで**故障種名を共有**する両刀ベース)・故障種9(user_not_registered/key_mismatch/src_iface_missing/port_mismatch/no_authz_exec/authz_no_fallback/list_not_applied/list_undefined/enable_via_radius)×要件世界4×出題形4= read/cause/trace/**★evidence(「次に取得すべき出力はどれか」= 紙面初の形)**。挙動は `topologies/aaa_model.py`(AAA 意味評価器・PoC 実測 B0/E1〜E18 と一致を selftest で保証)から生成。核心= **Reject は後段へ落ちない/無応答のときだけ落ちる**(認証・認可・昇格の3層で成立)・**共有鍵不一致と送信元誤りは機器側で区別不能**(決め手はサーバ側ログ)・**未定義リスト参照は default へ落ちる**(適用忘れと同症状)。実測表= poc/aaa/README.md。★2026-08-08 拡張= **console 観測**(実測 C1〜C5= console は vty と同一規則・専用リスト未適用だと**サーバ生存時に緊急用ローカル管理者すら入れない**)で故障種10種・要件世界 console_survives が判定可能に／**evidence 形の3つ巴化**(「最も多くの候補を除外できる出力はどれか」・観測を分割数で機械採点=消去法封じ)／**★サーバログを廃し `debug radius authentication` へ**(ENARSI 範囲外の証拠を使わない・実測で機器側だけで全ての無応答が割れると確認)／**新形 dbgread**(debug から送信元・auth-port・timeout・retransmit を読み取る)／ルータのアドレス表を常設。★**P1b(2026-08-08)= fix/patch 追加で出題形7種**= read/cause/trace/evidence/dbgread/**fix**(被覆エンジン=直る候補≥2・要件適合=1・CLI状態収束形・世界 server_frozen/default_frozen で正解反転)/**patch**(★切らずに移行する順序=no_lockout 専用・「今入れても誰も切れず切替を安全にする」を機械判定)。★**BL-103 ①(2026-08-08)= 新形 dbgconf で出題形8種**= `debug radius authentication` の出力だけを見せ**それを生じさせる構成**を4つの構成抜粋から選ばせる逆問題。`debug_render()` が dev の純関数なので候補構成それぞれから描き直して一意性を機械検証(被覆エンジンの debug 版)。選択肢は debug が明かす範囲の構成だけ(鍵・方式リストは全候補同一=読めない値を動かした候補は反証不能なので使わない)。**仕様表と一致する構成を選ぶだけで解ける抜け道は塞いである**(0/1000盤面)。★**BL-103 ②〜⑥完了(2026-08-09)= 故障種16・出題形9**(★2026-08-10 `deadtime_only` 追加= `deadtime` は書いてあるが `radius-server dead-criteria` が無く、応答しないサーバが DEAD にならないので**片系断で毎回タイムアウトを食う**。観測は所要時間の行を常設して表す)。追加故障種5= `authz_console_missing`(コンソールの認可はグローバル `aaa authorization console` が無いと**実行されず権限レベル1**になる=実測 X5/X6/X11/X12)/`authz_if_authenticated`(認可の代替が属性を与えず、**全断でフォールバックしたときだけ priv 1**)/`acl_block_request`・`acl_block_reply`(ACL 遮断は機器側の症状がサーバ停止と**完全同一**で、決め手は `show ip access-lists` のカウンタのみ。要求遮断と応答遮断は debug でも同一)/`vty_range_partial`(方式リストが `line vty 0 4` にしか当たらず**6セッション目以降だけ挙動が変わる**)。追加形= **authread(2つを選択・このリポ初の複数選択)**= `debug aaa authentication` の **enable 認証**の遍歴(`Method=`→`status = PASS/FAIL/ERROR`)を読ませる。★観測に**「認証サーバがすべて停止した場合」の表を常設**(全故障種一律)。これが無いとフォールバック側の故障が観測に現れず、設問文と矛盾していた(`authz_no_fallback` は 60/60 で健全と同じ表だった)。検証= 家族 selftest 3480/3480＋authread selftest 600/600・多エージェント監査で12件の欠陥を検出し修正済み。 | **acl(BL-106)= ACL 単独読解**: ロール(filter=ip access-group / routefilter=distribute-list)を衣装として着せる。故障種**30**・ロール**6種**(filter/routefilter/copp/urpf/nat/vty)・要件世界**16種**・形**10種**(select=構築系「このレンジを指定する行はどれか」/ read=読解(**2つ選べ**にも対応)/ cause / **counter**=カウンタが増える行(first-match) / **patch**=1行追加の**挿入位置** / **fix**=是正手段 / **evidence**=次に取るべき出力 / **logread**=ログ読解(2つ選べ))。一意性は `acl_cover.py`(32bit 三値キューブ代数)で機械検証。★実測(poc/acl §4-4)= **distribute-list の拡張 ACL は参照経路で意味論が入れ替わる**(直接指定= src=広告元ルータ/dst=網・長さ不可 / route-map経由= src=網/dst=マスク・長さ可)。★**dense_list(多エントリ読解・常に9行)**= 先行 deny の影・`range` 境界・ICMP タイプ・`established`・**送信元ポート**を1行ずつ突き合わせる。read(2〜3つ選べ)/counter/**compare(3フロー×8通り)** を持つ。★★**BL-109 段A(2026-08-11)= 適用点を主題化**: `ip access-group` の位置と向きを読ませる。追加故障種5= `apply_wrong_acl`(ACL が2枚あり広いほうが適用されている)/`apply_missing`/`apply_other_iface`/`filter_undef_ref`/`filter_empty_acl`。後ろ4種は**全部素通り**で症状が同じなので **evidence 形**(どの出力なら候補を最も絞れるか)で出す。併せて **filter ロールの設定抜粋を `show running-config | section ^interface` に差し替え**(従来の `| section access-list|access-group|...` は**インターフェイス名を出さない**うえ、実機は同じ正規表現で ACL 本体まで出すため不忠実だった。実測= poc/acl §16-1)。★★**段B(2026-08-11)= 適用マップと入口/出口の二段評価**。紙面の観測は往復の到達性なので、**復路だけが落ちる**盤面を表現できる= `apply_direction`(同じ IF で向きだけ逆)/`apply_iface_swap`(サーバ側の in)は**往路は素通りなのに全断**(要件どおりの ACL には暗黙の拒否があるため・実測 §16-10)。★**新形 `apply`**= 「どこに・どの向きで適用すべきか」の6択(要件世界3種で**正解の IF が反転**= `src_customer`→顧客側 in / `src_server`→サーバ側 in / ★**`deny_to_mgmt`→管理 IF の out**。★**3世界とも構造で一意**(2026-08-11 改訂= 管理セグメントとの通信を要件に入れたので、出口側の解は**関係のない通信を巻き添えにする**。以前は「早い段階で破棄」という文体上の制約で落としていた。実機ではさらに §16-11 のとおり 25 秒後にルーティングが壊れる)、`deny_to_mgmt` は**標準 ACL が送信元しか見ない**ことから構造的に1つに決まる＝**定石から外れた位置が正解**になり、パターン暗記を封じる)。常用= `--forms apply` で構築系だけ、`--kinds` で適用点だけ、**`--worlds` で要件世界**を指定できる(例= `--worlds deny_to_mgmt`)。★**WC トリック世界(2026-08-11)**= 対象集合の**形**を要件世界にし、1行で書くために必要なワイルドカードを変える= `wc_even`(第3オクテットが偶数→`0.0.6.255`)/`wc_odd`(奇数→base を+1して `0.0.6.255`)/`wc_split`(飛び地→**非連続** `0.0.5.255`)/`wc_block`(連続4本→`0.0.3.255`)。要件文は**列挙のまま**にして性質は気付かせる。錯乱肢は1行のものを4本以上並べ、理由文は盤面から計算する。★`wc_bits`(非連続=故障)×`wc_split`(非連続=正解)は**症状が出ない**ので非両立宣言＋draw() で毎回検査。★**戻り通信 `established`(2026-08-11・論点14)**= 盤面が**2枚のリスト**(顧客側 in=往路用／サーバ側 in=復路用)を持つ。`est_missing`(復路に established の行が無く戻りが落ちる)／`est_wrong_side`(established を往路側に書き SYN が落ちる)。どちらも全断なので cause/evidence で出す(**全断系の evidence 群**= apply_direction/apply_iface_swap と合わせて4種から3つ抽選)。観測の見出しは「TCP セッション/確立できる・できない」。実測= §17。★**`est_ret_narrow`**(復路リストの範囲が狭く**往路は全部通るのに一部の顧客網だけセッションが張れない**)はest 系で唯一 read/compare が成立する(compare は往復判定)。★**`est_build`**= 復路用リストを**これから書く**構築系(select・6択)。`established` を省くと**送信元ポートを当該サービスに合わせた新規接続**まで通る、が主題。一意性は4つの観測から**構造的**に出る。★**1行では書けないレンジ(2026-08-11・論点4)**= 対象を **base〜base+6 の7本**にすると最小キューブ(8本)に載らず**1行では厳密に書けない**。`nb_min`(deny 可・行数最小)= 過剰被覆＋deny 先行の2行 / `nb_no_deny`(deny 禁止)= **大きさの違うキューブ3つに分解**(集約の本題。/24 を並べるだけの `exact_no_deny` との違いはここ)。錯乱肢に4行の非最小分解を入れてある。★★**bgpbest(BL-112・2026-08-12)= BGP ベストパス読解(1.11.c)**: `show ip bgp`/detail の合成表を読ませる(★書式は poc/bgpbest 実測の写しで、**実測行との byte 一致を selftest が常時検査**)。kinds= 決め手11種(weight/lp/localorig/aspath/origin/med/**med_cross**=MEDはあるのに異ASで比較されず oldest・RID まで落ちる/ebgp/igp/**rid**=compare-routerid が oldest 段を飛ばす/**nh_invalid**=★表では `*` のまま見分け不可・detail の `(inaccessible)` が唯一の証拠)+誤認3種(weight_remote=別ルータに設定しても伝播しない/lp_ebgp=eBGP へは送られない・無警告受理/remote_lp=対向の LP が MED より先に決まる)。要件世界7(one_router→weight/whole_as→LP/return_med→MED out/return_prepend→prepend/respect_med→always-compare-med/igp_frozen→next-hop-self/**bgp_frozen→IGP 広告が正解に反転**)。形4= **read(★「取り下げ直後の no best path 過渡」で提示= `*>` を出すと答えが表に書いてあるため。B1 実測形)**/why(決め手の段=用語を文脈で問う)/fix(被覆エンジン)/cause(claim 機械判定。★全形 keep_ask= 設問を「正しいものはどれ」へ均すと**一般則として真の錯乱肢で二重正解**になる)。MED 順序依存盤面と「欠落 vs 有値」比較(B10 測定不能)はモデルが strict 拒否。oldest 決着盤面は「クリア/リフレッシュ未実施」を明記(Updated on は soft refresh でも動く=B16 実測)。
| `gen_params.py` | (既存問題の sNNNN variant) | 値違い量産 | `--problem <ID> --seed N` → `params/sN.yml` |
