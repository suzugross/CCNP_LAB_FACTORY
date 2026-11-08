# M11 — Q-in-Q

ここまでの E-Line は、どれも顧客の VLAN を 1 つだけ運びました。このページでは、顧客の複数の VLAN を 1 本の E-Line で
まとめて運びます。顧客のタグの外側に、プロバイダーのタグをもう 1 枚重ねる方法で、**Q-in-Q**(IEEE 802.1ad)と呼ばれます。
ラボは引き続き XRT-11 で、課題 M11-5 がこのページにあたります。

## 1. 何が嬉しいのか

### 1.1 VLAN ごとに E-Line を売る困りごと

顧客 B は、社内で VLAN 10 や 20 を使っていて、それをサイト 1 とサイト 3 の間でそのまま延ばしたいと考えています。
VLAN ごとに E-Line を 1 本ずつ作ると、顧客が VLAN を 1 つ足すたびに、プロバイダーは両端の PE に AC とクロスコネクトを
足すことになります。注文と工事の手間がかかり、顧客の社内の都合でプロバイダーの設定が増え続けます。

### 1.2 タグを重ねる

顧客の機器は、社内の VLAN のタグ(**C-VLAN**、顧客の VLAN)を付けたまま、その外側に、プロバイダーと取り決めた
タグ(**S-VLAN**、サービスの VLAN)をもう 1 枚付けて送ります。PE は外側のタグだけを見て E-Line を選び、内側のタグには
触れません。顧客は社内の VLAN を自由に足せ、プロバイダーの設定は S-VLAN ごとに 1 つで済みます。

IEEE 802.1ad(プロバイダー ブリッジ)は、外側のタグの種類(TPID)を 0x88a8 と決めています。昔からの実装では、外側も
内側と同じ 0x8100 を使うものもあり、「Q-in-Q」はどちらの形も指して使われます。このラボの CE(IOL)が付ける外側の
タグは 0x8100 です。

## 2. 仕組み

### 2.1 AC がどのフレームを拾うか

AC のサブインタフェースの `encapsulation` は、どの形のフレームを拾うかを決めます。外側 500 の単一タグ、
500/10 と 500/20 の二重タグ、後から足す 500/30 を CE から送ると、それぞれの形は次のように拾います。

| `encapsulation` | 500 だけ(単一) | 500/10、500/20 | 500/30 |
|---|---|---|---|
| `dot1q 500` | 拾う | 拾う | 拾う |
| `dot1q 500 exact` | 拾う | 拾わない | 拾わない |
| `dot1q 500 second-dot1q 10` | 拾わない | 10 だけ拾う | 拾わない |
| `dot1q 500 second-dot1q 10,20` | 拾わない | 拾う | 拾わない |
| `dot1q 500 second-dot1q any` | 拾わない | 拾う | 拾う |

IOS XR の `encapsulation dot1q 500` は、外側が 500 なら、内側にタグがあってもなくても拾います。二重タグだけを、内側を問わずに
拾うのが `second-dot1q any` です。どれにも合わないフレームは、どの AC にも入らず捨てられます。

### 2.2 1 ホップずつ: CEB1 から CEB3 へ(内側 VLAN 10)

:::topo
nodes:
  CEB1: [0, 1]
  XR01: [1.6, 1]
  XR03: [4.4, 1]
  CEB3: [6, 1]
links:
  - [CEB1, XR01, "tag 500 | tag 10 | IP"]
  - [XR01, XR03, "labels | tag 10 | IP"]
  - [XR03, CEB3, "tag 500 | tag 10 | IP"]
:::

1. XR01 の AC(`dot1q 500 second-dot1q any`、`pop 1`)は、外側のタグ 500 だけを外します。内側のタグ 10 は残ります。
2. 内側のタグ 10 が付いたままのフレームを、EVPN-VPWS(前のページ)のラベルで XR03 へ運びます。
3. XR03 の AC は、出るときに外側のタグ 500 を付け直します(`symmetric`)。CEB3 には 500/10 の二重タグで届きます。

内側のタグは、プロバイダーの網の中で一度も見られません。VLAN 20 も、後から足す VLAN 30 も、同じ E-Line を同じように通ります。

## 3. IOS XR の設定

### 3.1 設定の置き場

