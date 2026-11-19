# M14 — 付録

本文で手短にしか、またはまったく扱わなかったことをまとめます。共用の LAN へどのルータが転送するかを決める Assert、MSDP と
Anycast RP、マルチキャスト VPN の下見、IGMP と MLD のバージョンの比較です。続けて、IOS XR と IOS XE の既定値、コマンドの対応、
この単元で確かめたことと、文書と機器が食い違う所を並べます。MSDP、Anycast RP、マルチキャスト VPN はラボでは設定せず、
どれも実測していません。

## 1. Assert: 共用の LAN へ誰が転送するか

### 1.1 2 台のルータ、1 つの LAN、2 部のコピー

ふつう、1 つのグループを LAN へ転送するルータは 1 台です。2 台が転送してしまう瞬間もあります。DR が替わるときや、
2 台のルータのそれぞれに、同じグループをその LAN へ転送する理由があるとき(たとえば、それぞれにメンバーを設定してある)です。
すると、LAN のどのホストも、パケットを 2 回ずつ受け取ります。

2 台のルータは、パケットそのものから気づきます。どちらも、自分がそのグループを転送しているインターフェイスに、同じグループの
パケットが入ってくるのを見ます。そこで 2 台とも、そのグループの Assert メッセージを LAN へ送り、比べた結果で、転送を続ける
1 台が決まります。

### 1.2 Assert の決まり方

Assert には、送ったルータが知っている、送信元へ戻る経路(共有ツリーなら RP へ戻る経路)の情報が入っています。RFC 7761
(4.6.3 節)は、次の順に比べます。

1. **rpt ビット。** 最短パス ツリー、(S,G) の Assert が、共有ツリーとして送った Assert に勝つ。
2. **経路の metric preference。** Cisco のルータでは、その経路のアドミニストレーティブ ディスタンス。小さいほうが勝つ。
3. **経路のメトリック。** 小さいほうが勝つ。
4. **LAN の上のアドレス。** 大きいほうが勝つ。

負けたルータは、そのグループを LAN へ転送するのをやめ、勝ったルータが転送を続けます。LAN の下流のルータは、勝ったルータを
上流の隣接として扱います。IOS はそうした隣接に、`show ip mroute` で `*` を付けます(凡例は `* - determined by Assert`)。
アドレスは最後の決め手で、1 つの LAN の上では同じにはなりません。

### 1.3 機器での見え方

IOS XR は、Assert を経たインターフェイスに、`show pim topology` で `AS` を付けます(凡例は `AS - Assert`)。IOS XE は、
`show ip mroute` で勝ったルータの出力インターフェイスに `A` を付けます(`A - Assert winner`)。

PoC の盤面には、ACCESS-3 と同じように IOS XRd のルータと IOS XE のルータが並ぶ共用の LAN がありました(アドレスは別)。
DR は IOS XE のルータでした。`dr-priority 10` で XRd のルータを DR にすると、その LAN の受信者に 1 パケットが 2 回届き
(20 回の ping に 21 回の応答)、新しい DR のインターフェイスには Assert の跡がありました(XRd のルータの
`show pim topology` の抜粋)。

```console
(*,239.1.1.1) SM Up: 00:15:00 RP: 10.255.0.11 
JP: Join(00:00:03) RPF: GigabitEthernet0/0/0/0,10.0.3.11 Flags: LH 
  GigabitEthernet0/0/0/1      00:15:00  fwd LI AS(self,00:02:28) LH 
```

`AS(self,…)` は、そのインターフェイスでこのルータを指しています。二重に届いたのは 2 台がともに転送した瞬間の分で、
4 つの決まりのどれで Assert が決まったかは切り分けていません。それより前の、IOS のルータだけの盤面では、2 台のルータが
同じ (S,G) を、ディスタンスもメトリックも同じまま 1 つの LAN へ転送しました。アドレスの大きいほうが勝ち、その出力
インターフェイスに `A` が付きました。

