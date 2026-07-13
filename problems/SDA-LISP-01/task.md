# SDA-LISP-01: SD-Access の中身を素手で組む — LISP と VXLAN の原理ラボ

DNA Center（Catalyst Center）の SD-Access ファブリックは、GUI のボタン1つで
拠点ネットワークを「オーバーレイ化」します。しかしその裏でコントローラが
機器に流し込んでいるのは、**LISP（宛先解決のしくみ）と VXLAN（カプセル化のしくみ）**
の設定です。本ラボではコントローラ抜きで、その2つを**自分の手で** CLI から組み、
「ファブリックはなぜ動くのか」を腑に落とします。

★本ラボは**体験型・伴走形式**です。試験ドリルではありません（ENCOR では SD-Access は
describe レベル）。各 Phase の 📋観察チェックポイントで実際の出力を読み、
🤔考察を出題者と話しながら進めてください。**得点競争はしません**
（最後に軽い疎通確認だけ自動チェックします）。

★2部構成です。**第1部（LISP編）と第2部（VXLAN編）は独立した別のネットワーク**で、
ケーブルは1本も繋がっていません。「なぜ別々に学ぶのか」は終章で種明かしします。

## トポロジ

```
【第1部: LISP編 — 全て IOS-XE・アンダーレイ(OSPF)構成済み】

  XTR1                          XTR2
  EID: 172.16.1.0/24 (Lo1)      EID: 172.16.2.0/24 (Lo1)
  RLOC: 10.255.0.2 (Lo0)        RLOC: 10.255.0.3 (Lo0)
      └── 10.0.1.0/30 ──┐   ┌── 10.0.2.0/30 ──┘
                       MSMR   ← Map-Server/Map-Resolver 兼コア (RLOC 10.255.0.1)
                        │ 10.0.3.0/30
                       PXTR   ← LISP世界と外界の境界 (RLOC 10.255.0.4)
                        │ 192.168.100.0/30
                       EXT    ← 非LISPの世界 (198.51.100.0/24)・据付=触らない

【第2部: VXLAN編 — NX-OS×2・アンダーレイ(OSPF)構成済み】

  H1 ── Eth1/2 [LEAF1] Eth1/1 ══ 10.0.99.0/30 ══ Eth1/1 [LEAF2] Eth1/2 ── H2
  172.16.100.11        Lo0: 10.254.0.1        Lo0: 10.254.0.2   172.16.100.12
  (据付ホスト)          ↑この区間を VNI 10100 のトンネルにする↑    (据付ホスト)
```

| 項目 | 値 |
|---|---|
| あなたが設定する機器 | MSMR / XTR1 / XTR2 / PXTR（IOS-XE）、LEAF1 / LEAF2（NX-OS） |
| 据付（変更禁止） | EXT、H1、H2 |
| IOS-XE ログイン | console: `SUZUKI` / `CCNP`（enable も `CCNP`） |
| NX-OS ログイン | console: `SUZUKI` / `CCNP`（または admin / cisco） |
| 構成済みのもの | 各機器の IP・Loopback・**アンダーレイ OSPF**（両編とも） |

---

# 第1部 LISP編 — 「電話帳」を組む

## Phase 0: アンダーレイを観察する（設定なし）

XTR1 のコンソールで:

```
show ip route ospf
show ip cef 172.16.2.1
```

📋 **観察0**: OSPF で見えているのは **RLOC（各ルータの Lo0 /32）とコア区間だけ**
であること。XTR2 のサイトの **172.16.2.0/24 は経路表に存在しない**こと
（cef の答えは何と言っているか）。

🤔 **考察0**: 従来のネットワークなら 172.16.2.0/24 を OSPF に入れて終わりです。
SD-Access（および LISP）は**あえて入れません**。端末のセグメントを IGP に
入れない設計は、端末が数万台・移動もする（無線・在宅）キャンパスで
何を解決すると思いますか？（ヒント: 経路表のサイズと、端末が動くたびの再収束）

