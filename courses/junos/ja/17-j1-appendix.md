# J1 — 付録

## 1. 評価の順の早見表

1 つの経路が import・export のポリシーを通る順です。

1. 並べたポリシー(連鎖)を左から 1 つずつ。
2. ポリシーの中は term を上から 1 つずつ。term の外の `then` は、名前の無い最後の term。
3. term の `from` は、違う種類の条件がすべて当たり(AND)、同じ種類の値はどれか 1 つ当たれば(OR)当たる。
   route-filter・prefix-list・prefix-list-filter は合わせて 1 つの並びとして、最長一致の 1 本の型で決まる。
4. 当たった term の `then` を実行する。
   - `accept`・`reject`: ここで終わり。
   - `next policy`: 残りの term を飛ばして次のポリシーへ。
   - 属性を変える動作だけ・`next term`: 次の term へ。
5. どのポリシーでも決まらなければ、プロトコルの既定のポリシー。BGP の import は受け入れ、OSPF の export は拒む。

## 2. 一致の型の早見表

| 一致の型 | 当たるもの | IOS の prefix-list で言うと |
|---|---|---|
| `P/n exact` | P/n そのもの | `P/n` |
| `P/n orlonger` | P/n と、その中のすべて | `P/n le 32` |
| `P/n longer` | その中のすべて(P/n 自身は除く) | `P/n ge n+1` |
| `P/n upto /m` | P/n から長さ m まで | `P/n le m` |
| `P/n prefix-length-range /a-/b` | その中で長さ a〜b | `P/n ge a le b` |
| `P/n through Q/m` | P/n から Q/m までの道筋の上のもの | — |
| `prefix-list 名前` | 並びのプレフィックスそのもの | — |
| `prefix-list-filter 名前 型` | 並びのプレフィックスに型を付けて | — |

## 3. この仮想ルータの事情

### 3.1 PTX の既定の BGP ポリシーは、文書と違う

Juniper の BGP User Guide は、PTX のルータの既定の BGP ポリシーが、ほかの Junos のルータと違うと書いています。PTX は
フォワーディング テーブルに収まるプレフィックスが少ないので、既定では BGP の経路をフォワーディング テーブルに入れません。
そのための既定のポリシー `junos-ptx-series-default` があり、BGP の経路(inet.0・inet6.0)に `no-install-to-fib` を付けて、
`routing-options forwarding-table default-export` で当てると説明されています。入れたい経路には、自分の export ポリシーで
`install-to-fib` を付けます。

このラボのルータ(vJunos-Evolved、Junos OS Evolved 26.2R1.7、`Model: ptx10001-36mr`)では、同じ名前のポリシーが同じ場所に
当たっていますが、中身が違います。

```console
admin@jun02> show policy junos-ptx-series-default
Policy junos-ptx-series-default: [CHANGED/RESOLVED]
    Term t1:
        then
               load-balance per-flow
```

`no-install-to-fib` の term がありません。BGP の経路はフォワーディング テーブルに入り(`show route forwarding-table` に `user` で
並ぶ)、JUN02 は BGP の経路で転送します。ですから、このトラックのラボでは、ほかの Junos のルータと同じく、BGP の経路は使われれば
そのまま転送に使われます。

文書の記述が古い PTX(Junos OS)のままなのか、Junos OS Evolved やこの仮想ルータで違うのかは、文書からは分かりません。
本物の PTX を扱う時は、その機器で `show policy junos-ptx-series-default` を見てください。

### 3.2 BGP のライセンスの知らせ

OSPF と同じく、BGP を設定すると commit と `show bgp …` で `warning: requires 'BGP' license` が出ます。BGP は動きます。
扱いは J0 の付録で OSPF について書いたのと同じです。

## 4. 確かめのコマンドの早見表

| 知りたいこと | コマンド |
|---|---|
| 書いたポリシー | `show policy-options policy-statement 名前`(設定)・`show policy 名前`(読み込んだ形) |
| 当てたポリシー(BGP) | `show bgp neighbor 隣 \| match "Import\|Export"` |
| 当てたポリシー(OSPF) | `show configuration protocols ospf` の `export` の行 |
| BGP で受け取って使っている経路 | `show route receive-protocol bgp 隣` |
| BGP で受け取ったが使っていない経路 | `show route receive-protocol bgp 隣 hidden` と、`show route プレフィックス hidden extensive` の `Hidden reason:` |
| 数 | `show bgp summary` のピアの下の `active/received/accepted/damped` |
| BGP で広告している経路 | `show route advertising-protocol bgp 隣` |
| OSPF に出した外部経路 | 隣で `show ospf database external extensive`(`Type:`・`Metric:`) |
| 属性 | `show route プレフィックス exact detail`(`Localpref:`・`Communities:`・`AS path:`) |
| community で選ぶ | `show route community 65000:200` |
| 集約と寄与する経路 | `show route プレフィックス exact detail` の `Contributing Routes` |
| 当てる前の試し | `test policy 名前 プレフィックス`(既定を accept と数える・hidden の経路は評価しない) |

## 5. 調べる場所

- 『Routing Policies, Firewall Filters, and Traffic Policers User Guide』: ポリシーの構造・条件・動作・連鎖・route-filter・
  既定のポリシーの表・`test policy`。この単元のほとんどはここにあります。
- 『BGP User Guide』: BGP の設定、ポリシーを書く階層、RFC 8212 の扱い、PTX の既定の BGP ポリシー。
- 『OSPF User Guide』: OSPF の import と export、外部経路の metric の型。
- 機器の中: `help apropos 語`(設定の文の中から語を探す)と `?`。

:::note
出典: Juniper Networks『BGP User Guide』(2026-07-09)の「Understanding the Default BGP Routing Policy on Packet Transport Routers
(PTX Series)」と「Example: Overriding the Default BGP Routing Policy on PTX Series Packet Transport Routers」。この内容は
Juniper の古い版の文書の頁(Junos OS Release 12.1 以降の例)と同じ文です。『Routing Policies, Firewall Filters, and Traffic
Policers User Guide』(2026-06-23)の一致の型の表と評価の節。出力は containerlab の vJunos-Evolved(Junos OS Evolved 26.2R1.7)で
取ったものです。
:::
