#!/usr/bin/env python3
"""MPLS のサービスとラベル(BL-261 ④・単元 U-M9 / U-M11 の紙面)— gen_paper_mcq.py の shape=spvpn 素材。

1 つのパケット(フレーム)が 1 区間の上で運ぶラベルの積み方と、ラベルの表の読み方を問う。
設計= problems/_drafts/XR-TRACK.design.md §26.13。

kinds:
  l3_stack(思考・read)        : L3VPN のパケットが、指定した 1 区間の上で運ぶラベル
  l2_stack(思考・read)        : VPWS(LDP・EVPN)・VPLS・EVPN の E-LAN のフレームが運ぶラベル
  owner(瞬発・select/allthat) : 線の上で捕まえた 2 枚のラベルを誰が決め、入口 PE がどうやって知ったか
  lfib(瞬発・match)           : PE のラベル表の行と、そのラベルを付けて届いたパケットの扱い

盤面は 2 つで、どちらも PoC の実測だけを使う。
  svc= 5 サービスの盤面(`_POC-XRSVC`・2026-11-04 の取り直し)= XE1〜3(Catalyst 8000V)・XR01(XRv9000)・P1・RR1
  m9 = M9 の盤面(XRT-09・2026-11-07・課題 4 本を解いた状態)= XR01・RT01・RT02・RT03・XR02(RR)
図の出力(EX)は記録(poc/xr/expSVC-*.log・expM9R-out1.log)の行をそのまま写したもの。selftest が記録の中に
同じ行が同じ順で在るかを照合する(記録が無い環境では照合を飛ばす)。線の上のラベル(SCEN の h1・h2)は
CML のリンクの捕獲(poc/xr/pcap/)の実測で、selftest は図の表から導いた積み方とも突き合わせる。

公開 API は gen_paper_dmvpn.py と同じ(KINDS/kind_forms/draw/build_choices_*/build_match/question_body/
answer_body/pick_count/CORE/TITLES/selftest)。
"""
import os
import random
import re

KINDS = ["l3_stack", "l2_stack", "owner", "lfib"]
SPEED_KINDS = ["owner", "lfib"]
THINK_KINDS = ["l3_stack", "l2_stack"]
WORLDS = ["-"]
KIND_WORLDS = {k: ["-"] for k in KINDS}
FORMS = {"l3_stack": {"read"}, "l2_stack": {"read"}, "owner": {"select", "allthat"}, "lfib": {"match"}}
SPEED_FORMS = {"owner": ["select"], "lfib": ["match"]}
DIFF = {"l3_stack": 4, "l2_stack": 4, "owner": 3, "lfib": 3}
TITLES = {"l3_stack": "L3VPN のパケットが運ぶラベル", "l2_stack": "L2VPN のフレームが運ぶラベル",
          "owner": "ラベルを決めたのは誰か", "lfib": "PE のラベル表の読み方"}
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CORE_STACK = ("入口 PE はラベルを 2 枚積む。外側(先頭)は運ぶ層のラベルで、出口 PE のループバックへの道を表す。番号は**次の機器**が"
              "決めて LDP で配ったもので、入口 PE の表では出口 PE のループバックの行の Outgoing の列にある(Local の列は自分が隣に配った番号)。"
              "内側はサービスのラベルで、番号は**出口 PE** が決める(L3VPN と EVPN は BGP で広告し RR が変えずに反射する・"
              "LDP の疑似回線(VPWS・VPLS)は出口 PE が targeted LDP で直接渡す)。P は外側だけを見て付け替え、出口の 1 つ手前の P は"
              "外側を外して渡す(PHP。表では Pop Label / Pop)。出口 PE が explicit null を広告していれば、外側を外さずラベル 0 に"
              "付け替える(表では explicit-n)。出口 PE は内側の番号で、どの VRF の経路か・どの回線か・どのブリッジ ドメインかを決める。"
              "ラベルの番号は決めた機器の中でだけ意味を持つので、別の機器が同じ番号を別の用途に使っていてもよい。")
CORE = {
    "l3_stack": CORE_STACK,
    "l2_stack": CORE_STACK + (" L2 のサービスでも外側は L3VPN と同じ道のラベルで、違うのは内側だけである。VPLS と EVPN の E-LAN では、"
                              "入口 PE が宛先 MAC から相手の PE と内側の番号を選ぶ(VPLS= 疑似回線ごとの VC_LABEL・EVPN= MAC/IP 広告ルートの"
                              "Label1。宛先が分からないフレームとブロードキャストは EVPN では Inclusive Multicast のルートの BUM 用のラベル)。"),
    "owner": ("外側のラベルは、道の次の機器(P)が出口 PE のループバックに割り当てて LDP で配った番号。内側のラベルは出口 PE が割り当てた"
              "番号で、L3VPN と EVPN は BGP で広告され、RR はネクスト ホップもラベルも変えずに反射する。LDP の疑似回線は、出口 PE が"
              "targeted LDP のセッションで入口 PE に直接渡す。P は VRF も疑似回線も持たず、外側だけを見て転送する。ラベルの番号は"
              "決めた機器の中でだけ意味を持つ。"),
    "lfib": ("ラベルの表(LFIB)の Local の列は、この機器が決めて配った番号。先頭にこの番号が付いて届いたパケットは、その行の Outgoing の"
             "列のとおりに扱う: 番号= 付け替えて次の機器へ / Pop Label・Pop= 外して次の機器へ(PHP)/ No Label・Unlabelled= ラベルを"
             "外し IP パケット(フレーム)として出す / Aggregate= VRF の表で宛先を引き直す。[V] は VRF の経路、l2ckt と PW は"
             "疑似回線(出口の IF があれば AC へ直接、none ならブリッジ ドメインで MAC を引く)、evpn(mc:…) と evpn(uc:…) は"
             "EVPN のブリッジ ドメインの BUM とユニキャスト。"),
}

