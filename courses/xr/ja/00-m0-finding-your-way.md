# M0 — 入り方と調べ方

この単元は、IOS と IOS XE には慣れていて、IOS XR に初めて触る技術者のためのものです。
OSPF や VRF、スタティック ルーティングは教えません。それらは既に知っているはずです。
ここで扱うのは、IOS XR がそれらをどこに置いているか、どう表示するか、打ったことのないコマンドをどう探すか、です。

掲載した出力は、すべて IOS XRv 9000 のリリース 24.3.1 で採ったものです。

## 1. どこにログインしているのか

```console
RP/0/RP0/CPU0:XR01#
```

プロンプトは「場所」とホスト名でできています。`0/RP0/CPU0` は、ラック 0、スロット RP0 のルート プロセッサ、
CPU インスタンス 0 です。ライン カードを持つシャーシでは、カードからのログにカード自身の場所が付きます。

```console
LC/0/0/CPU0:Oct 12 13:43:16.484 UTC: ifmgr[239]: %PKT_INFRA-LINK-3-UPDOWN : Interface GigabitEthernet0/0/0/0, changed state to Up
RP/0/RP0/CPU0:Oct 12 13:44:12.701 UTC: ospf[1039]: %ROUTING-OSPF-5-ADJCHG : Process 1, Nbr 2.2.2.2 on GigabitEthernet0/0/0/0 in area 0 from LOADING to FULL, Loading Done
```

この 2 行をもう一度見てください。1 行目は、ライン カードで動く `ifmgr` というプロセスが出しています。
2 行目は、ルート プロセッサで動く `ospf` というプロセスが出しています。角かっこの数字はプロセス ID です。

IOS との構造上のいちばん大きな違いがこれです。IOS は 1 つのプログラムです。IOS XE は、その同じプログラム(IOSd)を
Linux の上でプロセスとして動かしています。IOS XR は、Linux カーネルの上で動く別々のプロセスの集まりです。
OSPF に 1 つ、BGP に 1 つ、インターフェイス管理に 1 つ、設定セッションごとに 1 つ、というように分かれ、
ルート プロセッサとライン カードに散らばっています。
コマンド ラインで感じる違和感の多くは、ここから来ています。

`enable` はありません。何ができるかは、ログインした時点で、ユーザが属するタスク グループによって決まります。

## 2. インターフェイスの名前と既定の状態

物理インターフェイスの名前は「種別 ラック/スロット/モジュール/ポート」です。

```console
RP/0/RP0/CPU0:XR01#show ipv4 vrf all interface brief

Interface                      IP-Address      Status          Protocol Vrf-Name
Loopback0                      1.1.1.1         Up              Up       default
MgmtEth0/RP0/CPU0/0            10.1.10.17      Up              Up       MGMT
GigabitEthernet0/0/0/0         10.0.12.1       Up              Up       default
GigabitEthernet0/0/0/1         10.0.13.1       Up              Up       CUST-A
GigabitEthernet0/0/0/2         10.0.21.1       Up              Up       default
```

見ておく点が 3 つあります。

- 管理ポートはルート プロセッサのインターフェイスなので、ルート プロセッサの場所が名前に入ります(`MgmtEth0/RP0/CPU0/0`)。
- IPv4 と IPv6 は別のコマンドです(`show ipv4 interface brief` と `show ipv6 interface brief`)。
  IOS の書き方の `show ip interface brief` もまだ受け付けますが、CLI 自身が `ip` を
  「Deprecated, use ipv4 instead」と説明しています。`ipv4` と `ipv6` の形を使います。
- 管理上ディセーブルのインターフェイスは、Status の列に `Shutdown` と出ます。

一度も設定されていない物理インターフェイスは管理上ダウンで、実行コンフィギュレーションには `shutdown` の行が
明示されます。アップにすると、その行が消えます。

```console
interface GigabitEthernet0/0/0/2
 description LINK2 to RT01
 ipv4 address 10.0.21.1 255.255.255.0
!
```

