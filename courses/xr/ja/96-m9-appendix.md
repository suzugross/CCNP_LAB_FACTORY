# M9 — 付録 ラベルの割り当て方、プロバイダーの間

この付録は、ラボの課題に出てこない M9 の話題を扱います。PE が VPN のラベルをどう割り当てるか、2 つのプロバイダーに
またがる VPN(ブループリントの 4.1.b)、顧客そのものがプロバイダーである場合(CSC、4.1.c)、そして IOS と IOS XR の
コマンドの対応です。ラベルの割り当て方には、ラボ XRT-09 で試せる「やってみる」があります。

## 1. VPN のラベルの割り当て方

### 1.1 何が変わるのか

PE は、VRF の経路にラベルを割り当て、経路と一緒にほかの PE へ配ります(ページ「L3VPN の仕組み」の 2.4 節)。
パケットがそのラベルを付けて戻ってきたとき、PE はラベルだけを手がかりに、パケットをどうするかを決めます。
いくつのラベルを割り当てるかで、PE が持つラベルの数と、パケットを受けたときの仕事が変わります。

| 方式 | ラベル 1 つが表すもの | そのラベルで受けたパケット | ラベルの数 |
|---|---|---|---|
| プレフィックスごと(per-prefix。IOS XR の既定) | VRF の経路 1 つ | 経路をくれた CE へそのまま送る | 経路の数 |
| CE ごと(per-ce) | 次のホップ(CE)1 つ | その CE へそのまま送る | CE の数 |
| VRF ごと(per-vrf) | VRF 1 つ | VRF のテーブルで宛先を引き直す | 1 つ |

どの方式でも、CE から学んだのではない経路には、VRF ごとのラベル(集約のラベル)が付きます。コマンド リファレンスは
接続の経路・集約・ローカルの経路を挙げ、ラボではグローバル テーブルから取り込んだデフォルト ルートもそうなりました。
次に送る CE が無いので、宛先を VRF のテーブルで引き直すしかないからです。

### 1.2 ラボで見る

ラボで 4 つの課題をすべて終えた後の XR01 です(既定のプレフィックスごと)。

```console
RP/0/RP0/CPU0:XR01#show bgp vrf CUST-A labels
   Network            Next Hop        Rcvd Label      Local Label
Route Distinguisher: 10.255.0.1:101 (default for vrf CUST-A)
*> 0.0.0.0/0          192.0.2.2       nolabel         24009
*> 10.101.1.0/24      172.16.11.2     nolabel         24004
*>i10.101.2.0/24      10.255.0.12     22              nolabel
*> 198.51.100.0/25    172.16.11.2     nolabel         24005
*>i198.51.100.128/25  10.255.0.12     23              nolabel

RP/0/RP0/CPU0:XR01#show mpls forwarding
Local  Outgoing    Prefix             Outgoing     Next Hop        Bytes
Label  Label       or ID              Interface                    Switched
------ ----------- ------------------ ------------ --------------- ------------
24000  20          10.255.0.21/32     Gi0/0/0/1    10.0.3.13       5123
24001  Pop         10.255.0.13/32     Gi0/0/0/1    10.0.3.13       4106
24002  16          10.255.0.12/32     Gi0/0/0/0    10.0.1.11       16120
24003  Pop         10.255.0.11/32     Gi0/0/0/0    10.0.1.11       2986
24004  Unlabelled  10.101.1.0/24[V]   Gi0/0/0/2    172.16.11.2     0
24005  Unlabelled  198.51.100.0/25[V] Gi0/0/0/2    172.16.11.2     0
24006  Unlabelled  10.102.1.0/24[V]   Gi0/0/0/3    172.16.21.2     0
24007  Unlabelled  10.99.1.0/24[V]    Gi0/0/0/4    172.16.91.2     500
24008  Unlabelled  10.99.2.0/24[V]    Gi0/0/0/4    172.16.91.2     0
24009  Aggregate   CUST-A: Per-VRF Aggr[V]   \
                                      CUST-A                       2500
```

