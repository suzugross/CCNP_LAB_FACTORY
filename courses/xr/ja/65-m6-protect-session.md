# M6 追補 — セッションを守る: GTSM と TCP-AO

前のページでは、予備の道を前もって配りました。このページは、外の AS との BGP のセッションそのものを守る 2 つを扱います。
GTSM(TTL セキュリティ)は、届いたパケットの TTL から、遠くで作られたものを見分けて捨てます。TCP-AO は、TCP のセグメントごとに
鍵から計算した MAC を付け、受け手がそれを確かめます。前からある MD5 認証も並べて扱います。

ブループリントの 1.5.b(BGP の TTL セキュリティとプロトコル認証)にあたり、ラボ XRT-17 の課題 M6-7 と M6-8 で使います。
追加パスと PIC は「予備の道を配る」のページ、経路数の上限・ダンプニング・集約は「受け取りすぎない」のページで扱います。

## 1. 何が嬉しいのか

### 1.1 困りごと: 外とのセッションは、外から叩ける

AS 65000 は、外の AS と 3 本の eBGP のセッションを張っています。PE1 と顧客の CE1、PE2 と X1、PE3 と X2 です。どれも
直接つながった線の両端のアドレスの間で、TCP の 179 番を使います。図の括弧は、このページの設定例を置くセッションです。
課題(M6-7、M6-8)では、GTSM を PE2–X1 に、TCP-AO を PE3–X2 に入れます。

:::topo
nodes:
  CE1: {at: [0, 1], label: "CE1 (AS 65001)"}
  PE1: {at: [2.2, 1], label: "PE1"}
  P1: {at: [4.2, 1], label: "P1"}
  RR1: {at: [4.2, 2.5], label: "RR1"}
  PE2: {at: [6.2, 0], label: "PE2"}
  PE3: {at: [6.2, 2], label: "PE3"}
  X1: {at: [8.4, 0], label: "X1"}
  X2: {at: [8.4, 2], label: "X2"}
  T: {at: [10.1, 1], kind: host, label: "T 203.0.113.1"}
links:
  - {a: CE1, b: PE1, label: "172.16.1.0/24\n(3.2 節 MD5 認証)"}
  - {a: PE1, b: P1}
  - {a: P1, b: PE2}
  - {a: P1, b: PE3}
  - {a: P1, b: RR1}
  - {a: PE2, b: X1, label: "172.16.2.0/24\n(3.3 節 TCP-AO)"}
  - {a: PE3, b: X2, label: "172.16.3.0/24\n(3.1 節 GTSM)"}
  - {a: X1, b: T}
  - {a: X2, b: T}
  - {a: X1, b: X2}
frames:
  - {label: "AS 65000", nodes: [PE1, P1, RR1, PE2, PE3]}
  - {label: "AS 65100", nodes: [X1, X2, T]}
:::

BGP は TCP の上で動くので、セッションに効くパケットを作るのに、BGP を話せる必要はありません。PE3 にとっては、172.16.3.1 から
自分の 179 番へ届いた TCP のセグメントが、X2 からのセグメントです。送信元のアドレスは送る側が書き込む値で、X2 の向こうにいる
T からでも、PE3 の 172.16.3.254 へパケットは届きます。

起こりうることは 2 つです。偽のセグメント(TCP のリセットなど)を受け入れて、セッションが切れること。大量のセグメントを
受けて、BGP を受け持つ CPU が忙しくなることです。M6 の設定には、届いたセグメントが本当に X2 から来たかを確かめる手が
ありません。アドレスが合えば、それが X2 です。

### 1.2 それ以前の手: ACL と MD5

1 つめの手は、アドレスで絞ることです。インフラ ACL(M12)は、プロバイダーのネットワークの入口で、基盤宛てのパケットのうち、
相手との BGP のような必要なものだけを通します。IOS XR の LPTS(M2)は、設定済みのピアからの BGP を別のフローに分け、
それ以外からの BGP 宛てのパケットを少ない枠に絞ります。

どちらも、判断に使うのはパケットのアドレスとポートです。172.16.3.1 を送信元に書いたパケットは、本物の X2 のパケットと
区別が付きません。偽るのに要るのは、アドレスを 1 つ書くことだけです。

2 つめの手は MD5 認証(RFC 2385)です。両端に同じパスワードを設定し、TCP のセグメントごとに、パスワードを混ぜて計算した
MD5 のダイジェストを付けます。パスワードを知らない者が作ったセグメントは、ダイジェストが合わずに捨てられます。IOS XR と
IOS XE の間でもつながります(3.2 節)。

弱いところもあります。MD5 認証を置き換えるために書かれた RFC 5925(TCP-AO)は、より強い MAC を使うこと、長く続く
セッションでもリプレイを防ぐこと、鍵の ID を持ち、セグメントを落とさずに鍵を替えられることを挙げています。MD5 認証には
鍵の ID が無く、鍵を替える間は、途中のセグメントを落とすか、届いたセグメントを複数の鍵で試すことになります。

それに、偽のセグメントも、捨てる前に 1 つずつダイジェストを計算されます。確かめるには、まず計算します。

### 1.3 答え: 距離を TTL で確かめ、セグメントに署名する

- **GTSM で、距離を確かめる**: 両端が TTL 255 で送り、受け手は、決めた値より小さい TTL で届いたものを捨てます。直接
  つながった相手のパケットは 255 のまま届き、線の向こうで作ったパケットは 255 では届きません。見るのは IP ヘッダーの
  TTL だけで、鍵の計算は要りません。
- **TCP-AO で、セグメントに署名する**: MD5 認証の後継です(RFC 5925)。キー チェーンの鍵と AES-128-CMAC-96 などの
  アルゴリズムで MAC を計算し、KeyID で、受け手にどの鍵を使ったかを伝えます。

