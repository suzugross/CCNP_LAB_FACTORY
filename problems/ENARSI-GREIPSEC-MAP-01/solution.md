# 模範解答 : ENARSI-GREIPSEC-MAP-01 (GRE over IPsec + crypto map, IKEv1, ハブ+2支店)

> RT01=本社ハブ / RT02=支店1 / RT03=支店2 / RT04=WANトランジット(変更禁止)。
> sVTI/tunnel protection を使わず、**GRE トンネル＋WAN物理IFへの crypto map** で
> 暗号化するレガシー方式。既存網・マルチベンダ相互接続で今も現役の構成。

## RT01 (本社/HQ ハブ)
```
crypto isakmp policy 10
 encryption aes 256
 hash sha256
 authentication pre-share
 group 14
!
crypto isakmp key Cm2026#HqBr1 address 10.0.24.1
crypto isakmp key Cm2026#HqBr2 address 10.0.34.1
crypto isakmp keepalive 10 3
!
crypto ipsec transform-set TS-GRE esp-aes 256 esp-sha256-hmac
 mode transport
!
ip access-list extended ACL-GRE-BR1
 permit gre host 10.0.14.1 host 10.0.24.1
ip access-list extended ACL-GRE-BR2
 permit gre host 10.0.14.1 host 10.0.34.1
!
crypto map CM-WAN 10 ipsec-isakmp
 set peer 10.0.24.1
 set transform-set TS-GRE
 set pfs group14
 match address ACL-GRE-BR1
crypto map CM-WAN 20 ipsec-isakmp
 set peer 10.0.34.1
 set transform-set TS-GRE
 set pfs group14
 match address ACL-GRE-BR2
!
interface GigabitEthernet0/0
 crypto map CM-WAN
!
interface Tunnel1
 description === GRE to Branch1 (RT02) ===
 ip address 10.255.12.1 255.255.255.252
 ip mtu 1400
 ip tcp adjust-mss 1360
 tunnel source GigabitEthernet0/0
 tunnel destination 10.0.24.1
!
interface Tunnel2
 description === GRE to Branch2 (RT03) ===
 ip address 10.255.13.1 255.255.255.252
 ip mtu 1400
 ip tcp adjust-mss 1360
 tunnel source GigabitEthernet0/0
 tunnel destination 10.0.34.1
!
interface Loopback10
 ip ospf network point-to-point
!
router ospf 1
 router-id 1.1.1.1
 network 10.255.12.0 0.0.0.3 area 0
 network 10.255.13.0 0.0.0.3 area 0
 network 192.168.1.0 0.0.0.255 area 0
```

## RT02 (支店1/Branch1)
```
crypto isakmp policy 10
 encryption aes 256
 hash sha256
 authentication pre-share
 group 14
!
crypto isakmp key Cm2026#HqBr1 address 10.0.14.1
crypto isakmp keepalive 10 3
!
crypto ipsec transform-set TS-GRE esp-aes 256 esp-sha256-hmac
 mode transport
!
ip access-list extended ACL-GRE-HQ
 permit gre host 10.0.24.1 host 10.0.14.1
!
crypto map CM-WAN 10 ipsec-isakmp
 set peer 10.0.14.1
 set transform-set TS-GRE
 set pfs group14
 match address ACL-GRE-HQ
!
interface GigabitEthernet0/0
 crypto map CM-WAN
!
interface Tunnel1
 description === GRE to HQ (RT01) ===
 ip address 10.255.12.2 255.255.255.252
 ip mtu 1400
 ip tcp adjust-mss 1360
 tunnel source GigabitEthernet0/0
 tunnel destination 10.0.14.1
!
interface Loopback10
 ip ospf network point-to-point
!
router ospf 1
 router-id 2.2.2.2
 network 10.255.12.0 0.0.0.3 area 0
 network 192.168.2.0 0.0.0.255 area 0
```

## RT03 (支店2/Branch2) — RT02 の鏡像
```
crypto isakmp policy 10
 encryption aes 256
 hash sha256
 authentication pre-share
 group 14
!
crypto isakmp key Cm2026#HqBr2 address 10.0.14.1
crypto isakmp keepalive 10 3
!
crypto ipsec transform-set TS-GRE esp-aes 256 esp-sha256-hmac
 mode transport
!
ip access-list extended ACL-GRE-HQ
 permit gre host 10.0.34.1 host 10.0.14.1
!
crypto map CM-WAN 10 ipsec-isakmp
 set peer 10.0.14.1
 set transform-set TS-GRE
 set pfs group14
 match address ACL-GRE-HQ
!
interface GigabitEthernet0/0
 crypto map CM-WAN
!
interface Tunnel1
 description === GRE to HQ (RT01) ===
 ip address 10.255.13.2 255.255.255.252
 ip mtu 1400
 ip tcp adjust-mss 1360
 tunnel source GigabitEthernet0/0
 tunnel destination 10.0.14.1
!
interface Loopback10
 ip ospf network point-to-point
!
router ospf 1
 router-id 3.3.3.3
 network 10.255.13.0 0.0.0.3 area 0
 network 192.168.3.0 0.0.0.255 area 0
```