# ==========================================================================
# 図の出力(PoC の記録からの写し・行は記録のまま。selftest が照合する)
# ==========================================================================
EX = {'P1_LFIB': {'src': 'poc/xr/expSVC-lbl.log',
             'cmd': 'P1#show mpls forwarding-table',
             'lines': ['Local      Outgoing   Prefix           Bytes Label   Outgoing   Next Hop',
                       'Label      Label      or Tunnel Id     Switched      interface',
                       '16         No Label   10.255.0.52/32   18630         Et1/1      10.0.52.52',
                       '17         Pop Label  10.255.0.41/32   14277         Et0/0      10.0.41.41',
                       '18         Pop Label  10.255.0.42/32   7446          Et0/1      10.0.42.42',
                       '19         Pop Label  10.255.0.43/32   6858          Et0/2      10.0.43.43',
                       '20         Pop Label  10.255.0.1/32    5610          Et1/0      10.0.1.1']},
 'XE1_LFIB': {'src': 'poc/xr/expSVC-lbl.log',
              'cmd': 'XE1#show mpls forwarding-table',
              'lines': ['Local      Outgoing   Prefix           Bytes Label   Outgoing   Next Hop',
                        'Label      Label      or Tunnel Id     Switched      interface',
                        '16         Pop Label  10.255.0.51/32   0             Gi1        10.0.41.51',
                        '17         Pop Label  10.0.1.0/24      0             Gi1        10.0.41.51',
                        '18         Pop Label  10.0.42.0/24     0             Gi1        10.0.41.51',
                        '19         Pop Label  10.0.43.0/24     0             Gi1        10.0.41.51',
                        '20         Pop Label  10.0.52.0/24     0             Gi1        10.0.41.51',
                        '21         16         10.255.0.52/32   0             Gi1        10.0.41.51',
                        '22         18         10.255.0.42/32   0             Gi1        10.0.41.51',
                        '23         19         10.255.0.43/32   0             Gi1        10.0.41.51',
                        '24         20         10.255.0.1/32    0             Gi1        10.0.41.51',
                        '25         No Label   10.100.1.0/24[V] 2080          Gi2.100    172.16.1.1',
                        '26         No Label   l2ckt(1)         606           Gi2        point2point',
                        '27         No Label   l2ckt(2)         626           none       point2point',
                        '28         No Label   l2ckt(3)         626           none       point2point',
                        '29         No Label   evpn(mc:bd 200)  60            none       point2point',
                        '30         No Label   evpn(uc:bd 200)  972           none       point2point']},
 'XE2_LFIB': {'src': 'poc/xr/expSVC-lbl.log',
              'cmd': 'XE2#show mpls forwarding-table',
              'lines': ['Local      Outgoing   Prefix           Bytes Label   Outgoing   Next Hop',
                        'Label      Label      or Tunnel Id     Switched      interface',
                        '16         Pop Label  10.255.0.51/32   0             Gi1        10.0.42.51',
                        '17         Pop Label  10.0.1.0/24      0             Gi1        10.0.42.51',
                        '18         Pop Label  10.0.41.0/24     0             Gi1        10.0.42.51',
                        '19         Pop Label  10.0.43.0/24     0             Gi1        10.0.42.51',
                        '20         Pop Label  10.0.52.0/24     0             Gi1        10.0.42.51',
                        '21         16         10.255.0.52/32   0             Gi1        10.0.42.51',
                        '22         17         10.255.0.41/32   0             Gi1        10.0.42.51',
                        '23         19         10.255.0.43/32   0             Gi1        10.0.42.51',
                        '24         20         10.255.0.1/32    0             Gi1        10.0.42.51',
                        '25         No Label   10.100.2.0/24[V] 826           Gi2.100    172.16.2.1',
                        '26         No Label   l2ckt(1)         646           Gi2        point2point',
                        '27         No Label   l2ckt(2)         708           none       point2point',
                        '28         No Label   l2ckt(3)         0             none       point2point',
                        '29         No Label   evpn(mc:bd 200)  120           none       point2point',
                        '30         No Label   evpn(uc:bd 200)  456           none       point2point']},
 'XE3_LFIB': {'src': 'poc/xr/expSVC-lbl.log',
              'cmd': 'XE3#show mpls forwarding-table',
              'lines': ['Local      Outgoing   Prefix           Bytes Label   Outgoing   Next Hop',
                        'Label      Label      or Tunnel Id     Switched      interface',
                        '16         Pop Label  10.255.0.51/32   0             Gi1        10.0.43.51',
                        '17         Pop Label  10.0.1.0/24      0             Gi1        10.0.43.51',
                        '18         Pop Label  10.0.41.0/24     0             Gi1        10.0.43.51',
                        '19         Pop Label  10.0.42.0/24     0             Gi1        10.0.43.51',
                        '20         Pop Label  10.0.52.0/24     0             Gi1        10.0.43.51',
                        '21         16         10.255.0.52/32   0             Gi1        10.0.43.51',
                        '22         18         10.255.0.42/32   0             Gi1        10.0.43.51',
                        '23         17         10.255.0.41/32   0             Gi1        10.0.43.51',
                        '24         20         10.255.0.1/32    0             Gi1        10.0.43.51',
                        '25         No Label   l2ckt(1)         646           Gi2        point2point',
                        '26         No Label   l2ckt(2)         708           none       point2point',
                        '27         No Label   l2ckt(3)         0             none       point2point',
                        '28         No Label   evpn(mc:bd 200)  180           none       point2point',
                        '29         No Label   evpn(uc:bd 200)  456           none       point2point']},
 'XR01_LFIB_S': {'src': 'poc/xr/expSVC-lbl.log',
                 'cmd': 'RP/0/RP0/CPU0:XR01#show mpls forwarding',
                 'lines': ['Local  Outgoing    Prefix             Outgoing     Next Hop        Bytes',
                           'Label  Label       or ID              Interface                    Switched',
                           '------ ----------- ------------------ ------------ --------------- ------------',
                           '24000  16          10.255.0.52/32     Gi0/0/0/0    10.0.1.51       1584',
                           '24001  Pop         10.255.0.51/32     Gi0/0/0/0    10.0.1.51       980',
                           '24002  19          10.255.0.43/32     Gi0/0/0/0    10.0.1.51       0',
                           '24003  18          10.255.0.42/32     Gi0/0/0/0    10.0.1.51       0',
                           '24004  17          10.255.0.41/32     Gi0/0/0/0    10.0.1.51       5163',
                           '24005  Pop         10.0.52.0/24       Gi0/0/0/0    10.0.1.51       0',
                           '24006  Pop         10.0.43.0/24       Gi0/0/0/0    10.0.1.51       0',
                           '24007  Pop         10.0.42.0/24       Gi0/0/0/0    10.0.1.51       0',
                           '24008  Pop         10.0.41.0/24       Gi0/0/0/0    10.0.1.51       0',
                           '24009  Unlabelled  10.100.4.0/24[V]   Gi0/0/0/1.100 172.16.4.1      0',
                           '24010  Pop         PW(10.255.0.41:130)   \\',
                           '                                      Gi0/0/0/1.130 point2point     516']},
 'XE1_VPNV4': {'src': 'poc/xr/expSVC-l3.log',
               'cmd': 'XE1#show bgp vpnv4 unicast all labels',
               'lines': ['   Network          Next Hop      In label/Out label',
                         'Route Distinguisher: 10.255.0.1:100',
                         '   10.100.4.0/24    10.255.0.1      nolabel/24009',
                         'Route Distinguisher: 10.255.0.41:100 (A)',
                         '   10.100.1.0/24    172.16.1.1      25/nolabel',
                         '   10.100.2.0/24    10.255.0.42     nolabel/25',
                         '   10.100.4.0/24    10.255.0.1      nolabel/24009',
                         'Route Distinguisher: 10.255.0.42:100',
                         '   10.100.2.0/24    10.255.0.42     nolabel/25']},
 'XE1_PW130': {'src': 'poc/xr/expSVC-pw.log',
               'cmd': 'XE1#show l2vpn atom vc vcid 130 detail',
               'lines': ['pseudowire100001 is up, VC status is up PW type: Ethernet',
                         '  Destination address: 10.255.0.1 VC ID: 130',
                         '    Next hop: 10.0.41.51',
                         '  Member of xconnect service CE1-CE4',
                         '    Associated member Gi2 is up, status is up',
                         '  Signaling protocol: LDP, peer 10.255.0.1:0 up',
                         '    Targeted Hello: 10.255.0.41(LDP Id) -> 10.255.0.1, LDP is UP',
                         '  Bindings',
                         '    Parameter    Local                          Remote',
                         '    ------------ ------------------------------ ------------------------------',
                         '    Label        26                             24010',
                         '    Control word off (configured: autosense)    off']},
 'XR01_XC130': {'src': 'poc/xr/expSVC-pw.log',
                'cmd': 'RP/0/RP0/CPU0:XR01#show l2vpn xconnect detail',
                'lines': ['Group SVC, XC CE4-CE1, state is up; Interworking none',
                          '  AC: GigabitEthernet0/0/0/1.130, state is up',
                          '  PW: neighbor 10.255.0.41, PW ID 130, state is up ( established )',
                          '    Encapsulation MPLS, protocol LDP',
                          '      MPLS         Local                          Remote',
                          '      ------------ ------------------------------ -----------------------------',
                          '      Label        24010                          26',
                          '      Control word disabled                       disabled']},
 'XE1_ATOMVC': {'src': 'poc/xr/expSVC-vp.log',
                'cmd': 'XE1#show l2vpn atom vc',
                'lines': ['                                       Service',
                          'Interface Peer ID         VC ID      Type   Name                     Status',
                          '--------- --------------- ---------- ------ ------------------------ ----------',
                          'pw100001  10.255.0.1      130        p2p    CE1-CE4                  UP',
                          'pw100003  10.255.0.42     210        vfi    VPLS210                  UP',
                          'pw100004  10.255.0.43     210        vfi    VPLS210                  UP']},
 'XE1_BD210': {'src': 'poc/xr/expSVC-vp.log',
               'cmd': 'XE1#show bridge-domain 210',
               'lines': ['Bridge-domain 210 (3 ports in all)',
                         'State: UP                    Mac learning: Enabled',
                         'Aging-Timer: 300 second(s)',
                         'Unknown Unicast Flooding Suppression: Disabled',
                         'Maximum address limit: 65536',
                         '    GigabitEthernet2 service instance 210',
                         '    vfi VPLS210 neighbor 10.255.0.42 210',
                         '    vfi VPLS210 neighbor 10.255.0.43 210',
                         '   AED MAC address    Policy  Tag       Age  Pseudoport',
                         '   -----------------------------------------------------------------------------',
                         '   0   AABB.CC00.8C00 forward dynamic   295  VPLS210.404012, VPLS',
                         '                                             VC_LABEL: 27, Intf: GigabitEthernet1',
                         '   0   AABB.CC00.8D00 forward dynamic   297  VPLS210.404013, VPLS',
                         '                                             VC_LABEL: 26, Intf: GigabitEthernet1',
                         '   0   AABB.CC00.8B00 forward dynamic   298  GigabitEthernet2.EFP210']},
 'XE1_EVI200': {'src': 'poc/xr/expSVC-el.log',
                'cmd': 'XE1#show l2vpn evpn evi 200 detail',
                'lines': ['EVPN instance:       200 (VLAN Based)',
                          '  RD:                10.255.0.41:200 (auto)',
                          '  Import-RTs:        65000:200',
                          '  Export-RTs:        65000:200',
                          '  Per-EVI Label:     none',
                          '  Bridge Domain:     200',
                          '    Ethernet-Tag:    0',
                          '    BUM Label:       29',
                          '    Per-BD Label:    30']},
 'XE1_EVPNMAC': {'src': 'poc/xr/expSVC-el.log',
                 'cmd': 'XE1#show l2vpn evpn mac',
                 'lines': ['MAC Address    EVI   BD    ESI                      Ether Tag  Next Hop(s)',
                           '-------------- ----- ----- ------------------------ ---------- ---------------',
                           'aabb.cc00.8b00 200   200   0000.0000.0000.0000.0000 0          Gi2:200',
                           'aabb.cc00.8c00 200   200   0000.0000.0000.0000.0000 0          10.255.0.42',
                           'aabb.cc00.8d00 200   200   0000.0000.0000.0000.0000 0          10.255.0.43']},
 'XE1_RT2_CE2': {'src': 'poc/xr/expSVC-el.log',
                 'cmd': 'XE1#show bgp l2vpn evpn route-type 2',
                 'lines': ['BGP routing table entry for [2][10.255.0.41:200][0][48][AABBCC008C00][0][*]/20, version 11',
                           'Paths: (1 available, best #1, table evi_200)',
                           '  Not advertised to any peer',
                           '  Refresh Epoch 2',
                           '  Local, imported path from [2][10.255.0.42:200][0][48][AABBCC008C00][0][*]/20 (global)',
                           '    10.255.0.42 (metric 30) (via default) from 10.255.0.52 (10.255.0.52)',
                           '      Origin incomplete, metric 0, localpref 100, valid, internal, best',
                           '      EVPN ESI: 00000000000000000000, Label1 30',
                           '      Extended Community: RT:65000:200',
                           '      Originator: 10.255.0.42, Cluster list: 10.255.0.52']},
 'XE1_RT3_XE2': {'src': 'poc/xr/expSVC-el.log',
                 'cmd': 'XE1#show bgp l2vpn evpn route-type 3',
                 'lines': ['BGP routing table entry for [3][10.255.0.41:200][0][32][10.255.0.42]/17, version 4',
                           'Paths: (1 available, best #1, table evi_200)',
                           '  Flag: 0x100',
                           '  Not advertised to any peer',
                           '  Refresh Epoch 2',
                           '  Local, imported path from [3][10.255.0.42:200][0][32][10.255.0.42]/17 (global)',
                           '    10.255.0.42 (metric 30) (via default) from 10.255.0.52 (10.255.0.52)',
                           '      Origin incomplete, metric 0, localpref 100, valid, internal, best',
                           '      Extended Community: RT:65000:200',
                           '      Originator: 10.255.0.42, Cluster list: 10.255.0.52',
                           '      PMSI Attribute: Flags:0x0, Tunnel type:IR, length 4, label:29, tunnel identifier: < Tunnel Endpoint: '
                           '10.255.0.42 >']},
 'XE2_EVPWS': {'src': 'poc/xr/expSVC-ev.log',
               'cmd': 'XE2#show l2vpn evpn vpws vc id 140 detail',
               'lines': ['EVPN name: CE2-CE3, state: up, type: point-to-point',
                         '  EVPN ID: 140',
                         '  VPWS Service Instance ID: Source 2, Target 3',
                         '  Labels: Local 26, Remote 25',
                         '  Next Hop Address: 10.255.0.43',
                         '  Associated member interface Gi2 up, Gi2:140 status is up']},
 'XR01_CUSTA_LBL': {'src': 'poc/xr/expM9R-out1.log',
                    'cmd': 'RP/0/RP0/CPU0:XR01#show bgp vrf CUST-A labels',
                    'lines': ['   Network            Next Hop        Rcvd Label      Local Label',
                              'Route Distinguisher: 10.255.0.1:101 (default for vrf CUST-A)',
                              'Route Distinguisher Version: 42',
                              '*> 0.0.0.0/0          192.0.2.2       nolabel         24009',
                              '*> 10.101.1.0/24      172.16.11.2     nolabel         24004',
                              '*>i10.101.2.0/24      10.255.0.12     22              nolabel',
                              '*> 198.51.100.0/25    172.16.11.2     nolabel         24005',
                              '*>i198.51.100.128/25  10.255.0.12     23              nolabel']},
 'XR01_LFIB_M9': {'src': 'poc/xr/expM9R-out1.log',
                  'cmd': 'RP/0/RP0/CPU0:XR01#show mpls forwarding',
                  'lines': ['Local  Outgoing    Prefix             Outgoing     Next Hop        Bytes',
                            'Label  Label       or ID              Interface                    Switched',
                            '------ ----------- ------------------ ------------ --------------- ------------',
                            '24000  20          10.255.0.21/32     Gi0/0/0/1    10.0.3.13       1854',
                            '24001  Pop         10.255.0.13/32     Gi0/0/0/1    10.0.3.13       580',
                            '24002  16          10.255.0.12/32     Gi0/0/0/0    10.0.1.11       10528',
                            '24003  Pop         10.255.0.11/32     Gi0/0/0/0    10.0.1.11       402',
                            '24004  Unlabelled  10.101.1.0/24[V]   Gi0/0/0/2    172.16.11.2     0',
                            '24005  Unlabelled  198.51.100.0/25[V] Gi0/0/0/2    172.16.11.2     0',
                            '24006  Unlabelled  10.102.1.0/24[V]   Gi0/0/0/3    172.16.21.2     0',
                            '24007  Unlabelled  10.99.1.0/24[V]    Gi0/0/0/4    172.16.91.2     500',
                            '24008  Unlabelled  10.99.2.0/24[V]    Gi0/0/0/4    172.16.91.2     0',
                            '24009  Aggregate   CUST-A: Per-VRF Aggr[V]   \\',
                            '                                      CUST-A                       2000']},
 'RT01_LFIB': {'src': 'poc/xr/expM9R-out1.log',
               'cmd': 'RT01#show mpls forwarding-table',
               'lines': ['Local      Outgoing   Prefix           Bytes Label   Outgoing   Next Hop',
                         'Label      Label      or Tunnel Id     Switched      interface',
                         '16         Pop Label  10.255.0.12/32   12438         Et0/1      10.0.12.12',
                         '17         Pop Label  10.0.23.0/24     0             Et0/1      10.0.12.12',
                         '18         24001      10.255.0.13/32   0             Et0/0      10.0.1.1',
                         '           16         10.255.0.13/32   0             Et0/1      10.0.12.12',
                         '19         No Label   10.0.3.0/24      0             Et0/0      10.0.1.1',
                         '20         18         10.0.33.0/24     0             Et0/1      10.0.12.12',
                         '           No Label   10.0.33.0/24     0             Et0/0      10.0.1.1',
                         '21         24000      10.255.0.21/32   0             Et0/0      10.0.1.1',
                         '           21         10.255.0.21/32   0             Et0/1      10.0.12.12',
                         '22         explicit-n 10.255.0.1/32    13260         Et0/0      10.0.1.1']},
 'RT02_LFIB': {'src': 'poc/xr/expM9R-out1.log',
               'cmd': 'RT02#show mpls forwarding-table',
               'lines': ['Local      Outgoing   Prefix           Bytes Label   Outgoing   Next Hop',
                         'Label      Label      or Tunnel Id     Switched      interface',
                         '16         Pop Label  10.255.0.13/32   0             Et0/1      10.0.23.13',
                         '17         19         10.0.3.0/24      0             Et0/0      10.0.12.11',
                         '18         Pop Label  10.0.33.0/24     0             Et0/1      10.0.23.13',
                         '19         Pop Label  10.255.0.11/32   0             Et0/0      10.0.12.11',
                         '20         Pop Label  10.0.1.0/24      0             Et0/0      10.0.12.11',
                         '21         20         10.255.0.21/32   0             Et0/1      10.0.23.13',
                         '22         No Label   10.101.2.0/24[V] 5230          Et0/2      172.16.12.2',
                         '23         No Label   198.51.100.128/25[V]   \\',
                         '                                       2280          Et0/2      172.16.12.2',
                         '24         No Label   10.102.2.0/24[V] 4788          Et1/0      172.16.22.2',
                         '25         22         10.255.0.1/32    0             Et0/0      10.0.12.11']},
 'RT02_VPNV4': {'src': 'poc/xr/expM9R-out1.log',
                'cmd': 'RT02#show ip bgp vpnv4 all labels',
                'lines': ['   Network          Next Hop      In label/Out label',
                          'Route Distinguisher: 10.255.0.1:101',
                          '   0.0.0.0          10.255.0.1      nolabel/24009',
                          '   10.101.1.0/24    10.255.0.1      nolabel/24004',
                          '   198.51.100.0/25  10.255.0.1      nolabel/24005',
                          'Route Distinguisher: 10.255.0.1:102',
                          '   10.102.1.0/24    10.255.0.1      nolabel/24006',
                          'Route Distinguisher: 10.255.0.1:900',
                          '   10.99.1.0/24     10.255.0.1      nolabel/24007',
                          'Route Distinguisher: 10.255.0.12:101 (CUST-A)',
                          '   0.0.0.0          10.255.0.1      nolabel/24009',
                          '   10.99.1.0/24     10.255.0.1      nolabel/24007',
                          '   10.101.1.0/24    10.255.0.1      nolabel/24004',
                          '   10.101.2.0/24    172.16.12.2     22/nolabel',
                          '   198.51.100.0/25  10.255.0.1      nolabel/24005',
                          '   198.51.100.128/25',
                          '                   172.16.12.2     23/nolabel',
                          'Route Distinguisher: 10.255.0.12:102 (CUST-B)',
                          '   10.99.1.0/24     10.255.0.1      nolabel/24007',
                          '   10.102.1.0/24    10.255.0.1      nolabel/24006',
                          '   10.102.2.0/24    172.16.22.2     24/nolabel']}}

