# EVPN-VPWS は何が嬉しいか — 同じ E-Line を 2 つの作り方で

E-Line(1 本のケーブルに見えるサービス)には、作り方が 2 つありました。LDP の疑似回線と EVPN-VPWS です。
1 本の線を 1 台ずつの PE で結ぶだけなら、運ばれ方は同じです。外側のラベルが出口の PE への道で、内側のラベルが
相手の AC を指します(「サービスを並べて見る」の 3.3 節)。

差が出るのは、次の 2 つの場面です。このページでは、同じ盤面に 2 つの作り方を並べて確かめます。

- お客さまの拠点を、2 台の PE につなぐとき
- コアの道を SR にして、網から LDP をなくすとき

出力は、このページのために組んだ次の盤面で取りました。PE は Catalyst 8000V(IOS XE 17.15.1a)3 台です。P1、RR1、
CE3 は IOL の IOS XE 17.15、SW1 は IOL-L2 です。P1 は P ルータだけで、BGP を持ちません。

:::topo
nodes:
  SW1: {at: [0, 1.6], label: "SW1(拠点 4)"}
  XE1: {at: [1.9, 0.3], label: "XE1(PE)"}
  XE2: {at: [1.9, 2.9], label: "XE2(PE)"}
  RR1: {at: [3.8, 0.3], label: "RR1(RR)"}
  P1: {at: [3.8, 1.6], label: "P1(P)"}
  XE3: {at: [5.7, 1.6], label: "XE3(PE)"}
  CE3: {at: [7.6, 1.6], label: "CE3(拠点 3)"}
links:
  - [SW1, XE1, "Po1 の 1 本"]
  - [SW1, XE2, "Po1 の 1 本"]
  - [XE1, P1, ""]
  - [XE2, P1, ""]
  - [P1, RR1, "IS-IS だけ"]
  - [P1, XE3, ""]
  - [XE3, CE3, "VLAN 150 160"]
frames:
  - {label: "AS 65000(IS-IS CORE、LDP。4 節で SR に)", nodes: [XE1, XE2, P1, RR1, XE3]}
:::

SW1 は、XE1 と XE2 への 2 本の線を 1 つの束(LACP の Port-channel1)にしています。どちらの E-Line も、拠点 4 の SW1 と
拠点 3 の CE3 を結びます。

| VLAN | 作り方 | アドレス |
|---|---|---|
| 150 | EVPN-VPWS(EVI 150。拠点 4 の端は 4、拠点 3 の端は 3) | 172.31.150.0/24(SW1 .4、CE3 .3) |
| 160 | LDP の疑似回線(XE1 ⇔ XE3 は PW ID 161、XE2 ⇔ XE3 は 162) | 172.31.160.0/24(SW1 .4、CE3 .3) |

## 1. 何が嬉しいのか

### 1.1 困りごと: 拠点を 2 台の PE につなぎたい

拠点 4 は止められない拠点なので、PE が 1 台落ちても通り続けるように、SW1 を XE1 と XE2 の両方につなぎました。
SW1 から見ると、2 本の線は 1 つの束です。束はフレームを 2 本の線に振り分けます。

E-Line は「拠点 4 と拠点 3 を結ぶ 1 本のケーブル」です。どちらの線に入ったフレームも、拠点 3 に届いてほしいところです。

### 1.2 それ以前の手: 主と予備の疑似回線

LDP の疑似回線は、相手の PE を名指しして結ぶ線です。XE3 から XE1 への線と XE2 への線を 2 本作り、片方を予備にします
(疑似回線の冗長)。使える線は、いつも 1 本です。

このため、CE 側の束も「予備の側へはフレームを流さない」ようにそろえる必要があります。PE 同士で束のどちらを使うかを
決める、別の仕組み(MC-LAG など)が要ります。この盤面では入れていないので、何が起きるかを 3.2 節で見ます。

### 1.3 EVPN-VPWS の答え: 2 台の PE が同じ ES を名乗る

EVPN-VPWS では、XE1 と XE2 が SW1 への束を同じ ES(Ethernet Segment。ESI という番号で呼ぶ)として BGP で広告します。
M11 追補で E-LAN に使ったマルチホームと同じ仕組みが、E-Line にも使えます。束の両方の線が使え、片方の PE が落ちたら
経路を取り下げるだけで切り替わります。

EVPN-VPWS の規格(RFC 8214)も、真っ先にこの冗長を嬉しさとして挙げています。さらに、相手の PE を BGP で見つけるので、
コアの道を SR にすれば、網から LDP がなくなります(4 節)。

## 2. 仕組み: 端の番号を BGP で配る

