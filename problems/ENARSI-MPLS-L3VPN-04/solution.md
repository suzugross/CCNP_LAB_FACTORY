# 模範解答 : ENARSI-MPLS-L3VPN-04 (PE-CE eBGP 化 + as-override + 受信広告制御)

> 変更対象は PE (RT01/RT03) のみ。コア (OSPF 1 / LDP / VPNv4 セッション / VRF 定義) は
> 完成済みなので触らない。作業は 3 チケット =
> ① VRF 別 AF で CE と eBGP（**再配布ゼロ** — 02 との対比） ② CUST_B に as-override
> ③ prefix-list 参照 route-map を **neighbor in** に適用。

## RT01 (PE1)
```
! --- チケット3 の部品: 受け入れてよいのは 172.16.0.0/16 の LAN だけ ---
ip prefix-list PL-CUST-LAN seq 5 permit 172.16.0.0/16 le 24
!
route-map RM-CE-IN permit 10
 match ip address prefix-list PL-CUST-LAN
!
! --- チケット1: VRF 別 AF で CE と eBGP (redistribute は書かない) ---
! --- チケット2: CUST_B は同一 AS 65200 → as-override が SP 側の唯一解 ---
router bgp 65000
 address-family ipv4 vrf CUST_A
  neighbor 192.168.1.1 remote-as 65101
  neighbor 192.168.1.1 activate
  neighbor 192.168.1.1 route-map RM-CE-IN in
 exit-address-family
 address-family ipv4 vrf CUST_B
  neighbor 192.168.11.1 remote-as 65200
  neighbor 192.168.11.1 activate
  neighbor 192.168.11.1 as-override
  neighbor 192.168.11.1 route-map RM-CE-IN in
 exit-address-family
```

## RT03 (PE2)
```
ip prefix-list PL-CUST-LAN seq 5 permit 172.16.0.0/16 le 24
!
route-map RM-CE-IN permit 10
 match ip address prefix-list PL-CUST-LAN
!
router bgp 65000
 address-family ipv4 vrf CUST_A
  neighbor 192.168.2.1 remote-as 65102
  neighbor 192.168.2.1 activate
  neighbor 192.168.2.1 route-map RM-CE-IN in
 exit-address-family
 address-family ipv4 vrf CUST_B
  neighbor 192.168.12.1 remote-as 65200
  neighbor 192.168.12.1 activate
  neighbor 192.168.12.1 as-override
  neighbor 192.168.12.1 route-map RM-CE-IN in
 exit-address-family
```

## 解説 — この問題の 3 つの芯

### 1. eBGP 化で再配布が消える（02 との対比）

02 (PE-CE OSPF) では OSPF⇄BGP の**相互再配布**が要だった。eBGP 化すると
CE の経路は PE の vrf AF に**BGP 経路として直接**入り、そのまま VPNv4 化される
（逆方向も AF 内の広告で完結）。`redistribute` が 1 行も要らないのが正解であり、
本問は制約で再配布を明示的に禁止して迂回解を封じている。

### 2. 同一 AS 顧客と as-override（本問最大の罠）

CUST_B は両サイト AS 65200。neighbor/activate を正しく組んでも、
**対向サイトの経路だけが CE に現れない**:

- PE の `show bgp vpnv4 unicast vrf CUST_B neighbors 192.168.11.1 advertised-routes`
  には経路が**在る**（PE は広告している）
- しかし CE の AS_PATH ループ検知が「自 AS 65200 を含むパス」を破棄する。
  CE 側デバッグ指紋: `debug ip bgp updates in` に
  `DENIED due to: AS-PATH contains our own AS`

**「PE は広告している / CE のテーブルに無い」の突き合わせ**で「CE が捨てている」に
到達するのが切り分けの芯。対策は 2 つあるが:
- `allowas-in`（CE 側設定）→ **CE 変更禁止の制約で不可**
- `as-override`（PE 側・広告時に CE の AS を自 AS に置換）→ **これが唯一解**

as-override 後、CE が受信する AS_PATH は `65000 65000`（2つ目の 65000 が
置換された旧 65200）。採点はこの指紋を拘束している。

### 3. 広告制御の適用点が redistribute → neighbor in へ移る

02 では OSPF→BGP の redistribute に route-map を噛ませた。eBGP 化後は
**neighbor 単位の in フィルタ**が適用点になる（SP エッジの実務でも受信側で
落とすのが基本 = 顧客の設定ミスから網を守る）。受信段階で破棄するため、
**収容 PE の VRF にすら 10.99 が載らない**（02 では収容 PE までは在った — 対比）。
in フィルタを広げ過ぎる（172.16 まで落とす）と E2E が全滅して自壊する。

## よくある誤答

| 誤答 | 症状 / 採点での落ち方 |
|---|---|
| as-override 忘れ | CUST_A は通るのに CUST_B だけ不通（E2/A1/A2/C2 で -23点） |
| route-map を out に適用 | 10.99 が収容 PE の VRF に残る（F1/F2 で -8点） |
| redistribute で OSPF 経由の迂回構成 | X3/X4 で減点＋そもそも CE は OSPF を話していない |
| remote-as を AS 65000 側と取り違え | セッション不成立（B チェックと以降全滅） |
| activate 忘れ | v4 セッションは Established でも AF 経路ゼロ（V/R/C で全滅） |
