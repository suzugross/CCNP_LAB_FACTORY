# M11 — EVPN-VPWS

前のページでは、LDP で疑似回線を作りました。このページでは、同じ E-Line を **BGP** で作ります。EVPN(Ethernet VPN)は、
レイヤ 2 のサービスを BGP で作る仕組みの一族で、その中でポイントツーポイントのものが **EVPN-VPWS** です。
ラボは引き続き XRT-11 で、課題 M11-3 と M11-4 がこのページにあたります。

## 1. 何が嬉しいのか

### 1.1 LDP の疑似回線の困りごと

LDP の疑似回線では、疑似回線を張る PE の組ごとに targeted LDP のセッションが要ります。E-Line を張る相手の PE が増えるほど、
セッションの数は増えます。しかも、プロバイダーは L3VPN のために、すでに BGP とルート リフレクタを動かしています。
L2 のサービスのためだけに、もう 1 つの制御プロトコルのセッションを全部の組で持つことになります。

また、LDP の疑似回線は 1 本の線です。顧客の拠点を 2 台の PE に収容して、両方を同時に使う(マルチホーム)ことは、
この仕組みだけではできません。

### 1.2 EVPN の答え: L3VPN と同じ道具で運ぶ

EVPN では、疑似回線の情報を BGP の経路として広告します。アドレス ファミリーは `l2vpn evpn` です。RD とルート ターゲット、
ルート リフレクタ、ポリシーなど、M9 の L3VPN で使った道具がそのまま使えます。PE はルート リフレクタとだけセッションを持てば
よく、PE の組ごとのセッションは要りません。

EVPN の一族には、E-LAN とマルチホーム(どちらも追補)、E-Tree(付録)も入っています。EVPN-VPWS は、その中で一番単純な
E-Line です。
このラボの XR が扱えるのは、このうち EVPN-VPWS です。

## 2. 仕組み

### 2.1 EVI と AC の識別子

EVPN-VPWS の E-Line は、次の 2 つで決まります。

- **EVI**(EVPN インスタンス): E-Line ごとの番号です。L3VPN の VRF にあたります。IOS XR は EVI から RD とルート ターゲットを
  自動で作ります。RD は「ルータ ID:EVI」、ルート ターゲットは「AS 番号:EVI」です。
- **AC の識別子**: E-Line の両端それぞれの番号です。各 PE は「自分の端は `source`、相手の端は `target`」と設定します。
  相手の `source` が自分の `target` と一致したときに、E-Line がつながります。

課題 M11-3 では、EVI は 400、拠点 1(XR01)の端の識別子は 1、拠点 3(XR03)の端は 3 です。XR01 は `target 3 source 1`、
XR03 は `target 1 source 3` と設定します。

### 2.2 運ぶ経路: 種類 1

各 PE は、自分の端について、EVPN の**種類 1** の経路(イーサネットの自動検出、EVI ごと)を 1 つ広告します。
経路が運ぶものは次のとおりです。

- RD と、イーサネット セグメント識別子(ESI)。拠点を 1 台の PE に収容しているときの ESI は 0 です。
- **イーサネット タグ**: ここに AC の識別子(`source`)が入ります。
- **ラベル**: 相手に付けてほしいラベル。LDP の疑似回線のラベルにあたります。
- ルート ターゲットと、L2 の属性の拡張コミュニティ(`0x604`)。

```console
RP/0/RP0/CPU0:XR03#show bgp l2vpn evpn
Route Distinguisher: 10.255.0.1:400
*>i[1][0000.0000.0000.0000.0000][1]/120
Route Distinguisher: 10.255.0.3:400 (default for vrf VPWS:400)
*>i[1][0000.0000.0000.0000.0000][1]/120
*> [1][0000.0000.0000.0000.0000][3]/120
```

`[1]` が種類、次の 0 が ESI、最後の `[1]` や `[3]` がイーサネット タグ(AC の識別子)です。XR03 は XR01 の経路(タグ 1)を
受け取り、自分の EVI の RD で取り込んでいます。

### 2.3 1 ホップずつ: CEB1 から CEB3 へ

CEB1 が VLAN 400 で送ったフレームを追います。ラベルの値は一例です。

:::topo
nodes:
  CEB1: [0, 1]
  XR01: [1.5, 1]
  RT01: [3.2, 1]
  XR03: [4.7, 1]
  CEB3: [6.2, 1]
links:
  - [CEB1, XR01, "tag 400 | IP"]
  - [XR01, RT01, "16003 | 24004 | frame"]
  - [RT01, XR03, "24004 | frame"]
  - [XR03, CEB3, "tag 40 | IP"]
