# M9 — L3VPN

プロバイダーは、顧客ごとにコアをまたぐプライベートなネットワークを提供し、顧客どうしが同じアドレスを使っていても互いを分けておきます。
これが MPLS のレイヤ 3 VPN(L3VPN)です。このページは CCNP Service Provider のブループリントの 4.3 にあたります。1 つのプロバイダーの
中の L3VPN(4.3.a)と、共有サービス、つまりエクストラネットとインターネット接続(4.3.b)です。プロバイダーの間の VPN(Inter-AS、4.1.b)と、
顧客そのものがプロバイダーである場合(CSC、4.1.c)は最後に説明します。IOS の L3VPN は Enterprise のトラックで学んでいるので、
このページは IOS XR が独自のやり方をするところに絞ります。

ラボは XRT-09 です。コアはラボ XRT-07 と同じで、XR01 と RT02 がプロバイダー エッジ(PE)、RT01 と RT03 がコアのルータで、IS-IS と
LDP が動いています。新しいのは XR02 で、VPN のルートのためのルート リフレクタです。このページの出力は、IOS XRv 9000 26.1.1(XR01)、
IOS XRd 26.1.1(XR02)、IOL 上の IOS XE 17.15(他のルータ)で取得しました。XR01 を XRd にして同じ手順を流しても、制御プレーンは
同じ結果でした。ここで XR01 を XRv 9000 にした理由は 2.3 節にあります。

:::topo
nodes:
  CEA1: {at: [0, 0], label: "CEA1 (A のサイト 1)"}
  CEB1: {at: [0, 0.9], label: "CEB1 (B のサイト 1)"}
  SVC: {at: [0, 1.8], label: "SVC (共有)"}
  INET: {at: [1.6, -0.8], label: "INET (インターネット)"}
  XR01: {at: [1.6, 0.9], label: "XR01 (PE)"}
  RT01: {at: [3.2, 0.2], label: "RT01 (P)"}
  RT03: {at: [3.2, 1.6], label: "RT03 (P)"}
  XR02: {at: [3.2, 2.7], label: "XR02 (RR)"}
  RT02: {at: [4.8, 0.9], label: "RT02 (PE)"}
  CEA2: {at: [6.4, 0.4], label: "CEA2 (A のサイト 2)"}
  CEB2: {at: [6.4, 1.4], label: "CEB2 (B のサイト 2)"}
links:
  - [CEA1, XR01, "CUST-A"]
  - [CEB1, XR01, "CUST-B"]
  - [SVC, XR01, "SVC"]
  - [INET, XR01, "global"]
  - [XR01, RT01, "PRIMARY"]
  - [XR01, RT03, "BACKUP"]
  - [RT01, RT02, "CORE-A"]
  - [RT03, RT02, "CORE-B"]
  - [RT03, XR02, "RR-LINK"]
  - [RT02, CEA2, "CUST-A"]
  - [RT02, CEB2, "CUST-B"]
frames:
  - {label: "AS 65000 (IS-IS CORE、LDP)", nodes: [XR01, RT01, RT03, RT02, XR02]}
:::

顧客 A は 2 つのサイトを持ち、それぞれの PE の背後にあって、どちらも AS 65101 です。顧客 B も 2 つのサイトを持ち、AS は 65201 と
65202 です。SVC にはプロバイダーの共有サーバがあり、INET はインターネットの役です。ルート リフレクタ XR02 は RT03 の先にぶら下がり、
どの顧客のパケットの経路にも入りません。

## 1. IOS XR の VRF

### 1.1 部品

部品はどのプラットフォームでも同じです。**VRF**(VPN routing and forwarding instance)は、PE の上の独立したルーティング テーブルで、
1 つの顧客のインターフェイスがそこに入ります。**ルート識別子**(RD)は、顧客のプレフィックスが VRF から出ていくときにその前に付ける
8 バイトです。これで 2 つの顧客の 10.0.0.0/24 は、BGP の中で 2 つの別のルートのままでいられます。こうしてできるのが VPN-IPv4(VPNv4)の
ルートで、RFC 4364 の 4.2 節が定義しています。**ルート ターゲット**(RT)は、エクスポートのときにルートに付ける拡張コミュニティです。
PE は、ルートのターゲットのどれかをインポートする VRF に、そのルートをインポートします(RFC 4364 の 4.3.1 節)。RD はルートを一意にし、
RT は行き先を決めます。

CEA1 からサイト 2 へ向かう顧客 A のパケットは、コアをラベル 2 つで渡ります。下のラベルが **VPN ラベル**です。RT02 が選んでルートと一緒に
BGP でアドバタイズしたもので、パケットがどの VRF のものかを RT02 に伝えます。上のラベルは LDP のトランスポートのラベルで、単元 M8 と
まったく同じように、パケットを RT02 のループバックまで運びます。コアのルータは上のラベルだけでスイッチングし、顧客のアドレスは
見ません。

### 1.2 部品の置き場所

IOS では、RD と RT は `vrf definition` の下にまとめて書きます。IOS XR はこれを分けます。

- RT は VRF に属します。`vrf <名前>` → `address-family ipv4 unicast` → `import route-target` と
  `export route-target` で、どちらも 1 行に 1 つのルート ターゲットを書くサブモードです。
