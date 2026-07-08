# ENARSI-BGP-POLICY-01 模範解答

方針（**AF方式=社内標準**: セッション定義は `router bgp` 直下、activate/ポリシー/経路投入は
`address-family ipv4` 配下。初期状態は `no bgp default ipv4-unicast` 済み＝**activate 忘れは
「セッションUPなのに経路ゼロ」になる**のが AF 方式の代表的な落とし穴）。
community で「学習元」をタグ→ **LP で AS 全体の出口を制御**（通常 LP200=RT01/ISP-A、
例外 203.0.113.0/24 は LP300=RT02/ISP-B）→ inbound は **MED**（RT01=100 < RT02=200）。
weight は使わない（iBGP で伝搬せず要件3/4の「全ルータで」を満たせない）。

## RT03（iBGP と顧客プレフィックス投入）

```
router bgp 65010
 bgp log-neighbor-changes
 no bgp default ipv4-unicast
 neighbor 1.1.1.1 remote-as 65010
 neighbor 1.1.1.1 update-source Loopback0
 neighbor 2.2.2.2 remote-as 65010
 neighbor 2.2.2.2 update-source Loopback0
 address-family ipv4
  neighbor 1.1.1.1 activate
  neighbor 2.2.2.2 activate
  network 198.51.100.0 mask 255.255.255.128
  network 198.51.100.128 mask 255.255.255.128
 exit-address-family
```

## RT01（edge-A: タグ+LP200・受信フィルタ・MED100・集約）

```
ip prefix-list BAD-IN seq 5 permit 10.0.0.0/8 le 32
ip prefix-list BAD-IN seq 10 permit 172.16.0.0/12 le 32
ip prefix-list BAD-IN seq 15 permit 192.168.0.0/16 le 32
ip prefix-list BAD-IN seq 20 permit 0.0.0.0/0 ge 25
!
route-map FROM-ISPA deny 5
 match ip address prefix-list BAD-IN
route-map FROM-ISPA permit 10
 set community 65010:100
 set local-preference 200
!
route-map TO-ISPA permit 10
 set metric 100
!
router bgp 65010
 neighbor 2.2.2.2 remote-as 65010
 neighbor 2.2.2.2 update-source Loopback0
 neighbor 3.3.3.3 remote-as 65010
 neighbor 3.3.3.3 update-source Loopback0
 address-family ipv4
  neighbor 2.2.2.2 activate
  neighbor 2.2.2.2 next-hop-self
  neighbor 2.2.2.2 send-community
  neighbor 3.3.3.3 activate
  neighbor 3.3.3.3 next-hop-self
  neighbor 3.3.3.3 send-community
  neighbor 100.64.14.2 route-map FROM-ISPA in
  neighbor 100.64.14.2 route-map TO-ISPA out
  aggregate-address 198.51.100.0 255.255.255.0 summary-only
 exit-address-family
```

## RT02（edge-B: ISP-A待機タグのみ・ISP-B タグ+例外LP300・MED200・集約）

```
ip prefix-list BAD-IN seq 5 permit 10.0.0.0/8 le 32
ip prefix-list BAD-IN seq 10 permit 172.16.0.0/12 le 32
ip prefix-list BAD-IN seq 15 permit 192.168.0.0/16 le 32
ip prefix-list BAD-IN seq 20 permit 0.0.0.0/0 ge 25
!
ip prefix-list EXC seq 5 permit 203.0.113.0/24
!
route-map FROM-ISPA2 deny 5
 match ip address prefix-list BAD-IN
route-map FROM-ISPA2 permit 10
 set community 65010:100
!
route-map FROM-ISPB deny 5
 match ip address prefix-list BAD-IN
route-map FROM-ISPB permit 10
 match ip address prefix-list EXC
 set community 65010:200
 set local-preference 300
route-map FROM-ISPB permit 20
 set community 65010:200
!
route-map TO-ISPA permit 10
 set metric 200
!
router bgp 65010
 neighbor 1.1.1.1 remote-as 65010
 neighbor 1.1.1.1 update-source Loopback0
 neighbor 3.3.3.3 remote-as 65010
 neighbor 3.3.3.3 update-source Loopback0
 address-family ipv4
  neighbor 1.1.1.1 activate
  neighbor 1.1.1.1 next-hop-self
  neighbor 1.1.1.1 send-community
  neighbor 3.3.3.3 activate
  neighbor 3.3.3.3 next-hop-self
  neighbor 3.3.3.3 send-community
  neighbor 100.64.24.2 route-map FROM-ISPA2 in
  neighbor 100.64.24.2 route-map TO-ISPA out
  neighbor 100.64.25.2 route-map FROM-ISPB in
  aggregate-address 198.51.100.0 255.255.255.0 summary-only
 exit-address-family
```