> **ここからの用語**: 端末側のアドレス空間を **EID**（Endpoint ID）、
> ルータ自身のアドレス（Lo0）を **RLOC**（Routing Locator）と呼びます。
> LISP は「EID宛の通信を、EIDを収容するルータのRLOC宛にカプセル化して飛ばす」
> しくみです。「どの EID がどの RLOC にいるか」を答えるのが Map-Server。
> **DNS にそっくり**だと思いながら進めてください。

## Phase 1: Map-Server / Map-Resolver（電話帳サーバ）を立てる

MSMR で。まず「電話帳に載せてよいサイト」を定義します（登録には認証鍵が必要）:

```
conf t
router lisp
 site SITE-A
  authentication-key CCNP
  eid-prefix 172.16.1.0/24
  exit
 site SITE-B
  authentication-key CCNP
  eid-prefix 172.16.2.0/24
  exit
 ipv4 map-server
 ipv4 map-resolver
end
```

- `site` = 「この EID 空間の登録を受け付ける」という**契約の枠**。
  鍵が合わない登録は拒否されます（勝手なルータが電話帳を汚せない）。
- `map-server` = 登録(Map-Register)の受付係。`map-resolver` = 問合せ(Map-Request)の受付係。
  本ラボでは兼務させます（実際の SD-Access でも Control Plane Node が兼務）。

📋 **観察1**: `show lisp site` — SITE-A / SITE-B が **Up=no** で並ぶこと。
枠はできたが、**まだ誰も登録に来ていない**状態です（電話帳は白紙）。

## Phase 2: xTR（サイトの出入口）を電話帳に登録させる

XTR1 で:

```
conf t
router lisp
 database-mapping 172.16.1.0/24 10.255.0.2 priority 1 weight 100
 ipv4 itr map-resolver 10.255.0.1
 ipv4 etr map-server 10.255.0.1 key CCNP
 ipv4 itr
 ipv4 etr
end
```

- `database-mapping` = 「**私（RLOC 10.255.0.2）が 172.16.1.0/24 を収容している**」
  という自己申告。この1行が電話帳の1エントリになります。
- ETR（Egress Tunnel Router）= 受信側の顔: Map-Server へ登録し、届いた
  カプセルを剥がす。ITR（Ingress）= 送信側の顔: 宛先を Map-Resolver に
  問合せ、カプセル化して送る。1台で両方やるので **xTR** と呼びます。

📋 **観察2-1**: MSMR で `show lisp site` — **SITE-A の行が Up=yes に変わる**こと。
`show lisp session` で XTR1 の RLOC とのセッションが established であること。

**やってみよう**: XTR2 を XTR1 に倣って自力で設定してください
（EID=172.16.2.0/24、RLOC=10.255.0.3。それ以外は同じ）。

📋 **観察2-2**: MSMR で SITE-B も Up=yes になり、`show lisp session` が
**established: 2** になること。電話帳が2件そろいました。

🤔 **考察2**: この時点で XTR1 の `show ip route` に 172.16.2.0/24 は
**まだ載っていません**（確認してみてください）。それでも次の Phase で
通信は成立します。「経路を配る」ことと「宛先を解決できる」ことの違いを
考えてみてください。

## Phase 3: EID 間で通信する — 電話帳が引かれる瞬間

XTR1 で、**必ず EID をソースにして** ping します:

```
ping 172.16.2.1 source Loopback1
```

📋 **観察3-1**: **最初の1〜2発は落ち、残りが通る**こと（`..!!!` のような出力）。
もう一度同じ ping を打つと **5/5 で通る**こと。

```
show lisp instance-id 0 ipv4 map-cache
```

📋 **観察3-2**: `172.16.2.0/24 ... via map-reply, complete` のエントリが
**いま生まれた**こと。Locator が XTR2 の RLOC（10.255.0.3）であること。
uptime がさっきの ping の瞬間であること。