# ==========================================================================
# 盤面
# ==========================================================================
BOARDS = {
    "svc": {
        "lo": {"XE1": "10.255.0.41", "XE2": "10.255.0.42", "XE3": "10.255.0.43", "XR01": "10.255.0.1",
               "P1": "10.255.0.51", "RR1": "10.255.0.52"},
        "rr": "RR1",
        "mermaid": "\n".join([
            "```mermaid", "graph LR",
            '  CE1["CE1(拠点 1)"] --- XE1["XE1(PE・Catalyst 8000V)<br/>Lo0 10.255.0.41"]',
            '  CE2["CE2(拠点 2)"] --- XE2["XE2(PE・Catalyst 8000V)<br/>Lo0 10.255.0.42"]',
            '  XE1 ---|"Gi1 / Et0/0<br/>10.0.41.0/24"| P1["P1(P)<br/>Lo0 10.255.0.51"]',
            '  XE2 ---|"Gi1 / Et0/1<br/>10.0.42.0/24"| P1',
            '  P1 ---|"Et0/2 / Gi1<br/>10.0.43.0/24"| XE3["XE3(PE・Catalyst 8000V)<br/>Lo0 10.255.0.43"]',
            '  P1 ---|"Et1/0 / Gi0/0/0/0<br/>10.0.1.0/24"| XR01["XR01(PE・IOS XR)<br/>Lo0 10.255.0.1"]',
            '  P1 ---|"Et1/1<br/>10.0.52.0/24"| RR1["RR1(ルート リフレクタ)<br/>Lo0 10.255.0.52"]',
            '  XE3 --- CE3["CE3(拠点 3)"]',
            '  XR01 --- CE4["CE4(拠点 4)"]',
            "```"]),
        "text": ("コア(PE 4 台・P1・RR1)は AS 65000 で、IS-IS と LDP が動いています。RR1 は VPNv4 と L2VPN EVPN の BGP の"
                 "ルート リフレクタで、各 PE は RR1 とだけ iBGP を張ります。P1 は BGP を持ちません。CE は PE との 1 本のリンクの上に、"
                 "VLAN でサービスを分けて載せています(PE の CE 側は XE が Gi2、XR01 が Gi0/0/0/1)。\n\n"
                 "| VLAN | サービス | つなぐ拠点 |\n|---|---|---|\n"
                 "| 100 | L3VPN(VRF A・拠点の LAN は 10.100.<拠点>.0/24) | 1、2、4 |\n"
                 "| 130 | VPWS(LDP の疑似回線・pw-id 130) | 1 ⇔ 4 |\n"
                 "| 140 | VPWS(EVPN-VPWS・EVI 140) | 2 ⇔ 3 |\n"
                 "| 200 | EVPN の E-LAN(EVI 200・ブリッジ ドメイン 200) | 1、2、3 |\n"
                 "| 210 | VPLS(VFI VPLS210・ブリッジ ドメイン 210) | 1、2、3 |\n\n"
                 "CE の MAC アドレスは、CE1 が aabb.cc00.8b00、CE2 が aabb.cc00.8c00、CE3 が aabb.cc00.8d00 です。"),
    },
    "m9": {
        "lo": {"XR01": "10.255.0.1", "RT01": "10.255.0.11", "RT02": "10.255.0.12", "RT03": "10.255.0.13",
               "XR02": "10.255.0.21"},
        "rr": "XR02",
        "mermaid": "\n".join([
            "```mermaid", "graph LR",
            '  CEA1["CEA1(顧客 A 拠点 1)"] ---|"Gi0/0/0/2"| XR01["XR01(PE・IOS XR)<br/>Lo0 10.255.0.1"]',
            '  CEB1["CEB1(顧客 B 拠点 1)"] ---|"Gi0/0/0/3"| XR01',
            '  XR01 ---|"Gi0/0/0/0 / Et0/0<br/>10.0.1.0/24・metric 10"| RT01["RT01(P)<br/>Lo0 10.255.0.11"]',
            '  RT01 ---|"Et0/1 / Et0/0<br/>10.0.12.0/24・metric 10"| RT02["RT02(PE・IOS XE)<br/>Lo0 10.255.0.12"]',
            '  XR01 ---|"Gi0/0/0/1 / Et0/0<br/>10.0.3.0/24・metric 100"| RT03["RT03(P)<br/>Lo0 10.255.0.13"]',
            '  RT03 ---|"Et0/1 / Et0/1<br/>10.0.23.0/24・metric 100"| RT02',
            '  RT03 ---|"Et0/2<br/>10.0.33.0/24"| XR02["XR02(ルート リフレクタ)<br/>Lo0 10.255.0.21"]',
            '  RT02 ---|"Et0/2"| CEA2["CEA2(顧客 A 拠点 2)"]',
            '  RT02 ---|"Et1/0"| CEB2["CEB2(顧客 B 拠点 2)"]',
            "```"]),
        "text": ("コアは AS 65000 で、IS-IS(メトリックは図のとおり)と LDP が動いています。XR02 は VPNv4 のルート リフレクタで、"
                 "XR01 と RT02 は XR02 とだけ VPNv4 のセッションを張ります。RT01 と RT03 は BGP を持ちません。\n\n"
                 "| 拠点 | つながる PE | VRF | LAN |\n|---|---|---|---|\n"
                 "| 顧客 A 拠点 1(CEA1) | XR01 Gi0/0/0/2 | CUST-A | 10.101.1.0/24(公開セグメント 198.51.100.0/25) |\n"
                 "| 顧客 A 拠点 2(CEA2) | RT02 Et0/2 | CUST-A | 10.101.2.0/24(公開セグメント 198.51.100.128/25) |\n"
                 "| 顧客 B 拠点 1(CEB1) | XR01 Gi0/0/0/3 | CUST-B | 10.102.1.0/24 |\n"
                 "| 顧客 B 拠点 2(CEB2) | RT02 Et1/0 | CUST-B | 10.102.2.0/24 |\n\n"
                 "XR01 には、共有サービスのサーバ(VRF SVC・Gi0/0/0/4)とインターネット(グローバル テーブル)もつながっています。"),
    },
}

