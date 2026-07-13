# EVPN-VXLAN-01: ファブリックを一枚岩で組む — BGP EVPN × VXLAN 正統編

前作 SDA-LISP-01 では、LISP（電話帳）と VXLAN（トンネル）を**別々のネットワーク**で
組み、終章で「SD-Access はこの2つの合体だ」と**頭の中で**合流させました。
本作はその続編にして正統編です。データセンターやオープンなキャンパスファブリックの
世界標準 **BGP EVPN** をコントロールプレーンに使うと、電話帳とトンネルを
**実機のまま一枚岩で**合流させられます。今日組むのは「本物の」ファブリックです。

★本ラボも**体験型・伴走形式**です（ENCOR では VXLAN/EVPN は describe レベル。
これはその先を体で覚えるエンリッチメント教材です）。各 Phase の
📋観察チェックポイントで実際の出力を読み、🤔考察を出題者と話しながら進めてください。
**得点競争はしません**（最後に軽い疎通確認だけ自動チェックします）。

★前作との最大の違い: 前作の VXLAN 編は leaf 2台の**直結**でした。今回は
**Spine-Leaf** — 本物のファブリックの形です。そして途中で**一度わざと壊れます**。
壊れたときに何を見るかまで含めて教材です。

## トポロジ

```
                     SPINE (IOS-XE・ルートリフレクタ・Lo0 10.254.0.254)
                    /         |          \
             10.0.1.0/30  10.0.2.0/30  10.0.3.0/30     ← アンダーレイ OSPF(構成済み)
                  /           |             \
             [LEAF1]       [LEAF2]        [LEAF3]       ← NX-OS ×3 (VTEP候補)
             Lo0 .0.1      Lo0 .0.2       Lo0 .0.3
               |            |    \           \
              H1           H2    H3          EXT ← 外部網の見立て(据付)
        VLAN100        VLAN100  VLAN200      192.168.100.0/30
        172.16.100.11  .100.12  .200.13      Lo1: 198.51.100.0/24
```

| 項目 | 値 |
|---|---|
| あなたが設定する機器 | SPINE（IOS-XE）、LEAF1 / LEAF2 / LEAF3（NX-OS） |
| 据付（変更禁止） | H1、H2、H3、EXT |
| IOS-XE ログイン | console: `SUZUKI` / `CCNP`（enable も `CCNP`） |
| NX-OS ログイン | console: `SUZUKI` / `CCNP`（または admin / cisco） |
| 構成済みのもの | 各機器の IP・Loopback・**アンダーレイ OSPF**・MGMT |

設計図（あなたがこれから実現する契約）:

| 項目 | 値 |
|---|---|
| BGP AS | 65100（iBGP・SPINE がルートリフレクタ） |
| テナント VRF | TENANT-A |
| VLAN 100 = **VNI 10100** | 172.16.100.0/24・GW .1・**LEAF1 と LEAF2** |
| VLAN 200 = **VNI 10200** | 172.16.200.0/24・GW .1・**LEAF2 のみ**（←わざと） |
| **L3VNI 50000**（VLAN 500 予約） | テナント内のサブネット間ルーティング用 |
| Anycast GW MAC | `0000.2222.3333`（全 leaf 共通） |
| ホスト収容 | H1=LEAF1 Eth1/2、H2=LEAF2 Eth1/2、H3=LEAF2 Eth1/3 |
| 外部接続 | LEAF3 Eth1/2 ⇔ EXT（192.168.100.0/30・198.51.100.0/24 は静的） |

---

# Phase 0: アンダーレイを観察する（設定なし）

LEAF1 のコンソールで:

```
show ip ospf neighbors
show ip route ospf-UNDERLAY
show vlan brief
```

📋 **観察0**: OSPF ネイバーは **SPINE 1台だけ**であること（leaf 同士は直結していない）。
経路表には各機器の **Lo0 /32 と spine-leaf の /30 だけ**が並ぶこと。
VLAN 100 も 200 もまだ存在しないこと。

🤔 **考察0**: 前作の VXLAN 編は leaf 直結でした。実際の DC はなぜ全 leaf を
spine に放射状に繋ぐのでしょう？（ヒント: leaf を1台増やすとき、ケーブルは
何本増えるか。leaf 同士を繋ぐ設計と比べてみてください。East-West 帯域と
等コストの話もあります。）

