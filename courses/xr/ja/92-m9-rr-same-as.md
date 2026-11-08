# M9 — ルート リフレクタと、同じ AS のサイト

このページは、VPN のルートを PE どうしで配る規模の問題と、同じ AS 番号を使う 2 つのサイトをつなぐときの問題を扱います。
課題 M9-2 で使います。前のページ「L3VPN の仕組み」の 2.4 節(VPNv4 と VPN のラベル)を先に読んでください。

## 1. 何が嬉しいのか

### 1.1 PE どうしのフル メッシュ

VPNv4 のルートは iBGP で配ります。iBGP のスピーカーは、iBGP で学んだルートを別の iBGP のネイバーへ送らないので、
ルート リフレクタが無ければ、すべての PE どうしにセッションが要ります。PE が N 台なら N(N−1)/2 本で、PE を 1 台足すたびに、
既存のすべての PE に設定を足すことになります。

**ルート リフレクタ**(RR)は、クライアントから受けたルートを、ほかのクライアントへ送り直します(反映)。PE は RR とだけ
セッションを張り、PE を足すときに触るのは、新しい PE と RR だけです。RFC 4364 も、PE の間をフル メッシュにする代わりに
ルート リフレクタを使うと規模に強くなる、と書いています(4.3.3 節)。

### 1.2 同じ AS 番号のサイト

顧客 A は、両方のサイトで AS 65101 を使っています。プライベートの AS 番号は限られていて、VPN の顧客がすべてのサイトに同じ
番号を使うのはよくあることです。ところが、BGP は AS パスに自分の AS 番号を見つけると、ループとみなしてルートを捨てます。
サイト 2 のルートは AS パス 65101 でサイト 1 に届くので、そのままでは CEA1 が受け入れません。

RFC 4364 は、こうしたサイトは同じ AS 番号を使ってよく、その番号は PE が取り除き、ループは Site of Origin の属性で防ぐ、と
書いています(7 節)。

### 1.3 答え

| 困りごと | 答え | 節 |
|---|---|---|
| PE どうしのセッションが PE の数の 2 乗で増える | ルート リフレクタ。PE は RR とだけ話す | 2.1〜2.3 |
| 同じ AS 番号のサイトが、互いのルートを受け入れない | PE が AS パスの顧客の番号を置き換える(as-override) | 2.4 |
| 置き換えると、ループを AS パスで見つけられない | ルートに出身のサイトの印を付ける(site-of-origin) | 2.5 |

## 2. 仕組み

### 2.1 VPNv4 のルート リフレクタは、すべてを持つ

PE は、自分のどの VRF も取り込まないルートを捨てます(前のページの 2.3 節)。ルート リフレクタは違います。自分には VRF が
無くても、すべての VPNv4 のルートを保持し、クライアントへ反映します。RFC 4364 は、ルート リフレクタと Inter-AS の境界ルータ
を除いて、PE は取り込む VRF の無いルートを入れるべきでない、と書き(4.3.2 節)、つながっていない VPN の経路を持つ必要が
あるのはルート リフレクタだけだ、とも書いています(4.3.3 節)。

4 つの課題を終えたラボの XR02 です。XR02 には VRF が 1 つもありませんが、2 台の PE のすべての RD のルートを持っています。

```console
RP/0/RP0/CPU0:XR02#show bgp vpnv4 unicast
...
   Network            Next Hop            Metric LocPrf Weight Path
Route Distinguisher: 10.255.0.1:101
*>i0.0.0.0/0          10.255.0.1                    100      0 64500 i
*>i10.101.1.0/24      10.255.0.1               0    100      0 65101 i
*>i198.51.100.0/25    10.255.0.1               0    100      0 65101 i
Route Distinguisher: 10.255.0.1:102
*>i10.102.1.0/24      10.255.0.1               0    100      0 65201 i
Route Distinguisher: 10.255.0.1:900
*>i10.99.1.0/24       10.255.0.1               0    100      0 ?
*>i10.99.2.0/24       10.255.0.1               0    100      0 ?
Route Distinguisher: 10.255.0.12:101
*>i10.101.2.0/24      10.255.0.12              0    100      0 65101 i
*>i198.51.100.128/25  10.255.0.12              0    100      0 65101 i
Route Distinguisher: 10.255.0.12:102
*>i10.102.2.0/24      10.255.0.12              0    100      0 65202 i
Processed 9 prefixes, 9 paths
```