- インターフェイスは `vrf <名前>` で VRF に入ります。
- RD は BGP に属します。`router bgp <AS>` → `vrf <名前>` → `rd` で、その VRF の CE のネイバーも同じ `vrf` の下に
  置きます。

IOS XR は、コミットのときにこれらの部品の順序を検査します。BGP は、VPNv4 のネイバーや VRF のアドレス ファミリーを置く前に、最上位に
`address-family vpnv4 unicast` を必要とします。また、BGP の中の VRF のアドレス ファミリーには、先に RD が必要です。エラーは
次のとおりです。

```console
!!% 'BGP' detected the 'warning' condition 'The address family has not been initialized'
!!% 'BGP' detected the 'warning' condition 'The parent address family has not been initialized'
!!% 'BGP' detected the 'warning' condition 'The RD for the VRF must be present before an address family is activated'
```

1 つ目は VPNv4 のネイバーから、2 つ目は VRF のアドレス ファミリーから出たもので、どちらも最上位に VPNv4 のファミリーが無い状態です。
失敗したコミットは丸ごと取り消されるので、RD の無い VRF が何もアドバタイズしないまま残ることはありません。新しいガイドは `rd` を
`vrf <名前>` の直下にも書いており、IOS XR 26.1.1 はそこでも受け付けます。このページは、コマンド リファレンスの形どおり RD を BGP に
置きます。

:::note
NCS 5500 と ASR 9000 の L3VPN のコンフィギュレーション ガイド(リリース 7.11)は、インターフェイスの VRF を割り当てる・外す・変える前に、
その IPv4 と IPv6 のアドレスを外す必要があり、外さないと変更は拒否されると書いています。ラボでは、IOS XR 26.1.1(XRv 9000 と XRd の
どちらも)がアドレスを付けたままの変更を受け付け、アドレスも残しました。インターフェイスをグローバル テーブルから VRF へ、その逆へ、
または既にある別の VRF へ移すのは、数秒後には動きました。同じコミットで作った VRF へ移した 1 回のテストでは、隣と通信できない
ままでした。ガイドに従ってください。ラボ XRT-09 では顧客側のインターフェイスにアドレスが無いので、`vrf` と `ipv4 address` を
一緒に入れます。
:::

### 1.3 CE とのセッション

PE はふつう、VRF の中で eBGP を使って CE から顧客のルートを学習します。単元 M5 のことはすべてそのまま当てはまります。IOS XR の
eBGP のネイバーは、両方向にルート ポリシーを持つまでルートを交換せず、VRF も例外ではありません。セッションは上がり、ルートは
捨てられます。

```console
RP/0/RP0/CPU0:XR01#show bgp vrf CUST-B summary
...
Some configured eBGP neighbors (under default or non-default vrfs)
do not have both inbound and outbound policies configured for IPv4 Unicast
address family. These neighbors will default to sending and/or
receiving no routes and are marked with '!' in the output below.
Use the 'show bgp neighbor <nbr_address>' command for details.

Neighbor        Spk    AS MsgRcvd MsgSent       TblVer  InQ OutQ  Up/Down  St/PfxRcd
172.16.21.2       0 65201      27      33          113    0    0 00:19:49          0!

RP/0/RP0/CPU0:XR01#show bgp vrf CUST-B neighbors 172.16.21.2 | include "policy|accepted|denied"
  eBGP neighbor with no inbound or outbound policy; defaults to 'drop'
  0 accepted prefixes, 0 are bestpaths
  Exact no. of prefixes denied: 0
  Cumulative no. of prefixes denied: 1
    No policy: 1, Failed RT match: 0
```

入と出にポリシーがあれば、ルートは VRF の BGP テーブルとルーティング テーブルに入ります。`show route vrf CUST-A` はそれらを BGP の
ルートとして並べ、`show bgp vrf CUST-A` はテーブルの前に RD を表示します。

:::try
ポリシーが無いと CE とのセッションがどうなるかを見ます。課題 M9-1 の後に行います。

1. XR01 の `router bgp 65000` → `vrf CUST-B` → `neighbor 172.16.21.2` → `address-family ipv4 unicast` の下から、
   `route-policy` の 2 行を外してコミットします。
2. XR01 で `show bgp vrf CUST-B summary` と `show bgp vrf CUST-B neighbors 172.16.21.2` を、CEB1 で
   `show ip bgp summary` と `show ip route bgp` を実行します。
3. 2 行を戻してコミットし、同じコマンドをもう一度実行します。

ラボで測った結果: セッションは上がったままで、リセットもされませんでした(稼働時間は数え続けました)。XR01 は `0!` を表示して
CEB1 のルートを `No policy: 1` に数え、CEB1 の BGP のルートは消えました。CEB1 も何も受け取っていません(`State/PfxRcd 0`)。
行を戻してから 30 秒以内に、XR01 は再びルートを受け入れ、CEB1 にもルートが戻りました。
:::

## 2. プロバイダー エッジの間の VPN のルート

### 2.1 VPNv4