2 つは役割が違います。RFC 5082 は、GTSM を CPU を狙う攻撃への簡単な守りとし、認証の代わりにはならないと書いています。
同じ線の上で偽られたパケットやリプレイは、TTL では止まりません。どれも両端に設定します。GTSM と MD5 認証は片側だけでは
セッションが確立せず、TCP-AO は両端の鍵の ID がそろわないと確立しません(2.1 節、3.2 節、3.4 節)。

## 2. 仕組み

2.1 節は、PE3 に届く 1 つのパケットの TTL を追います。2.2 節と 2.3 節は、1 つの TCP のセグメントが、ダイジェストや MAC を
付けて送られ、受け手で確かめられるまでです。

### 2.1 TTL で隣を確かめる: GTSM

IP パケットの TTL は、ルータが転送するたびに 1 つ減り、0 になったパケットは捨てられます。宛先のルータは転送しないので、
自分宛てのパケットの TTL は減らしません。届いた TTL を見れば、途中でいくつのルータを通ってきたかが分かります。送った時の
値が分かっていれば、の話です。

eBGP のパケットは、ふだん TTL 1 で送られます。直接つながった相手には届き、その先へは転送されない値です。受け手は、届いた
TTL を確かめません。GTSM を使っていない CE1 の表示では、`Outgoing TTL 1` と `Mininum incoming TTL 0` です(抜粋。
綴りは表示のまま)。

```console
CE1#show ip bgp neighbors 172.16.1.254
...
Connection is ECN Disabled, Mininum incoming TTL 0, Outgoing TTL 1
```

TTL 1 は、パケットが行き過ぎないための値です。遠くで作られた偽のパケットも、届いた時に TTL が残っていれば、本物と同じ
ように受け取られます。行き先を限る値で、出どころを確かめる値ではありません。

GTSM(RFC 5082)は、向きを逆にします。両端が TTL 255 で送ります。直接つながった相手のパケットは、間にルータが無いので
255 のまま届きます。1 台向こうから来たパケットは、そのルータで 1 減って 254 で届きます。255 は TTL の最大の値なので、
線の向こうで作ったパケットは 255 では届きません。受け手は、その相手からのパケットのうち、TTL 255 のものだけを受け付けます。

:::topo
nodes:
  T: {at: [0, 0], kind: host, label: "T (X2 の向こう)"}
  X2: {at: [3, 0], label: "X2 (直接接続の相手)"}
  PE3: {at: [6, 0], label: "PE3 (ttl-security)"}
links:
  - {a: T, b: X2, label: "T が TTL 255 で送る"}
  - {a: X2, b: PE3, label: "X2 が送ったもの: 255 → 受け付ける\nT が送ったもの: 254 → 捨てる"}
:::

RFC 5082 は、両端が GTSM を使うことを前提にしています。ループバックの間のような何ホップか離れた相手については、規定では
ない付録で、255 から決めた数の範囲(たとえば 254 か 255)を受け付ける形を挙げています。

IOS XR と IOS XE は、同じ考えを別の形で書きます。IOS XR のネイバーの `ttl-security` は hop の数を取らず、TTL 255 で送り、
255 だけを受け付けます。`?` の一覧にも、数の引数はありません。

```console
RP/0/RP0/CPU0:PE1(config-bgp-nbr)#ttl-security ?
  disable              (Deprecated from 7.4.1) Replaced by inheritance-disable
  inheritance-disable  Prevent ttl-security from being inherited from the parent
  <cr>
```

IOS XE の `neighbor <アドレス> ttl-security hops <1-254>` は、255 から hops を引いた値以上を受け付けます。`hops 1` なら
254 以上で、X2 は `Mininum incoming TTL 254, Outgoing TTL 255` と表示します(3.4 節)。IOS XE で書けるいちばん厳しい値ですが、
254 も通すので、相手の向こうにもう 1 台ルータを挟んだ所から来たパケットも、TTL の確かめは通ります。

送る TTL について、IOS XE 17.x のガイドは、`ttl-security hops` が守るのは入る向きだけで、出ていくパケットには効かないと
書いています。IOS XE 17.15 は、RFC 5082 のとおり 255 で送ります。パケット キャプチャでも、設定の前に 1 だった TTL が、
設定の後は 255 でした(付録の 6.1 節)。

片側だけに設定すると、TCP の接続ができません。PE3 だけに `ttl-security` を入れて張り直すと、X2 は TTL 1 で送り続け、
PE3 はそれを捨てます。PE3 が TTL 255 で送った SYN には X2 が TTL 1 で答え、その答えも PE3 で捨てられます。PE3 は `Active`、
X2 は `Idle` のままです(抜粋。設定は 3.1 節)。

```console
RP/0/RP0/CPU0:PE3#show bgp summary
...
Neighbor        Spk    AS MsgRcvd MsgSent       TblVer  InQ OutQ  Up/Down  St/PfxRcd
10.255.0.21       0 65000     277     227          330    0    0 00:14:30          4
172.16.3.1        0 65100     105     166            0    0    0 00:00:41  Active
X2#show ip bgp neighbors 172.16.3.254
BGP neighbor is 172.16.3.254,  remote AS 65000, external link
  BGP version 4, remote router ID 0.0.0.0
  BGP state = Idle, down for 00:02:29
...
  Last reset 00:02:29, due to Active open failed
...
  No active TCP connection
```

片方は 255 しか受け取らず、もう片方は 1 でしか送らないので、TCP の 3 ウェイ ハンドシェイクが終わりません。ASR 9000 の
Routing Command Reference は、片側だけの時、セッションは OpenSent か OpenConfirm まで進み、ホールド タイムで落ちると
書いていますが、この盤面では TCP の手前で止まりました(付録の 6.1 節)。

