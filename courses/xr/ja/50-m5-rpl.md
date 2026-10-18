# M5 — ルーティング ポリシー言語

IOS では、プレフィックス リスト、AS パス アクセス リスト、コミュニティ リスト、ルート マップでルートを濾過し、書き換えます。
IOS XR は、これらをすべて 1 つの言語、ルーティング ポリシー言語(RPL)で置き換えます。IOS XR で BGP を少し触るとすぐに出会います。
ポリシーが無いと、eBGP のネイバーは何も交換しないからです。

この単元の出力は、IOS XRd 26.1.1(ラボ XRT-03)で取得したものです。同じコマンドは IOS XRv 9000 26.1.1 でも同じ結果になりました。

## 1. ポリシーが必要な理由

IOS XR は RFC 8212 に従います。着信ポリシーの無い eBGP ネイバーはルートを受け入れず、発信ポリシーが無ければ送りません。
セッションはいつもどおり上がり、ルートだけが欠けます。BGP の summary がそう告げ、該当するネイバーに `!` を付けます。

```console
RP/0/RP0/CPU0:XR01#show bgp ipv4 unicast summary
...
Some configured eBGP neighbors (under default or non-default vrfs)
do not have both inbound and outbound policies configured for IPv4 Unicast
address family. These neighbors will default to sending and/or
receiving no routes and are marked with '!' in the output below.
Use the 'show bgp neighbor <nbr_address>' command for details.

Neighbor        Spk    AS MsgRcvd MsgSent       TblVer  InQ OutQ  Up/Down  St/PfxRcd
10.0.11.2         0 65101       3       5            5    0    0 00:00:55          0!
10.0.12.2         0 65102       3       3            5    0    0 00:00:57          0!
```

ネイバーの詳細は、どちらの向きが欠けているかを示し、拒否した数を数えます。

```console
RP/0/RP0/CPU0:XR01#show bgp neighbor 10.0.11.2 | include "olic|denied|No policy|By policy"
  eBGP neighbor with no inbound or outbound policy; defaults to 'drop'
  Cumulative no. of prefixes denied: 5
    No policy: 5, Failed RT match: 0
    By ORF policy: 0, By policy: 0
```

「No policy」は、ポリシーがまったく無いために拒否したルートの数です。「By policy」は、ポリシーが破棄したルートの数です。
この 2 つのカウンタを覚えておいてください。2 種類の失敗を見分けられます。iBGP のネイバーは影響を受けません。

## 2. set

set は、ポリシーがルートを照らし合わせる名前付きの一覧です。IOS のリストに代わるものです。

| IOS | IOS XR |
|---|---|
| `ip prefix-list` | `prefix-set` |
| `ip as-path access-list` | `as-path-set` |
| `ip community-list` | `community-set` |
| `ip extcommunity-list` | `extcommunity-set` |

set はブロックとして書き、エントリをカンマで区切り、`end-set` でブロックを閉じます。

```console
prefix-set PRIVATE
  10.0.0.0/8 le 32,
  172.16.0.0/12 le 32,
  192.168.0.0/16 le 32
end-set
```

知っているものとの違いは次のとおりです。

- prefix-set のエントリは、プレフィックス リストと同じく `ge` と `le` を取りますが、シーケンス番号も permit／deny もありません。
  set が言うのは、ルートが一致するかどうかだけです。どうするかはポリシーの仕事です。
- すでにある set を入力すると、それを**置き換えます**。CLI は `Policy object prefix-set PS-24 exists!
  Reconfiguring it via CLI will replace current definition.` と警告します。エントリを 1 つ足すにも、set 全体を入力し直します。
- `as-path-set` のエントリは、`ios-regex '…'` と書く正規表現です。`community-set` のエントリには
  ワイルドカード(`65000:*`)や範囲を書けます。
- set は、条件の中にインラインでも書けます: `destination in (0.0.0.0/0, 0.0.0.0/0 ge 25)`。

## 3. ポリシーの判定のしかた

ポリシーは、`route-policy 名前` と `end-policy` の間に書く小さなプログラムです。

```console
route-policy RP-IN
  if destination in PS-24 then
    set community CS-TAG
    apply SET-LP(200)
  elseif destination in (172.16.2.0/25) and as-path in AS-ORIGIN then
    pass
  endif
end-policy
```