## 2. MSDP と Anycast RP

### 2.1 RP が 1 台なら、場所も 1 か所

PIM-SM では、あるグループのどの送信元も 1 台のルータに Register し、そのグループのどの共有ツリーもそこを根にします。RP が
故障すると、ルータには別の RP が要ります。スタティックの RP なら誰かが設定を変え、BSR なら、故障した RP の項目が時間切れに
なったところで、ほかの候補が引き継ぎます(holdtime。既定の間隔では 150 秒)。

RP は、自分に Register した送信元しか知りません。それぞれに RP を持つ別々のドメインは、この仕組みでは互いの送信元を
知りません。

### 2.2 MSDP: RP どうしが送信元を知らせ合う

MSDP(Multicast Source Discovery Protocol、RFC 3618)は、RP どうしを TCP のセッション(ポート 639)でつなぎます。送信元が
ある RP に Register すると、その RP は MSDP のピアへ Source-Active(SA)メッセージを送ります。この送信元がこのグループへ
送っている、という知らせで、最初のデータ パケットが中に入っています。そのグループの受信者を持つ RP は、送信元へ向けて
Join します。MSDP は、別々のプロバイダーのドメインの間のマルチキャストのために作られました。

### 2.3 Anycast RP: 複数の RP に 1 つのアドレス

Anycast RP は、複数の RP に同じアドレスを、32 ビットのマスクのループバックで持たせ、IGP で広告します。各ルータの Join と
Register は、ユニキャストの経路が決めるとおり、そのうちの最も近い RP へ届き、1 台が故障すると、経路がほかの RP へ収束します。

送信元がある RP に Register し、受信者が別の RP へ Join することがあるので、RP どうしは MSDP で送信元を知らせ合います。
その MSDP のセッションは、共有のアドレスでなく各 RP 自身のアドレスを使い、SA の originator ID もそれにそろえます(既定では
RP のアドレスが使われます)。

RFC 4610 は、同じことを PIM だけで行います。RP どうしが Register を互いに渡し、MSDP は要りません。MSDP は IPv4 でしか
動かないので、IPv6 はこのやり方を使います。IOS XE では PIMv6 Anycast RP と呼びます。

### 2.4 どこでまた出てくるか

どちらも、このコースではまだ設定していません。SPRI のブループリント(300-510)には、MSDP の動作(2.2.d と 2.3.d)と、
anycast RP と Phantom RP(2.3.a)があります。どれも、このコースの後に来る SPRI の部で扱います。

## 3. マルチキャスト VPN の下見

### 3.1 困りごと: VRF の中のマルチキャスト

L3VPN(M9)では、顧客のパケットは VRF の中を運ばれ、コアの P ルータは顧客の経路を 1 つも知りません(M8)。顧客が拠点の
間でマルチキャストを使うと、その PIM の Join は顧客の送信元や顧客の RP を向きますが、コアにはそこへの経路がありません。
SPCOR は、その答えである mVPN を、4.1.d の説明する VPN サービスの 1 つに挙げています。

### 3.2 盤面にもう出ている言葉

この単元では mVPN を設定しませんが、IOS XRd のルータは、もうその部品を持っています。`multicast-routing` の下に `vrf` があり、
その `address-family ipv4` で `?` を打つと、次のようなものが並びます(抜粋)。

```console
  bgp                         Enable BGP MVPN Discovery
  core-tree-protocol          Configure Core-tree-protocol
  export-rt                   Configure Export Route-Target
  import-rt                   Configure Import Route-Target
  mdt                         MVPN configuration
```

`router pim` → `address-family ipv4` にも `mdt`(`Multicast Distribution Tree commands`)があり、`show pim topology` と
`show mrib route` の凡例にも、そのためのフラグがあります。`ME - MDT Encap`、`MD - MDT Decap`、`MT - Crossed Data MDT threshold`、
`BGP - BGP C-Multicast Join` です。