IOS XR の `ttl-security` が守るのは eBGP のセッションで、Command Reference は、iBGP のネイバーには使えないとしています。

### 2.2 TCP のセグメントに署名する: MD5 と TCP-AO

MD5 認証(RFC 2385)では、送り手がセグメントごとに、16 バイトの MD5 のダイジェストを TCP のオプションとして付けます。
計算に使うのは、TCP の疑似ヘッダー(送信元と宛先のアドレスなど)、オプションを除いた TCP ヘッダー、データ、両端で決めた
パスワードです。

受け手は、自分のパスワードで同じ計算をして、届いたダイジェストと比べます。合わないセグメントは、相手に何も返さずに
捨てます。使うかどうかを両端で交渉する仕組みはありません。片側だけに設定すると、設定した側はダイジェストの無い
セグメントを捨て、セッションは確立しません(3.2 節)。

TCP-AO(RFC 5925)は、MD5 認証を置き換える TCP のオプションです。セグメントごとに付けるのは、KeyID、RNextKeyID、MAC の
3 つです。KeyID は MAC の計算に使った鍵の番号、RNextKeyID は、送り手が次に受けたい鍵の番号です。この 2 つで、鍵を替える
時にどの鍵を使うかを両端が示し合い、セグメントを落とさずに替えられます。

MAC の計算には、キー文字列をそのまま使いません。キー文字列(RFC の言い方では master key)と、接続の両端のアドレスと
ポート、両側の初期シーケンス番号から、接続ごとの鍵(traffic key)を作って使います。同じキー文字列でも接続が替われば鍵も
替わるので、前の接続のセグメントを今の接続へ持ち込んでも通りません。IOS XR で使えるアルゴリズムは HMAC-SHA-1-96 と
AES-128-CMAC-96 です。

MAC に TCP のほかのオプションを含めるかどうかも、RFC 5925 では鍵ごとの取り決めです。IOS XR と IOS XE は、ネイバーの `ao` の
行で決めます(include-tcp-options)。両端で計算の範囲が違えば MAC は合わないので、そろえます。RFC 5925 は、TCP-AO と MD5 認証を 1 つの接続で同時に使うことを認めていません。

IOS XR のネイバーには、方式が 3 つあります。`password` は RFC 2385 の MD5 認証で、IOS XE の `neighbor … password` と
つながります。`keychain` はキー チェーンを使う別の方式で、Cisco の文書は draft-bonica-tcp-auth-05 に従うものとし、片側が
`keychain`、もう片側が `password` ではつながらないと書いています。

`ao` が TCP-AO です。1 つのネイバーに使えるのは 1 つだけで、2 つ目はコミットで拒まれます(3.4 節)。

PE2 の `keychain`(アルゴリズムは HMAC-MD5)と X1 の `password` に同じ文字列を書いても、セッションは確立しませんでした。
X1 のログには次の行が出ます(抜粋)。

```console
*Nov 21 08:57:13.944: %TCP-6-BADAUTH: No MD5 digest from 172.16.2.254(25975) to 172.16.2.1(179) tableid - 0
*Nov 21 08:57:21.944: %TCP-6-BADAUTH: No MD5 digest from 172.16.2.254(25975) to 172.16.2.1(179) tableid - 0
```

PE2 のセグメントには、RFC 2385 のダイジェストが付いていません。同じ文字列を両側に書いても、方式が違えば、合うダイジェストは
届きません。

### 2.3 TCP-AO の鍵: キー チェーン、KeyID、SendID と ReceiveID

RFC 5925 では、TCP-AO の鍵ごとに ID が 2 つあります。SendID は、送るセグメントの KeyID フィールドに入れる値です。
ReceiveID(RFC の言い方では RecvID)は、届いたセグメントの KeyID と照らし合わせる値です。どちらも 0〜255 です。

自分が送るセグメントの KeyID は、相手が照らし合わせる値なので、自分の SendID は相手の ReceiveID と同じにします。逆も同じ
です。3.3 節の例では、PE2 が SendID 12・ReceiveID 21、X1 が send-id 21・recv-id 12 で、組は交差します。自分の送る番号は、
相手の受ける番号です。

:::topo
nodes:
  PE2: {at: [0, 0], label: "PE2  SendID 12 / ReceiveID 21"}
  X1: {at: [4.5, 0], label: "X1  send-id 21 / recv-id 12"}
links:
  - {a: PE2, b: X1, label: "PE2 → X1: KeyID 12\nX1 → PE2: KeyID 21"}
:::

鍵そのものは、キー チェーンに置きます。キー チェーンは鍵の名前付きの一覧で、鍵ごとに番号、キー文字列、アルゴリズム、
送る期間(send-lifetime)と受け付ける期間(accept-lifetime)を持ちます。NCS 5500 の BGP のガイドは、TCP-AO では 2 つの期間を
同じ値にするよう求めています。このページの例も課題も、鍵は 1 本で、期間は無期限(`infinite`)です。

IOS XR では、TCP-AO を 3 か所で組みます。

- キー チェーン(`key chain <名前>` → `key <番号>`): キー文字列、アルゴリズム、2 つの期間。
- `tcp ao` → `keychain <名前>` → `key <番号> SendID <n> ReceiveID <n>`: その鍵の 2 つの ID。
- BGP のネイバーの `ao <名前> include-tcp-options enable`: このセッションにどのキー チェーンを使うか、TCP のオプションを
  MAC に含めるか。

キー チェーンと `tcp ao` は、鍵の番号(例では key 3)で結び付きます。セグメントの KeyID フィールドに入るのは、この番号では
なく SendID です。例の PE2 と X1 は、どちらも鍵の番号を 3 にしています。