> **ここからの用語**: VXLAN トンネルの出入口になるスイッチを **VTEP**、
> トンネルの識別子を **VNI** と呼びます（前作 VXLAN 編と同じ）。今回はこれに
> **「MAC/IP の居場所を BGP で先回り配布する」= EVPN** が加わります。
> 前作の LISP が「聞かれたら答える電話帳（pull）」だったのに対し、
> EVPN は「更新があったら全員に配る回覧板（push）」です。

# Phase 1: 回覧板の胴元 — SPINE をルートリフレクタにする

leaf が3台あります。iBGP をフルメッシュで張ると 3 ペア、leaf が 10台なら 45 ペア。
実務では **spine をルートリフレクタ（RR）にして leaf は spine とだけピア**します。
SPINE は IOS-XE です。MPLS L3VPN で使った `address-family vpnv4` の親戚、
**`address-family l2vpn evpn`** を使います:

SPINE で:

```
conf t
router bgp 65100
 bgp router-id 10.254.0.254
 no bgp default ipv4-unicast
 neighbor 10.254.0.1 remote-as 65100
 neighbor 10.254.0.1 update-source Loopback0
 neighbor 10.254.0.2 remote-as 65100
 neighbor 10.254.0.2 update-source Loopback0
 neighbor 10.254.0.3 remote-as 65100
 neighbor 10.254.0.3 update-source Loopback0
 address-family l2vpn evpn
  neighbor 10.254.0.1 activate
  neighbor 10.254.0.1 send-community both
  neighbor 10.254.0.1 route-reflector-client
  neighbor 10.254.0.2 activate
  neighbor 10.254.0.2 send-community both
  neighbor 10.254.0.2 route-reflector-client
  neighbor 10.254.0.3 activate
  neighbor 10.254.0.3 send-community both
  neighbor 10.254.0.3 route-reflector-client
end
```

- `send-community both` を忘れると **route-target が運ばれず**、ファブリック全体が
  静かに死にます（MPLS L3VPN と同じ急所）。
- SPINE は **VTEP ではありません**。トンネルは張らず、回覧板を配るだけです。

次に **LEAF1 / LEAF2 / LEAF3 の3台とも**（router-id は各自の Lo0 に読み替え）:

```
conf t
feature bgp
feature nv overlay
nv overlay evpn
router bgp 65100
 router-id 10.254.0.1
 neighbor 10.254.0.254
  remote-as 65100
  update-source loopback0
  address-family l2vpn evpn
   send-community
   send-community extended
end
copy running-config startup-config
```

> ★NX-OS の罠: `nv overlay evpn` を宣言するまで、BGP に
> **`address-family l2vpn evpn` というコマンド自体が存在しません**
> （`show bgp l2vpn evpn summary` すら Invalid になります）。
> 「EVPN を喋る」宣言が先、が NX-OS の流儀です。

📋 **観察1**: LEAF1 で `show bgp l2vpn evpn summary` — SPINE とのピアが Up
（State/PfxRcd が数字）になること。ただし **PfxRcd は 0**。SPINE でも
`show bgp l2vpn evpn summary` で **3つの leaf が全員集合**していることを確認。

🤔 **考察1**: なぜまだ 0 なのでしょう？（回覧板の仕組みはできたが、
**回覧する記事をまだ誰も書いていない**からです。記事=MAC/IP の居場所は、
次の Phase で VNI を作った瞬間から流れ始めます。）

# Phase 2: L2VNI — 同じサブネットを spine 越しに繋ぐ

前作 VXLAN 編の復習を、今度は**フルメッシュではなく RR 経由**でやります。
ゴール: H1（LEAF1・VLAN100）と H2（LEAF2・VLAN100）を同一 L2 セグメントにする。

**LEAF1 と LEAF2 の両方**で:

```
conf t
feature interface-vlan
feature vn-segment-vlan-based
vlan 100
  vn-segment 10100
exit
evpn
 vni 10100 l2
  rd auto
  route-target import auto
  route-target export auto
exit
interface nve1
 no shutdown
 host-reachability protocol bgp
 source-interface loopback0
 member vni 10100
  ingress-replication protocol bgp
exit
interface Ethernet1/2
 switchport
 switchport access vlan 100
 no shutdown
end
copy running-config startup-config
```

（すべて前作 Phase 6〜8 で打った道具です。忘れていたら前作の task.md を開いて
思い出しながらで構いません — それも復習のうち。）

📋 **観察2-1**: LEAF1 で `show nve peers` — **LEAF2 の Lo0 (10.254.0.2)** が
Up / **LearnType=CP** で載ること。★ここが前作との違いの見どころ:
**BGP のピアは SPINE としか張っていないのに、トンネルは LEAF2 へ直接**
張られています。`show bgp l2vpn evpn summary` の Type-3 カウントも見ること。