並べると、形が見えます。VRF、core-tree プロトコルで作るコアを渡るマルチキャスト配信ツリー
(MDT)、BGP で互いを見つける PE、M9 と同じルート ターゲットです。この単元のどの出力でも、凡例はずっとそれを説明していました。

### 3.3 どこでまた出てくるか

mVPN はこの単元では試しておらず、このページの mVPN についての記述は実測ではありません。このコースの SPRI の部で扱います。
そのブループリントには mLDP と P2MP(2.2.e)もあります。

## 4. IGMP と MLD のバージョンを並べる

### 4.1 バージョンごとに足されたもの

| バージョン | 規定 | 足されたもの |
|---|---|---|
| IGMPv1 | RFC 1112 | ルータからのクエリと、ホストからのレポート |
| IGMPv2 | RFC 2236 | Leave メッセージ(224.0.0.2 宛て)、グループ固有のクエリ、クエリの中の最大応答時間、クエリアの選出(アドレスの最も小さいルータ) |
| IGMPv3 | RFC 3376 | 送信元の一覧。レポートで、どの送信元から受けるか(INCLUDE)、どの送信元からは受けないか(EXCLUDE)を言う。レポートは 224.0.0.22 宛て。SSM にはこれが要る |
| MLDv1 | RFC 2710 | IGMPv2 にあたる IPv6 版。ICMPv6 で運ぶ(クエリ 130、レポート 131、Done 132) |
| MLDv2 | RFC 3810 | IGMPv3 にあたる IPv6 版(レポート 143、FF02::16 宛て) |

違いはルータの表示に出ます。PoC の盤面で PE2 のホスト側のインターフェイスをバージョン 1 にすると、`show igmp interface` から
クエリアの行と最大応答時間の行が消えました。バージョン 2 と 3 では、どちらの行もあります。IOS XE のホストは、既定では
バージョン 2 でレポートします。ルータの既定は、IOS XR がバージョン 3、IOS XE がバージョン 2 です(5 節)。

### 4.2 LAN の上でバージョンが違うとき

ホストは、聞こえる中で最も古いクエリアのバージョンで答えます。古いバージョンのクエリを聞くと、そのバージョンに下がり、
古いクエリがしばらく聞こえなくなってから自分のバージョンに戻ります。その時間は robustness × クエリの間隔 + クエリの応答時間
(RFC 3376 の 8.12 節)で、ここの値では 2 × 60 + 10 = 130 秒です。

結果の例: PoC の盤面で PE2 のホスト側のインターフェイスをバージョン 2 にすると、IOS XE のホストの RCV2 はバージョン 2 に
下がりました。PE2 をバージョン 3 に戻したあとも、RCV2 は 103〜136 秒の間、バージョン 2 でレポートし続けました。その間、
SSM のグループへのレポートは送信元を指定せず、PE2 はそれを捨て、SSM の範囲のものは何も届きませんでした。RCV2 がバージョン 3 に
戻ると、10 パケットがすべて届きました。

1 つの LAN のルータは、そろえる必要があります。RFC 3376(7.3.1 節)は、LAN のすべてのルータを、そこで使われている最も低い
バージョンに設定しなければならない(MUST)と定め、IOS XR の文書も、サブネットのすべてのルータを同じバージョンにすると書いて
います。構築した直後の ACCESS-3 は、そうなっていません。PE3 は IOS XR の既定のバージョン 3、PE4 は IOS XE の既定の
バージョン 2 です。それでも PE4 は、PE3 をクエリアとして表示します。

## 5. この機種での既定値

下の値は、何も設定していないときにこのラボの機器が表示するもので、同じことを書いている文書を添えます。「機器」は、IOS XR では
IOS XRd 26.1.1、IOS XE では IOL 17.15 です。

