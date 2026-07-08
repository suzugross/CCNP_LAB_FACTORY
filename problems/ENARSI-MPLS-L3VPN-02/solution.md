# 模範解答 : ENARSI-MPLS-L3VPN-02 (PE-CE OSPF 化 + route-map 広告制御 + MSS 調整)

> 変更対象は PE (RT01/RT03) のみ。コア (OSPF 1 / LDP / VPNv4 セッション / VRF 定義) は
> 完成済みなので触らない。作業は 3 チケット =
> ① VRF 別 OSPF プロセス + 相互再配布 ② route-map で OSPF→VPNv4 を最小化 ③ MSS。

## RT01 (PE1)
```
! --- チケット2 の部品: 広告してよいのは 172.16.0.0/16 の LAN だけ ---
ip prefix-list PL-CUST-LAN seq 5 permit 172.16.0.0/16 le 24
!
route-map RM-OSPF2VPN permit 10
 match ip address prefix-list PL-CUST-LAN
!
! --- チケット1: VRF 別 OSPF プロセス (vrf キーワードを忘れるとグローバルに立つ) ---
router ospf 10 vrf CUST_A
 router-id 1.1.1.1
 redistribute bgp 65000 subnets
 network 192.168.1.2 0.0.0.0 area 0
!
router ospf 20 vrf CUST_B
 router-id 1.1.1.1
 redistribute bgp 65000 subnets
 network 192.168.11.2 0.0.0.0 area 0
!
! --- チケット1+2: OSPF→VPNv4 は route-map を噛ませて再配布 ---
router bgp 65000
 address-family ipv4 vrf CUST_A
  redistribute ospf 10 route-map RM-OSPF2VPN
 exit-address-family
 address-family ipv4 vrf CUST_B
  redistribute ospf 20 route-map RM-OSPF2VPN
 exit-address-family
!
! --- チケット3: MSS 調整 (CE 向け IF) ---
interface Ethernet0/1
 ip tcp adjust-mss 1452
interface Ethernet0/2
 ip tcp adjust-mss 1452
```

## RT03 (PE2)
```
ip prefix-list PL-CUST-LAN seq 5 permit 172.16.0.0/16 le 24
!
route-map RM-OSPF2VPN permit 10
 match ip address prefix-list PL-CUST-LAN
!
router ospf 10 vrf CUST_A
 router-id 3.3.3.3
 redistribute bgp 65000 subnets
 network 192.168.2.2 0.0.0.0 area 0
!
router ospf 20 vrf CUST_B
 router-id 3.3.3.3
 redistribute bgp 65000 subnets
 network 192.168.12.2 0.0.0.0 area 0
!
router bgp 65000
 address-family ipv4 vrf CUST_A
  redistribute ospf 10 route-map RM-OSPF2VPN
 exit-address-family
 address-family ipv4 vrf CUST_B
  redistribute ospf 20 route-map RM-OSPF2VPN
 exit-address-family
!
interface Ethernet0/1
 ip tcp adjust-mss 1452
interface Ethernet0/2
 ip tcp adjust-mss 1452
```

## 確認コマンド
```
show ip ospf neighbor                            ! CE 4台と FULL (VRF プロセスも一覧に出る)
show ip route vrf CUST_A                         ! O 172.16.1.0/24, 10.99.4.1/32 (CE広告) + B 172.16.2.0/24
show bgp vpnv4 unicast all                       ! 172.16.x.0/24 だけが載る (10.99 が居ないこと)
show bgp vpnv4 unicast rd 65000:100 172.16.2.0   ! RD 単位の確認
show ip route vrf CUST_A 10.99.5.1 255.255.255.255  ! 対向の管理 /32 が "not in table" なら制御成功
show run interface Ethernet0/1                   ! ip tcp adjust-mss 1452
(CE 側) show ip route 172.16.2.0                 ! Known via "ospf 1" = 再配布が CE まで届いた
```

