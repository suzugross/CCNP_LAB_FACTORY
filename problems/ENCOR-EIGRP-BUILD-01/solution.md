# ENCOR-EIGRP-BUILD-01 解説（想定解・IOL 実機で 100/100 確認済み）

named mode の EIGRP（AS 100, プロセス名 `CCNP`）を全機に構成する。要件 1〜7 を満たす最小構成例。

## 要点
- **named mode**：`router eigrp CCNP` → `address-family ipv4 unicast autonomous-system 100`。
  IPv4 直結が複数あるため **`eigrp router-id` は手動**（Loopback0 アドレス）にして安定させる。
- **passive 既定 + 明示解除**：`af-interface default` で `passive-interface` を既定にし、
  隣接を張る L3 リンクだけ `no passive-interface`。Loopback は passive のまま広告される。
- **認証は RT01–RT02 のみ**：`af-interface Ethernet0/0` で `authentication mode md5` ＋
  `authentication key-chain EI-KC`。key-chain は両端同一文字列。他 IF には付けない。
- **不等コストLB（variance）**：RT01–RT03 が高遅延（`delay 5000`）のため、RT01 の
  `10.5.0.0/22` は既定では **RT02 経由 1 本**（FD=2048640）。RT03 直行は metric=26624640 で
  Feasible Successor（RD < FD を満たす）。比 26624640 / 2048640 ≒ **12.99** なので
  **`variance 13` 以上**で 2 経路化する（本解は `variance 16`）。RT01 の topology base に設定。
- **スタブ**：RT04/RT05 は `eigrp stub connected summary`。
- **集約**：RT02 は `10.4.0.0/22`、RT03 は `10.5.0.0/22` を **コア向け IF の `af-interface` に
  `summary-address`** で設定（RT02 は E0/0・E0/1、RT03 は E0/0・E0/1 の両コア面）。
- **フィルタ（RT03 のみ到達可）**：管理 `10.99.5.1/32` は **RT05 が普通に広告**（`network` に含める・
  RT05 では抑止しない）。RT03 が学習して RIB に持つ（＝RT03 は到達可）一方、**RT03 のコア面
  （E0/0=RT01, E0/1=RT02）out で distribute-list** し RT01/RT02 へは伝播させない。
  - 集約（`10.5.0.0/22`）はブロック外の `10.99.5.1` を覆わないため集約では抑止できない。かつ
    RT03 に見せる要件のため「EIGRP に載せない」では不可 → **中継点フィルタが必須**。
  - ★named mode `topology base` 配下の distribute-list キーワードは **`prefix`**（`prefix-list` ではない）。
    `distribute-list prefix <名> {in|out} [interface]`。prefix-list は事前定義要・global/per-interface とも可。
    番号/名前付き ACL・route-map も使える（`distribute-list <acl> out <if>` 等）。

## 各ノード設定

### RT01（コア・variance）
```
key chain EI-KC
 key 1
  key-string CCNPeigrp
!
router eigrp CCNP
 address-family ipv4 unicast autonomous-system 100
  eigrp router-id 10.0.1.1
  af-interface default
   passive-interface
  af-interface Ethernet0/0
   no passive-interface
   authentication mode md5
   authentication key-chain EI-KC
  af-interface Ethernet0/1
   no passive-interface
  topology base
   variance 16
  network 10.0.1.1 0.0.0.0
  network 10.1.12.0 0.0.0.3
  network 10.1.13.0 0.0.0.3
```

### RT02（コア・RT04 集約 10.4.0.0/22・認証）
```
key chain EI-KC
 key 1
  key-string CCNPeigrp
!
router eigrp CCNP
 address-family ipv4 unicast autonomous-system 100
  eigrp router-id 10.0.2.2
  af-interface default
   passive-interface
  af-interface Ethernet0/0
   no passive-interface
   authentication mode md5
   authentication key-chain EI-KC
   summary-address 10.4.0.0 255.255.252.0
  af-interface Ethernet0/1
   no passive-interface
   summary-address 10.4.0.0 255.255.252.0
  af-interface Ethernet0/2
   no passive-interface
  network 10.0.2.2 0.0.0.0
  network 10.1.12.0 0.0.0.3
  network 10.1.23.0 0.0.0.3
  network 10.2.24.0 0.0.0.3
```