| 設定 | IOS XR | IOS XE | どこに書いてあるか |
|---|---|---|---|
| インターフェイスのマルチキャスト ルーティング | `multicast-routing` で有効にするまで、どれも無効 | `ip multicast-routing` と `ip pim sparse-mode` を設定するまで無効 | Cisco 8000 の設定ガイド(「by default, no interfaces are enabled」)、機器 |
| IGMP のバージョン | 3 | 2 | Cisco 8000 のコマンド リファレンス、IOS のコマンド リファレンス、機器 |
| IGMP のクエリの間隔 | 60 秒 | 60 秒 | 同上 |
| IGMP の最大応答時間 | 10 秒 | 10 秒 | 同上 |
| last member query の間隔 | 1 秒 | 1000 ms | 機器 |
| MLD のバージョン | 2 | 2 | Cisco 8000 の設定ガイド(「MLDv2 is enabled … by default」)、機器 |
| MLD のクエリの間隔、最大応答時間 | 125 秒、10 秒 | 125 秒、10 秒 | 機器 |
| PIM の Hello の間隔 | 30 秒 | 30 秒 | IOS のコマンド リファレンス、機器 |
| DR priority | 1 | 1 | IOS のコマンド リファレンス、機器 |
| 最短パス ツリーへの切り替え | 最初のパケットで | 最初のパケットで | Cisco 8000 のコマンド リファレンスと設定ガイド、IOS のコマンド リファレンス、機器 |
| SSM の範囲 | 232.0.0.0/8 | `ip pim ssm default`(232/8)か `ip pim ssm range` を設定するまでなし | Cisco 8000 のコマンド リファレンス、IOS のコマンド リファレンス、機器 |
| 双方向 PIM | `rp-address … bidir` を受け付ける(この仮想機では) | PE4 では、`ip pim bidir-enable` を設定するまで `bidir` を拒む | 機器。7.2 節も参照 |
| 候補 RP の priority(小さいほうが勝つ) | 192 | 0 | Cisco 8000 の設定ガイド(例)、RFC 5059(3.2 節)、機器。IOS XE 17.x のガイド、機器 |
| 候補 RP の通知の間隔(holdtime) | 60 秒(150 秒) | 60 秒(150 秒) | 機器。IOS のコマンド リファレンス。IOS XR で `interval 30` にすると holdtime は 75 秒 |
| 候補 BSR の priority(大きいほうが勝つ) | 1 | 0 | Cisco 8000 のコマンド リファレンス、機器。IOS XE 17.x のガイド、IOS のコマンド リファレンス、機器。RFC 5059 の推奨は 64 |
| BSR の hash mask の長さ | 30 | 0 | 機器。IOS のコマンド リファレンス、機器 |
| Auto-RP のグループ 224.0.1.39 と 224.0.1.40 | デンス モードで全インターフェイスへ流す(`show pim group-map` で `DM perm`) | スパース モードのインターフェイスへは `ip pim autorp listener` があるときだけ転送する | Cisco 8000 のコマンド リファレンス(group-map の例)、CRS のコマンド リファレンス。IOS のコマンド リファレンス。機器 |
| 同じグループのスタティックの RP と学習した RP | 学習した RP(スタティックに `override` がなければ) | 同じ | ASR 9000 の設定ガイド、機器 |

候補 RP と候補 BSR の行は、勝つ向きが逆で(候補 RP は priority の小さいほう、候補 BSR は大きいほうが勝つ)、既定値も機種で
違います。両方が混ざるドメインで既定のままにすると、IOS XE の候補 RP(0)が IOS XR の候補 RP(192)に勝ち、IOS XR の
候補 BSR(1)が IOS XE の候補 BSR(0)に勝ちます。

## 6. コマンドの対応(IOS XE と IOS XR)

### 6.1 設定

IOS XR の列のコマンドは、行に別の書き方がない限り、`router pim` → `address-family ipv4` の下に置きます。