🤔 **考察3-1**: なぜ初回だけ落ちたのでしょう？（1発目のパケットが届く前に、
裏で Map-Request → Map-Reply の往復が走っています。DNS の「初回だけ遅い」と
同じ構図です。）このエントリの expires は約24時間 — キャッシュが切れたら
また聞き直します。

📋 **観察3-3**: `traceroute 172.16.2.1 source Loopback1` — ホップが
**「コア1段→いきなり宛先」**に見えること。実際は MSMR を物理的に経由して
いますが、**カプセルの中身から見ると途中は存在しない**——これがオーバーレイです。

🤔 **考察3-2**: MSMR は今、データ転送に関与しているでしょうか？
（電話帳は「聞かれたら答える」だけで、通話そのものは仲介しません。
コントロールプレーンとデータプレーンの分離、が体で分かる瞬間です。）

## Phase 4: PxTR — LISP の世界と外の世界をつなぐ（★今回一番の山場）

サイトから **LISP を知らない外部**（EXT の 198.51.100.0/24 —
インターネットや既設網の見立て）へ出入りさせます。境界ルータ PXTR を
**Proxy xTR** にします。

まず PXTR で:

```
conf t
router lisp
 ipv4 proxy-etr
 ipv4 proxy-itr 10.255.0.4
 ipv4 itr map-resolver 10.255.0.1
end
```

次に **XTR1 と XTR2 の両方**に「外向きの通信は PXTR に投げる」を追加:

```
conf t
router lisp
 ipv4 use-petr 10.255.0.4
end
```

では試します。XTR1 から:

```
ping 198.51.100.1 source Loopback1 repeat 4
show lisp instance-id 0 ipv4 map-cache
```

📋 **観察4-1**: **ping は 0% のはず**です。しかし map-cache には
`192.0.0.0/2 ... forward-native` / `Encapsulating to proxy ETR` という
**負のキャッシュ**が入っています（「その宛先は LISP の外だ」という
Map-Resolver からの回答。外向きは PETR 行きに切り替わった証拠）。
行きの仕組みはできているのに、通らない——なぜか。

**戻りを疑います。** EXT からの返事は PXTR に届きます（EXT のデフォルトルートは
PXTR 向き・据付済み）。PXTR は返事を **XTR1 へカプセル化し直す**（Proxy-ITR の
仕事）必要があります。PXTR で:

```
show ip lisp
show lisp instance-id 0 ipv4 map-cache
```

📋 **観察4-2**: 2つの故障指紋を確認:
- `ITR local RLOC (last resort): *** NOT FOUND ***`
- `% Could not find EID table instance ID 0 in LISP 0.`

🤔 **考察4-1**: PXTR は proxy-itr を名乗ったのに、**「どの宛先空間が LISP なのか」を
誰にも教わっていません**。172.16.1.1 宛のパケットが来ても、経路表に無い＝ただ捨てる。
Map-Request を出すきっかけ（トリガ）が無いのです。xTR は database-mapping が
そのトリガを作っていましたが、PXTR は EID を持ちません。

処方箋: **「この空間は LISP だ、来たら Map-Request を出せ」という静的エントリ**を
PXTR に置きます:

```
conf t
router lisp
 instance-id 0
  service ipv4
   eid-table default
   map-cache 172.16.0.0/16 map-request
end
```

> ★構文の罠: ここまで全部 `ipv4 〜` で通ってきたのに、**`ipv4 map-cache 〜` だけは
> Invalid** です（この設定だけ新しい階層構文が必要）。エラーになったら
> この注意書きを思い出してください。

📋 **観察4-3**: XTR1 から `ping 198.51.100.1 source Loopback1` → **通る**こと
（初回1〜2発落ちは例のアレです）。XTR2 からも確認。
PXTR の `show lisp instance-id 0 ipv4 map-cache` に、EXT からの戻りをきっかけに
学習した `172.16.1.0/24 → 10.255.0.2` が載ること。