10.99.2.0/24 は、どの顧客の VRF も取り込まない共有サービスの内部のルートです(ページ「共有サービスとインターネット」)。
XR02 は持っていますが、RT02 は持っていません。RT02 は PE なので、取り込む VRF の無いルートを捨てるからです。

```console
RT02#show ip bgp vpnv4 all
...
Route Distinguisher: 10.255.0.1:900
 *>i  10.99.1.0/24     10.255.0.1               0    100      0 ?
...
```

### 2.2 クライアントは、アドレス ファミリーごと

IOS XR は、クライアントを 1 つでも持てばルート リフレクタになり、既定ですべてのルートを保持します。クライアントは
ネイバーのアドレス ファミリーごとの性質で、`route-reflector-client` は `neighbor` → `address-family vpnv4 unicast` の下に
置きます。別のアドレス ファミリーの下に書いても、VPNv4 には何も効きません。

VRF も VPNv4 のクライアントも持たない iBGP スピーカーは、何も保持しません。その状態の XR02 は、送られたルートを 1 つも
受け入れず、拒否としても数えませんでした。

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

上の出力は、ルート リフレクタの行も `retain` も無い XR02 に、XR01 が 2 つのルートを送っている間のものです。XR02 がルート
リフレクタになると、`show bgp vpnv4 unicast neighbors` は、設定のあるアドレス ファミリーごとの部分に `Route-Reflector Client` を
表示します。VPNv4 の部分にあるものを見てください。

`address-family vpnv4 unicast` の下の `retain route-target all` は、どの VRF もインポートしない VPNv4 のルートをルータに保持させます。
XR02 はそれですべてのルートを持ちましたが、やはり 1 つも渡しませんでした。iBGP スピーカーは iBGP のルートを別の iBGP ネイバーへ
送らず、それを変えるのはクライアントだけです。

このコマンドは、VRF を持たないルートを保持しなければならない Inter-AS のオプション B の
境界ルータ(付録 2 節)のためのものです。`route-policy` の形を使うと、ルート リフレクタが一部のルート ターゲットだけを保持し、VPN を
複数のリフレクタに分けられます。

### 2.3 ルート リフレクタは道の外

XR02 は、ルートを反映するとき、ネクスト ホップを変えません。XR01 が受け取ったサイト 2 のルートは、XR02 から届いても
ネクスト ホップは RT02 のループバックのままで、`Originator` が出どころの PE、`Cluster list` が通ったリフレクタを示します
(前のページの 2.4 節)。そのため、顧客のパケットは PE から PE へ直接流れ、XR02 を通りません。前のページの traceroute にも
XR02 は出てきませんでした。

XR02 は顧客のパケットを運ばないので、ラベルも要りません。RR-LINK には LDP が無く、XR02 のラベルの表は空です。VPN の
ルートを BGP の表に持つだけで、自分のルーティング テーブルには入れません。

```console
RP/0/RP0/CPU0:XR02#show mpls forwarding
RP/0/RP0/CPU0:XR02#show route 10.101.1.0/24
% Network not in table
```

ルート リフレクタを道の外に置くことは、章 C0 の「RR は道の外に置く」で、P ルータに兼ねさせない形として見ました。この
ラボの XR02 も、RT03 の先の行き止まりにあります。

XR02 は IOS XRd で動いています。Cisco は XRd を、ルート リフレクタなど転送パスの外の役割向けに、制御プレーンの形で提供しています。

このラボの XR01 には向きません。XR01 を XRd にしたときは、ping は両方向に通りましたが、XRd が CE から受けてラベルを付けて送った
TCP と UDP のパケット、2 つの VRF の間や VRF とグローバル テーブルの間でルーティングしたパケットは、チェックサムが壊れて届きました。
CEA1 からの traceroute は最初の数ホップの先で止まりました。XRd がラベル付きで受けて CE へ送ったパケットは無傷でした。
IOS XRv 9000 は、これらをすべて正しく転送しました。

