# 模範解答 : ENARSI-MPLS-L3VPN-01 (MPLS L3VPN 基礎構築・マルチカスタマー)

> RT01=PE1 / RT02=P / RT03=PE2（構成対象）。RT04〜RT07=CE（変更不可）。
> 鉄則は **下の層から積み、各層で確認してから次へ**。トラブル時も同じ順で下から切り分ける。
> L1 IGP → L2 LDP → L3 MP-BGP(VPNv4) → L4 VRF → L5 PE-CE + 再配布。

## RT01 (PE1)
```
! --- L1: コア IGP。コアリンクと Lo0 のみ。CE 向けは絶対に入れない ---
router ospf 1
 router-id 1.1.1.1
 network 1.1.1.1 0.0.0.0 area 0
 network 10.1.12.0 0.0.0.3 area 0
!
! --- L2: LDP。ルータ ID を Lo0 に固定してからコア IF で有効化 ---
mpls ldp router-id Loopback0 force
interface Ethernet0/0
 mpls ip
!
! --- L4: VRF。RD=一意化の札 / RT=所属の合言葉 (両 PE で一致させる) ---
vrf definition CUST_A
 rd 65000:100
 address-family ipv4
  route-target export 65000:100
  route-target import 65000:100
 exit-address-family
vrf definition CUST_B
 rd 65000:200
 address-family ipv4
  route-target export 65000:200
  route-target import 65000:200
 exit-address-family
!
! ★vrf forwarding を投入した瞬間、既存のグローバル IP は黙って破棄される
!   → VRF 収容後に必ず IP を入れ直す (show ip int brief で確認)
interface Ethernet0/1
 vrf forwarding CUST_A
 ip address 192.168.1.2 255.255.255.252
interface Ethernet0/2
 vrf forwarding CUST_B
 ip address 192.168.11.2 255.255.255.252
!
! --- L3+L5: MP-BGP。Lo0 間 iBGP + VPNv4 AF のみ。AF 方式 (ipv4 既定有効化は切る) ---
router bgp 65000
 bgp router-id 1.1.1.1
 no bgp default ipv4-unicast
 neighbor 3.3.3.3 remote-as 65000
 neighbor 3.3.3.3 update-source Loopback0
 address-family vpnv4
  neighbor 3.3.3.3 activate
 exit-address-family
 address-family ipv4 vrf CUST_A
  redistribute connected
  redistribute static
 exit-address-family
 address-family ipv4 vrf CUST_B
  redistribute connected
  redistribute static
 exit-address-family
!
! --- L5: PE-CE スタティック (VRF の台帳に書く) ---
ip route vrf CUST_A 172.16.1.0 255.255.255.0 192.168.1.1
ip route vrf CUST_B 172.16.1.0 255.255.255.0 192.168.11.1
```

## RT02 (P)
```
! P は IGP + LDP だけ。BGP も VRF も持たない (= 顧客経路を一切知らずにラベルで運ぶ)
router ospf 1
 router-id 2.2.2.2
 network 2.2.2.2 0.0.0.0 area 0
 network 10.1.12.0 0.0.0.3 area 0
 network 10.1.23.0 0.0.0.3 area 0
!
mpls ldp router-id Loopback0 force
interface Ethernet0/0
 mpls ip
interface Ethernet0/1
 mpls ip
```

## RT03 (PE2)
```
router ospf 1
 router-id 3.3.3.3
 network 3.3.3.3 0.0.0.0 area 0
 network 10.1.23.0 0.0.0.3 area 0
!
mpls ldp router-id Loopback0 force
interface Ethernet0/0
 mpls ip
!
vrf definition CUST_A
 rd 65000:100
 address-family ipv4
  route-target export 65000:100
  route-target import 65000:100
 exit-address-family
vrf definition CUST_B
 rd 65000:200
 address-family ipv4
  route-target export 65000:200
  route-target import 65000:200
 exit-address-family
!
interface Ethernet0/1
 vrf forwarding CUST_A
 ip address 192.168.2.2 255.255.255.252
interface Ethernet0/2
 vrf forwarding CUST_B
 ip address 192.168.12.2 255.255.255.252
!
router bgp 65000
 bgp router-id 3.3.3.3
 no bgp default ipv4-unicast
 neighbor 1.1.1.1 remote-as 65000
 neighbor 1.1.1.1 update-source Loopback0
 address-family vpnv4
  neighbor 1.1.1.1 activate
 exit-address-family
 address-family ipv4 vrf CUST_A
  redistribute connected
  redistribute static
 exit-address-family
 address-family ipv4 vrf CUST_B
  redistribute connected
  redistribute static
 exit-address-family
!
ip route vrf CUST_A 172.16.2.0 255.255.255.0 192.168.2.1
ip route vrf CUST_B 172.16.2.0 255.255.255.0 192.168.12.1
```

