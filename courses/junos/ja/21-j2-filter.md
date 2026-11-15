# J2 — firewall filter: term と動作

## 1. なぜ term に分けて書くのか

### 1.1 困りごと: 1 つの口で、通信ごとに扱いを変えたい

JUN01 のサーバの網へ出る口では、Web は通したい、ping も通したい、それ以外は止めたい、止めた数も知りたい、と
扱いが通信ごとに違います。1 つの口に、条件と扱いの組をいくつも並べる書き方が要ります。

### 1.2 それ以前の手

IOS の拡張 ACL は、1 行に条件と permit・deny を書き、行を上から調べます。行の順は番号で決まり、
どの行にも当たらなければ暗黙の deny で捨てます。行ごとのカウンタが `show access-lists` に出ます。
IOS XR の ACL も同じ考え方で、行に番号を付けて並べます。

### 1.3 Junos の答え

Junos の firewall filter は、行の代わりに term を並べます。1 つの term に条件(`from`)をいくつも書け、動作(`then`)も
「数えてから通す」「数えて記録して捨てる」のように組み合わせられます。term の書き方は J1 のポリシーと同じなので、
`from` の AND と OR、term の順、`insert` は J1 の知識がそのまま使えます。

## 2. 仕組み

### 2.1 フィルタの形

フィルタは `firewall` の下に、プロトコル ファミリーごとに書きます。IPv4 なら `family inet`、IPv6 なら `family inet6` です。

```
firewall {
    family inet {
        filter フィルタの名前 {
            term term の名前 {
                from {
                    当たる条件;
                }
                then {
                    動作;
                }
            }
            term 次の term の名前 {
                ...
            }
        }
    }
}
```

`from` を書かない term は、すべてのパケットに当たります。フィルタの最後に「残りすべて」を受け止める term を置くときに使います。

### 2.2 from: 照合の条件

よく使う条件です。

| 条件 | 当たるもの |
|---|---|
| `source-address`・`destination-address` | 送信元・宛先のアドレス。プレフィックスで書く |
| `address` | 送信元か宛先のどちらか |
| `source-prefix-list`・`destination-prefix-list`・`prefix-list` | `policy-options` の prefix-list に並べたプレフィックス(4 ページ目) |
| `protocol` | IP のプロトコル(`tcp`・`udp`・`icmp`・`ospf` など) |
| `source-port`・`destination-port` | TCP・UDP のポート。`http`(80)・`https`(443)・`ssh`(22)・`bgp`(179)などの名前でも書ける |
| `port` | 送信元か宛先のどちらかのポート |
| `tcp-established` | TCP の ACK か RST のビットが立ったパケット(つなぎ始めの SYN 以外) |
| `icmp-type` | ICMP の種類(`echo-request` など) |

組み合わせ方は J1 の `from` と同じです。**同じ種類の値はどれか 1 つに当たればよく(OR)、違う種類の条件はすべてに
当たる必要があります(AND)。**`destination-port [ http https ]` は 80 番か 443 番、`protocol tcp` と
`destination-port http` を並べれば「TCP で、かつ 80 番」です。

ポートの条件は TCP にも UDP にもある欄を見るので、`protocol tcp` か `protocol udp` も同じ term に書きます。
`tcp-established` も TCP かどうかは確かめないので、`protocol tcp` と組にします。

### 2.3 then: 動作

動作は 2 つに分かれます。

| 種類 | 動作 | 何をするか |
|---|---|---|
| 終端の動作(評価を終わらせる) | `accept` | 通す |
| | `discard` | 黙って捨てる。送信元へは何も返さない |
| | `reject` | 捨てて、送信元へ ICMP の到達不能を返す |
| 評価を終わらせない動作 | `count 名前` | 名前を付けたカウンタで数える |
| | `log` | `show firewall log` で見られるように残す |
| | `syslog` | syslog のメッセージにする |
| | `policer 名前` | 量を制限する(4 ページ目) |
| 流れの制御 | `next term` | 次の term へ進む |

1 つの term に、終端の動作は 1 つだけ書けます。数える・記録する動作は、終端の動作と並べて書きます。

**終端の動作を書かなかった term に当たったパケットは、通されます(暗黙の accept)。**`then count X` だけの term に当たると、
数えられたうえで通ります。捨てたいなら `discard` を書き添えます。Junos OS Evolved では、`next term` を最後の term に
置くことはできません。

### 2.4 末尾の暗黙の discard

どの term にも当たらなかったパケットは、フィルタの末尾で捨てられます。IOS の ACL の暗黙の deny と同じ考え方です。
J1 のポリシーのように、プロトコルの既定に委ねられることはありません。

暗黙の discard で捨てたパケットは、どのカウンタにも数えられません。数えたいときは、最後に `from` の無い term を置き、
`count` と `discard` を書きます。前のページの例の `term LAST` がそれです。

### 2.5 discard と reject