条件はルートを調べます。`destination in`(prefix-set)、`as-path in`(as-path-set)、`community matches-any`
または `matches-every`(community-set)、それに `as-path originates-from '65201'`、`as-path neighbor-is`、
`as-path length` などの補助があります。`and`、`or`、`not` で組み合わせ、`if`、`elseif`、`else`、`endif` で分岐します。

アクションは、ルートの行き先を決めるか、ルートを書き換えます。

| アクション | 効果 |
|---|---|
| `pass` | ルートを受け入れる。ポリシーは続けて実行されるので、後の文でまだ書き換えられる |
| `drop` | ルートを拒否する。ポリシーは止まる |
| `done` | ルートを受け入れる。ポリシーは止まる |
| `set …` | 属性を書き換える。書き換えられたルートは受け入れられる |

そして、いちばん大事な規則です。

**pass も done もされず、`set` で書き換えられもしないまま `end-policy` に達したルートは破棄されます。**

したがって上のポリシーは、タグを付けた /24 のプレフィックスと、pass する 1 つの /25 を受け入れます。それ以外はすべて終わりに達し、
それを示す行が 1 つも無いまま破棄されます。ラボでは、この規則の両面を測りました。

- `set local-preference 150` だけのポリシーは、すべてのルートをローカル プリファレンス 150 で受け入れました。
- `if destination in (11.0.0.0/8) then set local-preference 150 endif` だけのポリシーは、11.0.0.0/8 を受け入れ、
  それ以外をすべて破棄しました。

IOS の習慣が裏目に出るのはここです。ルート マップも暗黙の deny で終わりますが、「悪いものを捨てる」と書いたポリシー
(`if destination in PRIVATE then drop endif`)は完全なフィルタのように読めて、実際には何も受け入れません。
`endif` の後に `pass` が要ります。

## 4. パラメータと apply

ポリシーはパラメータを取れます。名前の後ろで宣言し、`$` を付けて使い、ポリシーを付ける場所で値を渡します。

```console
route-policy SET-LP($lp)
  set local-preference $lp
end-policy
```

これで 1 つのポリシーが、値を変えて複数のネイバーに使え、新しいネイバーに新しい定義は要りません。パラメータは値の中、
たとえばコミュニティの中にも置けます: `set community (65000:$tag) additive`。

`apply` は、ポリシーの中から別のポリシーを実行します。フィルタを写さずに再利用する方法です。apply したポリシーが破棄したルートは
破棄されたままで、pass したルートは呼び出し元のポリシーで続きます。

`set community` は、ルートが持つコミュニティを置き換えます。`additive` を付けると追加します。`delete community in
<set>` は、set に一致するものだけを取り除き、ほかは残します。

## 5. 付け所と確認

ポリシーは、付けるまで何もしません。BGP でふつう付ける場所は、ネイバーのアドレス ファミリの下です。

```console
router bgp 65000
 neighbor 10.0.11.2
  address-family ipv4 unicast
   route-policy ISP-IN(200, 101) in
   route-policy ISP-OUT out
```

ほかの付け所には、再配送(`redistribute … route-policy`)、`network`、`aggregate-address`、`default-originate`、
OSPF と IS-IS の同様の場所があります。すべての属性がすべての付け所にあるわけではありません。コミュニティを設定するポリシーは
OSPF への再配送には付けられず、コミットは
`Policy [RP-IN] uses the 'community' attribute. There is no 'community' attribute at the ospf redistribution attach point.` で失敗します。

ポリシーや set がどこで使われているかを見るには、次のようにします。

```console
RP/0/RP0/CPU0:XR01#show rpl route-policy ISP-IN attachpoints
BGP Attachpoint: Neighbor
Neighbor/Group     type  afi/safi    in/out  vrf name   bound by
---------------------------------------------------------------------
10.0.11.2          --    IPv4/uni    in      default    ISP-IN(200, 101)
10.0.12.2          --    IPv4/uni    in      default    ISP-IN(100, 102)
```