PE は、ループバックの間の iBGP の VPNv4 アドレス ファミリーで VPN のルートを交換します。VPNv4 のルートは、RD、プレフィックス、
ルート ターゲット、VPN ラベルを運びます。ネクスト ホップは PE の Loopback0 で、LDP がそこへのラベルを持っています。

```console
RP/0/RP0/CPU0:XR01#show bgp vpnv4 unicast rd 10.255.0.12:101 10.101.2.0/24
BGP routing table entry for 10.101.2.0/24, Route Distinguisher: 10.255.0.12:101
...
Paths: (1 available, best #1)
  Not advertised to any peer
  Path #1: Received by speaker 0
  Not advertised to any peer
  65101
    10.255.0.12 (metric 30) from 10.255.0.21 (10.255.0.12)
      Received Label 22
      Origin IGP, metric 0, localpref 100, valid, internal, best, group-best, import-candidate, not-in-vrf
      Extended community: RT:65000:101
      Originator: 10.255.0.12, Cluster list: 10.255.0.21
```

これは、XR01 が受け取ったままの顧客 A のサイト 2 です。RT02 の RD、ネクスト ホップとしての RT02 のループバック、RT02 の VPN ラベル 22、
ルート ターゲット 65000:101 を持っています。XR02 から届きました(`Cluster list`)。`not-in-vrf` は受け取ったコピーであることを表します。
XR01 はこれを自分の RD 10.255.0.1:101 の下のコピーとして CUST-A にインポートし、`show bgp vrf CUST-A` が並べるのはそちらです。

IOS XR は既定で、プレフィックスごとに VPN ラベルを割り当てます(**per-prefix**)。BGP の中の VRF のアドレス ファミリーの下に
`label mode per-vrf` を置くと、VRF 全体でラベルが 1 つになります。PE はそのとき、IOS XR が常に VRF ごとのラベルを付けるルート
(接続、集約、ローカルのルート)と同じように、宛先を VRF のテーブルで引き直します。`show mpls forwarding` に違いが出ます。

```console
RP/0/RP0/CPU0:XR01#show bgp vrf CUST-A labels
   Network            Next Hop        Rcvd Label      Local Label
Route Distinguisher: 10.255.0.1:101 (default for vrf CUST-A)
*> 0.0.0.0/0          192.0.2.2       nolabel         24009
*> 10.101.1.0/24      172.16.11.2     nolabel         24004
*>i10.101.2.0/24      10.255.0.12     22              nolabel
*> 198.51.100.0/25    172.16.11.2     nolabel         24005
*>i198.51.100.128/25  10.255.0.12     23              nolabel

RP/0/RP0/CPU0:XR01#show mpls forwarding
Local  Outgoing    Prefix             Outgoing     Next Hop        Bytes
Label  Label       or ID              Interface                    Switched
------ ----------- ------------------ ------------ --------------- ------------
24000  20          10.255.0.21/32     Gi0/0/0/1    10.0.3.13       5123
24001  Pop         10.255.0.13/32     Gi0/0/0/1    10.0.3.13       4106
24002  16          10.255.0.12/32     Gi0/0/0/0    10.0.1.11       16120
24003  Pop         10.255.0.11/32     Gi0/0/0/0    10.0.1.11       2986
24004  Unlabelled  10.101.1.0/24[V]   Gi0/0/0/2    172.16.11.2     0
24005  Unlabelled  198.51.100.0/25[V] Gi0/0/0/2    172.16.11.2     0
24006  Unlabelled  10.102.1.0/24[V]   Gi0/0/0/3    172.16.21.2     0
24007  Unlabelled  10.99.1.0/24[V]    Gi0/0/0/4    172.16.91.2     500
24008  Unlabelled  10.99.2.0/24[V]    Gi0/0/0/4    172.16.91.2     0
24009  Aggregate   CUST-A: Per-VRF Aggr[V]   \
                                      CUST-A                       2500
```

これは 4 つの課題をすべて終えたラボです。CE からのルートはそれぞれ自分のラベルを持ち、XR01 はそのラベルを外して、ラベルなしで CE へ
送ります(`[V]` は VRF のプレフィックスの印です)。課題 M9-4 で XR01 がグローバル テーブルからインポートするデフォルト ルートは
CE から来たものではないので、per-prefix のモードでも VRF の集約のラベル 24009 が付きます。

:::try
CUST-A のラベルを 1 つにしてみます。課題 M9-2 の後に行います(ラボでは課題 M9-4 の後に測りました)。

1. XR01 の `router bgp 65000` → `vrf CUST-A` → `address-family ipv4 unicast` の下に `label mode per-vrf` を設定して
   コミットします。
2. XR01 で `show bgp vrf CUST-A labels` と `show mpls forwarding` を、RT02 で
   `show ip bgp vpnv4 vrf CUST-A labels` を、CEA2 で `ping 10.101.1.1 source Loopback10` を実行します。
3. `label mode` を外してコミットします。

ラボで測った結果: XR01 が CEA1 から学習したルートはすべて、インポートしたデフォルト ルートのために VRF が既に持っていたラベル 24009 に
なり、24004 と 24005 は `show mpls forwarding` から消えました。20 秒以内に RT02 はそれらに `nolabel/24009` を表示し、ping は
通りました。`label mode` を外すと、ルートは再び 24004 と 24005 になりました。
:::