`discard` は何も返さず、`reject` は ICMP を返します。外から見ると、待たされるか、すぐに断られるかの違いになります。
JUN02 の ISP 側の入力に、ICMP だけを通して残りを捨てるフィルタを当て、最後の term の動作を変えて NET1 から送った結果の例です。

```console
net1:/# probe 172.16.10.1 22 -s 198.51.100.10
timeout  tcp 172.16.10.1:22 from 198.51.100.10  3.00s
net1:/# probe 172.16.10.1 22 -s 198.51.100.10
unreachable (Host is unreachable)  tcp 172.16.10.1:22 from 198.51.100.10  0.00s
```

1 行目が `discard` のときで、送った側は応答を待ってあきらめます。2 行目が `reject` のときで、すぐに断られます。
`reject` が返すのは ICMP の宛先到達不能(type 3)で、既定のコードは 13(administratively prohibited。管理上の理由で禁止)です。
`reject` の後ろに種類を書くと、コードを変えられます。

`probe` は、このほかに `refused` を返すことがあります。フィルタを外して、SRV1 の誰も待っていない 8080 番へ送った結果です。

```console
net1:/# probe 172.16.20.1 8080 -s 198.51.100.10
refused  tcp 172.16.20.1:8080 from 198.51.100.10  0.00s
```

`refused` は、相手の機器が「そのポートでは誰も待っていない」と RST を返したときです。パケットが途中のフィルタを**通った**証拠です。

外へ見せる顔としては、ふつうは `discard` を選びます。`reject` は「ここにフィルタがある」と教えることになり、
ICMP を返す分の手間もかかります。中の利用者に早く失敗を知らせたいときは `reject` が向きます。

### 2.6 term の順と insert

term は書いた順に上から調べます。`set` で足した term は末尾に付くので、先に「残りすべてを捨てる」term があると、
後から足した term には何も届きません。J1 のポリシーと同じで、並べ替えは `insert` です。

```console
[edit]
admin@jun01# show firewall family inet filter TO-SERVERS | display set | match "term (EST|LAST)"
set firewall family inet filter TO-SERVERS term LAST then count TO-SERVERS-DROP
set firewall family inet filter TO-SERVERS term LAST then discard
set firewall family inet filter TO-SERVERS term EST from protocol tcp
set firewall family inet filter TO-SERVERS term EST from tcp-established
set firewall family inet filter TO-SERVERS term EST then accept

[edit]
admin@jun01# insert firewall family inet filter TO-SERVERS term EST before term LAST

[edit]
admin@jun01# show firewall family inet filter TO-SERVERS | display set | match "term (EST|LAST)"
set firewall family inet filter TO-SERVERS term EST from protocol tcp
set firewall family inet filter TO-SERVERS term EST from tcp-established
set firewall family inet filter TO-SERVERS term EST then accept
set firewall family inet filter TO-SERVERS term LAST then count TO-SERVERS-DROP
set firewall family inet filter TO-SERVERS term LAST then discard
```

### 2.7 ステートレス: 戻りの通信と tcp-established

firewall filter は、1 つずつのパケットをその中身だけで判断します。つないだ相手を覚えておくことはしません(ステートレス)。
ですから、中から外へ始めた TCP の戻りのパケットも、戻ってくる向きのフィルタで、改めて判断されます。

前のページの TO-SERVERS は、SRV1 へ出る向きに当ててあります。SRV1 から NET1 の Web(8080 番)へつなぐと、行きの SYN は
フィルタの無い向きなので通りますが、戻りの SYN と ACK は TO-SERVERS に当たり、どの term にも当たらずに捨てられます。

TCP の戻りのパケットには、必ず ACK のビットが立っています。`tcp-established` は ACK か RST の立ったパケットに当たるので、
`protocol tcp` と組にした term で、TCP の戻りを通せます。つなぎ始めの SYN には ACK が無いので、この term に当たりません。
外から新しく始める TCP は、今までどおり後ろの term で判断されます。

結果の例: 戻りの term(EST)を LAST の前に入れる前と後です。

```console
srv1:/# probe 198.51.100.10 8080 -s 172.16.20.1
timeout  tcp 198.51.100.10:8080 from 172.16.20.1  3.00s
srv1:/# probe 198.51.100.10 8080 -s 172.16.20.1
open  tcp 198.51.100.10:8080 from 172.16.20.1  0.00s
net1:/# probe 172.16.20.1 443 -s 198.51.100.10
timeout  tcp 172.16.20.1:443 from 198.51.100.10  3.00s
```

これは、本物の状態を見ているわけではありません。ACK を立てたパケットを外から作って送れば、この term は通します。
相手を覚えて戻りだけを通す仕組み(ステートフルなファイアウォール)は、別の機器や機能の仕事です。
IOS の ACL の `established` も同じ考え方で、ACK か RST のビットを見ています。

### 2.8 インターフェースに当てる

フィルタは、インターフェースの論理ユニットのファミリーに当てます。1 つの向きに 1 つです。

```
set interfaces et-0/0/1 unit 0 family inet filter input  フィルタの名前
set interfaces et-0/0/1 unit 0 family inet filter output フィルタの名前
```