# ==========================================================================
# 場面(線の上の実測)。h1= 入口 PE → P の区間、h2= P → 出口 PE の区間(左が外側)。
#   ing_local= 入口 PE の表で出口 PE のループバックの行の Local / p_rev= P が入口 PE のループバックに付けた番号(逆向きの外側)
#   self_inner= 入口 PE 自身が同じサービスで決めた番号 / alt_inner= 図に見える別の番号と、その意味
# ==========================================================================
SCEN = [
    dict(id="s_l3_12", kind="l3_stack", board="svc", svc="l3vpn", sig="bgp", ping=("CE1", "CE2", "10.100.2.1"), msg="エコー要求",
         path=("XE1", "P1", "XE2"), h1=[18, 25], h2=[25], ex=["XE1_VPNV4", "XE1_LFIB", "P1_LFIB"],
         ing_local=22, p_rev=17, self_inner=25,
         alt_inner=[(24009, "XR01 が拠点 4 の LAN(10.100.4.0/24)に決めた番号")],
         alt_outer=[(20, "P1 が XR01 のループバックに付けた番号")],
         inner_src="XE1 の `show bgp vpnv4 unicast all labels` で 10.100.2.0/24 の Out label 25(XE2 が決めて BGP で広告し、RR1 が反射した番号)",
         egr_use="VRF A の 10.100.2.0/24 の行(Gi2.100 から CE2 へ)", pcap="l3-xe1p1.pcap・l3-p1xe2.pcap"),
    dict(id="s_l3_21", kind="l3_stack", board="svc", svc="l3vpn", sig="bgp", ping=("CE1", "CE2", "10.100.2.1"), msg="エコー応答",
         path=("XE2", "P1", "XE1"), h1=[17, 25], h2=[25], ex=["XE1_VPNV4", "XE2_LFIB", "P1_LFIB"],
         ing_local=22, p_rev=18, self_inner=25,
         alt_inner=[(24009, "XR01 が拠点 4 の LAN(10.100.4.0/24)に決めた番号")],
         alt_outer=[(20, "P1 が XR01 のループバックに付けた番号")],
         inner_src="XE1 の `show bgp vpnv4 unicast all labels` で 10.100.1.0/24 の In label 25(XE1 が自分の拠点の LAN に決めた番号。XE2 は BGP でこれを受け取っている)",
         egr_use="VRF A の 10.100.1.0/24 の行(Gi2.100 から CE1 へ)", pcap="l3-p1xe2.pcap・l3-xe1p1.pcap"),
    dict(id="s_l3_14", kind="l3_stack", board="svc", svc="l3vpn", sig="bgp", ping=("CE1", "CE4", "10.100.4.1"), msg="エコー要求",
         path=("XE1", "P1", "XR01"), h1=[20, 24009], h2=[24009], ex=["XE1_VPNV4", "XE1_LFIB", "P1_LFIB"],
         ing_local=24, p_rev=17, self_inner=25,
         alt_inner=[],
         alt_outer=[(18, "P1 が XE2 のループバックに付けた番号")],
         inner_src="XE1 の `show bgp vpnv4 unicast all labels` で 10.100.4.0/24 の Out label 24009(XR01 が決めて BGP で広告し、RR1 が反射した番号)",
         egr_use="VRF A の 10.100.4.0/24 の行(Gi0/0/0/1.100 から CE4 へ)",
         pcap="XE1 の CEF(`label 20-(local:24)` と `label 24009`)・P1→XR01 の PHP は vpws-p1xr01.pcap"),
    dict(id="s_pw_14", kind="l2_stack", board="svc", svc="vpws", sig="ldp", ping=("CE1", "CE4", "192.168.130.4"), msg="エコー要求",
         path=("XE1", "P1", "XR01"), h1=[20, 24010], h2=[24010], ex=["XE1_PW130", "XE1_LFIB", "P1_LFIB"],
         ing_local=24, p_rev=17, self_inner=26,
         alt_inner=[], alt_outer=[(18, "P1 が XE2 のループバックに付けた番号")],
         inner_src="XE1 の疑似回線の Bindings で Remote の Label 24010(XR01 が決めて targeted LDP で XE1 に渡した番号)",
         egr_use="疑似回線 PW(10.255.0.41:130) の行(Gi0/0/0/1.130 から CE4 へ)", pcap="vpws-xe1p1.pcap・vpws-p1xr01.pcap"),
    dict(id="s_pw_41", kind="l2_stack", board="svc", svc="vpws", sig="ldp", ping=("CE1", "CE4", "192.168.130.4"), msg="エコー応答",
         path=("XR01", "P1", "XE1"), h1=[17, 26], h2=[26], ex=["XR01_XC130", "XR01_LFIB_S", "P1_LFIB"],
         ing_local=24004, p_rev=20, self_inner=24010,
         alt_inner=[], alt_outer=[(18, "P1 が XE2 のループバックに付けた番号")],
         inner_src="XR01 の `show l2vpn xconnect detail` で Remote の Label 26(XE1 が決めて targeted LDP で XR01 に渡した番号)",
         egr_use="l2ckt(1) の行(Gi2 から CE1 へ)", pcap="vpws-p1xr01.pcap・vpws-xe1p1.pcap"),
    dict(id="s_vpls_12", kind="l2_stack", board="svc", svc="vpls", sig="ldp", ping=("CE1", "CE2", "192.168.210.2"), msg="エコー要求",
         path=("XE1", "P1", "XE2"), h1=[18, 27], h2=[27], ex=["XE1_BD210", "XE1_LFIB", "P1_LFIB"],
         ing_local=22, p_rev=17, self_inner=27,
         alt_inner=[(26, "CE3(AABB.CC00.8D00)宛て= XE3 への疑似回線の VC_LABEL")],
         alt_outer=[(19, "P1 が XE3 のループバックに付けた番号")],
         inner_src="XE1 の `show bridge-domain 210` で CE2 の MAC(AABB.CC00.8C00)の行の VC_LABEL 27(XE2 への疑似回線で、XE2 が決めて targeted LDP で渡した番号)",
         egr_use="VPLS の疑似回線の行(ブリッジ ドメイン 210 で宛先 MAC を引いて CE2 へ)", pcap="vpls-xe1p1.pcap・vpls-p1xe2.pcap"),
    dict(id="s_elan_12", kind="l2_stack", board="svc", svc="elan", sig="bgp", ping=("CE1", "CE2", "192.168.200.2"), msg="エコー要求",
         path=("XE1", "P1", "XE2"), h1=[18, 30], h2=[30], ex=["XE1_EVPNMAC", "XE1_RT2_CE2", "XE1_RT3_XE2", "XE1_LFIB", "P1_LFIB"],
         ing_local=22, p_rev=17, self_inner=30,
         alt_inner=[(29, "XE2 が Inclusive Multicast(タイプ 3)のルートで広告した BUM 用の番号")],
         alt_outer=[(19, "P1 が XE3 のループバックに付けた番号")],
         inner_src="XE1 が CE2 の MAC(aabb.cc00.8c00)を XE2 のタイプ 2 のルートで学んでいる(Label1 30= XE2 が決めて BGP で広告し、RR1 が反射した番号)",
         egr_use="evpn(uc:bd 200) の行(ブリッジ ドメイン 200 で宛先 MAC を引いて CE2 へ)", pcap="elan-xe1p1.pcap・elan-p1xe2.pcap"),
    dict(id="s_evpws_23", kind="l2_stack", board="svc", svc="evpws", sig="bgp", ping=("CE2", "CE3", "192.168.140.3"), msg="エコー要求",
         path=("XE2", "P1", "XE3"), h1=[19, 25], h2=[25], ex=["XE2_EVPWS", "XE2_LFIB", "P1_LFIB"],
         ing_local=23, p_rev=18, self_inner=26,
         alt_inner=[], alt_outer=[(17, "P1 が XE1 のループバックに付けた番号")],
         inner_src="XE2 の `show l2vpn evpn vpws vc id 140 detail` で Labels の Remote 25(XE3 が決めてタイプ 1 のルートで広告し、RR1 が反射した番号)",
         egr_use="l2ckt(1) の行(Gi2 から CE3 へ)", pcap="evpws-xe2p1.pcap・evpws-p1xe3.pcap"),
    dict(id="s_evpws_32", kind="l2_stack", board="svc", svc="evpws", sig="bgp", ping=("CE2", "CE3", "192.168.140.3"), msg="エコー応答",
         path=("XE3", "P1", "XE2"), h1=[18, 26], h2=[26], ex=["XE2_EVPWS", "XE3_LFIB", "P1_LFIB"],
         ing_local=22, p_rev=19, self_inner=25,
         alt_inner=[], alt_outer=[(17, "P1 が XE1 のループバックに付けた番号")],
         inner_src="XE2 の `show l2vpn evpn vpws vc id 140 detail` で Labels の Local 26(XE2 が決めてタイプ 1 のルートで広告した番号。XE3 はこれを RR1 から受け取っている)",
         egr_use="l2ckt(1) の行(Gi2 から CE2 へ)", pcap="evpws-p1xe3.pcap・evpws-xe2p1.pcap"),
    dict(id="m_a_12", kind="l3_stack", board="m9", svc="l3vpn", sig="bgp", ping=("CEA1", "CEA2", "10.101.2.1"), msg="エコー要求",
         path=("XR01", "RT01", "RT02"), h1=[16, 22], h2=[22], ex=["XR01_CUSTA_LBL", "XR01_LFIB_M9", "RT01_LFIB"],
         ing_local=24002, p_rev=22, self_inner=24004,
         alt_inner=[(23, "RT02 が拠点 2 の公開セグメント(198.51.100.128/25)に決めた番号")],
         alt_outer=[(18, "RT01 が RT03 のループバックに付けた番号")],
         inner_src="XR01 の `show bgp vrf CUST-A labels` で 10.101.2.0/24 の Rcvd Label 22(RT02 が決めて BGP で広告し、XR02 が反射した番号)",
         egr_use="10.101.2.0/24[V] の行(Et0/2 から CEA2 へ)", pcap="m9-A-xr01rt01.pcap・m9-A-rt01rt02.pcap"),
    dict(id="m_a_21", kind="l3_stack", board="m9", svc="l3vpn", sig="bgp", ping=("CEA1", "CEA2", "10.101.2.1"), msg="エコー応答",
         path=("RT02", "RT01", "XR01"), h1=[22, 24004], h2=[0, 24004], enull=True, ex=["RT02_VPNV4", "RT02_LFIB", "RT01_LFIB"],
         ing_local=25, p_rev=16, self_inner=22,
         alt_inner=[(24005, "XR01 が拠点 1 の公開セグメント(198.51.100.0/25)に決めた番号")],
         alt_outer=[(19, "RT02 の表で RT01 のループバックの行(Local 19)")],
         inner_src="RT02 の `show ip bgp vpnv4 all labels` で 10.101.1.0/24 の Out label 24004(XR01 が決めて BGP で広告し、XR02 が反射した番号)",
         egr_use="10.101.1.0/24[V] の行(Gi0/0/0/2 から CEA1 へ)", pcap="m9-A-rt01rt02.pcap・m9-A-xr01rt01.pcap"),
    dict(id="m_b_12", kind="l3_stack", board="m9", svc="l3vpn", sig="bgp", ping=("CEB1", "CEB2", "10.102.2.1"), msg="エコー要求",
         path=("XR01", "RT01", "RT02"), h1=[16, 24], h2=[24], ex=["RT02_VPNV4", "XR01_LFIB_M9", "RT01_LFIB"],
         ing_local=24002, p_rev=22, self_inner=24006,
         alt_inner=[(22, "RT02 が顧客 A の拠点 2 の LAN(10.101.2.0/24)に決めた番号")],
         alt_outer=[(18, "RT01 が RT03 のループバックに付けた番号")],
         inner_src="RT02 の `show ip bgp vpnv4 all labels` で 10.102.2.0/24 の In label 24(RT02 が決めて BGP で広告した番号。XR01 は XR02 からこれを受け取っている)",
         egr_use="10.102.2.0/24[V] の行(Et1/0 から CEB2 へ)", pcap="m9-B-xr01rt01.pcap・m9-B-rt01rt02.pcap"),
    dict(id="m_b_21", kind="l3_stack", board="m9", svc="l3vpn", sig="bgp", ping=("CEB1", "CEB2", "10.102.2.1"), msg="エコー応答",
         path=("RT02", "RT01", "XR01"), h1=[22, 24006], h2=[0, 24006], enull=True, ex=["RT02_VPNV4", "RT02_LFIB", "RT01_LFIB"],
         ing_local=25, p_rev=16, self_inner=24,
         alt_inner=[(24004, "XR01 が顧客 A の拠点 1 の LAN(10.101.1.0/24)に決めた番号")],
         alt_outer=[(19, "RT02 の表で RT01 のループバックの行(Local 19)")],
         inner_src="RT02 の `show ip bgp vpnv4 all labels` で 10.102.1.0/24 の Out label 24006(XR01 が決めて BGP で広告し、XR02 が反射した番号)",
         egr_use="10.102.1.0/24[V] の行(Gi0/0/0/3 から CEB1 へ)", pcap="m9-B-rt01rt02.pcap・m9-B-xr01rt01.pcap"),
]
SCEN_BY_ID = {s["id"]: s for s in SCEN}
SVC_JA = {"l3vpn": "L3VPN", "vpws": "VPWS(LDP の疑似回線)", "vpls": "VPLS", "elan": "EVPN の E-LAN", "evpws": "EVPN-VPWS"}