CEA1 から学んだ 2 つの経路は、それぞれ自分のラベル(24004 と 24005)を持ち、XR01 はそのラベルで受けたパケットを、
ラベルを外して CEA1 へ送ります(`[V]` は VRF のプレフィックスの印です)。課題 M9-4 でグローバル テーブルから
取り込んだデフォルト ルートは CE から学んだものではないので、プレフィックスごとの方式でも VRF の集約のラベル 24009 が
付き、出口の欄は `Aggregate` です。

CE ごとの方式にすると、CEA1 から学んだ 2 つの経路が 1 つのラベル 24010 にまとまりました。ラベルの行き先は CEA1 そのもの
(Gi0/0/0/2 の 172.16.11.2)で、VRF の引き直しではありません。

```console
RP/0/RP0/CPU0:XR01#show bgp vrf CUST-A labels
...
*> 0.0.0.0/0          192.0.2.2       nolabel         24009
*> 10.101.1.0/24      172.16.11.2     nolabel         24010
*>i10.101.2.0/24      10.255.0.12     22              nolabel
*> 198.51.100.0/25    172.16.11.2     nolabel         24010
*>i198.51.100.128/25  10.255.0.12     23              nolabel

RP/0/RP0/CPU0:XR01#show mpls forwarding
...
24009  Aggregate   CUST-A: Per-VRF Aggr[V]   \
                                      CUST-A                       2000
24010  Unlabelled  No ID              Gi0/0/0/2    172.16.11.2     0
       Aggregate   No ID              CUST-A                       0            (!)
```

`show route` の凡例では、`(!)` は FRR の予備のパスの印です。24010 の 2 行目にも付いていて、VRF の引き直しが予備として
並んでいます。
RT02 は 20 秒以内にサイト 1 の 2 つの経路を `nolabel/24010` と表示し、CEA2 からの ping はどちらにも通りました。デフォルト
ルートは、CE ごとの方式でも集約のラベル 24009 のままです。

:::config XR01 — 顧客 A の VRF のラベルを 1 つにする
router bgp 65000
 vrf CUST-A
  address-family ipv4 unicast
   label mode per-vrf          ## VRF 全体でラベル 1 つ。per-ce なら CE ごと、書かなければプレフィックスごと
  !
 !
!
:::

:::config RT02(IOS XE)— 顧客 B の VRF のラベルを 1 つにする
mpls label mode vrf CUST-B protocol bgp-vpnv4 per-vrf   ## IOS XE はグローバルの設定。VRF とアドレス ファミリーを名指す
:::

RT02 でこれを入れると、CEB2 の経路のラベルは `IPv4 VRF Aggr:27` になり、ラベルの表の 27 は `aggregate/CUST-B`(VRF の
引き直し)を指しました。CEB1 からの ping は通り、行を消すと元の 24 に戻りました。

:::try
CUST-A のラベルを 1 つにしてみます。課題 M9-2 の後に行います(ラボでは課題 M9-4 の後に測りました)。

1. XR01 の `router bgp 65000` → `vrf CUST-A` → `address-family ipv4 unicast` の下に `label mode per-vrf` を設定して
   コミットします。
2. XR01 で `show bgp vrf CUST-A labels` と `show mpls forwarding` を、RT02 で
   `show ip bgp vpnv4 vrf CUST-A labels` を、CEA2 で `ping 10.101.1.1 source Loopback10` を実行します。
3. `label mode` を外してコミットします。

ラボで測った結果: XR01 が CEA1 から学習したルートはすべて、インポートしたデフォルト ルートのために VRF が既に持っていたラベル 24009 に
なり、24004 と 24005 は `show mpls forwarding` から消えました。20 秒以内に RT02 はそれらに `nolabel/24009` を表示し、ping は
通りました。`label mode` を外すと、ルートは再び 24004 と 24005 になりました。
:::

ラベルの数が問題になるのは、VRF の経路が多い大きな PE です。VRF ごとの方式はラベルを節約しますが、出口の PE は
受けたパケットごとに VRF のテーブルを引き直します。プレフィックスごとの方式は引き直しが無い代わりに、経路の数だけ
ラベルを使います。

## 2. プロバイダーの間

### 2.1 Inter-AS の 3 つのつなぎ方

VPN が 2 つのプロバイダーにまたがるとき、RFC 4364 の 10 節は 3 つのつなぎ方を挙げています。後のものほど規模に強く、
そのぶん、相手のプロバイダーに渡すもの(VPN のルート、PE のループバック)が増えます。