この出力に `no shutdown` はありませんが、インターフェイスはアップです。IOS XR では、`shutdown` の行は
ディセーブルの間だけ存在します。行が無いことがアップを意味します。

アドレスはアドレス ファミリを先に書きます。`ipv4 address 10.0.21.1 255.255.255.0`(`10.0.21.1/24` でも可)、
`ipv6 address 2001:db8:12::1/64` です。

## 3. 設定は木構造で、プロトコルが自分のインターフェイスを持つ

IOS では、多くのものがインターフェイスの下に集まります。`ip ospf 1 area 0`、`ip ospf cost`、`vrf forwarding` などは
すべて `interface` の下です。IOS XR では、インターフェイスのブロックに書くのはインターフェイス自身に属するものだけです
(アドレス、説明、VRF の所属、カプセル化)。ルーティング プロトコルがそのインターフェイスについて知るべきことは、
すべてプロトコルの下に書きます。

XR01 の OSPF は次のとおりです。

```console
RP/0/RP0/CPU0:XR01#show running-config router ospf
router ospf 1
 router-id 1.1.1.1
 area 0
  interface Loopback0
  !
  interface GigabitEthernet0/0/0/0
   network point-to-point
  !
  interface GigabitEthernet0/0/0/2
   cost 50
   network point-to-point
  !
 !
!
```

- `network` 文はありません。インターフェイスは、エリアの下に列挙されることで OSPF を実行します。
- インターフェイス単位の OSPF の設定(`cost`、`network point-to-point`、認証)は、その項目の下に書きます。
  `interface GigabitEthernet…` の下ではありません。
- 上の階層に書いた設定は、下の階層すべてに継承されます。Cisco のコンフィギュレーション ガイドは hello 間隔を例に
  こう説明しています。インターフェイスの階層に設定があればその値、無ければエリアの階層の値、
  それも無ければ `router ospf` の階層の値、どれも無ければ既定値を使う。
  認証、ネットワーク タイプ、その他ほとんどのインターフェイス パラメータも同じです。

スタティック ルートも同じ考え方です。`ip route` の行があちこちに並ぶのではなく、`router static` のブロックが
1 つあり、VRF とアドレス ファミリで区切られています。

```console
RP/0/RP0/CPU0:XR01#show running-config router static
router static
 address-family ipv4 unicast
  0.0.0.0/0 10.0.12.2
 !
 vrf CUST-A
  address-family ipv4 unicast
   172.16.2.0/24 10.0.13.2
  !
 !
!
```

VRF は、運ぶアドレス ファミリとともに最上位で宣言します。インターフェイスは、その下の 1 行で VRF に所属します。

```console
vrf CUST-A
 address-family ipv4 unicast
 !
!
interface GigabitEthernet0/0/0/1
 description CUST-A to RT02
 vrf CUST-A
 ipv4 address 10.0.13.1 255.255.255.0
!
```

:::note
IOS では、`vrf forwarding` を入れるとインターフェイスの IP アドレスが外れ、入れ直す必要があります。
この IOS XR のリリースでは、アドレスを持つインターフェイスを VRF に移してもアドレスは残りました。
どちらの記憶にも頼らず、結果を見て確認します。
:::

## 4. 設定の一部だけを見る

設定は木構造なので、枝を指定して表示できます。既に 2 つの例を見ました。
形は、`show running-config` の後に、コンフィギュレーション モードでそこへ行くときと同じ語を続けるだけです。

```console
RP/0/RP0/CPU0:XR01#show running-config interface GigabitEthernet0/0/0/1
RP/0/RP0/CPU0:XR01#show running-config router ospf
RP/0/RP0/CPU0:XR01#show running-config router static
RP/0/RP0/CPU0:XR01#show running-config vrf CUST-A
```

設定されていないものを指定しても、入力の誤りにはなりません。

```console
RP/0/RP0/CPU0:XR01#show running-config interface Loopback11
% No such configuration item(s)
```

