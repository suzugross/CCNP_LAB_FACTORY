# J1 — route-filter: プレフィックスと長さで選ぶ

## 1. なぜ route-filter なのか

### 1.1 困りごと: 範囲と長さの両方で選びたい

ISP から来る経路を選ぶとき、条件はたいてい 2 つ重なります。「どの範囲の中か」(私的アドレスの 10.0.0.0/8 の中か)と、
「長さはいくつか」(/24 より長い細かい経路か)です。範囲だけでも長さだけでも足りません。

### 1.2 それ以前の手

IOS の prefix-list は、プレフィックスに `ge` と `le` を付けて長さの範囲を書きます。`ip prefix-list P permit 10.0.0.0/8 le 32` が
「10.0.0.0/8 とその中のすべて」、`permit 0.0.0.0/0 ge 25` が「長さ 25 以上のすべて」です。上から順に調べ、最初に当たった行で
決まり、どれにも当たらなければ暗黙の deny です。IOS XR の prefix-set も同じ考え方で、`ge`・`le` か `eq` を使います。

### 1.3 Junos の答え

Junos の **route-filter** は、プレフィックスと**一致の型**(match type)の組です。`10.0.0.0/8 orlonger` が「10.0.0.0/8 と
その中のすべて」、`0.0.0.0/0 prefix-length-range /25-/32` が「長さ 25〜32 のすべて」です。route-filter は term の `from` に
書く条件の 1 つなので、ほかの条件(出どころ・隣など)と組み合わせて使えます。

## 2. 仕組み

### 2.1 route-filter の形

```
from {
    route-filter プレフィックス/長さ 一致の型;
    route-filter プレフィックス/長さ 一致の型 動作;     ← route-filter ごとに動作を付けることもできる(2.4 節)
}
```

経路はまずプレフィックスの範囲で比べられ、次に一致の型で長さを比べられます。

### 2.2 一致の型

ISP から JUN02 に届いている 10 本の経路(0.0.0.0/0・10.200.0.0/16・100.64.0.0/10・172.31.0.0/16・192.0.2.0/24・
192.168.50.0/24・198.18.0.0/15・198.51.100.0/24・198.51.100.128/25・203.0.113.0/24)を、型ごとに試した結果です。

| 一致の型 | 意味 | 試した route-filter | ISP の経路で当たったもの | IOS の prefix-list で言うと |
|---|---|---|---|---|
| `exact` | そのプレフィックスそのもの | `198.51.100.0/24 exact` | 198.51.100.0/24 | `198.51.100.0/24` |
| `orlonger` | それと、その中のもっと長いもの | `198.51.100.0/24 orlonger` | 198.51.100.0/24・198.51.100.128/25 | `198.51.100.0/24 le 32` |
| `longer` | その中のもっと長いものだけ(それ自身は含まない) | `198.51.100.0/24 longer` | 198.51.100.128/25 | `198.51.100.0/24 ge 25` |
| `upto /n` | それから長さ n まで | `0.0.0.0/0 upto /16` | 0.0.0.0/0・10.200.0.0/16・100.64.0.0/10・172.31.0.0/16・198.18.0.0/15 | `0.0.0.0/0 le 16` |
| `prefix-length-range /a-/b` | その中で、長さ a〜b のもの | `0.0.0.0/0 prefix-length-range /16-/24` | 10.200.0.0/16・172.31.0.0/16・192.0.2.0/24・192.168.50.0/24・198.51.100.0/24・203.0.113.0/24 | `0.0.0.0/0 ge 16 le 24` |
| `through プレフィックス` | そこから、指定したもっと長いプレフィックスまでの道筋の上にあるもの | `198.51.100.0/24 through 198.51.100.128/25` | 198.51.100.0/24・198.51.100.128/25 | (相当するものは無い) |

`prefix-length-range` の範囲に /0 は入りません。既定経路も残したいなら、`0.0.0.0/0 exact` を別に書きます。

### 2.3 同じ term に複数の route-filter: 最長一致の 1 本で決まる

同じ term の `from` に route-filter を何本か書くと、どれか 1 本に当たれば term に当たる(OR)と読めます。ただし、
Junos が最初にするのは**最長一致**です。経路のプレフィックスをいちばん長く含む route-filter を 1 本選び、その 1 本の一致の型だけを
見ます。型が合わなければ、ほかの route-filter が合っていても、その term は当たりません。Juniper の文書は
「プレフィックスに当たった route-filter で評価をやめる。一致の型が合わなくても」と書いています。

次の term で、ISP からの 198.51.100.128/25 を試します。

```
term t {
    from {
        route-filter 198.51.100.0/24 exact;
        route-filter 0.0.0.0/0 upto /25;
    }
    then accept;
}
then reject;
```