### 2.2 ルート ターゲットによるフィルタリング

PE は、自分が使える VPN のルートだけを保持します。ルート ターゲットがローカルの VRF のインポートするルート ターゲットのどれにも
一致しないルートは、ポリシーが無くても受信したときに捨てられ、ネイバーの詳細がそれを数えます。

```console
RP/0/RP0/CPU0:XR01#show bgp vpnv4 unicast neighbors 10.255.0.21 | include "refresh request|Failed RT|denied"
  Route refresh request: received 0, sent 2
  Exact no. of prefixes denied: 0
  Cumulative no. of prefixes denied: 2
    No policy: 0, Failed RT match: 2
```

ルートを捨てた PE が、後でそれを必要とすることがあります。新しい VRF を設定したとき、または PE がルートを持っていないインポートの
ルート ターゲットを足したとき、IOS XR はネイバーにルートを送り直すよう頼みます(BGP の**ルート リフレッシュ**)。ラボでは、VRF を
コミットしてから 5 秒以内に顧客 B のルートが届き、`show bgp vpnv4 unicast neighbors` がリフレッシュを数えました。

```console
RP/0/RP0/CPU0:XR01#show bgp vpnv4 unicast neighbors 10.255.0.21 | include "refresh request|Failed RT"
  Route refresh request: received 0, sent 3
    No policy: 0, Failed RT match: 2
```

これは、65000:102 を CUST-B のインポートするルート ターゲットに戻した直後です。PoC で VRF CUST-B を一から設定したときも同じで、
ルート リフレッシュが 1 回、顧客 B のルートが 5 秒以内でした。

:::try
XR01 がルートを捨て、もう一度求めるところを見ます。課題 M9-2 の後、課題 M9-3 の前に行います。課題 M9-3 からは VRF SVC も
65000:102 をインポートするので、XR01 はそのために顧客 B のルートを保持します。

1. XR01 で `show bgp vpnv4 unicast neighbors 10.255.0.21 | include "refresh request|Failed RT"` を実行します。
2. CUST-B のインポートするルート ターゲットから 65000:102 を外してコミットします。
   `show bgp vpnv4 unicast rd 10.255.0.12:102` を実行します。
3. `clear bgp vpnv4 unicast 10.255.0.21 soft in` を実行して XR02 にルートを送り直させ、それから手順 1 のコマンドを
   実行します。
4. 65000:102 を戻してコミットします。手順 1 のコマンドと `show bgp vrf CUST-B` を実行します。

ラボで測った結果: XR01 は 10.102.2.0/24 をすぐに捨て、RD 10.255.0.12:102 のテーブルは空になりました。ソフト リフレッシュの後、
ネイバーの詳細は `Failed RT match: 2` を表示し、送ったリフレッシュの要求は 0 から 2 になっていました。65000:102 を戻すと
カウンタは 3 になり、5 秒以内に 10.102.2.0/24 が再び CUST-B に入りました。CEB1 は CEB2 に到達できました。
:::

### 2.3 VPNv4 のルート リフレクタ

PE の間を VPNv4 のセッションのフル メッシュで結ぶと、その数は PE の数の 2 乗で増えるので、プロバイダーはルート リフレクタを使います。
ルート リフレクタは、インポートする VRF があってもなくても、すべての VPNv4 のルートを保持しなければならない唯一のルータです。
IOS XR では既定でそうし、クライアントを 1 つ持った時点でルート リフレクタになります。クライアントは、ネイバーのアドレス ファミリーごとの
性質です。`route-reflector-client` は `neighbor` → `address-family vpnv4 unicast` の下に置きます。別のアドレス ファミリーの
下に書いても、VPNv4 には何も効きません。

VRF も VPNv4 のクライアントも持たない iBGP スピーカーは、何も保持しません。その状態の XR02 は、送られたルートを 1 つも受け入れず、
拒否としても数えませんでした。

```console
RP/0/RP0/CPU0:XR02#show bgp vpnv4 unicast summary
...
Neighbor        Spk    AS MsgRcvd MsgSent       TblVer  InQ OutQ  Up/Down  St/PfxRcd
10.255.0.1        0 65000       4       3            1    0    0 00:00:37          0
10.255.0.12       0 65000       6       3            1    0    0 00:00:39          0

RP/0/RP0/CPU0:XR02#show bgp vpnv4 unicast neighbors 10.255.0.1 | include "accepted|denied"
  0 accepted prefixes, 0 are bestpaths
  Exact no. of prefixes denied: 0
  Cumulative no. of prefixes denied: 0
```

これは PoC で、ルート リフレクタの行も `retain` も無い XR02 に、XR01 が 2 つのルートを送っている間に取得しました。XR02 がルート
リフレクタになると、`show bgp vpnv4 unicast neighbors` は、設定のあるアドレス ファミリーごとの部分に `Route-Reflector Client` を
表示します。VPNv4 の部分にあるものを見てください。

