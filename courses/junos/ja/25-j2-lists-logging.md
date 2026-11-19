# J2 — 並べる・記録する: フィルタ リストとログ

## 1. フィルタを並べ、記録すると何が嬉しいか

### 1.1 困りごと: 1 つのインターフェースに、目的の違う判断が 2 つある

ISP からの入口では、「送信元のアドレスがおかしいパケットを捨てる」判断と、「通してよいサービスだけを通す」判断の
2 つが要ります。前者はどのインターフェースでも同じ中身になり、後者はインターフェースごとに違います。1 つのフィルタに混ぜて書くと、
同じ送信元の検査をインターフェースごとに書き写すことになります。

捨てたものを数えるだけでなく、何を捨てたのか(どこから、どこへ、どのポートへ)を後から見たいこともあります。

### 1.2 それ以前の手

IOS の ACL は、1 つのインターフェースの 1 つの向きに 1 つだけ当てられます。目的の違う行も 1 つの ACL に書き混ぜます。
捨てたものを記録するには、行の末尾に `log` を付け、syslog に出します。IOS XR も、1 つのインターフェースの 1 つの向きに 1 つの ACL です。

### 1.3 Junos の答え

Junos は、1 つの向きに**フィルタを並べて**当てられます(`input-list`・`output-list`)。送信元の検査のフィルタを 1 つ作れば、
インターフェースごとのフィルタの前に並べて使い回せます。記録には `log`(ルータの中のバッファ)と `syslog`(syslog メッセージ)の
2 つのアクションがあり、数える `count` と組み合わせて使います。

## 2. 仕組み

### 2.1 フィルタ リスト

`input-list [ A B ]` と書くと、入ってきたパケットは A、B の順に調べられます。どこかで終端アクション(`accept`・`discard`・`reject`)が
出れば、そこで終わりです。A のどの term にも当たらなかったパケットは、A の末尾で捨てられずに B へ進みます。
最後のフィルタのどの term にも当たらなければ、そこで暗黙の discard です。

JUN01 のサーバのネットワークからの入口に、送信元を検査する SRC-CHECK と、数える FROM-SERVERS を並べた例です。SRV1 から、
サーバのネットワークに無いアドレス(10.99.0.1)を送信元にしたパケットを追います。図の番号にカーソルを置く(スマホは押す)と、
そのブロックの設定が小窓に出て、下の設定例の行に色が付きます。

:::walk
legend: 線の上は IP パケット。並べたフィルタは左から順に調べ、終端アクションが出たところで終わる。
rows:
  - {node: SRV1, say: ["~送信元を 10.99.0.1 にして NET1(198.51.100.10)へ ping を送る"]}
  - {wire: "[[ICMP 10.99.0.1 → 198.51.100.10]] _echo-request"}
  - panel: JUN01
    sub: サーバのネットワークからの入口
    items:
      - ref: 1
        head: "**et-0/0/1 の入力** `filter input-list [ SRC-CHECK FROM-SERVERS ]`"
        say: ["並べた順に調べる。まず SRC-CHECK"]
      - ref: 2
        head: "**SRC-CHECK** 送信元がサーバのネットワークか"
        match:
          - ["term SPOOF  from source-address 0.0.0.0/0・172.16.10.0/24 except・172.16.20.0/24 except", true, "当たる(10.99.0.1 は 0/0 に入り、除いた 2 つに入らない) → `count SPOOF`・`syslog`・`log`・`discard`"]
      - {say: ["~ここで終わり。FROM-SERVERS は調べない"]}
  - {aside: "送信元が 172.16.20.1 なら", say: ["②の SPOOF に当たらない(除いた範囲に入る) → SRC-CHECK にはもう term が無い → 次のフィルタへ → ③の ALL に当たる → `count FROM-SERVERS`・`accept`"]}
  - {aside: "②の最後に `then accept` の term を足すと", say: ["~172.16.20.1 のパケットはそこで受け入れられて終わる → ③は調べられず、FROM-SERVERS は数えない"]}
:::