| すること | IOS XE(IOL 17.15) | IOS XR(26.1.1) |
|---|---|---|
| マルチキャスト ルーティングを有効にする | `ip multicast-routing` と、インターフェイスごとの `ip pim sparse-mode` | `multicast-routing` → `address-family ipv4` → `interface all enable`(または `interface <if> enable`) |
| 1 つのインターフェイスでマルチキャストを止める | インターフェイスで `no ip pim sparse-mode` | `multicast-routing` → `address-family ipv4` → `interface <if>` → `disable` |
| 1 つのインターフェイスで PIM だけを止める | (この単元では使わない) | `interface <if>` → `disable` |
| スタティック RP | `ip pim rp-address <rp> [<acl>] [override]` | `rp-address <rp> [<acl>] [override]` |
| 双方向の RP | `ip pim bidir-enable` のうえで `ip pim rp-address <rp> <acl> bidir` | `rp-address <rp> <acl> bidir` |
| 共有ツリーに留まる | `ip pim spt-threshold infinity [group-list <acl>]` | `spt-threshold infinity [group-list <acl>]` |
| SSM の範囲 | `ip pim ssm default`、または `ip pim ssm range <acl>` | 設定なしで 232/8。`ssm range <acl>` |
| 一部の送信元の Register だけを受け付ける(RP で) | (この単元では使わない) | `accept-register <acl>` |
| 候補 RP(BSR) | `ip pim rp-candidate <if> [group-list <acl>] [priority <n>]` | `bsr candidate-rp <アドレス> [group-list <acl>] [priority <n>] [interval <秒>]` |
| 候補 BSR | `ip pim bsr-candidate <if> [<hash-mask-length>] [<priority>]` | `bsr candidate-bsr <アドレス> [hash-mask-len <n>] [priority <n>]` |
| Auto-RP の候補 RP | `ip pim send-rp-announce <if> scope <ttl>` | `auto-rp candidate-rp <if> scope <ttl> interval <秒>` |
| Auto-RP のマッピング エージェント | `ip pim send-rp-discovery <if> scope <ttl>` | `auto-rp mapping-agent <if> scope <ttl> interval <秒>` |
| スパース モードのインターフェイスで Auto-RP を通す | `ip pim autorp listener` | 要らない(224.0.1.39 と 224.0.1.40 はデンス モードで流れる) |
| DR priority | インターフェイスで `ip pim dr-priority <n>` | `interface <if>` → `dr-priority <n>` |
| IGMP のバージョン | インターフェイスで `ip igmp version <1-3>` | `router igmp` → `interface <if>` → `version <1-3>` |
| ルータ自身をグループのメンバーにする | インターフェイスで `ip igmp join-group <グループ> [source <送信元>]` | `router igmp` → `interface <if>` → `join-group <グループ>` |
| メンバーがいなくても LAN へ転送する | インターフェイスで `ip igmp static-group <グループ>` | `router igmp` → `interface <if>` → `static-group <グループ>` |
| IPv6 | `ipv6 multicast-routing`、`ipv6 pim rp-address <rp>` | `multicast-routing` → `address-family ipv6` → `interface all enable`、`router pim` → `address-family ipv6` → `rp-address <rp>` |
| MLD | インターフェイスの `ipv6 mld …`(ホストは `ipv6 mld join-group <グループ>` で参加する) | `router mld` |

### 6.2 show コマンド

