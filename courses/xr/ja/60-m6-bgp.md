# M6 — BGP

BGP はもう知っています。セッション、属性、パス選択です。この単元で扱うのは、IOS XR での BGP の組み立て方と、
IOS から持ち込んだ習慣が裏目に出る場所です。M5 の上に積み上げます。IOS XR では、BGP のルートに対して行うことの大半を
ルート ポリシーで行います。

この単元の出力は、IOS XRd 26.1.1(ラボ XRT-03)で取得したものです。同じ BGP のコマンドは IOS XRv 9000 26.1.1 でも同じ結果になりました。

## 1. 設定の組み立て

IOS では、ネイバーを `neighbor … remote-as` で作り、アドレス ファミリごとに `neighbor … activate` で有効にします。
IOS XR の設定は木の形をしています。

```console
router bgp 65000
 bgp router-id 1.1.1.1
 address-family ipv4 unicast
  network 203.0.113.0/24
 !
 neighbor 10.0.11.2
  remote-as 65101
  description ISP-A
  address-family ipv4 unicast
   route-policy ISP-IN(200, 101) in
   route-policy ISP-OUT(1001, 0) out
  !
 !
```

- アドレス ファミリは、まずプロセスで有効にする必要があります(`router bgp` の直下の `address-family ipv4 unicast`)。
  そのあとで初めて、ネイバーがそれを使えます。
- ネイバーがあるアドレス ファミリで有効なのは、その下にアドレス ファミリが書かれているからです。`activate` はありません。
- セッションの設定(相手の AS、送信元、タイマー、パスワード)はネイバーの直下に置きます。ルートに関わる設定
  (ポリシー、next-hop-self、コミュニティの送信、プレフィックスの上限)は、ネイバーのアドレス ファミリの下に置きます。

## 2. ループバック間の iBGP

社内のピアは、ふつうループバックの間で張ります。リンクが 1 本落ちてもセッションが残るようにするためです。必要なものは 2 つで、
IOS XR の扱いは IOS と同じです。

- **送信元アドレス。** `update-source` が無いと、XR01 は出力インターフェイスからセッションを開きます。XR01 をループバックでしか
  知らない相手は接続を拒否し、セッションは Active のままです。ネイバーの下の `update-source Loopback0` で直ります。
- **ネクスト ホップ。** iBGP は、eBGP で学習したルートのネクスト ホップを変えません。RT04 はプロバイダのルートを、
  到達できないプロバイダのアドレスをネクスト ホップとして受け取ります。

```console
RT04#show ip bgp 11.0.0.0
BGP routing table entry for 11.0.0.0/8, version 0
Paths: (1 available, no best path)
  65101
    10.0.11.2 (inaccessible) from 1.1.1.1 (1.1.1.1)
      Origin IGP, metric 0, localpref 200, valid, internal
      Community: 65000:101
```

ネイバーのアドレス ファミリの下の `next-hop-self` で、XR01 は自身をネクスト ホップとしてアナウンスします。リンクのサブネットを
IGP で運んでも動きますが、外部のアドレスを社内のルーティングに入れることになります。

この出力には、eBGP との違いが 2 つ見えます。

- ルートは、iBGP のネイバーに**ルート ポリシーが無くても**届きました。M5 の既定の破棄は eBGP にだけ効きます。
- ルートは**コミュニティ**を持ったまま届きました。XR01 は iBGP のネイバーには既定でコミュニティを送ります。
  `send-community-ebgp` が要るのは eBGP のネイバーだけです。

## 3. 再配送

ほかのプロトコルのルートは、プロセスのアドレス ファミリの下の `redistribute` で BGP に入ります。ほかの付け所と同じく
ルート ポリシーを取り、ポリシーが無いと、元のプロトコルのルートを、ループバックやリンクのサブネットも含めてすべて取り込みます。

```console
router bgp 65000
 address-family ipv4 unicast
  redistribute ospf 1 route-policy OSPF-TO-BGP
```

再配送したルートは、BGP テーブルにはローカルに生成されたものとして、オリジン incomplete、IGP のメトリックを MED として現れます。

```console
RP/0/RP0/CPU0:XR01#show bgp ipv4 unicast 203.0.113.128/26
...
  Local
    10.0.14.2 from 0.0.0.0 (1.1.1.1)
      Origin incomplete, metric 2, localpref 100, weight 32768, valid, redistributed, best, group-best
```

再配送したルートが次にどこへ行くかは、発信ポリシーが決めます。`ge` も `le` も付けずに書いた prefix-set のエントリは、
そのプレフィックスだけに一致します。したがって `203.0.113.0/24` の発信フィルタは、/26 のプレフィックスを外に出しません。

## 4. プリペンドと、apply の罠

`prepend as-path own-as <n>` は自身の AS を n 回足し、`prepend as-path <AS> <n>` はほかの番号を足します。
回数 0 は受け付けられ、何もしません。このため回数をパラメータにできます。

罠は、書き換えとフィルタのポリシーを組み合わせるところにあります。ISP-OUT がプロバイダの受け取ってよいものを決めているとして、
ISP-B 用に新しいポリシーを書いたとします。

```console
route-policy B-OUT
  apply ISP-OUT(1002)
  prepend as-path own-as 3
end-policy
```