:::config JUN01 — 送信元を検査してから数える(フィルタ リスト)
set firewall family inet filter SRC-CHECK term SPOOF from source-address 0.0.0.0/0              ## ② どの送信元でも
set firewall family inet filter SRC-CHECK term SPOOF from source-address 172.16.10.0/24 except  ## ② ただしサーバのネットワークの 2 つは除く
set firewall family inet filter SRC-CHECK term SPOOF from source-address 172.16.20.0/24 except  ## ② 
set firewall family inet filter SRC-CHECK term SPOOF then count SPOOF                           ## ② 数える
set firewall family inet filter SRC-CHECK term SPOOF then syslog                                ## ② syslog メッセージにする
set firewall family inet filter SRC-CHECK term SPOOF then log                                   ## ② show firewall log に残す
set firewall family inet filter SRC-CHECK term SPOOF then discard                               ## ② 捨てる
set firewall family inet filter FROM-SERVERS term ALL then count FROM-SERVERS                   ## ③ 残ったものをすべて数えて
set firewall family inet filter FROM-SERVERS term ALL then accept                               ## ③ 通す
set interfaces et-0/0/1 unit 0 family inet filter input-list [ SRC-CHECK FROM-SERVERS ]         ## ① 2 つを並べて入力に当てる
set system syslog file fw-log firewall any                                                      ## firewall filter のメッセージをファイル fw-log へ
:::

結果の例: 送信元が 172.16.20.1 の ping は届き、10.99.0.1 の ping は捨てられます。

```console
srv1:/# ping -c 2 -W 1 -I 172.16.20.1 198.51.100.10
2 packets transmitted, 2 packets received, 0% packet loss
srv1:/# ping -c 2 -W 1 -I 10.99.0.1 198.51.100.10
2 packets transmitted, 0 packets received, 100% packet loss
```

SRC-CHECK に `then accept` だけの term を最後に足すと、図の 2 つ目の別の場合のとおり、後ろのフィルタは調べられなくなります。
JUN02 で同じ形を試したとき、1 本目のフィルタの最後に `accept` の term があると、2 本目のフィルタのカウンタは増えませんでした。
1 本目の終わりは「どの term にも当たらない」ままにして、次のフィルタへ渡します。

Junos OS Evolved には、`input-chain` という別の並べ方もあります。こちらは `accept` でも次のフィルタへ進みます。
使える機種が限られるので、この単元では `input-list` を使います。

### 2.2 アドレスの並びと except

送信元や宛先の条件には、アドレスを直に書くほかに、`policy-options` の prefix-list を使えます(`source-prefix-list`・
`destination-prefix-list`・`prefix-list`)。同じ並びを、フィルタとルーティング ポリシーの両方で使い回せます。

アドレスにも prefix-list にも `except` を付けられます。1 つの条件の中に並べたアドレスは、パケットのアドレスを**いちばん長く
含むもの**で決まり、それが `except` なら「当たらない」になります。SRC-CHECK の 172.16.20.1 は、0.0.0.0/0 より長い
172.16.20.0/24 に含まれ、それが `except` なので、term に当たりません。

広い範囲を捨てるときに、その中の一部だけを残したい、という形によく使います。たとえばプライベート アドレスを捨てる並びの中に、
自分が使っている接続のアドレスが入ってしまう時です。その部分を `except` で抜きます。

直に書くアドレス(`source-address`)と prefix-list(`source-prefix-list`)を同じ term に両方書くと、違う種類の条件(AND)としては
扱われません。2 つを合わせた 1 つの並びとして、最長一致で引かれます。J1 の route-filter と prefix-list と同じ形です。宛先の
`destination-address` と `destination-prefix-list` も同じです。書く場所が 2 つあっても、引かれる並びは 1 つです。

```
term t {
    from {
        source-address 10.200.0.0/16;
        source-prefix-list PL;      ← PL= 192.168.50.0/24 だけ
        protocol icmp;
    }
    then discard;
}
```

この term には、送信元が 10.200.0.1 のパケットも 192.168.50.1 のパケットも当たります。AND なら、どちらも外れるはずです。
`except` も 2 つをまたいで効きます。`source-address 10.0.0.0/8 except` と、10.200.0.0/16 だけの prefix-list を並べると、10.200.0.1 は
長いほうの /16 で決まり、当たります。文書の「term の条件はすべて当たって一致する」を、この組み合わせにそのまま当てはめると読み違えます。

一方、`except` の行しかない並びは、何にも当たりません。並びの末尾には暗黙の `0.0.0.0/0 except` があり、除いた範囲の外の
アドレスも、そこで「当たらない」になるからです。`source-address 10.0.23.0/30 except` だけの term は、どの送信元にも当たらず、
その term のカウンタは `show firewall` に出てきません。SRC-CHECK が 0.0.0.0/0 を並べているのは、このためです。除くものしか
書いていない並びは、何も含みません。