EVPN-VPWS では、各 PE が「この EVI のこの端(`source`)はここにある。ラベルはこれ」を、種類 1 の経路(EVI ごとの
Ethernet A-D 経路)で配ります。相手の PE は、自分の `target` の番号の経路を探します。

この盤面では、XE1 と XE2 が端 4 の経路を、XE3 が端 3 の経路を出します。XE3 には、端 4 の経路が RR1 経由で 2 本
(XE1 から 1 本、XE2 から 1 本)届きます。経路の末尾の `[4]` が端の番号です。

```console
XE3#show bgp l2vpn evpn route-type 1
BGP routing table entry for [1][10.255.0.43:150][00000000000000000000][4]/23, version 6
Paths: (2 available, best #2, table evi_150)
  Flag: 0x20000000100
  Not advertised to any peer
  Refresh Epoch 2
  Local, imported path from [1][10.255.0.42:150][00000000000000000000][4]/23 (global)
    10.255.0.42 (metric 30) (via default) from 10.255.0.52 (10.255.0.52)
      Origin incomplete, metric 0, localpref 100, valid, internal, multipath(oldest)
      Rcvd Label: 23, Local Label: None
      Extended Community: RT:65000:150
      Originator: 10.255.0.42, Cluster list: 10.255.0.52
      rx pathid: 0, tx pathid: 0
      Updated on Nov 6 2026 23:43:40 UTC
  Refresh Epoch 2
  Local, imported path from [1][10.255.0.41:150][00000000000000000000][4]/23 (global)
    10.255.0.41 (metric 30) (via default) from 10.255.0.52 (10.255.0.52)
      Origin incomplete, metric 0, localpref 100, valid, internal, multipath, best
      Rcvd Label: 23, Local Label: None
      Extended Community: RT:65000:150
      Originator: 10.255.0.41, Cluster list: 10.255.0.52
      rx pathid: 0, tx pathid: 0x0
      Updated on Nov 6 2026 23:43:33 UTC
```

(自分が出した経路と、取り込む前の経路の項目は省いています。)

XE3 の設定には、XE1 の住所も XE2 の住所も書いてありません。書いたのは端の番号(`service target 4 source 3`)だけです。
拠点 4 の PE が 2 台になっても、XE3 の設定は 1 台のときと同じです。

XE3 は、2 本のうち 1 本の PE へ送ります。このときは XE2 でした(`imposed label stack {19 23}` の 19 は、P1 が配った
XE2 への道のラベル、23 は XE2 の端 4 のラベルです)。

```console
XE3#show l2vpn evpn vpws vc id 150 detail
EVPN name: SITE3-SITE4, state: up, type: point-to-point
  EVPN ID: 150
  VPWS Service Instance ID: Source 3, Target 4
  Labels: Local 23, Remote 23
  Next Hop Address: 10.255.0.42
  Associated member interface Gi2 up, Gi2:150 status is up
  Output interface: Gi1, imposed label stack {19 23}
```

(以下の行は省いています。)

XE1 と XE2 は、同じ ESI を名乗る相手を種類 4 の経路で見つけ合います。`Forwarder List` に 2 台が並べば、ES ができています。

```console
XE1#show l2vpn evpn ethernet-segment detail
EVPN Ethernet Segment ID: 0000.0000.0000.0000.0401
  Local Discriminator:    4
  Interface:              Po1
  Redundancy mode:        all-active
  DF election wait time:  3 seconds
  Split Horizon label:    19
  State:                  Ready
  Encapsulation:          none
  Ordinal:                0
  Core Isolation:         No
  Forwarder List:         10.255.0.41 10.255.0.42
```

:::note
IOS XE 17.x の MPLS のコンフィギュレーション ガイドでは、マルチホームの章は E-LAN 向けで、EVPN-VPWS のマルチホームの
記述はありません(EVPN-VPWS は単一ホームの章だけです)。この盤面の Catalyst 8000V 17.15.1a は設定を受け付け、
このページのとおりに動きました。ただし規格どおりの形ではありませんでした。種類 1 の経路の ESI は 0 のまま(上の出力の
`[00000000000000000000]`)で、XE3 が使う PE は 1 台だけでした。PE が戻るたびに、最後に届いた経路の PE へ乗り換えました。

RFC 8214 の all-active では、遠くの PE が 2 台の PE へフローごとに振り分けることもできます。IOS XR のガイドは、
EVPN-VPWS のマルチホームを載せています。
:::

## 3. 2 つの作り方を同じ盤面で

### 3.1 EVPN-VPWS

XE1 と XE2 の設定は、この部分では 1 文字も違いません。束を ES にし、束のサービス インスタンスを EVI 150 の端 4 に
します。

