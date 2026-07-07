# 模範解答 : ENARSI-IPSEC-IKEV2-01 (sVTI + IPsec Profile + IKEv2, ハブ+2支店)

> RT01=本社ハブ / RT02=支店1 / RT03=支店2 / RT04=WANトランジット(変更禁止)。
> IKEv2 のオブジェクト連鎖 **proposal → policy → keyring → ikev2 profile →
> ipsec profile → tunnel protection** を明示的に組む、現行 Cisco の標準形。

## RT01 (本社/HQ)
```
crypto ikev2 proposal PROP-NGE
 encryption aes-gcm-256
 prf sha384
 group 19
!
crypto ikev2 policy POL-NGE
 proposal PROP-NGE
!
crypto ikev2 keyring KR-WAN
 peer BRANCH1
  address 10.0.24.1
  pre-shared-key Ss2026#HqB1-v2
 peer BRANCH2
  address 10.0.34.1
  pre-shared-key Ss2026#HqB2-v2
!
crypto ikev2 profile IKEV2-WAN
 match identity remote address 10.0.24.1 255.255.255.255
 match identity remote address 10.0.34.1 255.255.255.255
 authentication remote pre-share
 authentication local pre-share
 keyring local KR-WAN
 dpd 10 3 on-demand
!
crypto ipsec transform-set TS-GCM256 esp-gcm 256
 mode tunnel
!
crypto ipsec profile IPSEC-WAN
 set transform-set TS-GCM256
 set pfs group19
 set ikev2-profile IKEV2-WAN
!
interface Tunnel1
 description === sVTI to Branch1 (RT02) ===
 ip address 10.255.12.1 255.255.255.252
 ip mtu 1400
 ip tcp adjust-mss 1360
 tunnel source GigabitEthernet0/0
 tunnel destination 10.0.24.1
 tunnel mode ipsec ipv4
 tunnel protection ipsec profile IPSEC-WAN
!
interface Tunnel2
 description === sVTI to Branch2 (RT03) ===
 ip address 10.255.13.1 255.255.255.252
 ip mtu 1400
 ip tcp adjust-mss 1360
 tunnel source GigabitEthernet0/0
 tunnel destination 10.0.34.1
 tunnel mode ipsec ipv4
 tunnel protection ipsec profile IPSEC-WAN
!
router eigrp 100
 eigrp router-id 1.1.1.1
 network 10.255.12.0 0.0.0.3
 network 10.255.13.0 0.0.0.3
 network 192.168.1.0 0.0.0.255
```

## RT02 (支店1)
```
crypto ikev2 proposal PROP-NGE
 encryption aes-gcm-256
 prf sha384
 group 19
!
crypto ikev2 policy POL-NGE
 proposal PROP-NGE
!
crypto ikev2 keyring KR-WAN
 peer HQ
  address 10.0.14.1
  pre-shared-key Ss2026#HqB1-v2
!
crypto ikev2 profile IKEV2-WAN
 match identity remote address 10.0.14.1 255.255.255.255
 authentication remote pre-share
 authentication local pre-share
 keyring local KR-WAN
 dpd 10 3 on-demand
!
crypto ipsec transform-set TS-GCM256 esp-gcm 256
 mode tunnel
!
crypto ipsec profile IPSEC-WAN
 set transform-set TS-GCM256
 set pfs group19
 set ikev2-profile IKEV2-WAN
!
interface Tunnel1
 description === sVTI to HQ (RT01) ===
 ip address 10.255.12.2 255.255.255.252
 ip mtu 1400
 ip tcp adjust-mss 1360
 tunnel source GigabitEthernet0/0
 tunnel destination 10.0.14.1
 tunnel mode ipsec ipv4
 tunnel protection ipsec profile IPSEC-WAN
!
router eigrp 100
 eigrp router-id 2.2.2.2
 network 10.255.12.0 0.0.0.3
 network 192.168.2.0 0.0.0.255
```