IOS XE では、キー チェーンそのものを TCP 用にします(`key chain <名前> tcp`)。鍵の下に `send-id`、`recv-id`、`key-string`、
`cryptographic-algorithm` が並び、ID もキー チェーンの中にあります。

キー文字列は 16 進で 32 桁か 64 桁です。IOS XE のガイドは、IOS XE の `aes-128-cmac` が IOS XR の `AES-128-CMAC-96` と
つながると書いています。ネイバーには `neighbor <アドレス> ao <名前> include-tcp-options` です。

ID が交差していないと、セッションは確立しません。X1 も send-id 12・recv-id 21 にすると、PE2 は X1 からのセグメントを
受け付けず、`%IP-TCP-3-BADAUTH : Invalid AO digest …` を記録します(3.4 節)。キー文字列とアルゴリズムが合っていても、です。

## 3. IOS XR での設定

設定例は、課題とは別のセッションと値で書いています。GTSM は PE3–X2(3.1 節)、MD5 認証は PE1–CE1(3.2 節)、TCP-AO は
PE2–X1(3.3 節)です。どの例も、IOS XR の設定の後に、相手の IOS XE の設定を並べます。

### 3.1 GTSM の設定例

IOS XR はネイバーの下の 1 行、IOS XE は `router bgp` の下の 1 行で、IOS XE だけが hop の数を書きます。設定を足しても、張られて
いるセッションは張り直すまでそのままです(Command Reference も、`clear bgp` で張り直すよう書いています)。片側ずつ入れると、
2 台目を入れるまでセッションは落ちたままです(2.1 節)。

:::config PE3 — X2 とのセッションで、TTL 255 で届いたものだけを受け付ける
router bgp 65000
 neighbor 172.16.3.1                          ## X2
  ttl-security                                ## TTL 255 で送り、255 だけを受け付ける。hop の数は取らない
 !
!
:::

:::config X2(IOS XE)— PE3 とのセッションで、TTL 254 以上だけを受け付ける
router bgp 65100
 neighbor 172.16.3.254 ttl-security hops 1    ## 255 − 1 = 254 以上を受け付け、TTL 255 で送る
:::

PE3 にコミットして張り直した後(2.1 節の状態)、X2 にも設定して、X2 の側で張り直しました。PE3 は X2 から 2 本の経路を
受けています(抜粋)。

```console
RP/0/RP0/CPU0:PE3#clear bgp 172.16.3.1
X2#clear ip bgp 172.16.3.254
RP/0/RP0/CPU0:PE3#show bgp summary
...
Neighbor        Spk    AS MsgRcvd MsgSent       TblVer  InQ OutQ  Up/Down  St/PfxRcd
10.255.0.21       0 65000     282     231          334    0    0 00:15:18          4
172.16.3.1        0 65100     113     170          334    0    0 00:00:37          2
```

### 3.2 MD5 の設定例

IOS XR はネイバーの `password`、IOS XE は `neighbor … password` で、両側に同じ文字列を書きます。IOS XR の `clear` は、
平文で入力するという意味です。running-config には `encrypted` の形で残ります。

:::config PE1 — CE1 とのセッションの TCP のセグメントに、MD5 のダイジェストを付ける
router bgp 65000
 neighbor 172.16.1.1                          ## CE1
  password clear CUST-65001                   ## clear= 平文で入力する。running-config には encrypted の形で残る
 !
!
:::

:::config CE1(IOS XE)— 同じパスワードを使う
router bgp 65001
 neighbor 172.16.1.254 password CUST-65001    ## PE1 と同じ文字列
:::

PE1 にだけ入れて張り直すと、PE1 も CE1 も `Active` のままでした。パスワードを持たない CE1 のログには、何も出ません
(抜粋)。

```console
RP/0/RP0/CPU0:PE1#clear bgp 172.16.1.1
RP/0/RP0/CPU0:PE1#show bgp summary
...
Neighbor        Spk    AS MsgRcvd MsgSent       TblVer  InQ OutQ  Up/Down  St/PfxRcd
10.255.0.21       0 65000     352     119          393    0    0 00:16:12          2
172.16.1.1        0 65001     152     210            0    0    0 00:00:36  Active
CE1#show ip bgp summary
...
Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
172.16.1.254    4        65000       0       0        1    0    0 00:00:38 Active
CE1#show logging | include BADAUTH|TCP-6
CE1#
```

CE1 にも入れて、CE1 の側で張り直すと確立しました(抜粋)。

```console
CE1#clear ip bgp 172.16.1.254
RP/0/RP0/CPU0:PE1#show bgp summary
...
Neighbor        Spk    AS MsgRcvd MsgSent       TblVer  InQ OutQ  Up/Down  St/PfxRcd
10.255.0.21       0 65000     352     120          395    0    0 00:16:59          2
172.16.1.1        0 65001     157     215          395    0    0 00:00:30          2
RP/0/RP0/CPU0:PE1#show running-config router bgp 65000 neighbor 172.16.1.1
router bgp 65000
 neighbor 172.16.1.1
  remote-as 65001
  password encrypted 1434273838497C7E747862
  address-family ipv4 unicast
   route-policy PASS in
   route-policy PASS out
  !
 !
!
```

### 3.3 TCP-AO の設定例

IOS XR の設定は 3 つの塊で、キー チェーンの名前(UPLINK-AO)と鍵の番号(3)で互いを参照します。相手の X1(IOS XE)は 2 つの
塊です。図は、X1 から PE2 へ 1 つのセグメントが送られ、PE2 が確かめて答えるまでです。図の番号は、下の設定例の注記の番号と
同じです。図の番号にカーソルを置くと(スマホでは押すと)、その部分の設定が出ます。