「ISP-OUT が許すものを、プリペンドして」と読めます。そうではありません。ISP-OUT が drop したルートは破棄されます。
しかし ISP-OUT が pass しなかったルートは、未決のまま ISP-OUT の終わりに達し、B-OUT に戻るだけです。そこで `prepend` が
それを書き換え、書き換えたルートは受け入れられます(M5)。ラボで測ると、ISP-B は ISP-A から学習したすべてのルートと、
「ISP-B にアナウンスしない」印の付いた顧客のルートを、すべてプリペンドされた状態で受け取りました。

正しい書き方は 2 つです。

- apply したポリシーを条件として使う: `if apply ISP-OUT(1002) then prepend as-path own-as 3 endif`。
  この条件は、apply したポリシーが pass したルートについて真になります。
- プリペンドをフィルタのポリシー自体に入れ、回数をパラメータにする。

## 5. テンプレート

IOS XR には、ネイバー用のテンプレートが 3 種類あります。

| テンプレート | 持つもの |
|---|---|
| `session-group` | セッションの設定だけ(相手の AS、送信元、タイマー、パスワード…) |
| `af-group 名前 address-family …` | 1 つのアドレス ファミリの設定だけ(ポリシー、コミュニティの送信、プレフィックスの上限…) |
| `neighbor-group` | 両方。そのアドレス ファミリは af-group を使うこともできる |

ネイバーは `use neighbor-group 名前` で neighbor-group を、アドレス ファミリは `use af-group 名前` で af-group を取り込みます。
ネイバーは自身で設定していない値をすべて継承し、自身で設定した値が勝ちます。したがって、設定をテンプレートに移すときは、
ネイバーからも外す必要があります。

実行コンフィギュレーションは、`inheritance` を付けても継承した値を表示しません(M3 の OSPF と同じ振る舞いです)。
次のコマンドは表示し、値ごとに出どころを付けます。`n:` は neighbor-group、`a:` は af-group、`[]` はネイバー自身です。

```console
RP/0/RP0/CPU0:XR01#show bgp neighbor 10.0.11.2 configuration
neighbor 10.0.11.2
 remote-as 65101              []
 description ISP-A            []
 address-family IPv4 Unicast  []
  maximum-prefix 1000 80      [n:ISP     a:ISP-AF]
  policy ISP-IN(200, 101) in  []
  policy ISP-OUT(1001, 0) out []
  send-community-ebgp         [n:ISP     a:ISP-AF]
```

`show bgp neighbor-group 名前 configuration` と `show bgp af-group 名前 configuration` は、テンプレートを同じように表示します。
パラメータ付きのポリシー(M5)とテンプレートは組み合わせて使えます。テンプレートがすべてのプロバイダに共通のものを持ち、
各ネイバーが自身の値を渡したポリシーを持ちます。

## 6. パスの見方とコマンドの名前

パス選択は知っている順序に従います(weight、ローカル プリファレンス、ローカル生成、AS パス長、オリジン、MED、
iBGP より eBGP、ネクスト ホップまでの IGP メトリック、そして決着用の項目)。あるパスが選ばれた理由は、比較を求めて確かめます。

```console
RP/0/RP0/CPU0:XR01#show bgp ipv4 unicast 11.0.0.0/8 bestpath-compare
...
  Path #1: Received by speaker 0
    10.0.11.2 from 10.0.11.2 (101.101.101.101), if-handle 0x00000000
      Origin IGP, metric 0, localpref 200, valid, external, best, group-best
      best of AS 65101, Overall best
  Path #2: Received by speaker 0
    10.0.12.2 from 10.0.12.2 (102.102.102.102), if-handle 0x00000000
      Origin IGP, metric 0, localpref 100, valid, external, group-best
      best of AS 65102
      Lower local preference than best path (path #1)
```

負けたパスの末尾には、どの段階で負けたかが表示されます。

| IOS | IOS XR |
|---|---|
| `show ip bgp summary` | `show bgp ipv4 unicast summary`(または `show bgp summary`) |
| `show ip bgp` | `show bgp ipv4 unicast` |
| `show ip bgp neighbors X routes` | `show bgp ipv4 unicast neighbors X routes` |
| `show ip bgp neighbors X advertised-routes` | `show bgp ipv4 unicast neighbors X advertised-routes` |
| `show ip bgp neighbors X` | `show bgp neighbor X` |
| — | `show bgp neighbor X configuration`(値ごとの出どころ付き) |
| `clear ip bgp X soft in` | `clear bgp ipv4 unicast X soft in` |
| `neighbor X route-map M in` | ネイバーのアドレス ファミリの下の `route-policy P in` |
| `neighbor X activate` | ネイバーの下のアドレス ファミリ |
| `neighbor X maximum-prefix 1000 80` | ネイバーのアドレス ファミリの下の `maximum-prefix 1000 80` |
| `neighbor X peer-group G` | `use neighbor-group G` |

## 実践

ラボ **XRT-03** に移り、M5 の課題の後に M6 の課題に取り組んでください。

<p class="tolab"><a href="/_learn?id=XRT-03">ラボ XRT-03 をワークスペースで開く</a> — <a href="61-m6-practice.html">課題</a></p>

:::note
出典: ASR 9000 向け IOS XR の *Routing Configuration Guide*、*Implementing BGP* と *Implementing Routing Policy*(2026 年 10 月に確認)。
次は IOS XRd 26.1.1 の実測によるものです: 4 節の `apply` の罠、プリペンドの回数 0、`send-community-ebgp` なしで iBGP に
コミュニティが送られること、実行コンフィギュレーションが継承した値を表示しないこと。
:::