`address-family vpnv4 unicast` の下の `retain route-target all` は、どの VRF もインポートしない VPNv4 のルートをルータに保持させます。
XR02 はそれですべてのルートを持ちましたが、やはり 1 つも渡しませんでした。iBGP スピーカーは iBGP のルートを別の iBGP ネイバーへ
送らず、それを変えるのはクライアントだけです。このコマンドは、VRF を持たないルートを保持しなければならない Inter-AS のオプション B の
境界ルータ(6 節)のためのものです。`route-policy` の形を使うと、ルート リフレクタが一部のルート ターゲットだけを保持し、VPN を複数の
リフレクタに分けられます。

XR02 は IOS XRd で動いています。Cisco は XRd を、ルート リフレクタなど転送パスの外の役割向けに、制御プレーンの形で提供しています。
このラボの XR01 には向きません。XR01 を XRd にした PoC では、ping は両方向に通りましたが、XRd が CE から受けてラベルを付けて送った
TCP と UDP のパケット、2 つの VRF の間や VRF とグローバル テーブルの間でルーティングしたパケットは、チェックサムが壊れて届きました。
CEA1 からの traceroute は最初の数ホップの先で止まりました。XRd がラベル付きで受けて CE へ送ったパケットは無傷でした。
IOS XRv 9000 は、これらをすべて正しく転送しました。

## 3. 同じ AS の 2 つのサイト

### 3.1 AS のオーバーライド

顧客 A は、両方のサイトで AS 65101 を使っています。サイト 2 のルートは AS パス 65101 で XR01 に届き、CEA1 はそれをループとして
捨てるはずです。IOS と IOS XR はこれを違う方法で扱います。IOS の PE はルートを送り、CE が捨てます。IOS XR はそもそも送りません。
送る前に、AS パスと相手の AS を照らし合わせます。

```console
RP/0/RP0/CPU0:XR01#show bgp vrf CUST-A 10.101.2.0/24
BGP routing table entry for 10.101.2.0/24, Route Distinguisher: 10.255.0.1:101
...
Paths: (1 available, best #1)
  Not advertised to any peer
  Path #1: Received by speaker 0
  Not advertised to any peer
  65101
    10.255.0.12 (metric 30) from 10.255.0.21 (10.255.0.12)
...
RP/0/RP0/CPU0:XR01#show bgp vrf CUST-A neighbors 172.16.11.2 advertised-routes
Network            Next Hop        From            AS Path
Route Distinguisher: 10.255.0.1:101 (default for vrf CUST-A)
0.0.0.0/0          172.16.11.1     192.0.2.2       65000 64500i
10.99.1.0/24       172.16.11.1     0.0.0.0         65000?
```

XR01 が CEA1 に送るものから、サイト 2 の 2 つのルート(10.101.2.0/24 と 198.51.100.128/25、どちらもパス 65101)が抜けています。
パスに 65101 を含まないルートは出ていきます。これは課題 M9-4 の後に `as-override` を外して取得しました。

CE のネイバーのアドレス ファミリーの下の `as-override` は、パスの中の顧客の AS をプロバイダーの AS に置き換え、ルートは `65000 65000` で
出ていきます。代わりの `allowas-in` は受け取る側のルータ、つまり CE で設定するもので、CE は顧客のものです。1 つのサイトが 2 つの PE に
つながっていると、AS を置き換えたルートは、来たサイトへ戻ることを止められなくなります。同じネイバーの下の `site-of-origin` は、
サイトのルートに拡張コミュニティで印を付け、IOS XR はその印の付いたルートを、同じ印を持つネイバーへ送り返しません。

:::try
オーバーライドを外してみます。課題 M9-2 の後に行います。

1. XR01 で、CUST-A のネイバー 172.16.11.2 から `as-override` を外してコミットします。
2. XR01 で `show bgp vrf CUST-A 10.101.2.0/24` と
   `show bgp vrf CUST-A neighbors 172.16.11.2 advertised-routes` を、CEA1 で `show ip bgp` を実行します。
3. `as-override` を戻してコミットします。

ラボで測った結果: 20 秒以内に、XR01 はサイト 2 のルートに `Not advertised to any peer` を表示し、それらは `advertised-routes` から
消え、CEA1 からも無くなりました。XR01 は、パスに 65101 を含んだまま送るのではなく、取り消したのです。行を戻すと、CEA1 は再び
`65000 65000` でそれらを持ちました。
:::

## 4. 共有サービス

### 4.1 インポートとエクスポートのルート ポリシー

**エクストラネット**は、VPN どうしに一部のルートだけを共有させます。ルート ターゲットだけだと、VRF はすべてのルートを同じターゲットで
エクスポートします。1 つのルートにだけ別のターゲットを付けるには、IOS XR は VRF のアドレス ファミリーにルート ポリシーを付けます。
`export route-policy` は VRF から出ていくルートに、`import route-policy` は VRF に入ってくるルートに働きます。

ラボでは、共有サービスのすべてのルートに VRF のエクスポートするルート ターゲット 65000:999 が付き、10.99.1.0/24 にはさらに、顧客の VRF が
インポートする 65000:900 が付きます。ポリシーは、そのプレフィックスにだけ追加のターゲットを付けます。

