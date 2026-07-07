# 模範解答 : DMVPN-PHASE3-01 (Phase 3 / NHRP redirect + shortcut, 暗号なし)

> RT01=ハブ(NHS) / RT02=スポーク1 / RT03=スポーク2 / RT04=WANトランジット(変更禁止)。
> トポロジ・アドレスは DMVPN-POC-01(Phase 2)と同一。違いは制御方式のみ。

## RT01 (Hub)
```
interface Tunnel0
 ip address 10.255.0.1 255.255.255.0
 no ip redirects
 ip nhrp authentication DMVPNKEY
 ip nhrp network-id 1
 ip nhrp map multicast dynamic
 ip nhrp redirect
 no ip split-horizon eigrp 100
 tunnel source GigabitEthernet0/0
 tunnel mode gre multipoint
!
router eigrp 100
 network 1.1.1.1 0.0.0.0
 network 10.255.0.0 0.0.0.255
 no auto-summary
!
```
> ★Phase 2 と違い **`no ip next-hop-self eigrp 100` は入れない**（ハブは next-hop を
> 自分に保つ）。代わりに **`ip nhrp redirect`** でスポークに直接解決を促す。
> `no ip split-horizon eigrp 100` は対向スポーク経路をスポークへ広告するため必要。

## RT02 (Spoke1) / RT03 (Spoke2)
```
interface Tunnel0
 ip address 10.255.0.2 255.255.255.0          ! RT03 は 10.255.0.3
 no ip redirects
 ip nhrp authentication DMVPNKEY
 ip nhrp network-id 1
 ip nhrp nhs 10.255.0.1
 ip nhrp map 10.255.0.1 10.0.14.1
 ip nhrp map multicast 10.0.14.1
 ip nhrp shortcut
 tunnel source GigabitEthernet0/0
 tunnel mode gre multipoint
!
router eigrp 100
 network 2.2.2.2 0.0.0.0                       ! RT03 は 3.3.3.3
 network 10.255.0.0 0.0.0.255
 no auto-summary
!
```
> ★スポークに **`ip nhrp shortcut`** を入れる。これがハブの redirect を受けて
> 直接トンネルを張る Phase 3 の要。

## 確認
```
show dmvpn                                    ! 初期: ハブのみ。ping 後: 対向スポークが動的(D)UP
show ip route 3.3.3.3                          ! 定常: D 3.3.3.3 via 10.255.0.1(ハブ)
ping 3.3.3.3 source Loopback0 repeat 5         ! RT02->RT03 直結を誘発
show ip nhrp                                   ! shortcut で解決された 3.3.3.3 -> 10.255.0.3 / NBMA
show dmvpn                                     ! RT02 にスポーク2への動的エントリ UP
```

### ポイント（Phase 2 との違い・落とし穴）
- **Phase 2 vs Phase 3 の制御方式**:
  - **Phase 2** = ハブ `no ip next-hop-self`。スポークは対向スポーク経路を
    「next-hop = 対向スポーク」で学習し、その next-hop を解決して直結する。
    経路制御で直結を成立させる。
  - **Phase 3** = ハブ `ip nhrp redirect` + スポーク `ip nhrp shortcut`。
    スポークの経路は **next-hop = ハブのまま**（経路は常にハブ向きに見える）。
    支店間トラフィックが流れると、ハブが「直接やり取りせよ」と **NHRP redirect** を返し、
    スポークが **shortcut** で対向 NBMA を解決して直接トンネルを張る（オンデマンド）。
    → 採点でも「3.3.3.3 の next-hop はハブ(10.255.0.1)」かつ「ping 後に
       `show dmvpn` へ対向スポークの動的エントリが UP」で Phase 3 を判定する。
- **Phase 3 の利点**: ハブで経路を**集約**してもスポーク間直結が効く（経路ごとに
  next-hop を保つ必要がない）。大規模 DMVPN で経路表を小さく保てる。本問は集約まで
  要求しないが、next-hop をハブに保ったまま直結できるのがその基盤。
- **`no ip split-horizon eigrp 100` はハブに必要**: これが無いと、そもそも対向スポークの
  プレフィックスがスポークへ伝わらず、トリガとなるトラフィックの宛先経路が無い。
- **`ip nhrp redirect`(ハブ) と `ip nhrp shortcut`(スポーク) はペア**: 片方だけでは
  オンデマンド直結が成立しない。redirect=誘導する側、shortcut=従って直結する側。
- **再帰ルーティング回避**: tunnel destination(NBMA) は underlay の default route で解決。
  EIGRP は overlay と Lo0 のみ。

> 採点: DMVPN セッション(両スポークUP/hubUP)、Phase3 署名(対向スポーク経路の
> next-hop=ハブ)、支店間 ping、ping 誘発後の `show dmvpn` 動的スポークエントリ UP で判定。
> RT04 は採点対象外。