# ==========================================================================
# ラベル表(lfib)。行= (Local, 図の出力でその行と分かる手がかり, 扱いの説明)。説明は 1 表の中で重複しない。
# ==========================================================================
LFIB_TABLES = {
    "XE1": dict(board="svc", pe="XE1", ex=["XE1_LFIB", "XE1_ATOMVC"], rows=[
        (16, "Pop Label 10.255.0.51/32", "P1 のループバック宛て。ラベルを外して P1 へ送る。"),
        (22, "18 10.255.0.42/32", "XE2 のループバック宛て。ラベルを 18 に付け替えて P1 へ送る。"),
        (25, "No Label 10.100.1.0/24[V]", "VRF A の拠点 1 の LAN 宛て。ラベルを外し、IP パケットとして Gi2.100 から CE1 へ送る。"),
        (26, "l2ckt(1) Gi2", "XR01 との VPWS の疑似回線で届いたフレーム。ラベルを外し、Gi2 から CE1 へそのまま送る。"),
        (27, "l2ckt(2) none", "VPLS の疑似回線で届いたフレーム。ブリッジ ドメイン 210 で宛先 MAC を引いて送る。"),
        (29, "evpn(mc:bd 200)", "EVPN(EVI 200)で届いたブロードキャストや宛先不明のフレーム。ブリッジ ドメイン 200 で CE1 側へ流す。"),
        (30, "evpn(uc:bd 200)", "EVPN(EVI 200)で届いたユニキャストのフレーム。ブリッジ ドメイン 200 で宛先 MAC を引いて送る。"),
    ]),
    "XR01m9": dict(board="m9", pe="XR01", ex=["XR01_LFIB_M9"], rows=[
        (24002, "16 10.255.0.12/32", "RT02 のループバック宛て。ラベルを 16 に付け替えて RT01 へ送る。"),
        (24003, "Pop 10.255.0.11/32", "RT01 のループバック宛て。ラベルを外して RT01 へ送る。"),
        (24004, "Unlabelled 10.101.1.0/24[V]", "顧客 A の拠点 1 の LAN 宛て。ラベルを外し、IP パケットとして CEA1 へ送る。"),
        (24005, "Unlabelled 198.51.100.0/25[V]", "顧客 A の拠点 1 の公開セグメント宛て。ラベルを外し、IP パケットとして CEA1 へ送る。"),
        (24006, "Unlabelled 10.102.1.0/24[V]", "顧客 B の拠点 1 の LAN 宛て。ラベルを外し、IP パケットとして CEB1 へ送る。"),
        (24007, "Unlabelled 10.99.1.0/24[V]", "共有サービスのサーバ(10.99.1.0/24)宛て。ラベルを外し、IP パケットとして SVC へ送る。"),
        (24009, "Aggregate CUST-A", "ラベルを外し、VRF CUST-A の表で宛先を引き直してから送る。"),
    ]),
    "RT02m9": dict(board="m9", pe="RT02", ex=["RT02_LFIB"], rows=[
        (16, "Pop Label 10.255.0.13/32", "RT03 のループバック宛て。ラベルを外して RT03 へ送る。"),
        (19, "Pop Label 10.255.0.11/32", "RT01 のループバック宛て。ラベルを外して RT01 へ送る。"),
        (22, "No Label 10.101.2.0/24[V]", "顧客 A の拠点 2 の LAN 宛て。ラベルを外し、IP パケットとして CEA2 へ送る。"),
        (23, "No Label 198.51.100.128/25[V]", "顧客 A の拠点 2 の公開セグメント宛て。ラベルを外し、IP パケットとして CEA2 へ送る。"),
        (24, "No Label 10.102.2.0/24[V]", "顧客 B の拠点 2 の LAN 宛て。ラベルを外し、IP パケットとして CEB2 へ送る。"),
        (25, "22 10.255.0.1/32", "XR01 のループバック宛て。ラベルを 22 に付け替えて RT01 へ送る。"),
    ]),
}