:::config fold XR01(IOS XR)— S-VLAN 500 の中を内側を問わず運ぶ E-Line
interface GigabitEthernet0/0/0/3.500 l2transport
 encapsulation dot1q 500 second-dot1q any          ## 外側 500 の二重タグだけを拾う(内側は問わない。単一タグの 500 は拾わない)
 rewrite ingress tag pop 1 symmetric               ## 外側だけ外す。内側の顧客のタグは残して運ぶ
!
l2vpn
 xconnect group CUST-B
  p2p B-500
   interface GigabitEthernet0/0/0/3.500
   neighbor evpn evi 500 target 3 source 1
   !
  !
 !
!
:::

XR03 も同じ形で、`target 1 source 3` です。両端とも `rewrite` を書かずに、2 枚のタグをそのまま運んでも通ります。
そのときは、両端の外側のタグを同じ番号にそろえます。

外側のタグを 802.1ad の 0x88a8 で受けるときは、`encapsulation dot1ad` を使います。次の形は、IOS XRv 9000 でコミットできます
(このラボには 0x88a8 を送る CE が無いので、構文だけを示します)。

:::config IOS XR — 外側のタグが 802.1ad のとき(構文の確認だけ)
interface GigabitEthernet0/0/0/2.401 l2transport
 encapsulation dot1ad 401 dot1q 10                 ## 外側= 0x88a8 の 401、内側= 0x8100 の 10
 rewrite ingress tag pop 1 symmetric               ## 外側だけ外す
!
interface GigabitEthernet0/0/0/2.403 l2transport
 encapsulation dot1q 403                           ## 単一タグの 403 を拾い
 rewrite ingress tag translate 1-to-2 dot1ad 500 dot1q 403 symmetric   ## 外側に 0x88a8 の 500 を足した 2 枚に付け替える
!
:::

### 3.2 読み方と落とし穴

拾う形の間違いは、E-Line を DN にしません。`show l2vpn xconnect` は UP のまま、運ぶフレームの範囲だけが違います。
確かめるには、拾うべき形と拾ってはならない形の両方を、CE から実際に送ります。課題 M11-5 で、CE に単一タグの 500 と
VLAN 30 のアドレスが用意してあるのはそのためです。

:::try
`second-dot1q any` を外すと、何が運ばれるかを確かめます。課題 M11-5 の後に行います。

1. XR01 と XR03 の `.500` の AC を `encapsulation dot1q 500`(`second-dot1q` なし)にしてコミットします。
2. CEB1 から `ping 172.31.50.3`(単一タグ)と `ping 172.31.51.3`(内側 10)を実行します。
3. `second-dot1q any` に戻してコミットし、もう一度実行します。

結果の例: `second-dot1q` なしでは、単一タグの 500 も内側 10 も通りました。`any` に戻すと、単一タグは通らず、
内側 10 は通りました。
:::

## 4. コマンド名

| IOS XE では | IOS XR では |
|---|---|
| ルータのサブインタフェースの `encapsulation dot1Q 500 second-dot1q 10` | `l2transport` のサブインタフェースの `encapsulation dot1q 500 second-dot1q 10` |
| `service instance` の `encapsulation dot1q 500 second-dot1q any` | `encapsulation dot1q 500 second-dot1q any` |
| `service instance` の `encapsulation dot1ad 500 dot1q 10` | `encapsulation dot1ad 500 dot1q 10` |
| スイッチのポートの `switchport mode dot1q-tunnel` | (E-Line の AC の `encapsulation` で受ける) |

## 実践

ラボ **XRT-11** で、課題 M11-5 に取り組みます。終わったら先へ進みます。このラボの XR では動かせない E-LAN、マルチホーム、
イーサネット OAM は追補でラボ XRT-12 を使って扱い、E-Tree、G.8032、802.1ah は付録で扱います。

<p class="tolab"><a href="/_learn?id=XRT-11">ワークスペースでラボ XRT-11 を開く</a> — <a href="b5-m11-practice-3.html">課題</a></p>

:::note
出典: L2VPN and Ethernet Services Configuration Guide for the NCS 5500 と ASR 9000, IOS XR 25.x(2025。仮想 LAN の設定、
キャリア イーサネットのモデル、rewrite の制約)。IEEE 802.1ad。いずれも 2026 年 11 月に確認しました。次のものは、ラボ XRT-11 と
その PoC での測定によります。`encapsulation` ごとの拾う形、rewrite なしでの運び方、802.1ad の構文が通ることです。
:::