### 2.3 並べた時のカウンタの名前

フィルタを並べると、Junos はそのインターフェースのために 1 つのフィルタを組み立てます。名前は `論理インターフェース-inet-i`
(入力の時。出力は `-o`)で、カウンタもその名前を付けて数えられます。元のフィルタの名前で読むと、0 のままです。

```console
admin@jun01> show interfaces et-0/0/1.0 extensive | match ilter
      Input Filters: et-0/0/1.0-inet-i
      Output Filters: TO-SERVERS

admin@jun01> show firewall
Filter: FROM-SERVERS
Counters:
Name                                                                            Bytes              Packets
FROM-SERVERS                                                                        0                    0
...
Filter: SRC-CHECK
Counters:
Name                                                                            Bytes              Packets
SPOOF                                                                               0                    0
...
Filter: et-0/0/1.0-inet-i
Counters:
Name                                                                            Bytes              Packets
FROM-SERVERS-et-0/0/1.0-inet-i                                                    168                    2
SPOOF-et-0/0/1.0-inet-i                                                           168                    2
```

`show firewall filter et-0/0/1.0-inet-i` のように、組み立てられた名前で絞ることもできます。

### 2.4 log と syslog

**`log`** は、パケットのヘッダ(時刻・アクション・インターフェース・プロトコル・アドレス)を、パケットを中継する部分(PFE)の中の
バッファに残します。`show firewall log` で読みます。`Filter` の欄はいつも `pfe`、`Action` の欄は A(accept)・D(discard)・
R(reject)です。ポートまで見たいときは `detail` を付けます。

```console
admin@jun01> show firewall log
Log :
Time      Filter    Action Interface           Protocol        Src Addr                                Dest Addr
05:37:11  pfe       D      et-0/0/1.0          ICMP            10.99.0.1                               198.51.100.10
05:37:12  pfe       D      et-0/0/1.0          ICMP            10.99.0.1                               198.51.100.10

admin@jun01> show firewall log detail
Time of Log: Nov 15 05:37:11, Filter: pfe, Filter action: Discard, Name of interface: et-0/0/1.0
Name of protocol: ICMP, Packet Length: 84, Source address: 10.99.0.1 Port: 0, Destination address: 198.51.100.10 Port: 0
ICMP type: 0, ICMP code: 0
```

バッファは大きくなく、古いものから消えていきます。この盤面では、数分前の記録が見えなくなっていることがありました。
残しておきたい記録には向きません。

**`syslog`** は、同じ情報を syslog メッセージにします。メッセージは **firewall** という facility(メッセージの出どころの分類)で
出るので、受け取る側の設定が要ります。`set system syslog file 名前 firewall any` と書くと、firewall の facility のメッセージを
すべての重大度(severity)の分だけ、`/var/log/名前` のファイルに書きます。`show log 名前` で読みます。

```console
admin@jun01> show log fw-log
Nov 15 05:37:12  jun01 evo-aftmand-bt[14680]: FW: et-0/0/1.0   D ICMP 10.99.0.1 198.51.100.10     0     0 (2 packets)
```

`FW:` の後ろは、インターフェース・アクション・プロトコル・送信元・宛先・送信元のポート・宛先のポートの順です。
短い間に続いたものは、末尾の `(2 packets)` のようにまとめて 1 行になります。

`then syslog` を書いても、受け取るファイルの設定が無ければ、どこにも残りません。この盤面のルータでは、既定のメッセージの
ファイル(`messages`)にも firewall filter のメッセージは出ませんでした。

### 2.5 policer: 量を制限する

**policer** は、パケットの量に上限を付ける部品です。上限を超えた分を捨てる(またはマーキングする)ことで、
たとえば RE へ届く ICMP の量を抑えます。firewall filter の term のアクションに `policer 名前` と書いて使います。

```
set firewall policer 名前 if-exceeding bandwidth-limit 1m      ← 平均の速さの上限(ビット毎秒)
set firewall policer 名前 if-exceeding burst-size-limit 15k    ← 一度に超えてよい量(バイト)
set firewall policer 名前 then discard                         ← 超えた分を捨てる
```

`policer` は終端アクションではありません。上限の内側のパケットは、同じ term の終端アクション(書いていなければ暗黙の accept)に従います。