LET = "ABCDEFG"
CIRC = "①②③④"


def kind_forms(kind):
    return set(FORMS[kind])


def worlds_for(kind):
    return list(KIND_WORLDS[kind])


def fmt_stack(st, svc):
    if not st:
        return "ラベルなし(" + ("IP パケットのまま" if svc == "l3vpn" else "イーサネット フレームのまま") + ")"
    return "`" + " | ".join(str(x) for x in st) + "`"


def _ex_md(name):
    e = EX[name]
    lines = [ln for ln in e["lines"]]
    while lines and not lines[0].strip():
        lines.pop(0)
    return "```\n" + e["cmd"] + "\n" + "\n".join(lines) + "\n```"


def _exhibits(names):
    return "\n\n".join(_ex_md(n) for n in names)


# ==========================================================================
# draw
# ==========================================================================
RECENT_DAYS = 14
_SESSION = set()          # 同じ実行の中で既に引いた場面(パックは 1 回の実行で数問を作る)


def _key_of(d):
    """出した場面の印(answers/ の「- 仕込み:」の行に書く。解説ページでは gen_pack が消す)。"""
    if d["kind"] in ("l3_stack", "l2_stack"):
        return f"場面 `{d['scen']}`・区間 {d['hop']}"
    if d["kind"] == "owner":
        return f"持ち主 `{d['scen']}`"
    return f"表 `{d['table']}`"


def _recent_use():
    """answers/ の直近 RECENT_DAYS 日に出した場面の印 → 最後に出した問題 ID(YYYYMMDD-NNN)。"""
    import datetime
    import glob
    d0 = (datetime.date.today() - datetime.timedelta(days=RECENT_DAYS)).strftime("%Y%m%d")
    used = {}
    for path in glob.glob(os.path.join(REPO, "answers", "*.md")):
        base = os.path.basename(path)[:-3]
        if not base[:8].isdigit() or base[:8] < d0:
            continue
        try:
            txt = open(path, encoding="utf-8").read()
        except OSError:
            continue
        if "spvpn/" not in txt:
            continue
        for m in re.finditer(r"^- 仕込み: ((?:場面|持ち主|表) `[A-Za-z0-9_]+`(?:・区間 \d)?)", txt, re.M):
            used[m.group(1)] = max(used.get(m.group(1), ""), base)
    return used


def _pick_fresh(rnd, cands):
    """直近に出していない候補から選ぶ(全部出していれば、最後に出したのが古いものから)。"""
    used = _recent_use()
    for k in _SESSION:
        used[k] = "99999999-999"
    score = {i: used.get(_key_of(c), "") for i, c in enumerate(cands)}
    best = min(score.values())
    pick = cands[rnd.choice([i for i, v in score.items() if v == best])]
    _SESSION.add(_key_of(pick))
    return pick


def draw(rnd, kind, world=None, form=None):
    if kind not in KINDS:
        raise ValueError(f"unknown kind {kind}")
    if form is not None and form not in FORMS[kind]:
        raise ValueError(f"{kind} は form {form} を持たない")
    d = {"kind": kind, "world": "-", "form": form, "diff": DIFF[kind]}
    if kind in ("l3_stack", "l2_stack"):
        cands = [dict(d, scen=s["id"], hop=h) for s in SCEN if s["kind"] == kind for h in (1, 2)]
    elif kind == "owner":
        cands = [dict(d, scen=s["id"]) for s in SCEN]
    else:
        cands = [dict(d, table=t) for t in sorted(LFIB_TABLES)]
    return _pick_fresh(rnd, cands)


# ==========================================================================
# l3_stack / l2_stack(read)
# ==========================================================================
def _stack_pool(sc, hop):
    """(並び, 理由)の候補。正解と同じ並びは呼び出し側で捨てる。
    ★先頭の 1 つは必ず肢に入れる(その区間で一番効く取り違え: 1 区間目= Local の列・2 区間目= PHP/explicit null)。"""
    ing, p, egr = sc["path"]
    T, V = sc["h1"]
    lo = BOARDS[sc["board"]]["lo"][egr]
    ilo = BOARDS[sc["board"]]["lo"][ing]
    enull = sc.get("enull", False)
    P = []
    if hop == 1:
        P.append(([sc["ing_local"], V], f"{sc['ing_local']} は {ing} の表で {lo} の行の Local の列= {ing} 自身が決めて隣に配った番号。"
                                        f"{ing} が付けるのは次の {p} が決めた番号で、同じ行の Outgoing の列の {T}。"))
        P.append(([V, T], f"外側と内側が逆。先頭(外側)は運ぶ層のラベル {T}({p} が {egr} のループバック {lo} に付けた番号)で、"
                          f"サービスのラベル {V} はその下に入る。"))
        P.append(([sc["p_rev"], V], f"{sc['p_rev']} は {p} が {ing} のループバック {ilo} に付けた番号で、逆向き({egr} から {ing})の外側。"))
        P.append(([V], f"{ing} から {p} の区間ではまだ外側が残る。外側を外す(または 0 に付け替える)のは出口の 1 つ手前の {p} で、"
                       f"{p} から {egr} の区間の話。"))
        P.append(([T], f"内側のラベルが無いと、{egr} は届いたパケットをどのサービスのものとして扱えばよいか決められない。"
                       f"{ing} は外側の {T} の下に、{egr} が決めた {V} を積む。"))
        if sc.get("self_inner") is not None:
            P.append(([T, sc["self_inner"]], f"{sc['self_inner']} は {ing} 自身がこのサービスの自分の側に決めた番号(相手から {ing} に向かう"
                                             f"パケットに付く)。内側には出口の {egr} が決めた番号を積む。"))
        for a, why in sc.get("alt_inner", []):
            P.append(([T, a], f"{a} は {why}で、このパケットの宛先とは別のもの。"))
        for a, why in sc.get("alt_outer", []):
            P.append(([a, V], f"{a} は {why}。このパケットの出口は {egr} なので、{lo} 宛ての番号を使う。"))
    else:
        if enull:
            P.append(([V], f"{p} の表で {lo} の行の Outgoing は explicit-n。{egr} が explicit null を広告しているので、{p} は外側を"
                           f"外さずラベル 0 に付け替える。外側が消えるのは Pop Label の場合。"))
            P.append(([T, V], f"{T} は {p} 自身が {lo} に決めて配った番号(Local の列)。{p} はこれを Outgoing の列のとおりに付け替える"
                              f"(ここでは explicit-n= 0)。"))
            P.append(([V, 0], f"0 は外側(先頭)に入る。サービスのラベル {V} はその下のまま。"))
            for a, why in sc.get("alt_inner", []):
                P.append(([0, a], f"{a} は {why}で、このパケットとは別のもの。{p} は内側を書き換えない。"))
        else:
            P.append(([T, V], f"{p} の表で {lo} の行の Outgoing は Pop Label(Pop)。出口の 1 つ手前の {p} は外側を外して渡すので"
                              f"(PHP)、この区間には内側の {V} だけが残る。"))
            P.append(([0, V], f"ラベル 0(explicit null)が付くのは、{egr} が explicit null を広告した場合。{p} の表で {lo} の行は"
                              f" Pop Label なので外側そのものが外れる。"))
            for a, why in sc.get("alt_inner", []):
                P.append(([a], f"{a} は {why}で、このパケットとは別のもの。{p} は内側を書き換えない。"))
            if sc.get("self_inner") is not None:
                P.append(([sc["self_inner"]], f"{sc['self_inner']} は入口の {ing} が自分の側に決めた番号。内側は {ing} が積んだ {V} のまま"
                                              f"届く({p} は内側を見ない)。"))
        P.append(([], f"{p} が外すのは外側だけで、内側の {V} は {egr} が見るまで残る。{egr} は {V} で行き先を決める。"))
    return P