出力の絞り込みは IOS と同じです(`| include`、`| exclude`、`| begin`)。ただし、初日に必ず引っかかる違いが 1 つあります。
`|` を含む正規表現は引用符で囲む必要があります。囲まない `|` は、次の絞り込みの始まりと解釈されるからです。

```console
RP/0/RP0/CPU0:XR01#show version | include Version|uptime
                                                  ^
% Invalid input detected at '^' marker.
RP/0/RP0/CPU0:XR01#show version | include "Version|uptime"
Cisco IOS XR Software, Version 24.3.1
 Version      : 24.3.1
System uptime is 18 minutes
```

`| utility` は UNIX の道具(`egrep`、`wc`、`head`、`tail` など)を使え、`| file` は出力を保存します。

コンフィギュレーション モードの中では、`show running-config …` はいま動いている設定を、単なる `show configuration` は
入力したがまだ適用していない設定を表示します。大事なのは後者です。理由は次の節にあります。

## 5. コミットするまで何も起きない

IOS では、行は Enter を押した時点で有効になります。IOS XR では、コンフィギュレーション モードで入力した行は、
別の、自分専用の写しに入ります。これを**ターゲット コンフィギュレーション**と呼びます。
`commit` と入力するまで、ルータは以前の設定のまま動き続けます。`commit` で、入力した行がまとめて適用されます。

```console
RP/0/RP0/CPU0:XR01(config)#interface Loopback12
RP/0/RP0/CPU0:XR01(config-if)#ipv4 address 12.12.12.12 255.255.255.255
RP/0/RP0/CPU0:XR01(config-if)#show configuration
!! Building configuration...
!! IOS XR Configuration 24.3.1
interface Loopback12
 ipv4 address 12.12.12.12 255.255.255.255
!
end
RP/0/RP0/CPU0:XR01(config-if)#commit
```

最後の行まで、Loopback12 は存在しません。IOS XR の初日に「設定したのに何も起きない」となる原因は、
ほとんどがこれです。

`write memory` はありません。コミットした変更は、その時点で保存されています。

`abort` はコンフィギュレーション モードを抜け、入力した内容を捨てます。`end` もモードを抜けますが、
コミットしていない行があると、先にどうするかを尋ねます。

```console
RP/0/RP0/CPU0:XR01(config-if)#end
Uncommitted changes found, commit them before exiting(yes/no/cancel)? [cancel]:
```

`do` は、IOS と同じく、コンフィギュレーション モードから EXEC コマンドを実行します。

この仕組みで何ができるかは、単元 M1 で扱います。いまは `show configuration` と `commit` の 2 つを覚えておきます。

## 6. ルーティング テーブル

```console
RP/0/RP0/CPU0:XR01#show route

Gateway of last resort is 10.0.12.2 to network 0.0.0.0

S*   0.0.0.0/0 [1/0] via 10.0.12.2, 00:04:44
L    1.1.1.1/32 is directly connected, 00:14:53, Loopback0
O    2.2.2.2/32 [110/2] via 10.0.12.2, 00:04:38, GigabitEthernet0/0/0/0
C    10.0.12.0/24 is directly connected, 00:04:44, GigabitEthernet0/0/0/0
L    10.0.12.1/32 is directly connected, 00:04:44, GigabitEthernet0/0/0/0
C    10.0.21.0/24 is directly connected, 00:14:53, GigabitEthernet0/0/0/2
L    10.0.21.1/32 is directly connected, 00:14:53, GigabitEthernet0/0/0/2
B    198.51.100.0/24 [20/0] via 10.0.12.2, 00:04:12
```

- (上の出力では、ルート コードの凡例と一部のループバックのルートを省いています。)コマンドは `show route` です。
  VRF には `vrf <名前>`、IPv6 には `ipv6` を付けます。プロトコル名を付けると絞り込めます(`show route ospf`)。
- `L` は、接続ネットワーク上のルータ自身のアドレスで、/32 として別に載ります。
- プレフィックスを指定すると詳細が出ます。どのプロセスが入れたルートかも分かります。