```text
route-policy SVC-EXPORT
  if destination in (10.99.1.0/24) then
    set extcommunity rt (65000:900) additive
  endif
  pass
end-policy
```

`additive` が肝心です。これが無いと、`set extcommunity rt` はルートが既に持っているルート ターゲットを置き換え、10.99.1.0/24 は
65000:900 だけを持って出ていきます。

```console
RP/0/RP0/CPU0:XR01#show bgp vrf SVC 10.99.1.0/24 | include Extended
      Extended community: RT:65000:900

RP/0/RP0/CPU0:XR01#show bgp vrf SVC 10.99.1.0/24 | include Extended
      Extended community: RT:65000:900 RT:65000:999
```

1 つ目の出力は `additive` の無いポリシー、2 つ目はあるポリシーです。

エクスポートのポリシーはルートを止められません。コマンド リファレンスがそう書いており、ラボでも、ポリシーが通さなかったルートは
VRF のルート ターゲットを付けて VRF から出ていきました。10.99.2.0/24 を顧客から隠しているのは、ポリシーではなく、どの顧客も
インポートしないそのルート ターゲットです。インポートのポリシーは 2 段のフィルタの 2 段目で、VRF のインポートするルート ターゲットに
既に一致したルートだけを見ます。

### 4.2 1 つの PE の複数の VRF

共有サービスと顧客 A・B は、どれも XR01 に VRF を持っています。それらの間でも、ルート ターゲットは 2 つの PE の間と同じように働きます。
XR01 は、リモートの PE を介さずに、自分で 10.99.1.0/24 を SVC から CUST-A と CUST-B にインポートし、SVC は両方の顧客のルートを
インポートするので、戻りのトラフィックにも経路があります。それでも顧客どうしは互いに見えません。SVC がインポートした顧客 B のルートは
自分のルート ターゲット 65000:102 を持ったままで、SVC のもので再びエクスポートされることはありません。

```console
RP/0/RP0/CPU0:XR01#show bgp vrf CUST-A
   Network            Next Hop            Metric LocPrf Weight Path
Route Distinguisher: 10.255.0.1:101 (default for vrf CUST-A)
*> 0.0.0.0/0          192.0.2.2                              0 64500 i
*> 10.99.1.0/24       172.16.91.2              0         32768 ?
*> 10.101.1.0/24      172.16.11.2              0             0 65101 i
*>i10.101.2.0/24      10.255.0.12              0    100      0 65101 i
*> 198.51.100.0/25    172.16.11.2              0             0 65101 i
*>i198.51.100.128/25  10.255.0.12              0    100      0 65101 i

RP/0/RP0/CPU0:XR01#show route vrf CUST-B bgp
B    10.99.1.0/24 [200/0] via 172.16.91.2 (nexthop in vrf SVC), 00:04:01
B    10.102.2.0/24 [200/0] via 10.255.0.12 (nexthop in vrf default), 00:17:29
```

CUST-A の中で、10.99.1.0/24 は SVC のアドレスをネクスト ホップに持ち、重みはローカルのルートのものです。同じルータの VRF SVC から
インポートしたからです。ルーティング テーブルは、ネクスト ホップがどこにあるかを示します。共有サーバでは VRF SVC に、RT02 からの
ルートではグローバル テーブル(`vrf default`)にあり、そのネクスト ホップは RT02 のループバックです。

:::try
`additive` を外してみます。課題 M9-3 の後に行います。

1. XR01 で、ルート ポリシー SVC-EXPORT を `additive` の無い `set extcommunity rt (65000:900)` で入れ直し、
   コミットします。
2. XR01 で `show bgp vrf SVC 10.99.1.0/24` を、RT02 で `show ip bgp vpnv4 all 10.99.1.0` を、CEA2 で
   `ping 10.99.1.1 source Loopback10` を実行します。
3. `additive` を戻してコミットします。

ラボで測った結果: 10.99.1.0/24 は `RT:65000:900` だけを持って出ていき、RT02 のコピーも同じでした。ping は通り続けました。顧客は
65000:900 をインポートするので、顧客から見えるものは何も変わりません。壊れたのはプロバイダーの規約で、65000:999 に頼るものがあれば
そこで気づきます。`additive` を戻すと、ルートは再び 2 つのルート ターゲットを持ちました。
:::

## 5. インターネット接続

### 5.1 VRF とグローバル テーブルの間

顧客 A の公開セグメントはインターネットに到達する必要があり、XR01 はインターネットを INET からグローバル テーブルで学習します。
IOS XR は、VRF のアドレス ファミリーの下の 2 つのコマンドで、VRF とグローバル テーブル(デフォルト VRF)の間で BGP のルートを
リークします。どちらもルート ポリシーが必須です。

- `import from default-vrf route-policy <名前>` は、グローバルのルートを VRF に取り込みます。ルートは VRF の CE に渡り、
  `advertise-as-vpn` があれば、VRF のルート ターゲットを付けた VPNv4 のルートとして他の PE にも渡ります。これが無いと、CEA1 は
  デフォルト ルートを持ち、RT02 の背後の CEA2 は持ちませんでした。