🤔 **考察4-2**: SD-Access ではこの PXTR に相当するのが **Border Node** です。
「ファブリックの中は電話帳、外は普通のルーティング」の変換点が必ず1箇所必要——
DNAC はこれを自動で作っています。

**第1部完了。** MSMR=Control Plane Node、xTR=Edge Node、PXTR=Border Node。
あなたはいま SD-Access ファブリックの登場人物を全員、素手で組みました。

---

# 第2部 VXLAN編 — 「トンネル掘削機」を組む

第1部の LISP は、実は**運び方も LISP 独自のカプセル**でした。SD-Access の実物は
運び方に **VXLAN** を使います。第2部では VXLAN を、DC で標準の
**BGP EVPN** という別のコントロールプレーンと組み合わせて組みます
（NX-OS。CLI の流儀が変わるのも体験のうち）。

ゴール: **別々のスイッチにつながる H1 と H2（同じ 172.16.100.0/24）を、
L3 ルーテッド区間越しに同一 L2 セグメントとして繋ぐ。**

## Phase 5: アンダーレイ観察と NX-OS 入門

LEAF1 のコンソールで:

```
show ip ospf neighbors
show ip route 10.254.0.2
ping 10.254.0.2 source 10.254.0.1
```

📋 **観察5**: leaf 間は **L3（/30 + OSPF）**で、Lo0 同士が /32 で見えること。
つまり H1 と H2 の間に **L2 は 1cm も通っていない**こと。
`show vlan` で VLAN 100 がまだ無いことも見ておいてください。

## Phase 6: 機能を有効化し、VLAN と VNI を結婚させる

NX-OS は使う機能を明示的に有効化する思想です。**LEAF1 / LEAF2 の両方**で:

```
conf t
feature bgp
feature interface-vlan
feature vn-segment-vlan-based
feature nv overlay
nv overlay evpn
vlan 100
  vn-segment 10100
exit
```

- `vn-segment 10100` = 「このスイッチのローカルな VLAN 100 を、
  ファブリック共通の **VNI 10100** に対応づける」宣言。

🤔 **考察6**: VLAN ID は 12bit（〜4094）、VNI は **24bit（1600万）**です。
「ローカルには VLAN、ファブリック全体では VNI」という2段構えが、
マルチテナントの巨大環境で何を可能にするか考えてみてください。

## Phase 7: BGP EVPN — 「先回りで配る」電話帳

**LEAF1** で（LEAF2 は router-id と neighbor を読み替え）:

```
conf t
router bgp 65100
 router-id 10.254.0.1
 neighbor 10.254.0.2
  remote-as 65100
  update-source loopback0
  address-family l2vpn evpn
   send-community
   send-community extended
 exit
exit
evpn
 vni 10100 l2
  rd auto
  route-target import auto
  route-target export auto
end
```

- **l2vpn evpn** アドレスファミリ = 「経路」ではなく **「MACアドレスの居場所」を
  BGP で運ぶ**拡張。MPLS L3VPN をやった人は rd / route-target の再登場に
  ニヤリとしてください（同じ道具で L2 を運んでいます）。

📋 **観察7**: `show bgp l2vpn evpn summary` — ピアが **Up** になること。
受信プレフィックス数も見ておくこと（まだ 0 のはず。広告すべき「モノ」を
まだ作っていないからです — それが次の Phase）。

## Phase 8: NVE — トンネルの入口を開ける

**LEAF1 / LEAF2 の両方**で（そのまま同じ設定で可）:

```
conf t
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
```

- `nve1` = VXLAN の出入口（トンネルの坑口）。`host-reachability protocol bgp` が
  **「MAC 学習はフラッディングでなく BGP で」**という EVPN の核心の1行です。

📋 **観察8-1**: 両方に入れたら `show nve peers` — 相手の Lo0 が
**Up / LearnType=CP**（Control Plane）で載ること。`show nve vni` — VNI 10100 が
**Up / Mode=CP**、`show bgp l2vpn evpn summary` に **Type-3**（トンネル参加宣言）
が交換されていること。

