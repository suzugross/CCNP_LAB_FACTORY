# M3 — OSPF

OSPF はもう知っています。この単元で扱うのは、IOS XR での書き方と、IOS から持ち込んだ習慣が裏目に出る 3 つの場所だけです。

ここに示す出力は、すべて IOS XRv 9000 リリース 24.3.1 で取得したものです。

## 1. 1 つのブロック、3 つの階層

IOS では、OSPF は 2 か所に住んでいます。`router ospf` のブロックと、インターフェイス(`ip ospf …` の行)です。
IOS XR では、すべてが `router ospf` のブロックの中に、3 つの階層で住んでいます。

| 階層 | 持つもの |
|---|---|
| プロセス | ルータ ID と、すべてのエリアの既定値 |
| エリア | エリアの種類、集約、そのエリアのすべてのインターフェイスの既定値 |
| インターフェイス | ここに列挙されることでエリアに参加する。そのインターフェイスだけの設定 |

`network` 文は無く、インターフェイス自体の下にも OSPF の設定はありません(M0)。

## 2. 継承

インターフェイスの設定の多く(ネットワーク タイプ、コスト、タイマー、認証、passive)は、3 つの階層のどこにでも書けます。
プロセス単位の設定は、すべてのエリアのすべてのインターフェイスに効き、エリア単位の設定はそのエリアのすべてのインターフェイスに効きます。
インターフェイスにいちばん近い階層の設定が勝ちます。

便利ですが、1 行も書かれていないリンクが設定されてしまうのもこの仕組みです。次の例では、passive をプロセス単位で設定し、
LINK1 だけがそれを解除しています。

```console
router ospf 1
 router-id 1.1.1.1
 passive enable
 area 0
  interface Loopback0
  !
  interface GigabitEthernet0/0/0/0
   network point-to-point
   passive disable
  !
  interface GigabitEthernet0/0/0/2
   network point-to-point
  !
```

LINK2(Gi0/0/0/2)は OSPF に入っていて、ネットワーク タイプも正しく、それでも隣接関係を作りません。
LINK2 の項目は passive について何も言っていません。インターフェイスの表示は言っています。

```console
RP/0/RP0/CPU0:XR01#show ospf interface GigabitEthernet0/0/0/2
GigabitEthernet0/0/0/2 is up, line protocol is up
  Internet Address 10.0.21.1/24, Area 0, SID 0, Strict-SPF SID 0
  Process ID 1, Router ID 1.1.1.1, Network Type POINT_TO_POINT, Cost: 1
  Timer intervals configured, Hello 10, Dead 40, Wait 40, Retransmit 5
    No Hellos (Passive interface)
```

`show running-config router ospf 1 inheritance detail` は継承した値を表示するためのものです。このリリースでは、
継承した passive に何の注記も付きませんでした。実際に効いている状態は `show ospf interface` で読みます。

プロセス単位の `passive enable` と、隣接関係を作るべきリンクでの `passive disable` の組み合わせは、よくある設計です。
新しいインターフェイスは、誰かが決めるまで黙っています。黙っているリンクを、プロセス単位の行を消して「直す」前に、このことを思い出します。

`show ospf interface brief` が、インターフェイスごとに 1 行の概要を出します。

```console
Interface          PID   Area            IP Address/Mask    Cost  State Nbrs F/C
Lo0                1     0               1.1.1.1/32         1     LOOP  0/0
Gi0/0/0/0          1     0               10.0.12.1/24       1     P2P   1/1
Gi0/0/0/1          1     0               10.0.50.1/24       1     DR    0/0
Gi0/0/0/2          1     0               10.0.21.1/24       1     P2P   0/0
Gi0/0/0/3          1     1               10.0.23.1/24       1     P2P   0/0
```

## 3. OSPFv3

OSPFv3 は別のプロセス `router ospfv3` で、同じ 3 つの階層と同じ継承を持ちます。
show コマンドも名前に従います。`show ospfv3 neighbor`、`show ospfv3 interface`、`show ospfv3 database` です。

ラボで分かったことが 2 つあります。

- M0 のネットワーク タイプの罠は同じように働きます。XR01 が既定のブロードキャスト、RT01 がポイントツーポイントだと、
  隣接関係は FULL/DR になり、ルートは入りません。
- IPv6 のルーティング テーブルでは、OSPFv3 のルートはプロセス名 `ospf` で表示されます。

```console
RP/0/RP0/CPU0:XR01#show route ipv6 2001:db8::2/128
Routing entry for 2001:db8::2/128
  Known via "ospf 1", distance 110, metric 1, type intra area
```

## 4. エリア

エリアの種類と集約は、IOS で `area N` のキーワードで書くものを、エリアの下に書きます。
スタブ エリア、完全スタブ エリア(ABR がサマリー LSA を送らない)、NSSA、そして ABR で集約する `range` です。

hello のスタブ フラグは、IOS と同じく両端で一致する必要があります。片方だけがエリアをスタブと呼んでいると、隣接関係はできません。
両端をスタブにすると、拠点のルータはデフォルト ルートとすべてのエリア間ルートを受け取ります。

```console
RT02#show ip route ospf
O*IA  0.0.0.0/0 [110/11] via 10.0.23.1, 00:00:31, Ethernet0/0
O IA     1.1.1.1 [110/11] via 10.0.23.1, 00:00:31, Ethernet0/0
O IA     2.2.2.2 [110/12] via 10.0.23.1, 00:00:31, Ethernet0/0
...
```

完全スタブにするのは ABR だけの設定です。内部のルータは普通のスタブの設定のままです。

実行コンフィギュレーションは、ところどころ既定値を表示します。オプションなしで打った `range` は `range … advertise` と表示されます。

## 5. コマンドの名前

| IOS では | IOS XR では |
|---|---|
| `show ip ospf neighbor` | `show ospf neighbor` |
| `show ip ospf interface brief` | `show ospf interface brief` |
| `show ip ospf database` | `show ospf database` |
| `show ipv6 ospf neighbor` | `show ospfv3 neighbor` |
| `show ip route ospf` | `show route ospf` |
| `show ipv6 route` | `show route ipv6` |

OSPF への再配送とルートのフィルタは、IOS XR ではルート ポリシーで行います。M5 で扱います。

## 実践

ラボ **XRT-02** に移り、M2 の課題の後で M3 の課題に取り組みます。

<p class="tolab"><a href="/_learn?id=XRT-02">ワークスペースでラボ XRT-02 を開く</a> — <a href="31-m3-practice.html">課題の一覧</a></p>

:::note
出典: ASR 9000 向け IOS XR *Routing Configuration Guide* の *Implementing OSPF*(OSPF Hierarchical CLI and CLI Inheritance)、2026 年 10 月に確認。
次の点は 24.3.1 の実測によります。`inheritance detail` が継承した passive を注記しないこと、IPv6 のテーブルで OSPFv3 のルートが `ospf` と表示されること。
:::