:::walk
legend: "X1 から PE2 への TCP のセグメントと、PE2 の答え。橙の小箱: TCP-AO のオプション。青い番号: 設定の塊。"
rows:
  - panel: X1
    sub: IOS XE(送り手)
    items:
      - ref: 5
        head: "**ネイバー** `neighbor 172.16.2.254 ao UPLINK-AO include-tcp-options`"
        say: ["PE2 とのセッションのセグメントに TCP-AO を付ける。TCP のオプションも MAC に含める"]
      - ref: 4
        head: "**TCP 用のキー チェーン** `key chain UPLINK-AO tcp` → `key 3`"
        say: ["KeyID に send-id の 21 を入れる", "キー文字列と aes-128-cmac で MAC を計算する"]
  - wire:
      - "[[IP  → 172.16.2.254]] [[TCP  → 179]] [[!TCP-AO  KeyID 21  MAC]]"
      - "_X1 → PE2"
  - panel: PE2
    sub: IOS XR(受け手)
    items:
      - ref: 3
        head: "**BGP のネイバー** `ao UPLINK-AO include-tcp-options enable`"
        say: ["172.16.2.1 とのセッションのセグメントは、UPLINK-AO で確かめる"]
      - ref: 2
        head: "**TCP-AO の鍵の ID** `tcp ao` → `keychain UPLINK-AO`"
        say: ["届いた KeyID 21 を、鍵の ReceiveID と照らし合わせる"]
        match:
          - ["key 3 SendID 12 ReceiveID 21", true, "当たる → 鍵 3"]
      - ref: 1
        head: "**キー チェーン** `key chain UPLINK-AO` → `key 3`"
        say: ["同じキー文字列と AES-128-CMAC-96 で MAC を計算し直し、届いた MAC と比べる", "+合う → TCP へ渡す"]
  - wire:
      - "[[IP  → 172.16.2.1]] [[TCP  179 →]] [[!TCP-AO  KeyID 12  MAC]]"
      - "_PE2 の答え。KeyID は SendID の 12"
  - {node: X1, say: ["~recv-id 12 の鍵 3 で確かめる"]}
  - aside: "ID を交差させないと(X1 も send-id 12・recv-id 21)"
    say: ["~X1 のセグメントの KeyID は 12 → PE2 の ReceiveID 21 に当たらない", "~PE2 は `%IP-TCP-3-BADAUTH : Invalid AO digest …` を記録して捨てる。PE2 は `Active` のまま"]
  - aside: "③ を足した後に PE2 で張り直さないと"
    say: ["~X1 は設定の変更でセッションを閉じるが、PE2 は前からのセッションを `Established` のまま持つ", "~PE2 で `clear bgp 172.16.2.1`"]
:::

PE2 には、キー チェーン、`tcp ao`、ネイバーの `ao` の 3 つを入れます。キー チェーンと `tcp ao` は、`router bgp` の外の
グローバルの設定です。

:::config PE2 — X1 とのセッションのセグメントに、AES-128-CMAC-96 の MAC を付けて確かめる
key chain UPLINK-AO                           ## ① 鍵の一覧。tcp ao とネイバーから、この名前で参照する
 key 3                                        ## ① 鍵の番号。② の key 3 と結ぶ
  key-string clear 0F1E2D3C4B5A69788796A5B4C3D2E1F0   ## ① キー文字列。IOS XE に合わせて 16 進 32 桁
  cryptographic-algorithm AES-128-CMAC-96     ## ① MAC のアルゴリズム。IOS XE の aes-128-cmac にあたる
  accept-lifetime 00:00:00 january 01 2026 infinite   ## ① 受け付ける期間
  send-lifetime 00:00:00 january 01 2026 infinite     ## ① 送る期間。accept-lifetime と同じ値にする
 !
!
tcp ao                                        ## ② TCP-AO の設定(グローバル)
 keychain UPLINK-AO                           ## ② ① のキー チェーン
  key 3 SendID 12 ReceiveID 21                ## ② 送る KeyID は 12、受ける KeyID は 21。X1 と交差させる
 !
!
router bgp 65000
 neighbor 172.16.2.1                          ## ③ X1
  ao UPLINK-AO include-tcp-options enable     ## ③ このセッションに TCP-AO。TCP のオプションも MAC に含める
 !
!
:::

X1 は、TCP 用のキー チェーンと、ネイバーの 1 行です。ID は PE2 と逆にします。

:::config X1(IOS XE)— 同じ鍵と、交差させた ID を使う
key chain UPLINK-AO tcp                       ## ④ TCP 用のキー チェーン(最後の tcp)
 key 3                                        ## ④ 鍵の番号
  send-id 21                                  ## ④ 送る KeyID。PE2 の ReceiveID と同じ
  recv-id 12                                  ## ④ 受ける KeyID。PE2 の SendID と同じ
  key-string 0F1E2D3C4B5A69788796A5B4C3D2E1F0 ## ④ 16 進で 32 桁か 64 桁
  cryptographic-algorithm aes-128-cmac        ## ④ IOS XR の AES-128-CMAC-96 にあたる
!
router bgp 65100
 neighbor 172.16.2.254 ao UPLINK-AO include-tcp-options   ## ⑤ PE2 とのセッションに TCP-AO。オプションを含めるのは PE2 とそろえる
:::

両方にコミットしたら、PE2 の側で張り直します。X1 の側で張り直しても、PE2 は前からのセッションを持ったままです(3.4 節)。

