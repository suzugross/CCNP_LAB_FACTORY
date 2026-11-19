# J2 — RE を守る: lo0 フィルタ

## 1. RE を守ると何が嬉しいか

### 1.1 困りごと: ルータ自身が、誰からでも受け付けている

ルータの中で BGP・OSPF・SSH を動かしているのは RE(Routing Engine)です。経路を計算し、設定を受け付ける、ルータの頭脳です。
初めの盤面の JUN02 は、この RE への通信を誰からでも受け付けています。NET1 から JUN02 の SSH にもつながりますし、
BGP ピアでもない SRV1 から、JUN02 の 179 番(BGP)にも TCP でつながります。

```console
srv1:/# probe 192.168.0.2 179
open  tcp 192.168.0.2:179  0.00s
```

RE は、パケットを高速に中継する部分(PFE)より、ずっと少ない量しか扱えません。要らない通信で RE を忙しくさせると、
経路の計算やセッションの維持に響きます。RE が受け取る通信を、要るものだけに絞りたいところです。

### 1.2 それ以前の手

IOS では、SSH の入口は vty の `access-class` で、そのほかの RE 行きの通信は CoPP(control-plane に当てる policy-map)で絞ります。
道具が 2 つに分かれ、CoPP は量の制限が中心です。

IOS XR では、RE 行きの通信は LPTS が種類ごとに量を制限し、管理の入口は MPP(管理プレーン保護)で絞ります
(IOS XR トラックの M2)。こちらも、仕組みが目的ごとに分かれています。

### 1.3 Junos の答え

Junos は、インターフェースに当てるのと同じ firewall filter を **lo0** の入力に当てます。lo0 は RE を表すインターフェースで、
どのインターフェースから来た RE 行きのパケットも、RE に届く前に lo0 の入力フィルタを通ります。
RE が受け取ってよい通信を 1 つのフィルタに書き並べ、残りを捨てる、という書き方になります。

## 2. 仕組み

### 2.1 RE 行きのパケットが通る順

JUN01 の lo0 に、フィルタ RE-GUARD を当てた例です。SRV1 のサーバのネットワーク(172.16.20.1)から JUN01 の SSH へ来たパケットを追います。
図の番号にカーソルを置く(スマホは押す)と、そのブロックの設定が小窓に出て、下の設定例の行に色が付きます。

:::walk
legend: 線の上は IP パケット。RE 行きのパケットは、入ってきたインターフェースの入力フィルタを通った後、lo0 の入力フィルタを通る。
rows:
  - {node: SRV1, say: ["~172.16.20.1 から JUN01 の lo0(192.168.0.1)の SSH へ TCP の SYN を送る"]}
  - {wire: "[[TCP 172.16.20.1 → 192.168.0.1:22]] _SYN"}
  - panel: JUN01
    sub: RE の手前
    items:
      - {head: "**et-0/0/1 の入力** この例ではフィルタなし", say: ["インターフェース フィルタがあれば、中継でも RE 行きでも先にここで判断される"]}
      - ref: 1
        head: "**lo0 の入力** `filter input RE-GUARD`"
        say: ["ルーティング テーブルを引いた結果、宛先は自分(192.168.0.1)。RE へ渡す前に RE-GUARD を通す"]
      - ref: 2
        head: "**RE-GUARD** term を上から"
        match:
          - ["term OSPF  from protocol ospf", false, "当たらない"]
          - ["term ICMP  from protocol icmp", false, "当たらない"]
          - ["term SSH  from source-address 172.16.10.0/24・protocol tcp・destination-port ssh", false, "当たらない(送信元が 172.16.20.1)"]
          - ["term NTP  from source-prefix-list NTP-SERVERS・protocol udp・port ntp", false, "当たらない"]
          - ["term EST  from protocol tcp・tcp-established", false, "当たらない(SYN には ACK が無い)"]
          - ["term LAST  (from なし)", true, "当たる → `count RE-GUARD-DROP`・`discard`"]
      - {say: ["~RE には届かず、SRV1 には何も返らない(timeout)"]}
  - {aside: "送信元が 172.16.10.10 なら", say: ["②の SSH に当たる → `accept` → RE の SSH が受け付ける"]}
  - {aside: "JUN01 を通り抜けるパケットは", say: ["~NET1 から 172.16.20.1 へのパケットなどは宛先が自分ではないので、lo0 フィルタを通らない"]}