## 確認
```
show crypto session                  ! UP-ACTIVE (RT01 は 2 ピア)
show crypto isakmp sa detail         ! aes / sha256 / psk / 14, ACTIVE
show crypto ipsec sa                 ! transform=esp-256-aes esp-sha256-hmac,
                                     ! in use settings ={Transport, }, encaps/decaps 加算
show crypto map                      ! 1 map 2 エントリ(seq 10/20), IF=Gi0/0
show ip route ospf                   ! 支店で O 192.168.x.0/24 via 10.255.1x.1, Tunnel1
ping 192.168.3.1 source Loopback10   ! 支店間 (RT02→RT03, ハブ経由)
```

### ポイント（設計判断・落とし穴）
- **crypto map 方式の構造**: 「何を暗号化するか」を **ACL(match address)** で列挙し、
  **物理IF**に map を貼る。sVTI(=ルーティングが暗号化対象を決める)との最大の違い。
  ACL は対向と**鏡像**でなければならず、`permit gre host <自WAN> host <対向WAN>` の
  1 行が GRE over IPsec の定石（`permit ip any any` は underlay 通信まで巻き込む事故のもと）。
- **1 インタフェース = 1 crypto map**: 物理IFに貼れる map は 1 つだけ。複数ピアは
  **同一 map 名の別 seq エントリ**(10/20…)で収容する（本問のハブ側が該当）。
  2 つめの map 名を作って上書き適用してしまうのが典型ミス。
- **mode transport が使える理由**: GRE のトンネル終端(=WAN物理アドレス)と IPsec の
  暗号終端が**同一アドレスペア**だから。transport は元 IP ヘッダを再利用するため
  tunnel モード比で 20 バイト節約。GRE over IPsec / DMVPN では transport が定石。
  片側だけ transport にした場合はネゴでどちらかに寄る（採点は
  `show crypto ipsec sa` の `in use settings ={Transport,` で実効モードを見る）。
- **GRE keepalive は IPsec 併用不可**: keepalive 応答パケットは「対向が組み立てた
  自分宛 GRE」を折り返す仕組みで、crypto map の ACL/SA と噛み合わず戻ってこない
  → line protocol が down し**トンネルが永久フラップ**する。死活監視は
  **DPD (`crypto isakmp keepalive 10 3`＝on-demand)** ＋ルーティングプロトコルの
  hello で行う（本問の仕様書はそれを指定している）。`periodic` を付けると常時送信。
- **再帰ルーティングに注意**: OSPF で underlay(10.0.x.x) や tunnel destination を
  広告すると「トンネルの出口をトンネル経由で学習」する再帰が起き
  `%TUN-5-RECURDOWN` でトンネルが落ちる。仕様書の「広告対象=トンネル区間と LAN のみ」
  はこの防止。underlay への到達は既設デフォルトルートに任せる。
- **Loopback の OSPF 広告は既定で /32(ホスト)扱い**。「/24 のまま学習」させるには
  `ip ospf network point-to-point` を Loopback10 に入れる（VTI-01 と同じひねり・復習）。
- **MTU/MSS**: GRE(24 バイト)＋IPsec transport(ESP+パディングで約30〜40 バイト)を
  見込み `ip mtu 1400`＋`ip tcp adjust-mss 1360`(= ip mtu − 40)。カプセル化後の
  フラグメント・PMTUD ブラックホール防止の定番値。
- **PSK はピア毎に別鍵**＋`address <対向>` で限定定義（全ピア共通鍵 `0.0.0.0` は
  1 拠点の漏洩が全網に波及する）。IKEv1 メインモードの PSK はアドレスで鍵を
  引くため、鍵と address の対応ミスは MM_KEY_EXCH で止まる。
- **現代の位置づけ**: 新規設計なら sVTI/IPsec Profile(VTI-01)・IKEv2(IKEV2-01) が
  推奨。crypto map は「レガシー相互接続・買収統合・古い装置」で読める/書けることが
  ENARSI の要求水準。