## 確認コマンド（層ごとに。詰まったら下から）
```
show ip ospf neighbor                          ! L1: FULL か
ping 3.3.3.3 source 1.1.1.1                    ! L1: Lo0 同士の疎通 = 以後全部の土台
show mpls ldp neighbor                         ! L2: State Oper / Peer ID が Lo0 か
show mpls forwarding-table                     ! L2: 対向 PE /32 にラベルが並ぶか
traceroute 3.3.3.3 source 1.1.1.1 numeric      ! L2: [MPLS: Label ...] が見えるか
show bgp vpnv4 unicast all summary             ! L3: Established か (ip bgp summary には出ない)
show vrf                                       ! L4: VRF と収容 IF (IP が消えていないか)
ping vrf CUST_A 192.168.1.1                    ! L4: VRF 指定で CE へ届くか
show bgp vpnv4 unicast all                     ! L5: 同一プレフィックスが RD 違いで 2 本並ぶ
show bgp vpnv4 unicast rd 65000:100 172.16.2.0 ! L5: RD 単位で経路確認
show ip route vrf CUST_A                       ! L5: B(BGP) で対向サイトが載るか
```

## 解説

### なぜマルチカスタマーで RD / RT が「実感」できるか
CUST_A と CUST_B は**同じ 172.16.1.0/24, 172.16.2.0/24** を使っている。
`show bgp vpnv4 unicast all` を見ると同一プレフィックスが
`Route Distinguisher: 65000:100` と `65000:200` の下に **2 本並ぶ**。
これが RD の仕事（重複経路を MP-BGP 内で別物として共存させる）の実物。
一方どちらの VRF 台帳に入るかを決めるのは RD ではなく **RT**。
export された `65000:100` を import する VRF（=対向 PE の CUST_A）だけが取り込む。

- **RD** = 一意化（制御プレーン）。所属判断には関与しない。
- **RT** = 所属（制御プレーン）。extended community として経路に付いて運ばれる
  （`address-family vpnv4` の activate で send-community extended が自動有効になる）。
- **VPN ラベル** = 転送（データプレーン）。受信側 PE が割り当て、MP-BGP 更新に同梱。
  届いたパケットをどの VRF 台帳で引くかを教える内側の札。

### 1 個の ping に起きること（完成形の再確認）
CE1 が素の IP を送出 → PE1 が VRF 台帳を引き、**外側ラベル（LDP 由来・対向 PE 行き）
＋ VPN ラベル（MP-BGP 由来・台帳識別）の 2 枚**を積む → P はラベルだけ見てスイッチ
（顧客経路を知らない）→ 最終手前で外側ラベルが外れ（PHP）→ PE2 が VPN ラベルで
CUST_A/B を判別し、素の IP を CE2 へ。

### ハマりどころ（今回の採点で落ちやすい所）
1. **`vrf forwarding` を入れると既存 IP が黙って消える**。初期状態で CE 向け IF に
   付いていた IP は VRF 収容の瞬間に破棄されるため、入れ直さないと
   `ping vrf` チェック（8 点分）が全滅する。`show vrf` で IP を必ず確認。
2. **`update-source Loopback0` 忘れ**。iBGP の送信元が物理 IF になり
   3.3.3.3 とのセッションが上がらない。`ping 3.3.3.3 source 1.1.1.1` が通るのに
   BGP が Idle/Active ならこれ。
3. **VPNv4 は `show bgp vpnv4 unicast all summary` で見る**。
   `show ip bgp summary`（ipv4）に出ないのは正常（`no bgp default ipv4-unicast`）。
4. **再配布忘れ**。セッションが Established でも PfxRcd が 0 のまま。
   VRF 台帳の経路は `address-family ipv4 vrf` の redistribute で初めて VPNv4 化される。
5. **CE 向け IF を OSPF/LDP に入れる**。顧客経路がグローバル台帳・コアに漏れる。
   本問は network 文の範囲指定（192.168.0.0 を含めない）で自然に回避できるが、
   `network 0.0.0.0 255.255.255.255 area 0` のような全許可を使うと事故る。

### 補足（実務向け）
- **MTU**: MPLS はラベル 1 枚 4 byte、L3VPN では 2 枚で **+8 byte**。CML の仮想リンクは
  オーバーサイズを通すため無症状だが、実機・実回線ではコア IF の `mpls mtu` /
  経路上の MTU 設計（baby giant 許容）を必ず確認する。エンドホストの TCP には
  `ip tcp adjust-mss` での防御も有効（GRE/DMVPN 問と同じ考え方）。
- **PHP**: `traceroute` の最終ホップ手前でラベル表示が消えるのは
  implicit-null（PHP）による正常動作。
- 本問の PE-CE はスタティック。実務では OSPF / eBGP が主流で、その場合は
  `address-family ipv4 vrf` 内で双方向再配布（または vrf 対応 BGP ネイバー）になる
  （→ 次段の応用問テーマ）。