:::

:::config JUN01 — RE が受け取る通信を絞る(lo0 フィルタ)
set system ntp server 192.168.0.2                                                         ## 時刻を合わせる相手(NTP のクライアントとして)
set policy-options prefix-list NTP-SERVERS apply-path "system ntp server <*>"             ## ② NTP の相手のアドレスを設定から拾う
set firewall family inet filter RE-GUARD term OSPF from protocol ospf                     ## ② OSPF の隣接
set firewall family inet filter RE-GUARD term OSPF then accept                            ## ② 
set firewall family inet filter RE-GUARD term ICMP from protocol icmp                     ## ② ping・traceroute
set firewall family inet filter RE-GUARD term ICMP then accept                            ## ② 
set firewall family inet filter RE-GUARD term SSH from source-address 172.16.10.0/24      ## ② サーバのネットワークの 172.16.10.0/24 からの
set firewall family inet filter RE-GUARD term SSH from protocol tcp                       ## ② SSH だけ
set firewall family inet filter RE-GUARD term SSH from destination-port ssh               ## ② 
set firewall family inet filter RE-GUARD term SSH then accept                             ## ② 
set firewall family inet filter RE-GUARD term NTP from source-prefix-list NTP-SERVERS     ## ② NTP の相手からの
set firewall family inet filter RE-GUARD term NTP from protocol udp                       ## ② NTP の応答
set firewall family inet filter RE-GUARD term NTP from port ntp                           ## ② 
set firewall family inet filter RE-GUARD term NTP then accept                             ## ② 
set firewall family inet filter RE-GUARD term EST from protocol tcp                       ## ② 自分が始めた TCP の戻り
set firewall family inet filter RE-GUARD term EST from tcp-established                    ## ② 
set firewall family inet filter RE-GUARD term EST then accept                             ## ② 
set firewall family inet filter RE-GUARD term LAST then count RE-GUARD-DROP               ## ② 残りすべてを数えて
set firewall family inet filter RE-GUARD term LAST then discard                           ## ② 捨てる
set interfaces lo0 unit 0 family inet filter input RE-GUARD                               ## ① RE 行きのパケットに当てる
:::

結果の例: 172.16.10.10 からはつながり、172.16.20.1 からは捨てられます。

```console
srv1:/# probe 172.16.10.1 22
open  tcp 172.16.10.1:22  0.00s
srv1:/# probe 192.168.0.1 22 -s 172.16.20.1
timeout  tcp 192.168.0.1:22 from 172.16.20.1  3.00s

admin@jun01> show interfaces lo0.0 extensive | match ilter
      Input Filters: RE-GUARD

admin@jun01> show firewall filter RE-GUARD
Filter: RE-GUARD
Counters:
Name                                                                            Bytes              Packets
RE-GUARD-DROP                                                                     180                    3
```

1 本目は、172.16.10.1(et-0/0/1 のアドレス)へ送っています。宛先がどのインターフェースのアドレスでも、自分宛てなら
lo0 フィルタを通ります。

### 2.2 RE が受け取る通信を数え上げる

lo0 フィルタは「要るものを並べ、残りを捨てる」形にするので、RE が受け取っている通信を漏れなく数え上げるのが仕事の中心です。

