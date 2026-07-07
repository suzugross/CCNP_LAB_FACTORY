# 模範解答 : ENARSI-IPSEC-VTI-01 (sVTI + IPsec Profile, IKEv1)

> RT01=本社 / RT02=支店 / RT04=WANトランジット(変更禁止)。
> crypto map を使わず、**トンネルIFに IPsec を直載せするルーテッドVPN(sVTI)** を
> IPsec Profile で組む。これが現代の Cisco サイト間VPNの基本形。

## RT01 (本社/HQ)
```
crypto isakmp policy 10
 encryption aes 256
 hash sha256
 authentication pre-share
 group 14
!
crypto isakmp key Ss2026#WanHqB1 address 10.0.24.1
crypto isakmp keepalive 10 3 periodic
!
crypto ipsec transform-set TS-AES256 esp-aes 256 esp-sha256-hmac
 mode tunnel
!
crypto ipsec profile IPSEC-WAN
 set transform-set TS-AES256
 set pfs group14
!
interface Tunnel0
 description === S2S VPN to Branch (RT02) ===
 ip address 10.255.12.1 255.255.255.252
 ip mtu 1400
 ip tcp adjust-mss 1360
 tunnel source GigabitEthernet0/0
 tunnel destination 10.0.24.1
 tunnel mode ipsec ipv4
 tunnel protection ipsec profile IPSEC-WAN
!
interface Loopback10
 ip ospf network point-to-point
!
router ospf 1
 router-id 1.1.1.1
 network 10.255.12.0 0.0.0.3 area 0
 network 192.168.1.0 0.0.0.255 area 0
```

## RT02 (支店/Branch) — 鏡像
```
crypto isakmp policy 10
 encryption aes 256
 hash sha256
 authentication pre-share
 group 14
!
crypto isakmp key Ss2026#WanHqB1 address 10.0.14.1
crypto isakmp keepalive 10 3 periodic
!
crypto ipsec transform-set TS-AES256 esp-aes 256 esp-sha256-hmac
 mode tunnel
!
crypto ipsec profile IPSEC-WAN
 set transform-set TS-AES256
 set pfs group14
!
interface Tunnel0
 description === S2S VPN to HQ (RT01) ===
 ip address 10.255.12.2 255.255.255.252
 ip mtu 1400
 ip tcp adjust-mss 1360
 tunnel source GigabitEthernet0/0
 tunnel destination 10.0.14.1
 tunnel mode ipsec ipv4
 tunnel protection ipsec profile IPSEC-WAN
!
interface Loopback10
 ip ospf network point-to-point
!
router ospf 1
 router-id 2.2.2.2
 network 10.255.12.0 0.0.0.3 area 0
 network 192.168.2.0 0.0.0.255 area 0
```

## 確認
```
show crypto session                  ! UP-ACTIVE
show crypto isakmp sa detail         ! aes-256 / sha256 / psk / DH14, ACTIVE
show crypto ipsec sa                 ! transform=esp-256-aes esp-sha256-hmac, encaps/decaps 加算
show ip route ospf                   ! O 192.168.2.0/24 via 10.255.12.2, Tunnel0
ping 192.168.2.1 source Loopback10   ! LAN間疎通
```

### ポイント（設計判断・落とし穴）
- **VTI vs crypto map**: crypto map は「物理IFに貼る + 対象トラフィックをACLで列挙」する
  レガシー方式。sVTI は**トンネルIFへのルーティングがそのまま暗号化対象の選択**になるため、
  ACLメンテ不要・動的ルーティングと相性が良い。現行 Cisco 推奨はプロファイル方式。
- **`tunnel mode ipsec ipv4`** で GRE ヘッダなしの純粋な IPsec トンネル(VTI)になる。
  既定の `gre ip` のまま `tunnel protection` を貼ると「GRE over IPsec」になり別物
  （+4バイトGREヘッダ、採点は tunnel mode を見る）。
- **Loopback の OSPF 広告は既定で /32(ホスト)扱い**。仕様書の「/24 のまま学習」を満たすには
  `ip ospf network point-to-point` を Loopback10 に入れる（本問のひねり）。
- **DPD (`crypto isakmp keepalive 10 3 periodic`)**: IPsec で保護されたトンネルでは
  GRE keepalive は使えない。ピア死活は DPD＋ルーティングプロトコルの hello で監視するのが実務。
  `periodic` は常時送信（既定の on-demand はトラフィック要求時のみ）。
- **SAライフタイムは既定値 (IKE 86400秒 / IPsec 3600秒) が実務標準**。変えるなら短縮方向。
  PFS(group14) はリキー時にも新しい DH 交換を強制し、鍵漏洩の波及を防ぐ。
- **MTU/MSS**: IPsec tunnel mode のオーバーヘッド(ESP+新IPヘッダで50〜73バイト)を見込み
  `ip mtu 1400` + `ip tcp adjust-mss 1360`(= ip mtu − 40) が定番。カプセル化後の
  フラグメント・PMTUD ブラックホールを防ぐ。
- **PSK は `address <対向>` で限定**して定義（`0.0.0.0` の全ピア共通鍵は事故のもと）。
- 発展: 本問の IPsec Profile は DMVPN の mGRE トンネルにも `tunnel protection` で
  そのまま流用できる（その場合 transform は `mode transport` が定石）。