| 見るもの | IOS XE | IOS XR |
|---|---|---|
| PIM のインターフェイスと DR | `show ip pim interface [detail]` | `show pim interface [detail]` |
| PIM の隣接 | `show ip pim neighbor` | `show pim neighbor` |
| インターフェイスの IGMP: バージョン、クエリア、タイマ | `show ip igmp interface` | `show igmp interface` |
| IGMP のメンバー | `show ip igmp groups [<グループ>] [detail]` | `show igmp groups [<グループ>] [detail]` |
| マルチキャスト ルーティングの状態 | `show ip mroute [<グループ>]` | `show pim topology [<グループ>]`(PIM から見た状態)、`show mrib route [<グループ>]`(ルーティングの表) |
| 転送のカウンタ | `show ip mfib count` | `show mfib route <グループ> detail` |
| 送信元か RP への RPF | `show ip rpf <アドレス>` | `show pim rpf [<アドレス>]` |
| どの RP がどのグループを受け持つか | `show ip pim rp mapping` | `show pim rp mapping`、`show pim group-map [<グループ>]` |
| 1 つのグループに選ばれた RP(BSR) | `show ip pim rp-hash <グループ>` | `show pim group-map <グループ>` |
| BSR | `show ip pim bsr-router` | `show pim bsr election`、`show pim bsr candidate-rp` |
| Auto-RP | `show ip pim autorp` | `show auto-rp mapping-agent`、`show auto-rp candidate-rp` |
| BIDIR: インターフェイスごとの DF | `show ip pim interface df` | `show pim df winner` |
| IPv6 | `show ipv6 pim interface`、`show ipv6 pim neighbor`、`show ipv6 mroute`、`show ipv6 mld interface`、`show ipv6 mld groups` | `show pim ipv6 interface`、`show pim ipv6 neighbor`、`show pim ipv6 topology`、`show pim ipv6 group-map`、`show mld interface`、`show mld groups` |

IOS XR で IGMP のグループを消すコマンドは単数形の `clear igmp group` です。`clear igmp groups` は不正な入力として拒まれます。

## 7. 確かめたことと、文書と機器が食い違う所

### 7.1 確かめたこと

| 項目 | IOS XRd 26.1.1 | IOS XRv 9000 26.1.1 | IOL の IOS XE 17.15 |
|---|---|---|---|
| マルチキャストのデータの転送 | ファースト ホップ、RP、ラスト ホップ、中継として転送する | ファースト ホップとラスト ホップとして転送する(PoC の盤面) | 転送する(ACCESS-3 の DR の PE4) |
| MFIB のソフトウェアのカウンタ(`show mfib route … detail`) | パケットを数える | 0 のまま | — |
| 有効にする | `interface all enable` で、Loopback0 も含むすべてのインターフェイスに PIM と IGMPv3 が乗る。`router pim` だけではどれも有効にならない | `interface all enable`: 同じ(`router pim` なしで) | `ip multicast-routing` と `ip pim sparse-mode` |
| PIM の隣接の表 | 自分自身も載る(`*`)。XR の隣接には `B`、IOS XE の隣接には `P` | (別には確かめていない) | XR の隣接に `G` |
| 共用の LAN のクエリアと DR | クエリア= アドレスの最も小さいルータ、DR= 最も大きいルータ。IGMPv3 と IGMPv2 が並んでも同じ | (試していない) | 同じ。XR のルータをクエリアとして表示する |
| 最短パス ツリーへの切り替え | 最初のパケットで。`spt-threshold infinity` で共有ツリーに留まる | 同じ | 同じ(`ip pim spt-threshold infinity`) |
| SSM | 設定なしで 232/8。IGMPv3 の (S,G) の参加で届き、RP に状態はない。範囲の中の IGMPv2 の参加は表に載らない | 同じ | `ip pim ssm default`(か範囲)と、DR になる所で `ip igmp version 3` が要る |
| BIDIR | 動く。(S,G) はない。`show pim df winner` | 動く | `ip pim bidir-enable` が要る |
| BSR | 候補 RP: priority 192、interval 60。候補 BSR: priority 1、hash mask の長さ 30。候補 RP は priority の小さいほうが勝つ | 候補 BSR: priority 1 | XR の BSR から同じ RP を学習する |
| Auto-RP | 224.0.1.39 と 224.0.1.40 をデンス モードで流す。`show auto-rp mapping-agent`、`show auto-rp candidate-rp` | マッピング エージェントとして動く | `ip pim autorp listener` なしで、XR の隣から RP を学習する |
| スタティックの RP と学習した RP | (試していない) | 学習した RP が勝つ。`override` でスタティックが勝つ | 同じ(それより前の IOS だけの盤面) |
| ルータ自身をメンバーにする | `join-group`: ルータがグループ宛ての ping に答える(`II`) | `static-group`: ホストなしで LAN へ転送する | `ip igmp join-group`: ホストが ping に答える |
| IGMP のバージョンを変える | (試していない) | `version 2` と `version 1`。IOS XE のホストが合わせる | ルータが戻してから 103〜136 秒でホストがバージョン 3 に戻る |
| IPv6 | PIMv6 の隣接はリンクローカル アドレス。MLDv2。Register は `Decaps6tunnel0` で取り出す。最初のパケットで切り替える | PIMv6 の隣接はリンクローカル アドレス。MLDv2 | ホストで `ipv6 mld join-group`。IPv6 のグループへの ping は出力インターフェイスを聞いてくる |
| Assert | DR が替わるときに 1 パケットが二重。新しい DR に `AS(self,…)` | (試していない) | — |