- **オプション A**: 2 つのプロバイダーの境界ルータ(ASBR)が PE と CE として向き合い、VPN ごとに 1 つの VRF と 1 つの
  インターフェイスまたはサブインターフェイスを持ち、その間はただの IP です。簡単ですが、VPN の数だけ規模が増えます。
- **オプション B**: ASBR は eBGP で VPNv4 のルートをラベル付きで交換し、VRF を持ちません。IOS XR の ASBR には、VRF の無い
  VPNv4 のルートを保持するための `retain route-target all`(またはポリシー)、eBGP の VPNv4 のセッションのルート ポリシー、
  ラベル付きのトラフィックを転送するための相手の ASBR への /32 のスタティック ルートが必要です。
- **オプション C**: ASBR は PE のループバックだけを BGP ラベル付きユニキャスト(単元 M8 の Unified MPLS)で運び、2 つのプロバイダーの
  ルート リフレクタがマルチホップの eBGP で VPNv4 のルートを交換します。

| | ASBR が持つもの | ASBR の間 | VPN を足したとき ASBR で |
|---|---|---|---|
| オプション A | VPN ごとの VRF | VPN ごとのインターフェイスと IP の経路 | VRF とインターフェイスを足す |
| オプション B | すべての VPNv4 のルート(VRF は無い) | eBGP の VPNv4(ラベル付き) | 何もしない |
| オプション C | 相手の PE のループバックだけ | BGP ラベル付きユニキャスト | 何もしない |

### 2.2 Carrier Supporting Carrier

**Carrier Supporting Carrier**(CSC、RFC 4364 の 9 節)では、VPN の顧客そのものがプロバイダーです。VPN は顧客のキャリアのループバック
だけをラベル付きで運び(CSC-CE に向けたラベル付きユニキャスト、または VRF の中の LDP)、顧客のキャリアはその上で自分の VPN を
動かします。顧客のキャリアの顧客の経路は、運ぶ側の VRF に入りません。運ぶ側から見ると、顧客のキャリアのコアは、
ループバックの数だけの小さな VPN です。

## 3. コマンドの対応

| IOS | IOS XR |
|---|---|
| `rd` と `route-target` を持つ `vrf definition <名前>` | `import route-target` / `export route-target` を持つ `vrf <名前>`。`rd` は `router bgp` → `vrf <名前>` の下 |
| `vrf forwarding <名前>`(アドレスを外す) | インターフェイスの下の `vrf <名前>` |
| `address-family vpnv4` + `neighbor … activate` | BGP の最上位とネイバーの下の `address-family vpnv4 unicast` |
| `address-family ipv4 vrf <名前>` | `router bgp` の下の `vrf <名前>` → `address-family ipv4 unicast` |
| `neighbor … as-override` | ネイバーのアドレス ファミリーの下の `as-override` |
| `neighbor … soo <値>` | ネイバーのアドレス ファミリーの下の `site-of-origin <値>` |
| `route-target export` + `export map <route-map>` | `export route-target` + `export route-policy <名前>` |
| `bgp default route-target filter`(既定で有効) | 常に有効。`retain route-target` |
| `mpls label mode vrf <名前> protocol bgp-vpnv4 per-vrf`(グローバル) | BGP の VRF のアドレス ファミリーの下の `label mode per-vrf` |
| `show ip bgp vpnv4 all` / `vrf <名前>` | `show bgp vpnv4 unicast` / `show bgp vrf <名前>` |
| `show ip route vrf <名前>` | `show route vrf <名前>` |

:::note
出典は単元の各ページと同じです(ページ「L3VPN の仕組み」の末尾)。ラベルの割り当て方は Cisco 8000 と NCS 5500 の BGP の
コマンド リファレンス(`label mode`)と、Cisco 8000 の L3VPN のコンフィギュレーション ガイド(26.x、2026 年)、Inter-AS と CSC は
RFC 4364 の 9 節・10 節と、NCS 5500・ASR 9000 の L3VPN のガイド(リリース 7.11)によります。ラベルの値と、方式を変えたときの
動きは、ラボ XRT-09 での実測です。
:::