def _correct_stack(sc, hop):
    return list(sc["h1"] if hop == 1 else sc["h2"])


def build_choices_read(d, rnd):
    if d["kind"] not in ("l3_stack", "l2_stack"):
        raise ValueError("read は l3_stack / l2_stack だけ")
    sc = SCEN_BY_ID[d["scen"]]
    ok = _correct_stack(sc, d["hop"])
    seen = {tuple(ok)}
    pool = []
    for st, why in _stack_pool(sc, d["hop"]):
        if tuple(st) in seen:
            continue
        seen.add(tuple(st))
        pool.append((st, why))
    if len(pool) < 3:
        raise ValueError("stack: 誤りの肢が足りない")
    must = _stack_pool(sc, d["hop"])[0][0]
    head = [x for x in pool if x[0] == must]
    rest = [x for x in pool if x[0] != must]
    picks = head + rnd.sample(rest, 3 - len(head))
    c = [(fmt_stack(ok, sc["svc"]), True, "")] + [(fmt_stack(st, sc["svc"]), False, why) for st, why in picks]
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


# ==========================================================================
# owner(select / allthat)
# ==========================================================================
def _owner_facts(sc):
    ing, p, egr = sc["path"]
    T, V = sc["h1"]
    b = BOARDS[sc["board"]]
    lo = b["lo"][egr]
    rr = b["rr"]
    trues, falses = [], []
    trues.append((f"外側の {T} は {p} が {egr} のループバック({lo})に割り当てた番号で、{ing} は LDP で {p} から受け取った。", ""))
    if sc["sig"] == "bgp":
        trues.append((f"内側の {V} は {egr} が割り当てた番号で、{ing} は BGP で受け取った({rr} が反射した)。", ""))
        trues.append((f"{rr} は、この経路を反射するときにネクスト ホップも内側のラベルも変えない。", ""))
        falses.append((f"{rr} は、この経路を反射するときに内側のラベルを自分の決めた番号に付け替える。",
                       f"RR はネクスト ホップもラベルも変えずに反射する。{ing} が受け取った {V} は {egr} が決めた番号のまま。"))
    else:
        trues.append((f"内側の {V} は {egr} が割り当てた番号で、{ing} は {egr} との targeted LDP のセッションで受け取った。", ""))
        falses.append((f"内側の {V} は、{ing} が {rr} から BGP で受け取った。",
                       f"LDP の疑似回線のラベルは BGP では配られない。{egr} が targeted LDP で {ing} に直接渡す。"))
    if sc["svc"] == "l3vpn":
        trues.append((f"{p} は VRF の経路を持たず、外側の {T} だけを見て転送する。", ""))
    else:
        trues.append((f"{p} は疑似回線もブリッジ ドメインも持たず、外側の {T} だけを見て転送する。", ""))
    falses.append((f"内側の {V} は {ing} が割り当てた番号である。",
                   f"内側の番号は出口の {egr} が決める({egr} が自分に届いたパケットの扱いを決めるため)。{ing} は受け取った番号を積むだけ。"))
    falses.append((f"外側の {T} は {egr} が割り当てた番号である。",
                   f"外側の番号は道の次の機器(ここでは {p})が決めて LDP で配る。{egr} は自分のループバックに implicit null(ラベル 3。受け取った {p} が外側を外す= PHP)か explicit null(ラベル 0)を広告する。"))
    falses.append((f"{p} は内側の {V} を見て、どの線へ送るかを決める。",
                   f"{p} が見るのは外側の {T} だけ。内側を見るのは出口の {egr}。"))
    falses.append((f"ラベルの番号は網の中で共通であり、{V} の意味は {ing} のラベルの表を見ても分かる。",
                   f"ラベルの番号は決めた機器の中でだけ意味を持つ。{V} の意味は {egr} の表にあり、{ing} の表の同じ番号(あれば)は別のもの。"))
    return trues, falses


def _owner_choices(d, rnd, n_true, n_total):
    sc = SCEN_BY_ID[d["scen"]]
    trues, falses = _owner_facts(sc)
    if len(trues) < n_true or len(falses) < n_total - n_true:
        raise ValueError("owner: 肢が足りない")
    c = [(t, True, "") for t, _ in rnd.sample(trues, n_true)]
    c += [(t, False, w) for t, w in rnd.sample(falses, n_total - n_true)]
    order = list(range(len(c)))
    rnd.shuffle(order)
    return [c[i] for i in order]


def build_choices_select(d, rnd):
    if d["kind"] != "owner":
        raise ValueError("select は owner だけ")
    return _owner_choices(d, rnd, 1, 4)


def build_choices_allthat(d, rnd):
    if d["kind"] != "owner":
        raise ValueError("allthat は owner だけ")
    sc = SCEN_BY_ID[d["scen"]]
    trues, _ = _owner_facts(sc)
    return _owner_choices(d, rnd, rnd.randint(1, min(3, len(trues))), 5)


def build_choices_select2(d, rnd):
    raise ValueError("spvpn に select2 は無い")


def build_choices_fix(d, rnd):
    raise ValueError("spvpn に fix は無い")


def build_choices_cause(d, rnd):
    raise ValueError("spvpn に cause は無い")


# ==========================================================================
# lfib(match)
# ==========================================================================
def build_match(d, rnd):
    if d["kind"] != "lfib":
        raise ValueError("match は lfib だけ")
    tb = LFIB_TABLES[d["table"]]
    rows = rnd.sample(tb["rows"], 4)
    terms = [(CIRC[i], str(r[0])) for i, r in enumerate(rows)]
    order = list(range(4))
    rnd.shuffle(order)
    choices = [(LET[j], rows[i][2]) for j, i in enumerate(order)]
    ans = {CIRC[i]: LET[j] for j, i in enumerate(order)}
    d["_rows"] = [(r[0], r[1]) for r in rows]
    return terms, choices, dict(sorted(ans.items()))


# ==========================================================================
# 問題文・解答
# ==========================================================================
def _board_md(board):
    b = BOARDS[board]
    return b["mermaid"] + "\n\n" + b["text"]


def question_body(d, choices, form):
    k = d["kind"]
    if k in ("l3_stack", "l2_stack"):
        sc = SCEN_BY_ID[d["scen"]]
        ing, p, egr = sc["path"]
        src, dst, addr = sc["ping"]
        a, b = (ing, p) if d["hop"] == 1 else (p, egr)
        before = (_board_md(sc["board"]) + "\n\n" + f"{src} から {dst}({addr})へ {SVC_JA[sc['svc']]} の上で ping を送ります。"
                  f"このとき、次の出力を得ました(一部を省略しています)。\n\n" + _exhibits(sc["ex"]))
        ask = (f"{sc['msg']}が {a} から {b} への線の上を運ばれるとき、付いている MPLS のラベルとして正しいものは、次のうちどれですか。"
               "ラベルは外側(先頭)から順に、左から書いています。(1つを選択してください)")
        ch_md = "\n\n".join(f"{LET[i]}. {t}" for i, (t, _, _) in enumerate(choices))
        return before, ask, ch_md, ""
    if k == "owner":
        sc = SCEN_BY_ID[d["scen"]]
        ing, p, egr = sc["path"]
        src, dst, addr = sc["ping"]
        T, V = sc["h1"]
        before = (_board_md(sc["board"]) + "\n\n" + f"{src} から {dst}({addr})へ {SVC_JA[sc['svc']]} の上で ping を送り、"
                  f"{ing} と {p} の間の線で{sc['msg']}を捕まえると、ラベルは外側から順に `{T} | {V}` でした。")
        ask = ({"select": "この 2 つのラベルについて、正しく述べられているものは、次のうちどれですか。(1つを選択してください)",
                "allthat": "この 2 つのラベルについて、正しく述べられているものを、すべて選んでください。"}[form])
        ch_md = "\n\n".join(f"{LET[i]}. {t}" for i, (t, _, _) in enumerate(choices))
        return before, ask, ch_md, ""
    # lfib
    tb = LFIB_TABLES[d["table"]]
    terms, ch, _ = choices
    before = _board_md(tb["board"]) + "\n\n" + f"{tb['pe']} で次の出力を得ました。\n\n" + _exhibits(tb["ex"])
    ask = (f"{tb['pe']} に、先頭に①〜④のラベルが付いたパケットが届きました。{tb['pe']} がそれぞれをどう扱うかを、"
           "A〜D から選んでください。")
    terms_md = "### 対応させる項目\n\n| # | 先頭のラベル |\n|---|------|\n" + "\n".join(f"| {kk} | {t} |" for kk, t in terms)
    ch_md = "\n\n".join(f"{kk}. {t}" for kk, t in ch)
    return before, ask, ch_md, terms_md