:::config XE1(IOS XE)— 拠点 4 を 2 台で収容する EVPN-VPWS(XE2 も同じ)
l2vpn evpn ethernet-segment 4                      ## ES を作る。番号はこの PE の中だけの名前
 identifier type 0 00.00.00.00.00.00.00.04.01      ## ESI。XE1 と XE2 で同じ値にする(同じ拠点の印)
 redundancy all-active                             ## 2 台とも使う
!
interface Port-channel1
 description to SW1 (site 4)
 no ip address
 evpn ethernet-segment 4                           ## この束を ES 4 にする
 lacp device-id 0000.0000.0004                     ## SW1 から 1 台に見えるよう、2 台で同じ LACP の ID を名乗る
 service instance 150 ethernet
  encapsulation dot1q 150
  rewrite ingress tag pop 1 symmetric
!
interface GigabitEthernet3
 description to SW1 (site 4)
 no ip address
 channel-group 1 mode active                       ## SW1 への線を束に入れる
!
l2vpn evpn instance 150 point-to-point
 vpws context SITE4-SITE3
  service target 3 source 4                        ## 自分の端は 4、相手の端は 3。相手の PE の住所は書かない
  member Port-channel1 service-instance 150
:::

:::config XE3(IOS XE)— 拠点 3 の EVPN-VPWS
interface GigabitEthernet2
 description to CE3 (site 3)
 no ip address
 service instance 150 ethernet
  encapsulation dot1q 150
  rewrite ingress tag pop 1 symmetric
!
l2vpn evpn instance 150 point-to-point
 vpws context SITE3-SITE4
  service target 4 source 3                        ## 端 4 が 2 台の PE にあっても、書くことは同じ
  member GigabitEthernet2 service-instance 150
:::

`lacp device-id` を 2 台でそろえないと、SW1 は相手が 2 台いると見て、束の片方の線を止めます(M11 追補の実測)。
そろえると、SW1 の束は 2 本とも `P`(束に入っている)になります。

```console
SW1#show etherchannel summary
Group  Port-channel  Protocol    Ports
------+-------------+-----------+-----------------------------------------------
1      Po1(SU)         LACP        Et0/0(P)        Et0/1(P)
```

(凡例の行は省いています。)

SW1 は、CE3 への ping を XE2 側の線(Et0/1)へ流していました。100 発の ping の前後で、Et0/1 の送信の数は 101 増え、
Et0/0 は 2 増えただけです。それでも ping は全部通りました。XE2 に入ったフレームも、XE2 の端 4 から XE3 へ届いています。

```console
SW1#show interfaces Ethernet0/1 | include packets output
     56200 packets output, 6641213 bytes, 0 underruns
SW1#ping 172.31.150.3 repeat 100
Success rate is 100 percent (100/100), round-trip min/avg/max = 1/2/3 ms
SW1#show interfaces Ethernet0/1 | include packets output
     56301 packets output, 6653073 bytes, 0 underruns
```

(ping の途中の行は省いています。この数え値は、4 節で道を SR にした後に取りました。SW1 がどちらの線へ流すかは、
コアの道の作り方とは関係しません。)

切り替えも測りました。SW1 から CE3 へ、待ち時間 1 秒の ping を 15000 発流しながら、PE の SW1 向きの線を落としました。
連続して落ちた数が、途切れたおおよその秒数です。平常時も、ときどき 1 発ずつ落ちます。

| 落とした線 | そのとき XE3 が使っていた PE | 連続して落ちた ping |
|---|---|---|
| XE1 の Gi3 | XE2 | なし(1 発ずつの落ちだけ) |
| XE2 の Gi3 | XE2 → XE1 へ切り替え | 最長 4 発(約 4 秒) |

XE3 が使っている側を落としても、4 秒ほどで XE1 へ切り替わりました。XE2 は束の線を失うと端 4 の経路を取り下げ、XE3 は
残った XE1 の経路へ乗り換えます。XE2 の線を落とした 5 秒後の XE3 です。

```console
XE3#show bgp l2vpn evpn route-type 1
BGP routing table entry for [1][10.255.0.42:150][00000000000000000000][4]/23, version 15
Paths: (0 available, no best path)
  Not advertised to any peer
BGP routing table entry for [1][10.255.0.43:150][00000000000000000000][4]/23, version 16
Paths: (1 available, best #1, table evi_150)
  Not advertised to any peer
  Refresh Epoch 2
  Local, imported path from [1][10.255.0.41:150][00000000000000000000][4]/23 (global)
    10.255.0.41 (metric 30) (via default) from 10.255.0.52 (10.255.0.52)
```