### 7.2 文書と機器が食い違う所

- **IOS XRd のマルチキャスト**は、XRd の文書に書かれていません(8 節)。
- **IOS XR の BIDIR。** Cisco 8000 の設定ガイド(26.x)は、その機種では PIM Bidir に対応しないと書いています。IOS XRv 9000 と
  IOS XRd では動きます。`show pim df winner` は CRS のコマンド リファレンスにしかなく、今のコマンド リファレンスにはありませんが、
  ここでは使えます。
- **`ssm range` の置き場。** コマンド リファレンスは `multicast-routing` → `address-family ipv4` の下に置き、設定ガイドの
  サブモードの節は `router pim` の下に置いています。IOS XRd 26.1.1 はどちらでも受け付け、どちらでも効きます。
  `multicast-routing` の下では、`?` が `(cisco-support)` と表示します。自分で範囲を書くと、一覧に 232/8 を入れない限り 232/8 は
  外れます(コマンド リファレンス)。この単元の設定例は、自分の範囲に 232/8 も書いています。
- **IGMP の querier timeout。** コマンド リファレンスの本文は 120 秒と書いています。その出力例と機器は 125 秒と表示し、これは
  クエリの間隔が 60 秒のときの RFC 3376 の式(8.5 節)の値です。
- **MLD の既定のバージョン。** 古い CRS の文書(IOS XR 4.0)は MLDv1 と書いています。今の設定ガイドと機器は MLDv2 です。
- **IOS XE の `ip pim bidir-enable`。** Catalyst 9600 のコマンド リファレンス(17.13)は、既定を「enabled」と書いています。PE4
  (IOL 17.15)では、`ip pim bidir-enable` を設定するまで `ip pim rp-address … bidir` が `% Invalid input` で拒まれ、
  `no ip pim bidir-enable` で bidir の RP の行も消えます。既定は機種で違うようです。
- **重なるスタティック RP。** 2 つのスタティック RP が同じグループを含むとき、IOS XE はアドレスの最も大きい RP を使います
  (Catalyst 9600 のコマンド リファレンス 17.13: 「the RP for the group is determined by the RP with the highest RP address
  configured」)。IOS XR は長いほうの範囲を使いました。IOS XR の文書には記述がなく、この振る舞いは RFC 7761(4.7.1 節)の最長
  一致と一致します。
- **この単元の設定例**(すべてのグループを 10.255.0.11、239.2.0.0/16 を BIDIR で 10.255.1.11)では、長いほうの
  範囲がアドレスも大きいので、239.2.0.0/16 については 2 つの決まりが同じ RP を選びます。BIDIR の RP のアドレスが小さければ、
  そうはなりません。

文書とこのラボの機器が食い違う所では、この単元のページは機器がどう動いたかを書き、文書の名前を添えます。こうした点は、課題の正しさの
根拠には使っていません。

## 8. マルチキャスト ルータとしての IOS XRd

IOS XRd の文書は、マルチキャストを扱っていません。データシートにも 26.1.1 のリリース ノートにも記述がありません。この単元で
XRd がマルチキャストを転送すると書いていることは、すべて機器から来ています。