📋 **観察2-2**: H1 から `ping 172.16.100.12 repeat 10` — 初回 ARP で
**1発だけ落ち**、あとは通ること。

📋 **観察2-3**: SPINE で `show bgp l2vpn evpn` — RR の視点で **Type-2**（MAC の記事）
と **Type-3**（トンネル参加宣言）が RD 別に並ぶこと。SPINE は各記事の
**Next-Hop を書き換えずに**配っていること（Next-Hop が leaf の Lo0 のままであること）。

🤔 **考察2**: 前作 LISP の初回 ping は 2発落ちました（Map-Request の往復待ち）。
今回はなぜ1発で済むのでしょう？（H2 の MAC は、H2 が最初に何かを喋った瞬間に
**先回りで**全 leaf に配られています。落ちた1発は純粋にローカルの ARP 解決だけ。
pull と push の差が、落ちた発数にそのまま出ています。）

# Phase 3: Symmetric IRB — サブネットを跨ぐ（★一度壊れます）

H3（172.16.200.13・VLAN200）は **LEAF2 にだけ**います。設計図どおり
**VLAN200 は LEAF1 に作りません**（そのサブネットの端末がいない leaf に
サブネットを配らないのは、実務の基本です）。それでも H1（LEAF1）から
H3 へ**ファブリック越しにルーティング**で届かせます。使う道具が
**L3VNI（VNI 50000）と分散 Anycast Gateway** です。

**LEAF1 / LEAF2 の両方**で（VRF とゲートウェイの土台）:

```
conf t
feature fabric forwarding
fabric forwarding anycast-gateway-mac 0000.2222.3333
vlan 500
  vn-segment 50000
exit
vrf context TENANT-A
 vni 50000
 rd auto
 address-family ipv4 unicast
  route-target both auto
  route-target both auto evpn
exit
interface Vlan100
 no shutdown
 vrf member TENANT-A
 ip address 172.16.100.1/24
 fabric forwarding mode anycast-gateway
exit
interface Vlan500
 no shutdown
 vrf member TENANT-A
 ip forward
exit
router bgp 65100
 vrf TENANT-A
  address-family ipv4 unicast
   advertise l2vpn evpn
end
```

**LEAF2 だけ**、H3 のサブネットを追加:

```
conf t
vlan 200
  vn-segment 10200
exit
evpn
 vni 10200 l2
  rd auto
  route-target import auto
  route-target export auto
exit
interface Vlan200
 no shutdown
 vrf member TENANT-A
 ip address 172.16.200.1/24
 fabric forwarding mode anycast-gateway
exit
interface nve1
 member vni 10200
  ingress-replication protocol bgp
exit
interface Ethernet1/3
 switchport
 switchport access vlan 200
 no shutdown
end
copy running-config startup-config
```

- `Vlan500` は **L3VNI 用の SVI**。IP を持たず `ip forward` だけ —
  「ルーティングの通り道」専用です。
- `fabric forwarding mode anycast-gateway` = **全 leaf が同じ IP・同じ MAC で
  ゲートウェイを名乗る**仕掛け。端末はどの leaf に繋がっても（移動しても）
  GW の設定を変えずに済みます。

では試します。H1 から:

```
ping 172.16.200.13 repeat 10
```

📋 **観察3-1**: まず H2→H3（同じ LEAF2 の中のサブネット間）は通るのに、
**H1→H3 は 0% のはず**です。ローカルのルーティングはできて、
ファブリック越しだけができない——なぜか。

**指紋を採ります。** まず LEAF1 で:

```
show nve vni
show bgp l2vpn evpn 172.16.200.13
```

📋 **観察3-2**: 2つの故障指紋を確認:
- `show nve vni` に 10100 はあるのに **VNI 50000 の行が無い**
- `show bgp l2vpn evpn 172.16.200.13` が**空**（H3 のルーティング記事が
  **そもそも回覧されていない**）

回覧が無いなら、書き手を疑います。LEAF2（H3 を収容している側）で:

```
show ip arp vrf TENANT-A
show bgp l2vpn evpn 172.16.200.13
```

📋 **観察3-3**: LEAF2 は ARP で **H3 を知っています**。それなのに
`show bgp l2vpn evpn 172.16.200.13` は **LEAF2 でも空**——
知っているのに、**記事を書いていない**。