(XE1 の経路そのものの項目と、続きの行は省いています。)

CML では、XE 側でインタフェースを shutdown しても、SW1 側の線は up のままです。SW1 は LACP のパケットが途絶えて初めて
気づきます(`lacp rate fast` で 3 秒)。4 秒の多くはこの待ちです。

### 3.2 LDP の疑似回線: 主と予備

同じ形を、LDP の疑似回線で作りました。XE1 と XE2 はそれぞれ XE3 へ疑似回線を張ります。XE3 は 2 本を 1 つのグループに
まとめ、XE1 への線を主、XE2 への線を予備にします。

:::config XE1(IOS XE)— 拠点 4 の LDP の疑似回線(XE2 は PW ID 162)
interface Port-channel1
 service instance 160 ethernet
  encapsulation dot1q 160
  rewrite ingress tag pop 1 symmetric
!
l2vpn xconnect context SITE4-SITE3-LDP
 member Port-channel1 service-instance 160
 member 10.255.0.43 161 encapsulation mpls          ## 相手の PE(XE3)を住所で名指しする
:::

:::config XE3(IOS XE)— 主と予備の疑似回線
interface GigabitEthernet2
 service instance 160 ethernet
  encapsulation dot1q 160
  rewrite ingress tag pop 1 symmetric
!
l2vpn xconnect context SITE3-SITE4-LDP
 member GigabitEthernet2 service-instance 160
 member 10.255.0.41 161 encapsulation mpls group SITE4 priority 1   ## 主= XE1。PE を 2 台とも名指しする
 member 10.255.0.42 162 encapsulation mpls group SITE4 priority 2   ## 予備= XE2。同じグループの、優先度の低い線
:::

XE3 では、主の線が UP、予備の線が STANDBY になります。

```console
XE3#show l2vpn atom vc
                                       Service
Interface Peer ID         VC ID      Type   Name                     Status
--------- --------------- ---------- ------ ------------------------ ----------
pw100001  10.255.0.41     161        p2p    SITE3-SITE4-LDP          UP
pw100002  10.255.0.42     162        p2p    SITE3-SITE4-LDP          STANDBY
```

ところが、SW1 から CE3 への ping は 1 発も通りませんでした。SW1 は、EVPN-VPWS のときと同じく XE2 側の線へ流しています。
XE2 はフレームを予備の線へ送っています(20 発の ping の間に `Tx Counters` が 29 から 47 に増えた)。それでも XE3 は、
予備の線から来たものを使いません。

```console
XE2#show l2vpn atom vc vcid 162 detail
pseudowire100001 is up, VC status is standby PW type: Ethernet
      Status sent to access circuit           : DOWN(standby)
      Status received from network peer       : DOWN(standby)
  Tx Counters
    47 output transit packets, 6580 bytes
    0 drops
```

(関係する行だけを抜き出しています。)

SW1 の XE2 側の線を止めて、束を XE1 側の 1 本だけにすると、ping は 100% 通りました。1.2 節のとおり、主と予備の
疑似回線では、CE 側の束も予備の側を使わないようにそろえる必要があります。

主の XE1 の線を落とすと、XE3 は主の線を DOWN にして、予備の XE2 への線を UP にしました。そこで初めて、XE2 側へ流れる
フレームが通りました。XE1 の線を戻すと、XE3 は主へ戻り、ping はまた通らなくなりました。

```console
XE3#show xconnect all
XC ST  Segment 1                         S1 Segment 2                         S2
------+---------------------------------+--+---------------------------------+--
IA pri   ac Gi2:160(Eth VLAN)            UP mpls 10.255.0.41:161              DN
UP pri   ac Gi2:160(Eth VLAN)            UP mpls 10.255.0.42:162              UP
```

(XE1 の線を落とした後。凡例の行は省いています。)

### 3.3 比べると

| | EVPN-VPWS | LDP の疑似回線(主と予備) |
|---|---|---|
| 拠点 3 の PE(XE3)に書くもの | 端の番号だけ(`target 4 source 3`) | 拠点 4 の PE を 2 台とも住所で |
| 使える線 | 束の 2 本とも(XE2 に入ったフレームも届く) | 主の 1 本だけ。予備に入ったフレームは届かない |
| CE 側の束 | そのままでよい(2 台で ES と LACP の ID をそろえる) | 予備の側を使わないよう、別の仕組みでそろえる |
| PE が落ちたとき | 経路の取り下げで乗り換え(この盤面で約 4 秒) | 主の線が落ちて、予備が UP になる |

## 4. 道を SR にして、LDP を外す