## 解説

### 1. PE-CE OSPF — VRF 別プロセスと「再配布の輪」
PE の OSPF は **`router ospf 10 vrf CUST_A`** のように VRF 指定で立てる。顧客ごとに
プロセスを分けるのは、経路テーブルも隣接も顧客ごとに独立させるため
（プロセス番号は同一ルータ内で一意。router-id は別プロセスなら同値でよい）。

経路の流れは「**OSPF → (redistribute) → VPNv4 → 対向 PE → (redistribute) → OSPF**」の
リレーになる。両方向の再配布が要る:
- `address-family ipv4 vrf` 内の `redistribute ospf 10` … CE から聞いた経路を VPNv4 化
- `router ospf 10 vrf` 内の `redistribute bgp 65000 subnets` … VPNv4 経路を CE へ広告。
  **`subnets` を忘れるとクラスフル境界の経路しか再配布されず**、/24 が CE に届かない。

なお両 PE のプロセス番号を揃えると **OSPF ドメイン ID が一致**し、対向サイトの経路は
CE 上で `O E2`（外部）でなく **`O IA`（エリア間）** として現れる。MP-BGP が OSPF の
属性を拡張コミュニティで運び、対向 PE が「スーパーバックボーンの続き」として
LSA を作り直すため（ENARSI 頻出ポイント）。

### 2. route-map による「必要最低限の広告」
再配布は**境界での経路ポリシー適用点**でもある。何も絞らないと CE が OSPF に載せた
もの全部（機器管理 10.99.x.x/32 など）が VPN 全体へ流れる。本問は
`prefix-list 172.16.0.0/16 le 24` + `route-map` を **OSPF→BGP 再配布に一方向**噛ませ、
「LAN だけが VPN をまたぐ」状態にした。
- 10.99.x.x は**収容 PE の VRF RIB には居る**（CE との OSPF 内では正常に流通）が、
  **VPNv4 には乗らない** — 「どこまで広告するか」を境界で決めるのが SP 流。
- route-map を付けずに全部流しても疎通はする。**疎通する構成と、契約通りの構成は別物**
  というのがチケット 2 の主題。

### 3. MSS 調整 — なぜ 1452 か
MPLS L3VPN のコア通過中はラベル 2 枚で **+8 byte**。イーサネット MTU 1500 の網では
1500 を超えるフレームが作れず、DF ビット付きの大きな TCP セグメントが落ちる。
ICMP Unreachable が返らない・見ない環境では PMTUD が機能せず「大きい転送だけハングする」
典型症状になる。
```
1500 (リンクMTU) − 8 (MPLSラベル 4B×2) − 20 (IP) − 20 (TCP) = 1452
```
`ip tcp adjust-mss 1452` は **TCP 3-way ハンドシェイクの SYN を書き換える**ため、
PE の CE 向け IF（顧客トラフィックが必ず通る場所）に置く。TCP 以外（UDP 等）には
効かないので、実務では併せてコア MTU の拡大（baby giant / `mpls mtu`）を検討する。
DMVPN/GRE の `ip mtu 1400` + `ip tcp adjust-mss 1360` と同じ発想の MPLS 版。

### ハマりどころ
1. **`vrf` を付け忘れて `router ospf 10` を立てる** — グローバルに空プロセスができ、
   CE と隣接が張れない（CE 向け IF は VRF の中に居る）。
2. **`redistribute bgp 65000` の `subnets` 忘れ** — 隣接は FULL・VPNv4 にも経路が
   あるのに CE に /24 が届かない、という「途中まで動く」故障になる。
3. **route-map の向き** — 絞るのは OSPF→BGP（VPNv4 へ出る方向）。BGP→OSPF 側に
   付けると 10.99 は既に VPN を渡り終えており手遅れ。
4. **MSS は CE 向け IF に** — コア IF に付けても顧客 TCP の SYN はラベル転送で
   素通りするため効かない。