📋 **観察8-2**: H1 のコンソールから `ping 172.16.100.12 repeat 10` —
**初回の ARP で1発落ち、あとは全部通る**こと。

📋 **観察8-3**: LEAF1 で:

```
show l2route evpn mac all
show bgp l2vpn evpn
```

- H1 の MAC が **Local**、H2 の MAC が **BGP** 産（Next-Hop=相手の Lo0、
  Label 10100）で並ぶこと。
- BGP テーブルに **Type-2**（MAC そのものの広告）が increased していること。

🤔 **考察8**: 第1部の LISP は「**聞かれたら**答える」（初回パケットが
トリガ・pull 型）でした。EVPN は「**先回りで**配る」（ARP を学習した瞬間に
BGP で全員へ・push 型）。観察3-1 と観察8-2 の**落ちた発数の違い**は
この設計思想の違いがそのまま出ています。どちらが優れているかではなく、
「未知の宛先が多い WAN 向き＝pull」「メンバーが決まっている DC/キャンパス
向き＝push」という適材適所を考えてみてください。

---

# 終章: 2つを頭の中で合流させる — これが SD-Access

手は動かしません。2つの出力を並べて見てください:

- 第1部: XTR1 の `show lisp instance-id 0 ipv4 map-cache`（IP → RLOC の対応）
- 第2部: LEAF1 の `show l2route evpn mac all`（MAC → VTEP の対応）

**どちらも「端末の居場所を、収容スイッチのアドレスに解決する電話帳」**です。
本物の SD-Access は:

| SD-Access の部品 | 本ラボで組んだもの |
|---|---|
| Control Plane Node | 第1部の MSMR（LISP Map-Server/Resolver） |
| Edge Node | 第1部の xTR（＋端末情報は MAC/IP とも LISP に登録） |
| Border Node | 第1部の PXTR |
| データプレーン | **第2部の VXLAN**（ただし SGT を運べる拡張版 VXLAN-GPO） |
| （ポリシープレーン） | 本ラボ対象外（ISE/TrustSec。CML では再現不可） |

つまり SD-Access ＝ **「第1部の電話帳」で解決し「第2部のトンネル」で運ぶ**、
2つのいいとこ取りです（LISP の pull 型は無線端末の移動に強く、VXLAN は
ASIC で高速に処理できる）。それを cat9k の ASIC と DNAC の自動生成コンフィグで
量産可能にした製品名が SD-Access——この一文が腑に落ちていれば、本ラボは完了です。

🤔 **最終考察**: DNAC の GUI で「ファブリックにスイッチを追加」を押すと、
裏で何行くらいのコンフィグが流れると思いますか？ あなたが今日手で打った
行数が、その答えのおおよそです。

---

## 完成条件（軽い自動チェックのみ・伴走の答え合わせ用）

1. MSMR に SITE-A / SITE-B が両方登録済み（Up=yes）
2. EID 間疎通: XTR1⇄XTR2（source Loopback1）
3. 外部相互到達: XTR1/XTR2 → 198.51.100.1、EXT → 172.16.1.1（PxTR 経由・双方向）
4. VXLAN: NVE ピア CP 学習・VNI 10100 Up・H1⇄H2 疎通・リモート MAC が BGP 産

## ログイン・注意

- 全機器 CML コンソールから操作（IOS-XE: `SUZUKI`/`CCNP`、NX-OS: `SUZUKI`/`CCNP`）
- **EXT / H1 / H2 は据付**（観察のためのログインは可・設定変更は禁止）
- アンダーレイ（OSPF・IP・Loopback）は構成済み。**消さない・変えない**こと
  （特に Lo0 は RLOC/VTEP の土台です）
- NX-OS は `copy running-config startup-config`、IOS-XE は `write memory` で保存