- `export to default-vrf route-policy <名前>` は、VRF のルートをグローバル テーブルにコピーし、そこから INET へ送れるように
  します。既定でエクスポートされるのは、XR01 が自分の CE から学習したルートだけです。サイト 2 の 198.51.100.128/25 のように
  別の PE から学習したルートには、`allow-imported-vpn` が必要です。

```console
RP/0/RP0/CPU0:XR01#show route vrf CUST-A 0.0.0.0/0
Routing entry for 0.0.0.0/0
  Known via "bgp 65000", distance 20, metric 0, candidate default path
  Tag 64500, type external
  ...
  Routing Descriptor Blocks
    192.0.2.2, from 192.0.2.2, BGP external
      Nexthop in Vrf: "default", Table: "default", IPv4 Unicast, Table Id: 0xe0000000

RP/0/RP0/CPU0:XR01#show bgp ipv4 unicast 198.51.100.128/25
BGP routing table entry for 198.51.100.128/25
...
  Advertised IPv4 Unicast paths to peers (in unique update groups):
    192.0.2.2
  65101
    10.255.0.12 (metric 30) from 10.255.0.21 (10.255.0.12)
      Received Label 23
      Origin IGP, metric 0, localpref 100, valid, internal, best, group-best, import-candidate, imported
      Extended community: RT:65000:101
      Originator: 10.255.0.12, Cluster list: 10.255.0.21
      Source AFI: VPNv4 Unicast, Source VRF: CUST-A, Source Route Distinguisher: 10.255.0.1:101
      Original Source AFI: VPNv4 Unicast, Original Source Route Distinguisher: 10.255.0.12:101
```

CUST-A のデフォルト ルートは、グローバル テーブルの INET を指しています。サイト 2 の公開セグメントは CUST-A からエクスポートされて
グローバルの BGP テーブルにあり、XR01 はそれを INET へ送ります。

スタティック ルートでも、1 つのプレフィックスについて同じことができます。`router static` → `vrf CUST-A` の中で、
`0.0.0.0/0 vrf default 192.0.2.2` のようなルートは、ネクスト ホップをグローバル テーブルに持ちます。BGP のリークと違い、VRF の BGP に
再配送しない限り、XR01 の CE にしか届きません。

### 5.2 パケットを追う

グローバル テーブルの中でも、サイト 2 のセグメントは VPN のネクスト ホップとラベルを持ったままです。INET から 198.51.100.129 へのパケットは、
XR01 で RT02 へのトランスポートのラベルと RT02 の VPN ラベルを付けられ、RT02 が CUST-A の中で届けます。

```console
RP/0/RP0/CPU0:XR01#show cef 198.51.100.128/25
198.51.100.128/25, version 61, internal 0x5000001 0x40 (ptr 0xf7974e8) [1], 0x600 (0xf92fd58), 0xa08 (0xf3357b8)
...
   via 10.255.0.12/32, 5 dependencies, recursive [flags 0x6000]
    path-idx 0 NHID 0x0 [0xedbdd90 0x0]
    recursion-via-/32
    next hop 10.255.0.12/32 via 24002/0/21
     next hop 10.0.1.11/32 GigabitEthernet0/0/0/0 labels imposed {16 23}

INET#traceroute 198.51.100.129 source Loopback10 numeric timeout 1 probe 1
  1 192.0.2.1 4 msec
  2 10.0.1.11 [MPLS: Labels 16/23 Exp 0] 2 msec
  3 172.16.12.1 [MPLS: Label 23 Exp 0] 1 msec
  4 172.16.12.2 2 msec
```

16 は RT02 のループバックに対する RT01 の LDP のラベルで、23 は 198.51.100.128/25 に対する RT02 の VPN ラベルです。RT02 が次のルータ
なので RT01 は上のラベルを外し、RT02(ホップ 3)は VPN ラベルだけを受け取ります。逆の方向、CEA2 から INET へは、RT02 がいちばん下に
XR01 の集約のラベル 24009 を付けてパケットを XR01 へ送ります。XR01 は CUST-A で宛先を引き、ネクスト ホップがグローバル テーブルにある
デフォルト ルートを見つけて、パケットを INET へ送ります。

```console
CEA2#traceroute 203.0.113.10 source Loopback11 numeric timeout 1 probe 1
  1 172.16.12.1 [AS 64500] 0 msec
  2 10.0.12.11 [AS 64500] [MPLS: Labels 22/24009 Exp 0] 2 msec
  3 10.0.1.1 [AS 64500] 3 msec
  4 192.0.2.2 [AS 64500] 2 msec
```

:::try
`advertise-as-vpn` を外してみます。課題 M9-4 の後に行います。

1. XR01 の `vrf CUST-A` → `address-family ipv4 unicast` の下で、`import from default-vrf` の行を `advertise-as-vpn` 無しで
   入れ直してコミットします。
2. XR01 で `show bgp vrf CUST-A 0.0.0.0/0` を、RT02 で `show ip route vrf CUST-A 0.0.0.0` を、CEA1 と CEA2 で
   `show ip route 0.0.0.0` を、CEA2 で `ping 203.0.113.10 source Loopback11` を実行します。
3. `advertise-as-vpn` を戻してコミットします。