### 2.4 AS パスの検査と、AS のオーバーライド

サイト 2 のルートは AS パス 65101 で XR01 に届き、CEA1 はそれをループとして捨てるはずです。IOS XR の PE は、受け取る側が
捨てるのを待たず、そもそも送りません。送る前に、AS パスと相手の AS を照らし合わせます。

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
パスに 65101 を含まないルートは出ていきます。上の出力は、課題 M9-4 の後に `as-override` を外した状態です。

CE のネイバーのアドレス ファミリーの下の `as-override` は、パスの中の顧客の AS をプロバイダーの AS に置き換え、ルートは
`65000 65000` で出ていきます。CEA1 の BGP の表では、サイト 2 のルートがそう見えます。

```console
CEA1#show ip bgp
...
     Network          Next Hop            Metric LocPrf Weight Path
 *>   10.101.1.0/24    0.0.0.0                  0         32768 i
 *>   10.101.2.0/24    172.16.11.1                            0 65000 65000 i
...
```

代わりの `allowas-in` は受け取る側のルータ、つまり CE で設定するもので、CE は顧客のものです。プロバイダーが自分の PE で
片付けられるのが `as-override` です。

### 2.5 サイトの印: site-of-origin

AS を置き換えると、AS パスでループを見つけることはできなくなります。サイトが 1 台の PE にだけつながっていれば問題は
ありませんが、1 つのサイトを 2 台の PE につなぐと、サイトから出たルートが、もう一方の PE を通って同じサイトへ戻れて
しまいます。

**site-of-origin**(SoO)は、ルートに「どのサイトから来たか」の印を拡張コミュニティで付けます。PE は、CE から受けた
ルートにそのネイバーの SoO を付け、同じ SoO を持つネイバーへは、その印の付いたルートを送りません。RFC 4364 は、Site of
Origin の属性が示すサイトの CE へ、そのルートを配ってはならない、と書いています(8 節)。

XR01 の CEA1 のネイバーに SoO 65101:1 を付けると、RT02 が受け取ったサイト 1 のルートに印が付きました。

```console
RT02#show ip bgp vpnv4 vrf CUST-A 10.101.1.0
BGP routing table entry for 10.255.0.12:101:10.101.1.0/24, version 20
Paths: (1 available, best #1, table CUST-A)
  Advertised to update-groups:
     1
  Refresh Epoch 1
  65101, imported path from 10.255.0.1:101:10.101.1.0/24 (global)
    10.255.0.1 (metric 20) (via default) from 10.255.0.21 (10.255.0.21)
      Origin IGP, metric 0, localpref 100, valid, internal, best
      Extended Community: SoO:65101:1 RT:65000:101
      Originator: 10.255.0.1, Cluster list: 10.255.0.21
      mpls labels in/out nolabel/24004
```

次に、RT02 の CEA2 のネイバーにも同じ 65101:1 を付けました。CEA2 を、サイト 1 と同じサイトにある CE とみなしたことに
なります。RT02 は、サイト 1 のルートを CEA2 に送らなくなりました。

```console
RT02#show ip bgp vpnv4 vrf CUST-A 10.101.1.0
...
  Not advertised to any peer
...
      Extended Community: SoO:65101:1 RT:65000:101
RT02#show ip bgp vpnv4 vrf CUST-A neighbors 172.16.12.2 advertised-routes
...
Route Distinguisher: 10.255.0.12:101 (default for vrf CUST-A)
 *>i  0.0.0.0          10.255.0.1                    100      0 64500 i
 *>i  10.99.1.0/24     10.255.0.1               0    100      0 ?
Total number of prefixes 2
```

ラボのサイトは、どちらも 1 台の PE にだけつながっているので、ふつうは SoO を付けても何も変わりません。同じ値を 2 つの
サイトに付けたのは、印が効くところを見るためです(RT02 の据え付けの設定に SoO はありません)。

## 3. IOS XR で組む

### 3.1 ルート リフレクタ

XR02 を、2 台の PE の VPNv4 のルート リフレクタにする設定です。

