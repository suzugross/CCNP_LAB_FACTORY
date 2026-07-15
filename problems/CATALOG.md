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
| ENCOR-EDGE-HARDEN-01 | 5 | security,aaa,copp | 2 | ssh |  |  |
| ENCOR-EEM-01 | 3 | eem,automation,assurance | 1 | ssh |  |  |
| ENCOR-EIGRP-01 | 2 | eigrp,igp | 3 | ssh | base,bfd,s4242,v2 |  |
| ENCOR-EIGRP-BUILD-01 | 4 | eigrp,igp,summarization | 5 | ssh | base,bfd | 要件7フィルタ強化の宿題あり(BL-005)。出題は可 |
| ENCOR-EIGRP-VARIANCE-01 | 5 | eigrp,variance,feasible-successor | 5 | ssh | base,bfd |  |
| ENCOR-FHRP-01 | 3 | fhrp,hsrp,l2 | 4 | ssh |  |  |
| ENCOR-FNF-01 | 2 | netflow,flexible-netflow,telemetry | 3 | ssh | base,v2 | IOL は cache timeout active 不可 |
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
| ENARSI-BGP-COMM-01 | 4 | bgp,attributes,community | 2 | ssh |  |  |
| ENARSI-BGP-MED-01 | 3 | bgp,attributes,med | 2 | ssh |  |  |
| ENARSI-BGP-NHSELF-01 | 4 | bgp,ibgp,next-hop | 3 | ssh |  |  |
| ENARSI-BGP-ORIGIN-01 | 4 | bgp,origin,path-selection | 3 | ssh |  |  |
| ENARSI-BGP-POLICY-01 | 5 | bgp,path-control,community | 6 | ssh | base,bfd,s4242,s7777 |  |
| ENARSI-BGP-PREFIX-01 | 3 | bgp,filter,prefix-list | 2 | ssh | base,bfd |  |
| ENARSI-BGP-ROUTEMAP-01 | 4 | bgp,route-map,prefix-list | 3 | ssh |  |  |
| ENARSI-BGP-WEIGHT-01 | 3 | bgp,attributes,weight | 3 | ssh | base,bfd |  |
| ENARSI-DHCPV6-01 | 5 | ipv6,dhcpv6,slaac | 4 | ssh |  |  |
| ENARSI-DMVPN-BGP-01 | 5 | dmvpn,mgre,nhrp | 5 | console |  | DMVPN+BGP再配送 |
| ENARSI-DMVPN-IPSEC-01 | 5 | dmvpn,mgre,nhrp | 4 | console |  | DMVPN+IPsec完全版。★出題済(ユーザ100点) |
| ENARSI-EIGRP-SIA-01 | 5 | eigrp,sia,query | 4 | ssh |  |  |
| ENARSI-GREIPSEC-MAP-01 | 4 | ipsec,gre,crypto-map | 4 | console |  |  |
| ENARSI-IPSEC-IKEV2-01 | 4 | ipsec,svti,ikev2 | 4 | console |  |  |
| ENARSI-IPSEC-VTI-01 | 3 | ipsec,svti,ikev1 | 3 | console |  |  |
| ENARSI-MPLS-L3VPN-01 | 3 | mpls,ldp,l3vpn | 7 | ssh |  |  |
| ENARSI-MPLS-L3VPN-02 | 4 | mpls,l3vpn,vpnv4 | 7 | ssh |  |  |
| ENARSI-MPLS-L3VPN-03 | 5 | mpls,l3vpn,vpnv4 | 7 | ssh |  |  |
| ENARSI-MPLS-L3VPN-04 | 4 | mpls,l3vpn,vpnv4 | 7 | ssh |  |  |
| ENARSI-MPLS-L3VPN-05 | 4 | mpls,l3vpn,vpnv4 | 12 | ssh |  |  |
| ENARSI-MPLS-L3VPN-06 | 5 | mpls,l3vpn,vpnv4 | 9 | ssh |  |  |
| ENARSI-OSPF-MADJ-01 | 4 | ospf,multi-area,abr | 6 | ssh |  |  |
| ENARSI-REDIST-BGP-LOOP-01 | 5 | redistribution,bgp,eigrp | 4 | ssh | base,s28776 | Ping-t#28776派生。s28776=実機検証済インスタンス |
| ENARSI-REDIST-LOOP-01 | 5 | redistribution,ospf,eigrp | 4 | ssh | base,s73519 |  |
| ENARSI-REDIST-MUTUAL-01 | 4 | redistribution,ospf,eigrp | 4 | ssh | base |  |
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
| FGT-IPSEC-01 | 3 | ipsec,ikev2,svti | 2 | `fgtipsec_ops.py` | FGT×IOS interop。共用ラボFGT-LAB。同上 |
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
| `gen_bgp_pathts.py` | GEN-BGPPATH | BGP 経路選択TS | |
| `gen_bgp_rrts.py` | GEN-BGPRR | RR 伝播TS | |
| `gen_bgp_complex_ts.py` | GEN-BGPCX | BGP 複合TS(7台4AS・26故障・48変種) | `--faults` `--policy-faults` ほか変種軸 |
| `gen_eigrp_complex_ts.py` / `gen_ospf_complex_ts.py` / `gen_ospfv3_complex_ts.py` / `gen_eigrpv6_complex_ts.py` | GEN-EIGRPCX 等 | IGP 複合TS | |
| `gen_redist_mutual_ts.py` | GEN-REDIST系 | 相互再配送TS | |
| `gen_redist_ripospf_ts.py` | GEN-REDISTRO | RIP⇄OSPF 再配送ループTS(7故障) | ★seed_loop 以外は出題前に実機1サイクル推奨 |
| `gen_redist_loop_ts.py` | GEN-REDISTLOOP | 再配送リング BGP ループTS | `--variant ad_ospf/ad_eigrp`(両方実機済) |
| `gen_chain_ts.py` | GEN-CHAIN | 12台レイヤ連鎖故障(17故障) | `--chain-depth 0/2/3/4`・fullmesh/branch×IGP軸 |
| `gen_mpls_ts.py` | GEN-MPLSTS / GEN-MPLSEB | 12台 MPLS L3VPN TS | `--pece ebgp` で PE-CE eBGP 軸 |
| `gen_l2_troubleshoot.py` | GEN-L2TS | EtherChannel 等 L2 TS | access=telnet |
| `gen_urpf_ts.py` | GEN-URPF | uRPF 4故障(データプレーン効果採点) | `--fault` 指定可 |
| `gen_dmvpn_ts.py` | GEN-DMVPN | DMVPN+IPsec TS(14故障) | 6種実機済。IOSv・console採点 |
| `gen_list_dojo.py` | GEN-DOJO-* | フィルタ道場(prefix/aspath/ACL) | `--dojo prefix/aspath/acl` |
| `gen_dnsdhcp_build.py` / `gen_dnsdhcp_ts.py` | GEN-DNSDHCP / GEN-DNSTS | BIND9+DHCP 構築/TS | Linux ノード |
| `gen_radius_build.py` | GEN-RADIUS | FreeRADIUS 構築 | |
| `gen_snmpv3_ts.py` | GEN-SNMPTS / GEN-ZBXBUILD(2) | SNMPv3/Zabbix 監視TS・構築 | `--mode build [--level 2]` で構築問 |
| `gen_params.py` | (既存問題の sNNNN variant) | 値違い量産 | `--problem <ID> --seed N` → `params/sN.yml` |