:::

1. XR01 は VLAN 400 のフレームを AC で拾い、タグを外します。
2. XR03 の種類 1 の経路が運んできたラベル **24004** を付け、その外側に XR03 へのトランスポートのラベル **16003**(XR03 の
   プレフィックス SID)を付けます。
3. RT01 は 16003 を見て XR03 へ送り、1 つ手前なので外します。
4. XR03 は 24004 を見て、それが EVI 400 の E-Line だと分かります。ラベルを外し、VLAN 40 のタグを付けて CEB3 へ送ります。

データの形は LDP の疑似回線と同じです。違うのは、ラベルを配る方法だけです。

### 2.4 ルート リフレクタが運ぶ

PE は、`l2vpn evpn` の経路をルート リフレクタの XR02 とだけ交換します。XR02 は M9 から VPNv4 のルート リフレクタで、
同じセッションに `l2vpn evpn` のアドレス ファミリーを足せば、EVPN の経路も反映します。XR02 は IOS XRd で、転送には
加わらないので、XRd でも務まります。

新しい PE の XR03 とのセッションは、上がってから経路がそろうまで、このラボでは 1 分ほどかかります。セッションが上がった
直後は、どちらの E-Line もまだ `None` のままです。

### 2.5 MTU とコントロール ワード

EVPN-VPWS では、IOS XR は既定で MTU を比べません。詳細には `Ignore MTU mismatch: Enabled`、`Transmit MTU zero: Enabled` と
出て、相手には MTU 0 を伝えます。そのため、LDP の疑似回線で起きた `MTU mismatched` は、EVPN-VPWS では起きません。
タグを外し忘れた AC は、E-Line を UP のまま、フレームの形だけを食い違わせます(3.3 節)。MTU を比べたいときは、EVI の下で
`transmit-l2-mtu` と `enforce-mtu-match` を設定します。

## 3. IOS XR で EVPN-VPWS を作る

### 3.1 設定の置き場

EVPN-VPWS は、BGP の `l2vpn evpn`、AC のサブインタフェース、`l2vpn` の下のクロスコネクトの 3 か所に書きます。

:::config fold XR01(IOS XR)— EVPN-VPWS の E-Line
router bgp 65000
 address-family l2vpn evpn                         ## BGP 全体で EVPN のアドレス ファミリーを使う
 !
 neighbor 10.255.0.21                              ## ルート リフレクタ XR02(M9 からの VPNv4 のセッション)
  address-family l2vpn evpn                        ## 同じセッションで EVPN の経路も交換する
  !
 !
!
interface GigabitEthernet0/0/0/3.400 l2transport
 encapsulation dot1q 400
 rewrite ingress tag pop 1 symmetric               ## タグなしで運ぶので、相手の VLAN(40)と違ってよい
!
l2vpn
 xconnect group CUST-B
  p2p B-400
   interface GigabitEthernet0/0/0/3.400
   neighbor evpn evi 400 target 3 source 1          ## EVI 400。自分の端は 1、相手の端は 3
   !
  !
 !
!
:::

XR03 は、BGP を初めて動かすので、`router bgp 65000` に `bgp router-id 10.255.0.3` と、XR02 への近隣(`remote-as`・
`update-source Loopback0`)が要ります。AC とクロスコネクトは、`target 1 source 3` で XR01 と対になります。

:::config fold XR02(IOS XR)— ルート リフレクタに EVPN を足す
router bgp 65000
 address-family l2vpn evpn                         ## RR も BGP 全体で EVPN を使う
 !
 neighbor 10.255.0.1
  address-family l2vpn evpn
   route-reflector-client                          ## XR01 を EVPN のクライアントに
  !
 !
 neighbor 10.255.0.3                               ## 新しい PE の XR03
  remote-as 65000
  update-source Loopback0
  address-family l2vpn evpn
   route-reflector-client
  !
 !
!
:::

IOS XR では、`evpn` の下に何も書かなくても、EVI は自動の RD とルート ターゲットで動きます。ルート ターゲットを
決め打ちしたいときは、`evpn` → `evi 400` → `bgp` の下に `route-target import`・`export` を書きます。

### 3.2 状態の読み方

`show l2vpn xconnect` の Segment 2 には、`EVPN <EVI>,<target>,<相手の PE>` が出ます。

```console
RP/0/RP0/CPU0:XR01#show l2vpn xconnect
CUST-B     B-400      UP   Gi0/0/0/3.400          UP       EVPN 400,3,10.255.0.3  UP
```