```console
admin@jun02> test policy LM 198.51.100.0/24

inet.0: 19 destinations, 19 routes (19 active, 0 holddown, 0 hidden)
+ = Active Route, - = Last Active, * = Both

198.51.100.0/24    *[BGP/170] 00:04:21, MED 0, localpref 100
                      AS path: 64500 I, validation-state: unverified
                    >  to 10.0.23.2 via et-0/0/1.0

Policy LM: 1 prefix accepted, 1 prefix rejected
```

198.51.100.128/25 は `0.0.0.0/0 upto /25` に収まります。それでも拒まれました。198.51.100.128/25 をいちばん長く含むのは
`198.51.100.0/24` の route-filter で、その型は `exact` だからです。ほかの経路(192.0.2.0/24 など)は `0.0.0.0/0` の 1 本だけに
含まれるので、`upto /25` で受け入れられます。

型を見てから短いほうへ戻る振る舞いにするには、`set policy-options defaults route-filter walkup` を入れます。入れると、
同じ試しで 198.51.100.128/25 も受け入れられました。walkup はルータ全体の振る舞いを変えるので、既にあるポリシーの結果も
変わり得ます。この単元では入れずに、範囲の重なる route-filter を別々の term に分けて書きます。

### 2.4 route-filter ごとの動作

route-filter の行の終わりに動作を書くと、その route-filter に当たった時は term の `then` の代わりにその動作をします。

```
term t {
    from {
        route-filter 198.51.100.0/24 exact accept;      ← /24 そのものは受け入れる
        route-filter 198.51.100.0/24 longer reject;     ← その中の細かい経路は拒む
        route-filter 192.0.2.0/24 exact;                ← 動作の無い行は term の then に従う
    }
    then {
        local-preference 300;
        accept;
    }
}
```

これで 198.51.100.0/24 は受け入れ、198.51.100.128/25 は拒まれました。同じプレフィックスを 2 行に書いた時は、上から順に型を調べ、
最初に合った行の動作になります。

### 2.5 prefix-list と prefix-list-filter

**prefix-list** は、名前を付けたプレフィックスの並びです。`policy-options` の下に作り、いくつものポリシーから名指しできます。

```
set policy-options prefix-list PL 198.51.100.0/24
```

`from prefix-list PL` は、並びのプレフィックス**そのもの**(exact)だけに当たります。長さの範囲は書けません。範囲を付けたい時は
`from prefix-list-filter PL orlonger` のように、一致の型を付けて名指しします。

| 書き方 | ISP の経路で当たったもの |
|---|---|
| `from prefix-list PL` | 198.51.100.0/24 |
| `from prefix-list-filter PL orlonger` | 198.51.100.0/24・198.51.100.128/25 |

IOS の prefix-list とは役割が違います。IOS では prefix-list そのものに permit・deny と `ge`・`le` を書きますが、Junos の
prefix-list はただの並びで、許すか拒むかはポリシーの `then` が決めます。

route-filter と prefix-list・prefix-list-filter を同じ term に並べると、違う種類の条件(AND)としては扱われません。全部が
1 つの並びとして最長一致で引かれ、2.3 節と同じく、経路をいちばん長く含む行の型(と、その行に書いた動作)だけで決まります。

```
term t {
    from {
        route-filter 0.0.0.0/0 prefix-length-range /8-/24;
        prefix-list-filter BOGONS orlonger reject;      ← BOGONS= 10.0.0.0/8・172.16.0.0/12・192.168.0.0/16 など
    }
    then accept;
}
then reject;
```

ISP の経路で試すと、10.200.0.0/16 は拒まれ、192.0.2.0/24 は受け入れられました。10.200.0.0/16 をいちばん長く含むのは BOGONS の
10.0.0.0/8 の行なので、その行の動作 reject になります。192.0.2.0/24 は BOGONS のどの行にも含まれず、0.0.0.0/0 の行で term の
accept になります。AND なら、BOGONS に当たらない 192.0.2.0/24 は外れるはずです。

逆に、いちばん長い行の型が外れると、短い行が合っていても term は外れます。`route-filter 198.51.100.0/24 exact` と、0.0.0.0/0 だけの
並びの `prefix-list-filter … orlonger` を並べると、198.51.100.128/25 は拒まれました。型の無い `prefix-list` も同じ並びに入ります。

Juniper の文書は、route-filter と prefix-list などを組み合わせると「OR か最長一致で評価する」とだけ書き、どちらになるかは
書いていません。試すと最長一致でした。2.2 節の AND と読み違えやすいので、この単元では、拒む範囲と受け入れる範囲を別々の term に書きます。

### 2.6 IOS・IOS XR と並べる