```console
RP/0/RP0/CPU0:PE2#clear bgp 172.16.2.1
RP/0/RP0/CPU0:PE2#show bgp summary
...
Neighbor        Spk    AS MsgRcvd MsgSent       TblVer  InQ OutQ  Up/Down  St/PfxRcd
10.255.0.21       0 65000     307     163          407    0    0 01:26:24          2
172.16.2.1        0 65100     300     163          407    0    0 00:00:39          2
```

running-config では、IOS XR のキー文字列は `key-string password …` の暗号化した形で出ます。`tcp ao` は入力したとおりです
(抜粋)。

```console
RP/0/RP0/CPU0:PE2#show running-config key chain UPLINK-AO
key chain UPLINK-AO
 key 3
  accept-lifetime 00:00:00 january 01 2026 infinite
  key-string password 014320557E59225C02186C5C38534E45535453737D057D11610140234426507009
  send-lifetime 00:00:00 january 01 2026 infinite
  cryptographic-algorithm AES-128-CMAC-96
 !
!
RP/0/RP0/CPU0:PE2#show running-config tcp ao
tcp ao
 keychain UPLINK-AO
  key 3 SendID 12 ReceiveID 21
 !
!
```

### 3.4 出力の読み方と落とし穴

**GTSM**: IOS XR の `show bgp neighbor <ネイバー>` は、最後の行に `TTL security is configured` と出します。IOS XE の
`show ip bgp neighbors <アドレス>` には、hop の数と、受ける TTL・送る TTL が出ます(3.1 節の後の PE3 と X2 の抜粋)。

```console
RP/0/RP0/CPU0:PE3#show bgp neighbor 172.16.3.1

BGP neighbor is 172.16.3.1
 Remote AS 65100, local AS 65000, external link
 Remote router ID 10.100.255.2
  BGP state = Established, up for 00:00:37
...
  TTL security is configured
X2#show ip bgp neighbors 172.16.3.254
BGP neighbor is 172.16.3.254,  remote AS 65000, external link
  BGP version 4, remote router ID 10.255.0.3
  BGP state = Established, up for 00:00:39
...
  External BGP neighbor may be up to 1 hop away.
...
Connection is ECN Disabled, Mininum incoming TTL 254, Outgoing TTL 255
```

- `TTL security is configured`: IOS XR は、設定があることだけを表示します。受け付けるのは 255 だけなので、数は出ません。
- `External BGP neighbor may be up to 1 hop away.`: `hops 1` の表示です。
- `Mininum incoming TTL 254`: 受け付けるいちばん小さい TTL です。GTSM の無いセッションでは 0 です(2.1 節)。
- `Outgoing TTL 255`: 送る TTL です。GTSM の無いセッションでは 1 です。

**MD5 認証**: IOS XE は、TCP の接続の `Option Flags` に `md5` を出します。IOS XR の `show bgp neighbor` には、パスワードに
ついての行は出ません。設定は running-config で見ます(3.2 節)。

```console
CE1#show ip bgp neighbors 172.16.1.254
...
Option Flags: nagle, path mtu capable, md5, win-scale
```

**TCP-AO**: IOS XR では `show tcp authentication keychain <名前>` で、キー チェーンの鍵が使える状態かを見ます。

```console
RP/0/RP0/CPU0:PE2#show tcp authentication keychain UPLINK-AO

Keychain name: UPLINK-AO, configured for tcp-ao
Desired key: 3
Total number of keys: 1
Key details:
    Key ID: 3, Active, Valid
Total number of usable (Active & Valid) keys: 1
    Keys: 3, 
```

ID を交差させずにセッションが確立しなかった時も、PE2 は同じ `Key ID: 3, Active, Valid` を表示しました。この表示は、
相手と ID が合っているかを見るものではありません。鍵が有効なことと、相手と話が合うことは別です。

IOS XE では、`show ip bgp neighbors <アドレス>` に、ネイバーの設定と、TCP の接続が使っている鍵が出ます(X1 の抜粋)。

```console
X1#show ip bgp neighbors 172.16.2.254
...
  AO keychain UPLINK-AO include-tcp-options
...
Option Flags: nagle, path mtu capable, win-scale, TCP AO
...
TCP AO Key chain: UPLINK-AO

TCP AO Current Key:
 Id: 3, Send-Id: 21, Recv-Id: 12
 Include TCP Options: Yes
 Accept AO Mismatch: No

TCP AO Next Key:
 Id: 3, Send-Id: 21, Recv-Id: 12
 Include TCP Options: Yes
 Accept AO Mismatch: No
```

- `AO keychain UPLINK-AO include-tcp-options`: ネイバーの設定です。セッションが確立していなくても出ます。
- `Option Flags: … TCP AO`: この TCP の接続が TCP-AO を使っています。MD5 認証なら `md5` です。
- `TCP AO Current Key`: 今の鍵と、その 2 つの ID です。鍵は 1 本なので、`TCP AO Next Key` も同じ鍵 3 です。
- この IOL(IOS XE 17.15)は `show tcp ao key-chain <名前>` を受け付けません(`% Invalid input detected at '^' marker.`)。

| コマンド | 何を見るか |
|---|---|
| `show bgp summary`(IOS XR) | ネイバーの行が `Active` などの状態か、受けた経路の数か |
| `show bgp neighbor <ネイバー>`(IOS XR) | `BGP state`、GTSM なら最後の `TTL security is configured` |
| `show tcp authentication keychain <名前>`(IOS XR) | TCP-AO の鍵が `Active, Valid` か |
| `show running-config key chain`、`show running-config tcp ao`(IOS XR) | 鍵の設定と、鍵ごとの SendID・ReceiveID |
| `show ip bgp neighbors <アドレス>`(IOS XE) | `Mininum incoming TTL`・`Outgoing TTL`、`Option Flags` の `md5`・`TCP AO`、`TCP AO Current Key` の ID |
| `show logging`(両方) | `BADAUTH`(ダイジェストや MAC が合わない)、`AO_KEYCHAIN` |