### RT03（コア・ABR的＝RT05 集約 10.5.0.0/22・管理 /32 を核へ出さない中継点フィルタ）
```
ip prefix-list BLOCK-MGMT seq 5 deny 10.99.5.1/32
ip prefix-list BLOCK-MGMT seq 10 permit 0.0.0.0/0 le 32
!
router eigrp CCNP
 address-family ipv4 unicast autonomous-system 100
  eigrp router-id 10.0.3.3
  af-interface default
   passive-interface
  af-interface Ethernet0/0
   no passive-interface
   summary-address 10.5.0.0 255.255.252.0
  af-interface Ethernet0/1
   no passive-interface
   summary-address 10.5.0.0 255.255.252.0
  af-interface Ethernet0/2
   no passive-interface
  topology base
   distribute-list prefix BLOCK-MGMT out Ethernet0/0
   distribute-list prefix BLOCK-MGMT out Ethernet0/1
  network 10.0.3.3 0.0.0.0
  network 10.1.13.0 0.0.0.3
  network 10.1.23.0 0.0.0.3
  network 10.3.35.0 0.0.0.3
```
※ global 形 `distribute-list prefix BLOCK-MGMT out`（IF 指定なし）でも可（RT05 面 E0/2 にも掛かるが
RT05 は発生源なので無害）。RT03 自身の RIB には 10.99.5.1 が残る＝RT03 は到達可。

### RT04（スポーク・スタブ）
```
router eigrp CCNP
 address-family ipv4 unicast autonomous-system 100
  eigrp router-id 10.0.4.4
  eigrp stub connected summary
  af-interface default
   passive-interface
  af-interface Ethernet0/0
   no passive-interface
  network 10.0.4.4 0.0.0.0
  network 10.4.0.1 0.0.0.0
  network 10.4.1.1 0.0.0.0
  network 10.4.2.1 0.0.0.0
  network 10.2.24.0 0.0.0.3
```

### RT05（スポーク・スタブ・管理 Loopback は普通に広告＝RT03 に見せる）
```
router eigrp CCNP
 address-family ipv4 unicast autonomous-system 100
  eigrp router-id 10.0.5.5
  eigrp stub connected summary
  af-interface default
   passive-interface
  af-interface Ethernet0/0
   no passive-interface
  network 10.0.5.5 0.0.0.0
  network 10.5.0.1 0.0.0.0
  network 10.5.1.1 0.0.0.0
  network 10.5.2.1 0.0.0.0
  network 10.99.5.1 0.0.0.0
  network 10.3.35.0 0.0.0.3
```
※ RT05 では 10.99.5.1 を**フィルタしない**（RT03 へ広告する）。抑止は中継点 RT03 が担う。

## 検証
```
show ip eigrp neighbors                 ! 隣接(RT01-RT02 は認証一致で UP)
show ip route eigrp                     ! RT01 で 10.5.0.0/22 が 2 next-hop
show ip eigrp neighbors detail          ! RT04/RT05 が "Stub Peer Advertising"
show ip route 10.5.0.0 255.255.252.0    ! 集約・構成要素抑制の確認
```

## 別解・補足
- フィルタ実装は `distribute-list prefix <名>` / 番号・名前付き ACL / route-map いずれでも可。
  RT03 の **コア面（E0/0・E0/1）out** に掛けるのが本質（global out でも可）。採点は
  「RT03 は 10.99.5.1 到達可・RT01/RT02 は不可」の結果で判定。
- ★**「`network` に載せない」逃げは不可**：RT03 に見せる要件のため、載せなければ RT03 到達チェック
  が落ちる。中継点フィルタでしか成立しない（本問の狙い）。
- summary-address は集約 Null0 ルートを生む（ループ防止の正常動作）。
- 認証を誤って全 IF に付けると他リンクの隣接が落ちる（要件 3 の罠）。

## 変種 "bfd"（-e variant=bfd）の追加解答
全ルータ間リンクの IF に BFD タイマを設定し、named mode の af-interface で連動させる。

```
! 例: RT01（リンクIFごと）
interface Ethernet0/0
 bfd interval 500 min_rx 500 multiplier 3
interface Ethernet0/1
 bfd interval 500 min_rx 500 multiplier 3
router eigrp CORP
 address-family ipv4 unicast autonomous-system 100
  af-interface Ethernet0/0
   bfd
  exit-af-interface
  af-interface Ethernet0/1
   bfd
  exit-af-interface
 exit-address-family
```

> af-interface default で `bfd` を入れると Loopback にも掛かるが実害なし（相手不在で
> セッションは張られない）。採点は各リンクのセッション Up＋EIGRP 登録＋乗数。
> 確認: `show bfd neighbors details`