| 選びたいもの | IOS の prefix-list | IOS XR の prefix-set | Junos の route-filter |
|---|---|---|---|
| 10.0.0.0/8 とその中のすべて | `10.0.0.0/8 le 32` | `10.0.0.0/8 le 32` | `10.0.0.0/8 orlonger` |
| 長さ /25 以上のすべて | `0.0.0.0/0 ge 25` | `0.0.0.0/0 ge 25` | `0.0.0.0/0 prefix-length-range /25-/32` |
| 長さ /8〜/24 のすべて | `0.0.0.0/0 ge 8 le 24` | `0.0.0.0/0 ge 8 le 24` | `0.0.0.0/0 prefix-length-range /8-/24` |
| 既定経路だけ | `0.0.0.0/0` | `0.0.0.0/0` | `0.0.0.0/0 exact` |
| 評価の順 | 行の順(最初に当たった行) | 集まり(`if destination in` で調べる) | 最長一致の 1 本(walkup で変えられる) |
| 当たらない時 | 暗黙の deny | `if` が偽になる | term に当たらない → 次の term へ |

## 3. 設定例

### 3.1 ISP 自身の網と既定経路だけを受け入れる

JUN02 が ISP から受け取る経路のうち、ISP 自身の網(203.0.113.0/24 とその中の /25 まで)と既定経路だけを受け入れます。

:::config JUN02 — ISP から受け入れる経路を範囲と長さで選ぶ
set policy-options policy-statement ISP-OWN term OWN from route-filter 203.0.113.0/24 upto /25 ## 203.0.113.0/24 から /25 まで
set policy-options policy-statement ISP-OWN term OWN then accept                            ## 
set policy-options policy-statement ISP-OWN term DEFAULT from route-filter 0.0.0.0/0 exact  ## 既定経路そのもの
set policy-options policy-statement ISP-OWN term DEFAULT then accept                        ## 
set policy-options policy-statement ISP-OWN term REST then reject                           ## 残りを拒む。無ければ BGP の既定(受け入れ)へ
set protocols bgp group ISP import ISP-OWN                                                  ## ISP の group の入口に当てる
:::

`0.0.0.0/0` の route-filter は、どの経路のプレフィックスも含みます。ほかの route-filter と同じ term に書くと、
2.3 節の最長一致に気を付ける必要があります。ここでは term を分けました。

結果の例:

```console
admin@jun02> show route receive-protocol bgp 10.0.23.2 table inet.0

inet.0: 19 destinations, 19 routes (11 active, 0 holddown, 8 hidden)
  Prefix                  Nexthop              MED     Lclpref    AS path
* 0.0.0.0/0               10.0.23.2            0                  64500 I
* 203.0.113.0/24          10.0.23.2            0                  64500 I

admin@jun02> show route receive-protocol bgp 10.0.23.2 hidden table inet.0

inet.0: 19 destinations, 19 routes (11 active, 0 holddown, 8 hidden)
  Prefix                  Nexthop              MED     Lclpref    AS path
  10.200.0.0/16           10.0.23.2            0                  64500 I
  100.64.0.0/10           10.0.23.2            0                  64500 I
  172.31.0.0/16           10.0.23.2            0                  64500 I
  192.0.2.0/24            10.0.23.2            0                  64500 I
  192.168.50.0/24         10.0.23.2            0                  64500 I
  198.18.0.0/15           10.0.23.2            0                  64500 I
  198.51.100.0/24         10.0.23.2            0                  64500 I
  198.51.100.128/25       10.0.23.2            0                  64500 I
```

受け入れなかった経路は消えずに hidden として残ります。なぜ使われないかは `show route 10.200.0.0/16 hidden extensive` の
`Hidden reason:` の行に出ます(次のページの 2.3 節)。

## 実践

ラボ **JNT-02** に移り、課題 J1-3 に取り組みます。

<p class="tolab"><a href="/_learn?id=JNT-02">ワークスペースでラボ JNT-02 を開く</a> — <a href="14-j1-practice-2.html">課題</a></p>

:::note
出典: Juniper Networks『Routing Policies, Firewall Filters, and Traffic Policers User Guide』(2026-06-23)の route-filter の
一致の型の節、「How Route Filters Are Evaluated in Routing Policy Match Conditions」(最長一致・型が合わなくても評価をやめる・
walkup の注記・同じプレフィックスは上から)、prefix-list と prefix-list-filter の節。route-filter・prefix-list・source-address-filter
の組み合わせは同書の match conditions の節(p.61)の「evaluated according to a logical OR operation or a longest-route match lookup」で、
どちらになるかの記述は同書にも Day One『Configuring Junos Policy and Firewall Filters』にも無く、実機で確かめた(walkup なし)。
IOS XR の prefix-set は IOS XR トラック M5 による。
出力は containerlab の vJunos-Evolved(Junos OS Evolved 26.2R1.7)で取ったものです。
:::