## RT03 (支店2) — RT02 の鏡像
差分のみ: PSK `Ss2026#HqB2-v2` / Tunnel1 `10.255.13.2` / EIGRP `network 10.255.13.0 0.0.0.3`
/ `network 192.168.3.0 0.0.0.255` / `eigrp router-id 3.3.3.3`。

## 確認
```
show crypto ikev2 sa                  ! 両ピア READY
show crypto ikev2 sa detailed         ! Encr: AES-GCM, keysize: 256 / PRF: SHA384 / DH Grp:19
show crypto session                   ! UP-ACTIVE
show crypto ipsec sa                  ! transform: esp-gcm 256, encaps/decaps 加算
show ip route eigrp                   ! 支店: D 192.168.3.0/24 via 10.255.12.1 (ハブ経由)
ping 192.168.3.1 source Loopback10    ! 支店間 (ハブ縦断)
```

### ポイント（設計判断・落とし穴）
- **IKEv2 のオブジェクト連鎖**が本問の骨格:
  `proposal`(アルゴリズム) → `policy`(proposalの適用) → `keyring`(ピア毎PSK) →
  `ikev2 profile`(誰と・どう認証・DPD) → `ipsec profile`(transform+PFS+`set ikev2-profile`)
  → `tunnel protection`。**`set ikev2-profile` を忘れると IKEv1 で試みて失敗**する
  （smart default の isakmp が無いので単に上がらない）。
- **AES-GCM は AEAD**（暗号化と整合性を一体で提供）。よって
  - transform-set は `esp-gcm 256` のみで**整合性アルゴリズムを併記しない**
    （仕様書の「追加指定なし」の意図）。
  - IKEv2 proposal も GCM 使用時は `integrity` 不要で、代わりに **`prf` の明示が必須**
    （非AEADなら integrity がPRFを兼ねる）。
- **スマートデフォルトに頼らない**: IOS には既定の ikev2 proposal/policy が存在するが、
  古いアルゴリズムを含むため実務では明示定義で固めるのが流儀（仕様書でも明示を要求）。
- **PSK はピア単位に別鍵**（keyring の peer ブロック）。全支店共通鍵は1拠点の侵害が
  全体に波及するため避ける。さらに堅くするなら `pre-shared-key local/remote` の非対称鍵。
- **DPD `on-demand`**: 送るべきトラフィックがあるのに応答が無いときだけ probe する省力型
  （Cisco 推奨の既定スタイル）。障害検知の即時性が欲しい場合は periodic だが、
  本構成ではルーティングプロトコル(EIGRP hello)が実質のキープアライブを担う。
- **sVTI 複数本と `shared` キーワード**: 同じ tunnel source でも **destination が異なる
  sVTI 同士なら `tunnel protection ... shared` は不要**。`shared` が要るのは同一
  source/destination の組を複数トンネルで共有するケース（GRE over IPsec の多重化等）。
- **MTU/MSS**: IPsec tunnel mode + GCM のオーバーヘッド(50〜73バイト)を見込み
  `ip mtu 1400` + `ip tcp adjust-mss 1360` が定番（PMTUD ブラックホール対策）。
- **ライフタイムは既定値** (IKEv2 SA 86400秒 / Child SA 3600秒) が実務標準。
  リキーは IKEv2 が自動処理し、PFS(group19) がリキー毎の鍵独立性を保証する。
- 発展 (DMVPN への流用): この IKEv2/IPsec profile 群は DMVPN の mGRE にほぼそのまま
  `tunnel protection` できる。差分は ①ハブの keyring/match identity をワイルドカード化
  (`address 0.0.0.0 0.0.0.0`) ②transform を `mode transport` に（mGRE では NBMA アドレス
  がヘッダに残るため transport で20バイト節約が定石）③mGRE トンネルは1本なので
  protection も1箇所、の3点のみ。