🤔 **考察3-1**: どこが足りないのでしょう？ VRF も SVI も BGP もある。
——**運び屋（NVE）に L3VNI が繋がっていません**。leaf は
「この VRF の記事はトンネル VNI 50000 で運ぶ」と教わって初めて、
MAC+IP の記事に **L3 の荷札**（ラベル 50000・RT 65100:50000・自分の Router MAC）を
貼って回覧できます。荷札を貼れない記事は書かない——だから電話帳のどこにも
H3 のルーティング情報が存在しなかったのです。

処方箋（**LEAF1 / LEAF2 の両方**）:

```
conf t
interface nve1
 member vni 50000 associate-vrf
end
copy running-config startup-config
```

📋 **観察3-4**: H1 から `ping 172.16.200.13 repeat 10` → **通る**こと。
LEAF1 で `show bgp l2vpn evpn 172.16.200.13` — さっき空だった記事が現れ、
**`Received label 10200 50000`・`RT:65100:10200 RT:65100:50000`・`Router MAC:`** が
付いていること（これが「L3 の荷札」の正体です）。
`show ip route 172.16.200.13 vrf TENANT-A` に **/32 のホストルート**が
`segid: 50000 ... encap: VXLAN` 付きで入ること（★Symmetric IRB の指紋:
「/24 ではなく **/32** が、L3VNI 経由で入る」）。
`show nve vni` にも `50000 ... L3 [TENANT-A]` が生えていること。

📋 **観察3-5**: H1 で `show ip arp 172.16.100.1`、H2 でも `show ip arp 172.16.100.1`
— **別々の leaf にいるのに、GW の MAC がどちらも `0000.2222.3333`** であること。

🤔 **考察3-2**: LEAF1 は 172.16.200.0/24 という**サブネットを持っていない**のに
H3 に届きました（/32 が直接 L3VNI を指すから）。「全 leaf に全サブネットを
配らなくてよい」——これが大規模ファブリックでスケールする理由です。
前作 LISP の「EID を IGP に入れない」思想と、同じ匂いがしませんか？

🤔 **考察3-3（発展）**: では、もし H3 が**生まれてから一度も喋っていなかったら**
どうなるでしょう？ LEAF2 は H3 の ARP を知らない → MAC+IP の記事を書けない →
H1 からは永遠に届きません（今回は観察3-1 で H2→H3 を先に叩いたので、
そこで LEAF2 が学習済みでした）。これは **silent host 問題**という EVPN の
有名な論点です（実務の解: 収容 leaf がサブネット /24 も広告して、
届いた先で ARP を代行させる等）。「push 型は、誰かが最初に記事を
書かないと配れない」——pull 型なら起きない悩みです。

# Phase 4: Border Leaf — ファブリックの外と繋ぐ（Type-5）

最後に LEAF3 を **border leaf** に仕立て、外部網（EXT の 198.51.100.0/24）と
テナントを繋ぎます。LEAF3 には端末が1台もいないことに注目してください。
L2VNI もアクセスポートも要りません — **必要なのは VRF と L3VNI だけ**です。
ここまで自力で組めるか、腕試しの Phase です（下に手順はありますが、
まず設計図から自分で書き出してみることを勧めます）。

LEAF3 で:

```
conf t
feature interface-vlan
feature vn-segment-vlan-based
feature nv overlay
nv overlay evpn
vlan 500
  vn-segment 50000
exit
vrf context TENANT-A
 vni 50000
 rd auto
 address-family ipv4 unicast
  route-target both auto
  route-target both auto evpn
 ip route 198.51.100.0/24 192.168.100.2
exit
interface Vlan500
 no shutdown
 vrf member TENANT-A
 ip forward
exit
interface Ethernet1/2
 no switchport
 vrf member TENANT-A
 ip address 192.168.100.1/30
 no shutdown
exit
ip prefix-list PL-EXT seq 5 permit 198.51.100.0/24
route-map RM-EXT permit 10
 match ip address prefix-list PL-EXT
exit
router bgp 65100
 vrf TENANT-A
  address-family ipv4 unicast
   advertise l2vpn evpn
   redistribute static route-map RM-EXT
exit
interface nve1
 no shutdown
 host-reachability protocol bgp
 source-interface loopback0
 member vni 50000 associate-vrf
end
copy running-config startup-config
```

（Phase 1 で LEAF3 の BGP ピアは張ってあります。NX-OS の redistribute は
route-map 必須 — 裸の `redistribute static` は受け付けません。）

📋 **観察4-1**: LEAF1 で `show ip route vrf TENANT-A` — **198.51.100.0/24** が
`segid: 50000 ... encap: VXLAN` で入ること。`show bgp l2vpn evpn summary` の
**Type-5** カウントが増えていること（サブネット丸ごとの記事は Type-2 ではなく
**Type-5** で運ばれます）。