**失敗の見え方**: ID を交差させないと(X1 も send-id 12・recv-id 21)、PE2 はセッションを `Active` のまま持ち、ログに
`Invalid AO digest` を記録します。X1 のログには `AO_KEYCHAIN` の行が出ます(抜粋)。

```console
RP/0/RP0/CPU0:PE2#show logging last 15
...
RP/0/RP0/CPU0:Nov 21 11:07:41.785 UTC: tcp[144]: %IP-TCP-3-BADAUTH : Invalid AO digest from 172.16.2.1:27110 to 172.16.2.254:179 for vrf:default (0x60000000) 
...
X1#show logging | include AO|TCP
...
*Nov 21 11:07:41.785: %BGP-4-AO_KEYCHAIN: Failed to set TCB AO properties
```

IOS XE では、ネイバーが使っている鍵の ID を、そのままでは直せません。先にネイバーの `ao` を外し、鍵を直してから戻します。
外す行は、設定したとおりに `include-tcp-options` まで書きます。途中までの `no neighbor … ao <名前>` は
`%BGP: No match to an existing config command` で、使っているキー チェーンは消せません。使っている鍵は、使っている間は
直せません。

```console
X1(config)#key chain UPLINK-AO tcp
X1(config-keychain-tcp)#key 3
X1(config-keychain-tcp-key)#send-id 21
% Key 3 on key-chain UPLINK-AO is in use and cannot be modified
X1(config-keychain-tcp-key)#recv-id 12
% Key 3 on key-chain UPLINK-AO is in use and cannot be modified
```

```console
X1(config)#router bgp 65100
X1(config-router)#no neighbor 172.16.2.254 ao UPLINK-AO include-tcp-options
X1(config-router)#exit
X1(config)#key chain UPLINK-AO tcp
X1(config-keychain-tcp)#key 3
X1(config-keychain-tcp-key)#send-id 21
X1(config-keychain-tcp-key)#recv-id 12
X1(config-keychain-tcp-key)#exit
X1(config-keychain-tcp)#exit
X1(config)#router bgp 65100
X1(config-router)#neighbor 172.16.2.254 ao UPLINK-AO include-tcp-options
```

IOS XR は、保護の設定を足しても、張られているセッションを切りません。Command Reference は、`password` を足しても今の
セッションはすぐには終わらず、ホールド タイムが過ぎたところで終わると書いています。TCP-AO を足した時、X1 は設定の変更で
セッションを閉じましたが、PE2 は `Established` のままで、最後に X1 から受け取ったのは 1 分 52 秒前でした(抜粋)。

```console
RP/0/RP0/CPU0:PE2#show bgp neighbor 172.16.2.1

BGP neighbor is 172.16.2.1
 Remote AS 65100, local AS 65000, external link
 Remote router ID 10.100.255.1
  BGP state = Established, up for 00:03:18
...
  Last read 00:01:52, Last read before reset 00:06:27
X1#show ip bgp summary
...
Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
10.100.255.2    4        65100     140     143      199    0    0 01:15:55        3
172.16.2.254    4        65000       0       0        1    0    0 00:00:51 Idle
X1#show logging | include AO|TCP-
...
*Nov 21 10:57:41.542: %BGP-5-NBR_RESET: Neighbor 172.16.2.254 reset (TCP AO config change)
```

X1 の側で `clear ip bgp 172.16.2.254` を打っても、PE2 は `Established` のままでした。PE2 で `clear bgp 172.16.2.1` を
打つと、新しい設定でセッションが張り直されます。古いセッションは、新しい設定とは関係なく続きます。

IOS XR のネイバーに 2 つ目の方式を足すと、コミットが拒まれます。PE1 に `password` がある状態で、キー チェーン CUST-KC を
作り、同じネイバーに `keychain CUST-KC` を足したコミットです(抜粋)。

```console
RP/0/RP0/CPU0:PE1(config-bgp-nbr)#keychain CUST-KC
RP/0/RP0/CPU0:PE1(config-bgp-nbr)#commit
% Failed to commit one or more configuration items during a pseudo-atomic operation. All changes made have been reverted. Please issue 'show configuration failed [inheritance]' from this session to view the errors
RP/0/RP0/CPU0:PE1(config-bgp-nbr)#show configuration failed
!! SEMANTIC ERRORS: This configuration was rejected by 
!! the system due to semantic errors. The individual 
!! errors with each failed configuration command can be 
!! found below.
router bgp 65000
 neighbor 172.16.1.1
  keychain CUST-KC
!!% Change would result in neighbor (172.16.1.1) with Password and Keychain/AO based authentication together
 !
!
end
```

`ttl-security` と `ebgp-multihop` の組み合わせは、OS で扱いが違います。IOS XR は両方を受け付け、running-config に並べます
(Command Reference では `ttl-security` が勝ちます)。IOS XE は拒みます(抜粋)。

```console
RP/0/RP0/CPU0:PE3#show running-config router bgp 65000 neighbor 172.16.3.1
router bgp 65000
 neighbor 172.16.3.1
  remote-as 65100
  ebgp-multihop 2
  ttl-security
  address-family ipv4 unicast
   route-policy PASS in
   route-policy PASS out
  !
 !
!
X2(config-router)#neighbor 172.16.3.254 ebgp-multihop 2
Remove ttl-security before configuring ebgp-multihop
```

落とし穴をまとめます。