**この仮想ルータ(vJunos-Evolved)では、policer は量を制限しません。**設定は commit でき、`show firewall` に Policers の欄も
出ますが、上限を大きく超える ping を送っても 1 つも捨てず、捨てた数は 0 のままでした。仕組みと設定の形だけを覚え、
効き目は実機で確かめてください(付録 3.2)。

## 3. 設定例

### 3.1 送信元を検査してから数える

2.1 節の SRC-CHECK と FROM-SERVERS です。結果の syslog の 1 行は 2.4 節のとおりです。

### 3.2 RE へ届く ICMP に policer を付ける

前のページの RE-GUARD の ICMP の term に、policer を足した形です。この仮想ルータでは量は制限されません。

:::config JUN01 — RE へ届く ICMP の量に上限を付ける(この仮想ルータでは効かない)
set firewall policer ICMP-1M if-exceeding bandwidth-limit 1m           ## 平均 1 Mbps まで
set firewall policer ICMP-1M if-exceeding burst-size-limit 15k         ## 一度に 15 KB まで超えてよい
set firewall policer ICMP-1M then discard                              ## 超えた分を捨てる
set firewall family inet filter RE-GUARD term ICMP then policer ICMP-1M   ## ICMP の term に足す(accept はそのまま)
:::

```console
admin@jun01> show firewall filter RE-GUARD
Filter: RE-GUARD
Counters:
Name                                                                            Bytes              Packets
RE-GUARD-DROP                                                                     180                    3
Policers:
Name                                                                            Bytes              Packets
ICMP-1M-ICMP                                                                        0                    0
```

Policers の欄の名前は `policer の名前-term の名前` です。数は、上限を超えて捨てたパケットです。

### 3.3 IOS・IOS XR から Junos へ

| IOS では | IOS XR では | Junos では |
|---|---|---|
| 1 つのインターフェースの 1 つの向きに ACL は 1 つ | 同じ | `input-list [ A B ]` で並べられる |
| `deny ip 10.0.0.0 0.255.255.255 any`(範囲を並べる) | 同じ | `source-address`・`source-prefix-list`。一部を残すなら `except` |
| 行の末尾の `log` → syslog | 同じ | `then log`(バッファ)・`then syslog`(＋ firewall の facility のファイル) |
| `show logging` | `show logging` | `show firewall log`・`show log 名前` |
| CoPP の `police` | LPTS・`police` | `firewall policer` を term の `then policer` で使う |

## 実践

ラボ **JNT-03** に移り、課題 J2-4 と J2-5 に取り組みます。

<p class="tolab"><a href="/_learn?id=JNT-03">ワークスペースでラボ JNT-03 を開く</a> — <a href="26-j2-practice-3.html">課題</a></p>

:::note
出典: Juniper Networks『Routing Policies, Firewall Filters, and Traffic Policers User Guide』(2026-06-23)の
「Understanding Multiple Firewall Filters Applied as a List」(並べたフィルタの評価・`-i`・`-o` の名前)、filter chain の節
(`input-list` は accept か discard で止まる・`input-chain` は Junos OS Evolved 21.4R1 から一部の PTX で使える)、`log` の動作
(PFE の中のバッファ)と `show firewall log` の読み方(Filter はいつも pfe)、policer の節。『Network Management and Monitoring
Guide』(2026-07-06)の System Logging の章(facility の表に firewall・最小の設定は `file 名前 { facility severity; }`)。
『vJunosEvolved Deployment Guide』(2025-11-11)の制約の節(vJunosEvolved-BX は firewall policer を扱わない)。
同じ文書の Match Conditions の節(term の条件はすべて当たって一致)、「Firewall Filter Match Conditions Based on Address Fields」
(アドレスの並びの最長一致と末尾の暗黙の 0/0 except・except だけの term は当たらずカウンタが `show firewall` に出ない)。文書は
`source-address` と `source-prefix-list` を同じ term に書いた時の組み合わせ方を書いていません。2.2 節のその挙動は、J2 の盤面
(JNT-03)の JUN02 で確かめたものです。
policer が効かないことと、並べたフィルタの 1 本目の accept の出力は、J1 の盤面(JNT-02)の JUN02 で確かめたものです。
出力は containerlab の vJunos-Evolved(Junos OS Evolved 26.2R1.7)で取ったものです。
:::