📋 **観察4-2**: H1 から `ping 198.51.100.1 repeat 10` → 通ること。
EXT から `ping 172.16.100.11 source Loopback1 repeat 10` → 通ること
（戻り: EXT はファブリックを知らず、ただ LEAF3 にデフォルトで投げるだけ。
LEAF3 が H1 の /32 を Type-2 で知っているから届きます）。

🤔 **考察4**: 前作の PXTR（Border Node）を思い出してください。あちらは
「どの宛先が LISP か」を教える静的 map-cache が要りました（pull 型は
トリガが要る）。今回の border は**何もトリガが要りません** — Type-5 で
先回り配布するだけ（push 型は配れば終わり）。同じ「境界」という仕事の、
思想の違いがここにも出ています。

---

# 終章: 前作の宿題を回収する — 電話帳とトンネルの一枚岩

前作の終章で「SD-Access = LISP の電話帳 + VXLAN のトンネル」という対応表を
作りました。今日組んだものを、その表に**3列目**として書き足します:

| 役割 | SD-Access（前作） | 本作（EVPN ファブリック） |
|---|---|---|
| 電話帳（居場所の解決） | LISP Map-Server（**pull**・聞かれたら答える） | **BGP EVPN**（**push**・先回りで配る） |
| 電話帳の胴元 | Control Plane Node (MSMR) | **ルートリフレクタ (SPINE)** |
| 端末の出入口 | Edge Node (xTR) | **Leaf (VTEP)** |
| 外との境界 | Border Node (PXTR)＋静的トリガ | **Border Leaf**＋Type-5（トリガ不要） |
| 運び方 | VXLAN(-GPO) | VXLAN（同じ！） |
| 初回パケット | 2発落ちる（Map-Request 往復） | 1発（ローカル ARP のみ） |
| サブネット間 | （前作では未体験） | **Symmetric IRB**（L3VNI・/32 ホストルート） |

- **運び方（VXLAN）は両者で同一**です。違いは電話帳の思想だけ。
  移動の多い無線端末を数万台さばくキャンパス = pull（LISP）、
  メンバーがほぼ固定で帯域勝負の DC = push（EVPN）。適材適所です。
- 今日の構成（NX-OS + EVPN + VXLAN + Anycast GW）は、そのまま実務の
  DC ファブリックの標準形です。`show bgp l2vpn evpn` を読める人は現場で強い。

🤔 **最終考察**: もし明日 H1 を LEAF1 から LEAF3 に差し替えたら、
何がどの順で起きるでしょう？（H1 が喋る → LEAF3 が MAC を学習 → Type-2 を配る →
各 leaf の電話帳が更新される → GW は Anycast なので H1 は何も気づかない。
——「端末の移動にネットワークが追従する」。SD-Access が LISP でやったことを、
EVPN は BGP でやっている、というだけの話でした。）

> **コラム（手は動かしません）**: 本物の leaf は ARP をトンネル越しに流さず
> 代理応答する **ARP suppression** も使います。本ラボで触らないのは、
> Nexus では TCAM の割当変更（`hardware access-list tcam region ...`）と
> **再起動2回**が要るためです。「ASIC のリソースは有限で、機能を足すには
> 別の何かを削る」— これも実機の現実として覚えておいてください。

---

## 完成条件（軽い自動チェックのみ・伴走の答え合わせ用）

1. SPINE（RR）と leaf 3台の EVPN ピアが全て確立
2. L2VNI: H1⇄H2 疎通・NVE ピア CP 学習・VNI 10100/10200 Up
3. Symmetric IRB: H1⇄H3 疎通・リモート /32 が L3VNI(50000) 経由・VNI 50000 Up
4. Anycast GW: H1 と H2 の GW MAC がともに 0000.2222.3333
5. Type-5: H1→198.51.100.1・EXT(Lo1)→H1 の双方向疎通

## ログイン・注意

- 全機器 CML コンソールから操作（IOS-XE: `SUZUKI`/`CCNP`、NX-OS: `SUZUKI`/`CCNP`）
- **H1 / H2 / H3 / EXT は据付**（観察のためのログインは可・設定変更は禁止）
- アンダーレイ（OSPF・IP・Loopback）は構成済み。**消さない・変えない**こと
  （特に Lo0 は VTEP/RR の土台です）
- NX-OS は `copy running-config startup-config`、IOS-XE は `write memory` で保存
- VLAN200 を LEAF1 に作りたくなっても**作らない**こと（Phase 3 の学びが消えます）