| 種類 | 例 | term の書き方の例 |
|---|---|---|
| ルーティング プロトコル | OSPF の hello と LSA | `protocol ospf` |
| | BGP | `protocol tcp`・`port bgp`。相手のアドレスで絞る |
| 管理 | SSH | `protocol tcp`・`destination-port ssh`。管理するネットワークで絞る |
| 診断 | ping・traceroute の応答 | `protocol icmp` |
| RE がクライアントになる通信の応答 | NTP・DNS・syslog の相手からの応答 | `protocol udp`・`port ntp` など。相手で絞る |
| RE が始めた TCP の戻り | ルータから他の機器への SSH・ファイルの転送 | `protocol tcp`・`tcp-established` |

数え漏れたプロトコルは、すぐには壊れません。OSPF はネイバーからの hello が届かなくなっても、dead interval(既定 40 秒)の間は
隣接を保ちます。BGP は hold time(この盤面では 90 秒)の間はセッションを保ちます。commit の直後には何も起きず、
しばらくして壊れるので、原因に気づきにくいのです。

JUN02 の lo0 フィルタから OSPF の term を外して 45 秒待ったときの結果の例です。JUN02 はネイバーを失い、JUN01 は JUN02 の hello を
受け取れても自分の hello が届かないので、`Init` のまま止まります。

```console
admin@jun02> show ospf neighbor

admin@jun01> show ospf neighbor
Address          Interface              State           ID               Pri  Dead
10.0.12.2        et-0/0/0.0             Init            192.168.0.2      128    33
```

OSPF の隣接が保たれているかは、`show ospf neighbor` の `Dead` の欄でも見えます。hello が届いている間は 30 秒台に戻り続け、
届かなくなると 1 秒ずつ減っていきます。

### 2.3 apply-path: 相手のアドレスを設定から拾う

BGP ピアや NTP の相手で絞るとき、アドレスをフィルタに直に書くと、相手を足すたびにフィルタも直すことになります。
直し忘れると、新しい相手とはつながりません。

`apply-path` を使うと、prefix-list の中身を設定の中から拾えます。設定の階層のパスを書き、変わる部分を `<*>` にします。
`system ntp server <*>` なら、NTP の相手として書いたアドレスがすべて並びに入ります。何が入ったかは `display inheritance` で見ます。

```console
admin@jun01> show configuration policy-options prefix-list NTP-SERVERS | display inheritance
##
## apply-path was expanded to:
##     192.168.0.2;
##
apply-path "system ntp server <*>";
```

BGP の neighbor のアドレスも、`protocols bgp` の下の階層をパスに書けば同じように拾えます。group が増えても neighbor が増えても、
フィルタを書き直す必要がありません。

### 2.4 自分が始めた通信の戻り

lo0 フィルタは、RE が受け取るものすべてを見ます。RE 自身が外へ始めた通信の戻りも、その中に入ります。
TCP の戻りには ACK が立っているので、前のページの `tcp-established` の term で通せます。

BGP は、相手からつないでくる時も、自分からつなぐ時も、片方のポートが 179 番です。`port bgp`(送信元か宛先のどちらかが 179 番)で
書けば、どちら向きのセッションも通ります。`destination-port bgp` だけにすると、自分からつないだセッションの戻り
(送信元が 179 番)は、この term に当たりません。

JUN02 の lo0 フィルタに戻りの term が無いとき、JUN02 から ISP の 8080 番へつないだ結果の例です。行きは出ていきますが、
戻りの SYN と ACK が lo0 フィルタで捨てられ、3 秒でタイムアウトになります(`rc=124` はタイムアウトの印)。

```console
admin@jun02> start shell command "timeout 3 bash -c 'exec 3<>/dev/tcp/10.0.23.2/8080 && head -c 2 <&3'; echo rc=$?"
rc=124
```

### 2.5 管理ポートは別(Junos OS Evolved)

このルータ(Junos OS Evolved)では、lo0 フィルタは**管理ポートの通信には効きません**。管理ポート `re0:mgmt-0` は、
ルーティング テーブル `mgmt_junos` を使う別のインターフェースとして扱われます。管理ポートの通信を絞るときは、`re0:mgmt-0` の論理ユニットに別のフィルタを当てます。