相手の経路がまだ届いていないとき、相手の PE の欄は `None` です。詳細(`show l2vpn xconnect detail`)では、
`EVPN: neighbor 10.255.0.3, PW ID: evi 400, ac-id 3, state is up ( established )` の下に、ラベル(Local と Remote)が並びます。
`show evpn evi vpn-id 400 detail` は、自動の RD とルート ターゲット、コントロール ワード、MTU の扱いを表示します。

### 3.3 上がらないとき、上がっているのに通らないとき

食い違いごとの表れ方は次のとおりです。

| 食い違い | この端 | 相手の端 | 通信 |
|---|---|---|---|
| この端の `target` が違う(相手の端の識別子を取り違えた) | DN、`neighbor None … local ready` | **UP** | 通らない |
| ルート ターゲットが違う | DN | DN | 通らない |
| 片方の AC がタグを外さない | UP | UP | 通らない |
| ルート リフレクタに EVPN が無い | DN、`None` | DN、`None` | 通らない |

1 行目は、表示が非対称になります。相手の端は、この端の経路(タグ= この端の `source`)を受け取り、それが自分の `target` と
一致するので UP です。この端は、自分の `target` に一致する経路を受け取れないので DN です。片方の端だけを見て
「向こうは UP だから向こうは正しい」と決めないことが大事です。

3 行目は、MTU を比べない(2.5 節)ために、E-Line は UP のままです。タグを外した端から来たフレームはタグなしで、
タグを外さなかった端は、それをタグなしのまま CE に出すので、CE のサブインタフェースは受け取りません。逆向きは、
タグの付いたフレームにもう 1 枚タグが重なります。

:::try
片方の AC がタグを外さないと、どう見えるかを確かめます。課題 M11-4 の後に行います。

1. XR03 で、`interface GigabitEthernet0/0/0/1.40 l2transport` の下の rewrite を外してコミットします。
2. XR01 と XR03 で `show l2vpn xconnect` を、CEB1 で `ping 172.31.40.3` を実行します。
3. rewrite を戻してコミットし、同じコマンドをもう一度実行します。

結果の例: 両端とも UP のまま、ping は失敗しました(0 percent)。戻すと ping は成功しました(100 percent)。
:::

### 3.4 IOS XE との組み合わせ

このラボの環境では、IOS XR と IOS XE(IOL と Catalyst 8000V の両方)の間の EVPN-VPWS は、制御は両端で up になりましたが、
フレームは IOS XR から IOS XE への向きで IOS XE に捨てられました。IOS XE 同士、IOS XR 同士では通りました。そのため、
このラボの EVPN-VPWS は XR 同士だけで作ります。IOS XE のルータ向けの公式の設定ガイドには、EVPN-VPWS の章が
ありません(ASR 920 にはあります)。

## 4. コマンド名

| IOS XE では | IOS XR では |
|---|---|
| `l2vpn evpn instance <EVI> point-to-point` → `vpws context <名前>` → `service target <n> source <n>` | `l2vpn` → `xconnect group` → `p2p` → `neighbor evpn evi <EVI> target <n> source <n>` |
| `member <IF> service-instance <n>` | `p2p` の下の `interface <サブインタフェース>` |
| `show l2vpn evpn vpws vc id <EVI> detail` | `show l2vpn xconnect [detail]` |
| `show bgp l2vpn evpn` | `show bgp l2vpn evpn` |
| `address-family l2vpn evpn` → `neighbor … activate`、`send-community both` | `address-family l2vpn evpn`(全体と近隣の両方) |

## 実践

ラボ **XRT-11** で、課題 M11-3 と M11-4 に取り組みます。終わったら、次のページ「Q-in-Q」に進みます。

<p class="tolab"><a href="/_learn?id=XRT-11">ワークスペースでラボ XRT-11 を開く</a> — <a href="b3-m11-practice-2.html">課題</a></p>

:::note
出典: L2VPN and Ethernet Services Configuration Guide for the ASR 9000, IOS XR 25.x(2025。EVPN Virtual Private Wire Service、
EVPN の制約= 7.3.2 以降は MTU 0 を広告し食い違いを無視)。IOS XE の MPLS L2VPNs Configuration Guide(ASR 920、EVPN VPWS)。
RFC 7432、8214。いずれも 2026 年 11 月に確認しました。次のものは、ラボ XRT-11 とその PoC での測定によります。
経路とラベル、自動の RD とルート ターゲット、セッションが上がってから経路がそろうまでの時間、食い違いごとの表示、
IOS XE との組み合わせの結果です。
:::