## 反映（両エッジで）

```
clear ip bgp * soft
```

## 要件との対応 / 解説の骨子

| 要件 | 実装 | ポイント |
|------|------|---------|
| 1 | Lo0ピア + update-source + NHS | NHS が無いと RT03 は 100.64.x を解決できず経路不使用 |
| 2 | set community + **send-community** | send-community 忘れが最頻の落とし穴（既定で iBGP にも送られない） |
| 3 | RT01 で LP200 | LP は iBGP で伝搬 → RT02 も自分の eBGP(LP100) より RT01 経由を選ぶ。weight では不可 |
| 4 | RT02 で例外のみ LP300 | LP300 > LP200 で AS 全体が ISP-B へ。route-map の順序（例外→汎用）が肝 |
| 5 | aggregate-address summary-only ×両エッジ | 素材の /25 は RT03 が network 文で BGP に投入（OSPF には入れない設計） |
| 6 | TO-ISPA out で set metric (RT01=100 < RT02=200) | 同一隣接AS(65010)からの2経路なので IOS 既定で MED 比較される。prepend は要件で禁止 |
| 7 | BAD-IN (RFC1918 3ブロック + ge 25) を deny | ge/le の使い分け。過剰フィルタ（beacon まで消す）は減点 |
| 8 | 上記の総合結果 | ping source Lo10/Lo11 で集約の戻り経路も同時検証される |

## 検証コマンド

- `show ip bgp neighbors | include BGP neighbor|BGP state`
- `show ip bgp 192.0.2.0` / `show ip bgp 203.0.113.0`（LP/community/bestpath 確認）
- `show ip route bgp`（RT03 の next-hop が 1.1.1.1/2.2.2.2 か）
- RT04: `show ip bgp 198.51.100.0 255.255.255.0`（両エッジ受信・MED・bestpath）
- RT06: `show ip bgp | include 198.51.100`（/25 が漏れていないか）

## 生成器化（seed バリアント運用, 2026-07-05〜）

値ランダム化は gen_params.py の汎用フロー（base マージ＋ comm の fmt 派生）を使う。
`solution/*.cfg.j2` が params 追従の模範解答テンプレート（検証自動化用）。

```
# 1) seed から params/s<seed>.yml を生成（AS×4, Lo×6, 内部seg×2, comm は AS 追従）
.venv/bin/python3 topologies/gen_params.py --repo . --problem ENARSI-BGP-POLICY-01 --seed <N>
# 2) 出題
scripts/lab.sh provision ENARSI-BGP-POLICY-01 s<N>
# 3) 採点
ansible-playbook playbooks/grade.yml -e problem=ENARSI-BGP-POLICY-01 -e variant=s<N> \
  --vault-password-file <(printf 'CCNP\n')
```

- 実機100点検証済み seed: **base(固定値), s4242, s7777**。新しい seed は出題前に実機1サイクル推奨。
- 固定のまま残す値: beacon_* / cust_net / leak_* / 外部 seg (100.64.x)
  （公開風アドレスの可読性と採点 regex の安定を優先。ランダム化は _gen.yml に追記すれば拡張可）

## 変種 "bfd"（-e variant=bfd）の追加解答
ISP 側（RT04/RT05）は BFD 対応済み。顧客側エッジ（RT01/RT02）の eBGP 直結リンクに
タイマと fall-over bfd を設定する（iBGP Loopback ピアは対象外）。

```
! RT01（ISP-A 向き）
interface Ethernet0/0
 bfd interval 500 min_rx 500 multiplier 3
router bgp 65010
 neighbor 100.64.14.2 fall-over bfd
! RT02（ISP-A 待機系・ISP-B 向き）
interface Ethernet0/0
 bfd interval 500 min_rx 500 multiplier 3
interface Ethernet0/1
 bfd interval 500 min_rx 500 multiplier 3
router bgp 65010
 neighbor 100.64.24.2 fall-over bfd
 neighbor 100.64.25.2 fall-over bfd
```

> fall-over bfd はセッションパラメータなので `router bgp` 直下（AF 配下ではない）。
> 確認: `show bfd neighbors details`（3 セッション Up / Registered protocols: BGP）