`show rpl prefix-set 名前 attachpoints` は set について同じことをします。`show rpl active route-policy` は使用中のポリシーを、
`apply` 経由でだけ使われているものも含めて並べます。`show rpl inactive route-policy` と `show rpl unused route-policy`
が残りを並べます。`show rpl route-policy 名前 detail` は、ポリシーを、それが使うすべての set とポリシーとともに表示します。

ポリシーが何をしたかは、ルートを見ます。

```console
RP/0/RP0/CPU0:XR01#show bgp ipv4 unicast 11.0.0.0/8
...
  Path #1: Received by speaker 0
  65101
    10.0.11.2 from 10.0.11.2 (101.101.101.101)
      Origin IGP, metric 0, localpref 200, valid, external, best, group-best
      Community: 65000:101
  Path #2: Received by speaker 0
  65102 65101
    10.0.12.2 from 10.0.12.2 (102.102.102.102)
      Origin IGP, metric 0, localpref 100, valid, external, group-best
      Community: 65000:102
```

`show bgp ipv4 unicast neighbors <アドレス> routes` はネイバーから受け入れたルートを、`advertised-routes` は
ネイバーに送ったルートを並べます。受信したままの(着信ポリシーにかける前の)ルートは、そのネイバーに `soft-reconfiguration inbound`
があるときだけ保持されます。無いと、`received routes` は着信のソフト再構成が有効でないと答えます。

## 6. ポリシーの変更

ポリシーや set の変更は、コミットした時点で効きます。XR01 は持っているルートを新しいポリシーにかけ直すので、`clear bgp` は要りません。
ラボでは、付けてある prefix-set に足したプレフィックスが、数秒のうちに BGP テーブルに現れました。

コミットは全体を検査し、成り立たないものを拒否します。

| やろうとしたこと | コミットが失敗するときのメッセージ |
|---|---|
| 存在しないポリシーを付ける | `Policy [NOPE] must be defined before it can be attached.` |
| 付いているポリシーを削除する | `Deletion of policy [PASS] is not allowed because it is in use at the bgp neighbor-out-dflt attach point.` |
| パラメータなしで付いているポリシーにパラメータを足す | `Mismatch in number of parameters passed to policy at an attachpoint.` |

どの場合も、直し方は 2 つの変更を同じコミットで行うことです。定義と付け外しを一緒に、取り外しと削除を一緒に、
定義の変更と付け所の変更を一緒に行います。失敗したコミットの後は、`show configuration failed` がメッセージを表示します(M1)。

## 7. ルート マップから RPL へ

| IOS | IOS XR |
|---|---|
| `route-map 名前 permit 10` + `match ip address prefix-list L` | `if destination in L then … endif` |
| シーケンス番号の順に評価 | `if` / `elseif` / `else` を順に書く |
| `continue` | 文はそのまま次へ続く。`pass` でポリシーは止まらない |
| 終わりに暗黙の deny | 終わりまでに pass も書き換えもされなかったルートは破棄 |
| permit 節の中の `set local-preference 200` | `set local-preference 200`(書き換え自体がルートを受け入れる) |
| 値の組ごとに 1 つのルート マップ | パラメータ付きの 1 つのポリシー |
| `neighbor … route-map 名前 in` | ネイバーのアドレス ファミリの下の `route-policy 名前 in` |
| `neighbor … send-community` | `send-community-ebgp`(影響するのは eBGP だけ。iBGP には既定でコミュニティを送る) |
| eBGP ネイバーにルート マップ無し: すべて通る | eBGP ネイバーにポリシー無し: 何も通らない |

## 実践

ラボ **XRT-03** に移り、M5 の課題に取り組んでください。

<p class="tolab"><a href="/_learn?id=XRT-03">ラボ XRT-03 をワークスペースで開く</a> — <a href="51-m5-practice.html">課題</a></p>

:::note
出典: ASR 9000 向け IOS XR の *Routing Configuration Guide*、*Implementing Routing Policy*(2026 年 10 月に確認)。
次は IOS XRd 26.1.1 と IOS XRv 9000 26.1.1 の実測によるものです: summary とネイバー詳細の文言、`pass` なしでも
`set` で書き換えたルートが受け入れられること、`clear bgp` なしで変更が効くこと、6 節のコミットのメッセージ。
:::