ラボで測った結果: XR01 は、デフォルト ルートを自分の CE にだけアドバタイズしていると表示しました(`Advertised to CE peers` があり、
`PE peers` が無い)。RT02 と CEA2 からはそれが消え(`% Network not in table`)、CEA1 には残り、CEA2 からの ping は失敗しました。
キーワードを戻してから 1 分以内に、CEA2 は再びデフォルト ルートを持ち、ping は通りました。
:::

## 6. プロバイダーの間

VPN が 2 つのプロバイダーにまたがるとき、RFC 4364(10 節)は 3 つのつなぎ方を挙げています。

- **オプション A**: 2 つのプロバイダーの境界ルータ(ASBR)が PE と CE として向き合い、VPN ごとに 1 つの VRF と 1 つのインターフェイス
  またはサブインターフェイスを持ち、その間はただの IP です。簡単ですが、VPN の数だけ規模が増えます。
- **オプション B**: ASBR は eBGP で VPNv4 のルートをラベル付きで交換し、VRF を持ちません。IOS XR の ASBR には、VRF の無い
  VPNv4 のルートを保持するための `retain route-target all`(またはポリシー)、eBGP の VPNv4 のセッションのルート ポリシー、
  ラベル付きのトラフィックを転送するための相手の ASBR への /32 のスタティック ルートが必要です。
- **オプション C**: ASBR は PE のループバックだけを BGP ラベル付きユニキャスト(単元 M8 の Unified MPLS)で運び、2 つのプロバイダーの
  ルート リフレクタがマルチホップの eBGP で VPNv4 のルートを交換します。

**Carrier Supporting Carrier**(CSC、RFC 4364 の 9 節)では、VPN の顧客そのものがプロバイダーです。VPN は顧客のキャリアのループバック
だけをラベル付きで運び(CSC-CE に向けたラベル付きユニキャスト、または VRF の中の LDP)、顧客のキャリアはその上で自分の VPN を
動かします。

## 7. コマンドの対応

| IOS | IOS XR |
|---|---|
| `rd` と `route-target` を持つ `vrf definition <名前>` | `import route-target` / `export route-target` を持つ `vrf <名前>`。`rd` は `router bgp` → `vrf <名前>` の下 |
| `vrf forwarding <名前>`(アドレスを外す) | インターフェイスの下の `vrf <名前>` |
| `address-family vpnv4` + `neighbor … activate` | BGP の最上位とネイバーの下の `address-family vpnv4 unicast` |
| `address-family ipv4 vrf <名前>` | `router bgp` の下の `vrf <名前>` → `address-family ipv4 unicast` |
| `neighbor … as-override` | ネイバーのアドレス ファミリーの下の `as-override` |
| `route-target export` + `export map <route-map>` | `export route-target` + `export route-policy <名前>` |
| `bgp default route-target filter`(既定で有効) | 常に有効。`retain route-target` |
| `show ip bgp vpnv4 all` / `vrf <名前>` | `show bgp vpnv4 unicast` / `show bgp vrf <名前>` |
| `show ip route vrf <名前>` | `show route vrf <名前>` |

## 実践

ラボ **XRT-09** で M9 の課題に取り組みます。XR01 は IOS XRv 9000 なので、ラボの構築に約 10 分かかります。

<p class="tolab"><a href="/_learn?id=XRT-09">ワークスペースでラボ XRT-09 を開く</a> — <a href="91-m9-practice.html">課題</a></p>

:::note
出典: Cisco 8000(累積版、2026 年)と NCS 5500 の BGP のコマンド リファレンス(ルート識別子と `rd auto`、`retain route-target`、
`as-override`、`allowas-in`、`site-of-origin`、`label mode`、`export route-policy`)。ASR 9000 の Routing Configuration Guide、
IOS XR 24.x(2026 年。アドレス ファミリー、ルート リフレクタと `retain route-target`、新しい VRF のためのルート リフレッシュ、
`advertise-as-vpn` と `allow-imported-vpn` による VRF の動的なルートのリーク、VRF のインポートとエクスポートのルーティング ポリシー、
別の VRF へのスタティック ルート)。NCS 5500 と Cisco 8000 の L3VPN のコンフィギュレーション ガイドと ASR 9000 の MPLS L3VPN の
ガイド、リリース 7.11(インターフェイスの VRF、Inter-AS のオプション B、CSC)。Cisco 8000 のガイド「BGP Route Distinguisher」。
Cisco の TAC 文書「Cisco IOS-XR BGP with MPLS Designs」(2021 年)と「Configure Route Leak between GRT and VRF with IOS XR」。
IOS XRd のデータ シート。RFC 4364。いずれも 2026 年 10 月に確認。次の項目は、ラボ XRT-09 とその PoC での実測によるものです。
コミットのエラー、VRF の変更で残るインターフェイスのアドレス、捨てられたルートとそのカウンタ、ルート リフレッシュ、クライアントの無い
ルート リフレクタと `retain` のあるルート リフレクタ、送る前の AS パスの検査、ラベル、`additive` の無いときに置き換わるルート ターゲット、
ポリシーが通さないルートのエクスポート、リーク、PE としての XRd の転送。
:::