def _stack_explain(sc, hop):
    ing, p, egr = sc["path"]
    T, V = sc["h1"]
    lo = BOARDS[sc["board"]]["lo"][egr]
    out = [f"- 外側: {ing} の表で {egr} のループバック {lo} の行は、Local が {sc['ing_local']}・Outgoing が {T}。{ing} が付けるのは"
           f"次の {p} が決めた {T}。",
           f"- 内側: {sc['inner_src']}。"]
    if sc.get("enull"):
        out.append(f"- {p} の表で {lo} の行の Outgoing は explicit-n。{egr} が explicit null を広告しているので、{p} は外側をラベル 0 に"
                   f"付け替えて渡す。{egr} は 0 を外し、内側の {V} で {sc['egr_use']}を引く。")
    else:
        out.append(f"- {p} の表で {lo} の行の Outgoing は Pop Label(PHP)。{p} は外側を外して渡し、{egr} は内側の {V} で"
                   f" {sc['egr_use']}を引く。")
    out.append(f"- 線の上の実測(CML のリンクの捕獲): {ing} から {p} は {fmt_stack(sc['h1'], sc['svc'])}、"
               f"{p} から {egr} は {fmt_stack(sc['h2'], sc['svc'])}。")
    return "\n".join(out)


def answer_body(d, choices, form):
    k = d["kind"]
    if form == "match":
        terms, ch, ans = choices
        tb = LFIB_TABLES[d["table"]]
        rows = "\n".join(f"- {lab}: 表の行 `{lab} … {hint}`" for lab, hint in d.get("_rows", []))
        return "\n".join(["## 正解", "", "**" + "、".join(f"{kk}－{v}" for kk, v in ans.items()) + "**", "",
                          "## 解説", "", CORE[k], "", f"{tb['pe']} の表で該当する行:", "", rows, "", f"- 仕込み: {_key_of(d)}"])
    keys = [kk for kk, (t, ok, w) in zip(LET, choices) if ok]
    lines = ["## 正解", "", "**" + "、".join(keys) + "**", "", "## 各選択肢の判定", ""]
    for kk, (t, ok, w) in zip(LET, choices):
        lines.append(f"- **{kk}**: {'(正解)' if ok else w}")
    lines += ["", "## 解説", "", CORE[k]]
    if k in ("l3_stack", "l2_stack"):
        lines += ["", _stack_explain(SCEN_BY_ID[d["scen"]], d["hop"])]
    if k == "owner":
        sc = SCEN_BY_ID[d["scen"]]
        lines += ["", _stack_explain(sc, 1)]
    lines += ["", f"- 仕込み: {_key_of(d)}"]
    return "\n".join(lines)


def pick_count(form, choices):
    if form == "allthat":
        return -1
    return 1


# ==========================================================================
# selftest
# ==========================================================================
def _check_ex_against_logs():
    """EX の行が記録の中に同じ順で在るか(記録が無い環境では None)。"""
    bad = []
    checked = 0
    for name, e in EX.items():
        path = os.path.join(REPO, e["src"])
        if not os.path.exists(path):
            continue
        src = [ln.rstrip() for ln in open(path, encoding="utf-8").read().split("\n")]
        i = 0
        for ln in e["lines"]:
            while i < len(src) and src[i] != ln:
                i += 1
            if i >= len(src):
                bad.append(f"{name}: 記録に無い行 {ln!r}")
                break
            i += 1
        checked += 1
    return checked, bad


def _lfib_rows(name):
    """図の LFIB から {Local: (Outgoing, Prefix)}(継続行は無視)。"""
    rows = {}
    for ln in EX[name]["lines"]:
        m = re.match(r"^(\d+)\s+(Pop Label|No Label|explicit-n|Pop|Unlabelled|Aggregate|\d+)\s+(\S+)", ln)
        if m:
            rows[int(m.group(1))] = (m.group(2), m.group(3))
    return rows


def _derive(sc):
    """図の表から h1 の外側と h2 を導き、実測と突き合わせる。"""
    ing, p, egr = sc["path"]
    lo = BOARDS[sc["board"]]["lo"][egr] + "/32"
    lf_ing, lf_p = sc["ex"][-2], sc["ex"][-1]     # 約束: 図の最後の 2 つ= 入口 PE の表・P の表
    out_ing = [(loc, o) for loc, (o, pre) in _lfib_rows(lf_ing).items() if pre == lo]
    out_p = [(loc, o) for loc, (o, pre) in _lfib_rows(lf_p).items() if pre == lo]
    errs = []
    if len(out_ing) != 1 or int(out_ing[0][1]) != sc["h1"][0] or out_ing[0][0] != sc["ing_local"]:
        errs.append(f"{sc['id']}: 入口の表 {out_ing} と h1 {sc['h1']}・ing_local {sc['ing_local']} が合わない")
    if len(out_p) != 1 or out_p[0][0] != sc["h1"][0]:
        errs.append(f"{sc['id']}: P の表 {out_p} と h1 の外側 {sc['h1'][0]} が合わない")
    else:
        o = out_p[0][1]
        want = ([0] if o == "explicit-n" else [] if o in ("Pop Label", "Pop") else None)
        if want is None or want + [sc["h1"][1]] != sc["h2"]:
            errs.append(f"{sc['id']}: P の Outgoing {o} と h2 {sc['h2']} が合わない")
        if (o == "explicit-n") != bool(sc.get("enull")):
            errs.append(f"{sc['id']}: enull の印と P の表が合わない")
    if sc["p_rev"] not in _lfib_rows(lf_p):
        errs.append(f"{sc['id']}: p_rev {sc['p_rev']} が P の表に無い")
    blob = "\n".join("\n".join(EX[n]["lines"]) for n in sc["ex"])
    if not re.search(rf"(?<![\d.]){sc['h1'][1]}(?![\d.])", blob):
        errs.append(f"{sc['id']}: 内側 {sc['h1'][1]} が図のどこにも無い")
    return errs


def selftest(seeds=40):
    import random as _r
    ng = n = 0
    bad = {}
    checked, exbad = _check_ex_against_logs()
    for msg in exbad:
        print("  NG", msg)
    ng += len(exbad)
    for sc in SCEN:
        for msg in _derive(sc):
            print("  NG", msg)
            ng += 1
    for key, tb in LFIB_TABLES.items():
        rows = _lfib_rows(tb["ex"][0])
        descs = [r[2] for r in tb["rows"]]
        if len(set(descs)) != len(descs):
            print("  NG", key, "説明の重複")
            ng += 1
        for loc, hint, _ in tb["rows"]:
            if loc not in rows or not all(h in "\n".join(EX[tb["ex"][0]]["lines"]) for h in hint.split()):
                print("  NG", key, loc, "行が図に無い")
                ng += 1
    for sc in SCEN:                                  # 区間ごとの「必ず入れる誤り」が肢に入るか
        for hop in (1, 2):
            must = fmt_stack(_stack_pool(sc, hop)[0][0], sc["svc"])
            for s in range(10):
                c = build_choices_read({"kind": sc["kind"], "scen": sc["id"], "hop": hop}, _r.Random(s))
                if must not in [t for t, _, _ in c]:
                    print("  NG", sc["id"], hop, "必ず入れる誤りが無い")
                    ng += 1
                    break
    builders = {"select": build_choices_select, "allthat": build_choices_allthat, "read": build_choices_read}
    for kind in KINDS:
        for form in sorted(FORMS[kind]):
            for s in range(seeds):
                n += 1
                rnd = _r.Random(hash((kind, form, s)) & 0xFFFFFFFF)
                try:
                    d = draw(_r.Random((hash((kind, form, s)) * 7) & 0xFFFFFFFF), kind, None, form)
                    if form == "match":
                        choices = build_match(d, rnd)
                        terms, ch, ans = choices
                        assert len(ans) == 4 and len(set(ans.values())) == 4
                    else:
                        choices = builders[form](d, rnd)
                        n_true = sum(1 for x in choices if x[1])
                        if form == "allthat":
                            assert 1 <= n_true <= 3, f"allthat 正解数 {n_true}"
                        else:
                            assert n_true == 1, f"{form} 正解数 {n_true}"
                        texts = [x[0] for x in choices]
                        assert len(set(texts)) == len(texts), "選択肢の重複"
                        assert not any(re.search(r"(ため|ので)[、。]", t) for t in texts), "肢に因果"
                    question_body(d, choices, form)
                    assert "## 正解" in answer_body(d, choices, form)
                except (AssertionError, ValueError, KeyError) as exc:
                    ng += 1
                    bad.setdefault((kind, form), [0, repr(exc)])[0] += 1
    for (k, f), (cnt, ex) in sorted(bad.items()):
        print(f"  NG {k}/{f}: {cnt} 件 (例: {ex})")
    print(f"spvpn selftest: {n} 件中 NG {ng}(図の照合 {checked}/{len(EX)} 件)")
    return ng == 0


if __name__ == "__main__":
    import sys
    sys.exit(0 if selftest() else 1)