- **片側だけの GTSM**: TCP の接続ができない(PE3 は `Active`、X2 は `Idle`)。両端に入れる。
- **IOS XR の `ttl-security` に数を書こうとする**: 引数は無く、受け付けるのは 255 だけ。IOS XE は `hops 1`(254 以上)。
- **`ttl-security` と `ebgp-multihop`**: IOS XR は両方を受け付け、IOS XE は拒む。
- **張り直しを IOS XE の側だけで済ませる**: IOS XR は前からのセッションを持ったまま。IOS XR の側で `clear bgp <ネイバー>`。
- **IOS XR の `keychain` を MD5 認証だと思う**: IOS XE の `password` とはつながらない。MD5 認証は `password`。
- **1 つのネイバーに 2 つの方式**: コミットで拒まれる。
- **ID を交差させない**: `Invalid AO digest` で確立しない。自分の SendID は相手の ReceiveID。
- **IOS XE の使っている鍵を直す**: `in use and cannot be modified`。先にネイバーの `ao` を、設定したとおりの行で外す。
- **include-tcp-options が片側だけ**: MAC の計算の範囲が両端で違ってしまう。両端でそろえる。
- **IOS XE のキー文字列**: 16 進で 32 桁か 64 桁。IOS XR にも同じ文字列を書く。

ラボ **XRT-17** で課題 M6-7 と M6-8 に取り組みます。ラボの初めの状態では、GTSM も認証も、どこにも設定されていません。

<p class="tolab"><a href="/_learn?id=XRT-17">ワークスペースでラボ XRT-17 を開く</a> — <a href="66-m6-practice-3.html">課題 M6-7、M6-8</a></p>

:::note
このページの設定例と出力は、XRT-17 の上で、課題とは違う場所と値で取得しました(PE1 は IOS XRv 9000 26.1.1、PE2・PE3 は
IOS XRd 26.1.1、CE1・X1・X2 は IOS XE 17.15 の IOL)。GTSM は PE3–X2、MD5 認証は PE1–CE1(パスワード CUST-65001)、TCP-AO は
PE2–X1(キー チェーン UPLINK-AO、鍵 3)です。次のものは、PE1〜PE3・P1・RR1・CE1・X1・X2・T が XRT-17 と同じ名前とアドレスを
持つ別の盤面のものです。そこでは PE1 が IOS XRd 26.1.1 で、入口の PE がもう 1 台(IOS XRv 9000 26.1.1)ありました。
`ttl-security ?` の一覧(IOS XRv 9000 でも同じ)。送る TTL の値(PE2–X1 のパケット キャプチャ: GTSM を入れる前は PE2 も X1 も
TTL 1、PE2 は `ttl-security` の後に 255、X1 は `ttl-security hops 1` の後に 255。PE2 だけに入れた時、PE2 の SYN に X1 は TTL 1 で
答え、X1 の SYN も TTL 1 でした)。IOS XR の `keychain` と IOS XE の `password` がつながらないこと(PE2–X1。アルゴリズムが MD5 の
時も HMAC-MD5 の時もつながらず、2.2 節のログは HMAC-MD5 の時のもの)。`no neighbor … ao <名前>` の `No match` と、使っている
キー チェーンを消せないこと。
出典: RFC 5082(1 節の目的と認証との関係、2 節と 3 節の送る TTL 255 と受け付ける範囲、5.2 節のトンネルの例外、付録 A の
何ホップか離れた相手)、RFC 2385(2 節のダイジェストの計算と、合わない時に何も返さず捨てること、交渉の無いこと)、RFC 5925
(TCP-AO の形式、KeyID と RNextKeyID、3.1 節の SendID と RecvID、TCP option flag、5.2 節の traffic key、MD5 認証との同時使用の
禁止)。Routing Command Reference for Cisco ASR 9000 Series Routers(`ttl-security`: 既定で無効、255 だけを受け付けて 255 で
送ること、片側だけの時の記述、`ebgp-multihop` との同居、iBGP に使えないこと、`clear bgp` が要ること。`password`: 今の
セッションはホールド タイムまで続くこと。`keychain`)。BGP Configuration Guide for Cisco NCS 5500, IOS XR 25.x(TCP-AO の
手順とアルゴリズム、SendID と ReceiveID の対応、2 つの期間を同じ値にすること、1 つのネイバーに 1 つの方式、`keychain` が
draft-bonica-tcp-auth-05 に従い `password` とつながらないこと)。System Security Command Reference for Cisco ASR 9000 の
「Keychain Management Commands」(`tcp ao`、`key … SendID … ReceiveID …`、ネイバーの `ao`)。IP Routing Configuration Guide,
Cisco IOS XE 17.x の「Configuring BGP Neighbor Session Options」(`ttl-security hops`、255 から hops を引いた値、送りには
効かないという記述、`ebgp-multihop` と一緒に書けないこと)と「BGP Support for TCP Authentication Option」(`key chain … tcp`、
キー文字列の桁数、`aes-128-cmac` と `AES-128-CMAC-96`、MD5 認証と TCP-AO のどちらか一方)。いずれも 2026 年 11 月に確認。
次は実測によるものです: 片側だけの GTSM で TCP の接続ができないこと、IOS XE の送る TTL、IOS XR と IOS XE の MD5 認証が
つながること、表示とログの文言、`show tcp authentication keychain` が ID の食い違いを表示しないこと、IOS XE の使っている鍵を
直せないこと、IOS XR が古いセッションを持ち続けること、この IOL で `show tcp ao key-chain` を受け付けないこと。
文書と機器が食い違う所: 片側だけの GTSM(文書は OpenSent か OpenConfirm まで進むと書き、機器は TCP の接続ができなかった)と、
IOS XE の `ttl-security hops` の送る TTL(文書は送りには効かないと書き、機器は 255 で送った)。どちらも付録の 6.1 節。
:::