:::config fold XR02 — 2 台の PE の VPNv4 のルート リフレクタ
router bgp 65000
 bgp router-id 10.255.0.21
 address-family vpnv4 unicast                ## 最上位の VPNv4。retain は要らない(RR は既定ですべてを持つ)
 !
 neighbor 10.255.0.1                         ## PE の XR01
  remote-as 65000
  update-source Loopback0
  address-family vpnv4 unicast
   route-reflector-client                    ## クライアントは VPNv4 のアドレス ファミリーの下に書く
  !
 !
 neighbor 10.255.0.12                        ## PE の RT02
  remote-as 65000
  update-source Loopback0
  address-family vpnv4 unicast
   route-reflector-client
  !
 !
!
:::

PE の側は、ルート リフレクタだけをネイバーに持ちます(前のページの 3.1 節の XR01 と RT02)。PE の側にクライアントの設定は
要りません。

### 3.2 AS のオーバーライド

XR01 の、CEA1 のネイバーの設定です。

:::config fold XR01 — 同じ AS 番号のサイトへ、AS を置き換えて送る
router bgp 65000
 vrf CUST-A
  neighbor 172.16.11.2
   address-family ipv4 unicast
    as-override                              ## パスの中の 65101 を 65000 に置き換えて CEA1 へ送る
   !
  !
 !
!
:::

:::try
オーバーライドを外してみます。課題 M9-2 の後に行います。

1. XR01 で、CUST-A のネイバー 172.16.11.2 から `as-override` を外してコミットします。
2. XR01 で `show bgp vrf CUST-A 10.101.2.0/24` と
   `show bgp vrf CUST-A neighbors 172.16.11.2 advertised-routes` を、CEA1 で `show ip bgp` を実行します。
3. `as-override` を戻してコミットします。

結果の例: 20 秒以内に、XR01 はサイト 2 のルートに `Not advertised to any peer` を表示し、それらは `advertised-routes` から
消え、CEA1 からも無くなりました。XR01 は、パスに 65101 を含んだまま送るのではなく、取り消したのです。行を戻すと、CEA1 は再び
`65000 65000` でそれらを持ちました。
:::

### 3.3 site-of-origin

SoO は、CE のネイバーのアドレス ファミリーの下に、サイトごとの値で書きます。2 台の PE につながる 1 つのサイトには、両方の
PE で同じ値を付けます。

:::config XR01 — CEA1 のルートにサイトの印を付ける
router bgp 65000
 vrf CUST-A
  neighbor 172.16.11.2
   address-family ipv4 unicast
    site-of-origin 65101:1                   ## CEA1 から受けたルートに付け、この印のルートは CEA1 へ送らない
   !
  !
 !
!
:::

:::config RT02(IOS XE)— 同じことを IOS XE で
router bgp 65000
 address-family ipv4 vrf CUST-A
  neighbor 172.16.12.2 soo 65101:1           ## IOS XE ではネイバーの行に soo
 exit-address-family
!
:::

## 実践

ラボ **XRT-09** で課題 M9-2 に取り組みます。課題 M9-1 を終えた状態から始めます。

<p class="tolab"><a href="/_learn?id=XRT-09">ワークスペースでラボ XRT-09 を開く</a> — <a href="93-m9-practice-2.html">課題 M9-2</a></p>

:::note
出典は単元の各ページと同じです(ページ「L3VPN の仕組み」の末尾)。このページの論点は、RFC 4364 の 4.3.2 節・4.3.3 節・7 節・8 節、
Cisco 8000 と NCS 5500 の BGP のコマンド リファレンス(`retain route-target`、`as-override`、`allowas-in`、`site-of-origin`)、
ASR 9000 の Routing Configuration Guide(IOS XR 24.x。ルート リフレクタと `retain route-target`)、TAC 文書「Cisco IOS-XR BGP with
MPLS Designs」、IOS XRd のデータ シートによります。次の項目は、ラボ XRT-09 とその PoC での実測によるものです。クライアントの無い
ルート リフレクタと `retain` のあるルート リフレクタ、送る前の AS パスの検査、SoO の印とその効き目、PE としての XRd の転送。
:::