当たっているかは `show interfaces … extensive` の `Input Filters`・`Output Filters` の行で見ます。

```console
admin@jun01> show interfaces et-0/0/1.0 extensive | match ilter
      Output Filters: TO-SERVERS
```

出力フィルタは、ルータ自身(RE)が送るパケットにも効きます。この盤面では、TO-SERVERS を当てた後、SRV1 から JUN01 への SSH が
つながらなくなりました。JUN01 が SRV1 へ返す SYN と ACK が、et-0/0/1 から出るときに TO-SERVERS で捨てられたためです。
戻りの term(EST)を足すと、つながるようになりました。

### 2.9 数を読む: show firewall

`show firewall` は、当てているフィルタのカウンタをすべて出します。`show firewall filter 名前` で 1 つに絞れます。

```console
admin@jun01> show firewall filter TO-SERVERS
Filter: TO-SERVERS
Counters:
Name                                                                            Bytes              Packets
TO-SERVERS-DROP                                                                  1080                   18
WEB-IN                                                                            320                    6
```

カウンタは、通信の直後に読むと増えていないことがあります。数秒待ってから読み直します。数を 0 に戻すのは
`clear firewall filter 名前` か `clear firewall all` です。

## 3. 設定例

### 3.1 サーバの網へ出る通信を絞り、戻りの通信を通す

前のページの TO-SERVERS に、戻りの term を入れた形です。

:::config JUN01 — サーバの網へ出る通信を絞る(戻りの通信も通す)
set firewall family inet filter TO-SERVERS term ICMP from protocol icmp                       ## ICMP はすべて通す
set firewall family inet filter TO-SERVERS term ICMP then accept                              ## 
set firewall family inet filter TO-SERVERS term WEB from destination-address 172.16.20.0/24   ## サーバの網の TCP の 80 番だけ
set firewall family inet filter TO-SERVERS term WEB from protocol tcp                         ## 
set firewall family inet filter TO-SERVERS term WEB from destination-port http                ## 
set firewall family inet filter TO-SERVERS term WEB then count WEB-IN                         ## 数えて通す
set firewall family inet filter TO-SERVERS term WEB then accept                               ## 
set firewall family inet filter TO-SERVERS term EST from protocol tcp                         ## TCP の
set firewall family inet filter TO-SERVERS term EST from tcp-established                      ## ACK か RST の立ったもの(戻り)
set firewall family inet filter TO-SERVERS term EST then accept                               ## 通す
set firewall family inet filter TO-SERVERS term LAST then count TO-SERVERS-DROP               ## 残りすべてを数えて
set firewall family inet filter TO-SERVERS term LAST then discard                             ## 黙って捨てる
set interfaces et-0/0/1 unit 0 family inet filter output TO-SERVERS                           ## et-0/0/1 から出るパケットに当てる
:::

この順で書けば、EST は LAST の前に入ります。EST を後から足したときは、`insert … term EST before term LAST` で前へ動かします。

### 3.2 IOS・IOS XR から Junos へ

| IOS では | IOS XR では | Junos では |
|---|---|---|
| `ip access-list extended 名前` | `ipv4 access-list 名前` | `firewall family inet filter 名前` |
| `10 permit tcp any 172.16.20.0 0.0.0.255 eq 80` | `10 permit tcp any 172.16.20.0/24 eq 80` | `term WEB from destination-address 172.16.20.0/24 protocol tcp destination-port http`・`then accept` |
| `permit tcp any any established` | `permit tcp any any established` | `term EST from protocol tcp tcp-established`・`then accept` |
| 最後の暗黙の deny | 最後の暗黙の deny | 末尾の暗黙の discard |
| `deny ip any any log` | `deny ipv4 any any log` | `term LAST then count …`・`log`・`discard` |
| 行の番号で順を決める | 行の番号で順を決める | 書いた順。並べ替えは `insert` |
| `ip access-group 名前 out` | `ipv4 access-group 名前 egress` | `set interfaces … family inet filter output 名前` |
| `show access-lists` | `show access-lists` | `show firewall` |

## 実践

ラボ **JNT-03** に移り、課題 J2-1 と J2-2 に取り組みます。

<p class="tolab"><a href="/_learn?id=JNT-03">ワークスペースでラボ JNT-03 を開く</a> — <a href="22-j2-practice.html">課題</a></p>

:::note
出典: Juniper Networks『Routing Policies, Firewall Filters, and Traffic Policers User Guide』(2026-06-23)の
「Firewall Filter Match Conditions for IPv4 Traffic」(ポートの条件は protocol と組にする・`tcp-established` は
`tcp-flags "(ack | rst)"` の別名で TCP かどうかは確かめない)、終端の動作と動作の修飾、term に動作が無いときの暗黙の accept、
PTX の動作の表(`reject` の既定は administratively prohibited)。IOS XR の ACL は IOS XR トラック M2 による。
出力は containerlab の vJunos-Evolved(Junos OS Evolved 26.2R1.7)で取ったものです。
:::