```console
RP/0/RP0/CPU0:XR01#show route 0.0.0.0/0

Routing entry for 0.0.0.0/0
  Known via "static", distance 1, metric 0, candidate default path
  Installed Oct 12 13:44:48.794 for 00:00:05
  Routing Descriptor Blocks
    10.0.12.2
      Route metric is 0
  No advertising protos.
RP/0/RP0/CPU0:XR01#show route 9.9.9.9/32

% Network not in table
```

プロトコルのコマンドも `ip` が取れます。`show ospf neighbor`、`show ospf interface brief`、`show bgp summary` です。

```console
RP/0/RP0/CPU0:XR01#show ospf interface brief

Interfaces for OSPF 1

Interface          PID   Area            IP Address/Mask    Cost  State Nbrs F/C
Lo0                1     0               1.1.1.1/32         1     LOOP  0/0
Gi0/0/0/0          1     0               10.0.12.1/24       1     P2P   1/1
Gi0/0/0/2          1     0               10.0.21.1/24       50    P2P   1/1
```

## 7. 知らないコマンドの探し方

実践の課題では、コマンドは示されません。探し方は次のとおりです。

**CLI に聞く。** `?` はどの階層でも使え、**木構造のその位置で**有効なものを一覧します。
期待したキーワードが無いときは、たいてい階層を間違えています。3 節の内容からして、これがいちばん多い誤りです。
`show running-config ?` は、指定できる枝を一覧します。

**いまある設定から始める。** 機能を変更する前に、実行コンフィギュレーションのその枝を表示します。
既存の行が、階層と綴りを教えてくれます。

**正しい文書を引く。** Cisco は、IOS XR の文書をプラットフォームごとに公開しています。IOS XRv 9000 は
ASR 9000 シリーズの文書を使います。文書は 2 種類あり、答える問いが違います。

| 文書 | 使う場面 |
|---|---|
| コンフィギュレーション ガイド(Routing、Interface and Hardware Component、MPLS、L3VPN、System Security など) | 実現したいことは分かっていて、手順と考え方が知りたいとき |
| コマンド リファレンス(同じ巻構成) | コマンドは分かっていて、構文、既定値、モードが知りたいとき |

- コンフィギュレーション ガイド: <https://www.cisco.com/c/en/us/support/routers/asr-9000-series-aggregation-services-routers/products-installation-and-configuration-guides-list.html>
- コマンド リファレンス: <https://www.cisco.com/c/en/us/support/routers/asr-9000-series-aggregation-services-routers/products-command-reference-list.html>

この単元で使う章は、Routing Configuration Guide の「Implementing OSPF」と「Implementing Static Routes」、
Interface and Hardware Component Configuration Guide の「Configuring Ethernet Interfaces」です。

## 8. IOS から IOS XR へ — 最初の読み替え

| IOS で打つもの | IOS XR では |
|---|---|
| `enable` | なし(権限はユーザのタスク グループで決まる) |
| `show ip interface brief` | `show ipv4 interface brief` / `show ipv6 interface brief`(`ip` の形は非推奨) |
| `show ip route` | `show route`(`vrf <名前>`、`ipv6`、`ospf` など) |
| `show … \| include a\|b` | `show … \| include "a\|b"` |
| `show ip ospf neighbor` | `show ospf neighbor` |
| `ip address 10.0.0.1 255.255.255.0` | `ipv4 address 10.0.0.1 255.255.255.0` |
| `interface …` / `ip ospf 1 area 0` | `router ospf 1` / `area 0` / `interface …` |
| `ip route 0.0.0.0 0.0.0.0 10.0.12.2` | `router static` / `address-family ipv4 unicast` / `0.0.0.0/0 10.0.12.2` |
| `vrf definition X` + `vrf forwarding X` | `vrf X` + インターフェイスの下で `vrf X` |
| (各行がその場で有効になる) | `commit` |
| `write memory` | なし(コミットは保存済み) |

## 実践

ワークスペースでラボ **XRT-01** を開き、M0 の課題に取り組みます。XR01 は設定が途中の状態です。
変更する前に、何が入っているかを調べます。