M10 で見たとおり、コアの道は LDP でなく SR でも作れます。SR にすると、道のための LDP は要りません。では、2 つの
E-Line は LDP を必要とするでしょうか。

この盤面で、P1 と XE1〜3 の IS-IS に SR を入れ、各ループバックに SID を付けてから、コアのリンクの `mpls ip` を外しました。

:::config XE1(IOS XE)— 道を SR にする(P1・XE2・XE3 も番号だけ変えて同じ)
segment-routing mpls
 connected-prefix-sid-map
  address-family ipv4
   10.255.0.41/32 index 41 range 1                 ## ループバックに SID の番号 41 を付ける(ラベルは 16000+41)
  exit-address-family
!
router isis CORE
 segment-routing mpls                              ## IS-IS で SID を配り、SR の道を作る
!
interface GigabitEthernet1
 no mpls ip                                        ## コアのリンクの LDP を止める
:::

P1 の LDP のセッションは 0 本になり、道のラベルは SR のラベル(16041 など)に替わりました。

```console
P1#show mpls ldp neighbor
P1#show mpls forwarding-table
Local      Outgoing   Prefix           Bytes Label   Outgoing   Next Hop
Label      Label      or Tunnel Id     Switched      interface
20         Pop Label  10.0.41.41-A     0             Et0/0      10.0.41.41
21         Pop Label  10.0.42.42-A     0             Et0/1      10.0.42.42
22         Pop Label  10.0.43.43-A     0             Et0/2      10.0.43.43
23         Pop Label  10.0.52.52-A     0             Et1/1      10.0.52.52
16041      Pop Label  10.255.0.41/32   582           Et0/0      10.0.41.41
16042      Pop Label  10.255.0.42/32   506           Et0/1      10.0.42.42
16043      Pop Label  10.255.0.43/32   1088          Et0/2      10.0.43.43
```

(20〜23 は、隣のルータへのリンクの SID です。)

EVPN-VPWS は、SR の道(外側 16041)の上でそのまま通りました。ラベルを BGP で伝えるので、LDP はどこにも出てきません。

```console
XE3#show l2vpn evpn vpws vc id 150 detail
EVPN name: SITE3-SITE4, state: up, type: point-to-point
  EVPN ID: 150
  VPWS Service Instance ID: Source 3, Target 4
  Labels: Local 23, Remote 23
  Next Hop Address: 10.255.0.41
  Associated member interface Gi2 up, Gi2:150 status is up
  Output interface: Gi1, imposed label stack {16041 23}
```

(以下の行は省いています。)

LDP の疑似回線も、SR の道の上で UP のままでした。ただし XE3 には、XE1 と XE2 との targeted の LDP のセッションが
残っています。疑似回線のラベルを伝えるためのセッションです。

```console
XE3#show mpls ldp neighbor | include Peer|Targeted|Src
    Peer LDP Ident: 10.255.0.41:0; Local LDP Ident 10.255.0.43:0
	  Targeted Hello 10.255.0.43 -> 10.255.0.41, active, passive
    Peer LDP Ident: 10.255.0.42:0; Local LDP Ident 10.255.0.43:0
	  Targeted Hello 10.255.0.43 -> 10.255.0.42, active, passive
```

XE3 から疑似回線を消すと、LDP のセッションは 0 本になりました。EVPN-VPWS は通ったままです。

```console
XE3#show mpls ldp neighbor
XE3#
```

道を SR にしても、LDP の疑似回線を使う限り、網には疑似回線のためだけの LDP が残ります。EVPN-VPWS に移せば、
道も E-Line も LDP なしで動き、網から LDP をなくせます。

## 5. まとめ

| | LDP の疑似回線 | EVPN-VPWS |
|---|---|---|
| 相手の見つけ方 | 相手の PE を住所で名指し | 端の番号の経路(種類 1)と RT。BGP で RR 経由 |
| ラベルを伝える手段 | PE 同士の targeted LDP | BGP |
| 拠点を 2 台の PE に | 主と予備の線。CE 側の束も別の仕組みでそろえる | 同じ ES を 2 台で名乗る(E-LAN のマルチホームと同じ) |
| 道を SR にしたとき | 疑似回線のために LDP が残る | LDP をなくせる |
| 1 本の線を 1 台ずつの PE で | 同じ | 同じ |

一言でいうと、**EVPN-VPWS は E-Line を EVPN の仲間に入れる作り方**です。マルチホームも、LDP を使わない運用も、
L3VPN や E-LAN と同じ BGP の上にそろいます。逆に、PE が数台で線も数本だけなら、BGP の EVPN を用意しない分、
LDP の疑似回線のほうが手軽です。