この仮想機では、XRd はどの役でもマルチキャストを転送しました。ファースト ホップ(Register を作る)、RP(`Decapstunnel` の
インターフェイスで Register から取り出す)、ラスト ホップ、中継です。XRT-16 では、PIM-SM、共有ツリーに留まる設定、SSM、
BIDIR、BSR、IPv6 のどれも、10 パケットのうち 10 が届きました。

カウンタは 2 つの仮想機で違います。XRd では、`show mfib route … detail` の `SW Forwarding Counts` がパケットとともに増えます。
IOS XRv 9000 ではパケットが届いても 0 のままなので、XRv 9000 では受信者の側で数えます。結果の例(共有ツリーに留まった
グループへ 3 + 10 回 ping したあとの P1。抜粋):

```console
RP/0/RP0/CPU0:P1#show mfib route 239.1.1.2 detail
...
(192.168.1.1,239.1.1.2),  Flags:  , FMA: 0x10000 ,
...
  SW Forwarding Counts: 13/12/1200
  SW Replication Counts: 13/12/1200
  SW Failure Counts: 0/0/0/0/0
```

XRd は約 80 秒で起動します。XRv 9000 は約 9 分かかり、このラボのホストでは同時に 2 台までしか動きません。XRT-16 が XRd だけで
できているのはそのためです。

ハードウェアの機種が機能に対応するかどうかは、その機種のガイドで確かめることです。この単元の例が BIDIR で、Cisco 8000 の
ガイドは非対応と書き、ここでは 2 つの仮想機のどちらでも動きます。

:::note
出典: RFC 7761(4.3.2 節・4.6.3 節・4.7.1 節)、RFC 1112、RFC 2236、RFC 3376(7.3.1 節・8.5 節・8.12 節)、RFC 2710、
RFC 3810、RFC 4604(3.5 節)、RFC 4607、RFC 5015、RFC 5059(3.2 節)、RFC 3618、RFC 4610。Cisco: Cisco 8000 の Multicast
Configuration Guide(IOS XR 26.1.x–26.3.x)と Multicast Command Reference(2026-09-11)、ASR 9000 の Multicast Configuration
Guide(IOS XR 25.1.x–25.4.x)と Command Reference(2026-09-11)、CRS の Multicast Command Reference(2020)と IOS XR 4.0 の
CRS の文書、IOS XE 17.x の IP Multicast Configuration Guide(MSDP と PIMv6 Anycast RP を含む)、Cisco IOS IP Multicast
Command Reference、Catalyst 9600 の IOS XE 17.13 のコマンド リファレンス(`ip pim rp-address`・`ip pim bidir-enable`)、
IOS XRd のデータシートと IOS XRd 26.1.1 のリリース ノート。SPCOR(350-501)と SPRI(300-510)のブループリント。いずれも
2026 年 11 月に確認。実測: XRT-16(IOS XRd 26.1.1 と IOL 17.15)で、5 節の既定値(IOS XE の候補 RP と候補 BSR の値と、最後の
行を除く)、7.1 節の BSR と Auto-RP の行、重なるスタティック RP、`bidir-enable`、8 節のカウンタ。IOS XRv 9000 26.1.1・
IOS XRd 26.1.1・IOL 17.15 の PoC の盤面(PE1 と PE2 が XRv 9000、P1 が XRd、XRd のルータと IOS XE のルータが並ぶ共用の LAN)で、
Assert、IGMP のバージョンとホストがバージョン 3 に戻るまで、`join-group` と `static-group`、スタティックの RP と学習した RP、
`ssm range`、XRv 9000 のカウンタ、IPv6 の行、3.2 節の `?` の一覧。それより前の IOS のルータだけの盤面(IOL 17.15)で、IOS の
ルータどうしの Assert、IOS XE の候補 RP と候補 BSR の既定値、listener なしの Auto-RP。
:::