この盤面のコンソールは、管理ポートへの SSH で開いています。RE-GUARD には管理ネットワークの term が無いのに、RE-GUARD を当てた後も、
新しいコンソールを開くことができました。

```console
admin@jun01> show system users
 5:36AM  up 39 min, 2 users, load averages: 0.43, 0.28, 0.34
USER     TTY      FROM                              LOGIN@  IDLE WHAT
admin    pts/0    172.20.20.1                      05:35   4.00s -cli
admin    pts/1    172.20.20.1                      05:36   0.00s -cli
```

Junos OS(Evolved でない方)では、lo0 フィルタは管理ポートの通信にも効きます。管理ネットワークの term を書き忘れると、
自分のログインも締め出されます。そういう機器で lo0 フィルタを試すときは、J0 の `commit confirmed` を使います。

### 2.6 確かめ方

1. 当たっているか: `show interfaces lo0.0 extensive | match ilter` の `Input Filters`。
2. 捨てているか: `show firewall filter 名前` の、最後の term のカウンタ。
3. 要るものが生きているか: `show ospf neighbor` の `Full` と `Dead` の欄、`show bgp summary` の `Establ`。
   BGP は `clear bgp neighbor 相手` で張り直させて、もう一度 `Establ` まで戻るかを見ると確かです。
4. 外から: 許していない送信元から SSH を試して `timeout` になること、許した送信元から `open` になること。

## 3. 設定例

### 3.1 JUN01 の RE を守る

2.1 節の RE-GUARD です。JUN01 は BGP を動かしていないので BGP の term は無く、代わりに NTP の相手からの応答を通しています。

結果の例: RE-GUARD を当てた後も、OSPF の隣接は `Full` のまま、`Dead` は 30 秒台です。

```console
admin@jun01> show ospf neighbor
Address          Interface              State           ID               Pri  Dead
10.0.12.2        et-0/0/0.0             Full            192.168.0.2      128    32
```

### 3.2 IOS・IOS XR から Junos へ

| IOS では | IOS XR では | Junos では |
|---|---|---|
| `line vty 0 4` の `access-class 名前 in` | MPP(`control-plane management-plane`)で SSH の入口を絞る | lo0 フィルタの SSH の term |
| CoPP(`control-plane` に `service-policy input`) | LPTS(種類ごとに自動で量を制限) | lo0 フィルタ(量の制限は policer。4 ページ目) |
| 相手ごとの ACL を手で直す | prefix-set を手で直す | `apply-path` で設定から拾う |
| 管理インターフェースも同じ制御の対象 | MPP で管理用のインターフェースを決める | Junos OS Evolved は管理ポートが別(`re0:mgmt-0` に別のフィルタ) |

## 実践

ラボ **JNT-03** に移り、課題 J2-3 に取り組みます。

<p class="tolab"><a href="/_learn?id=JNT-03">ワークスペースでラボ JNT-03 を開く</a> — <a href="24-j2-practice-2.html">課題</a></p>

:::note
出典: Juniper Networks『Routing Policies, Firewall Filters, and Traffic Policers User Guide』(2026-06-23)の
「Junos OS Evolved Local Packet Flow Control」(lo0 のフィルタは管理の通信に効かず、管理ポートには別にフィルタを当てる・
従来の Junos OS では lo0 のフィルタが管理の通信にも効く)、prefix-list の `apply-path` の節、lo0 で RE を守る例。
IOS XR の LPTS と MPP は IOS XR トラック M2 による。OSPF の term を外した時と、RE が始めた TCP の戻りの出力は、
J1 の盤面(JNT-02)で JUN02 に lo0 のフィルタを当てた時のものです。出力は containerlab の vJunos-Evolved
(Junos OS Evolved 26.2R1.7)で取ったものです。
:::
