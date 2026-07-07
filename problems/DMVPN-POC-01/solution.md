# 模範解答 : DMVPN-POC-01 (Phase 2 マルチスポーク / mGRE + NHRP + EIGRP, 暗号なし)

> RT01=ハブ(NHS) / RT02=スポーク1 / RT03=スポーク2 / RT04=WANトランジット(変更禁止)。
> tunnel source は各エッジの underlay 物理 IF（`links[0]` = `GigabitEthernet0/0`）。

## RT01 (Hub)
```
interface Tunnel0
 ip address 10.255.0.1 255.255.255.0
 no ip redirects
 ip nhrp authentication DMVPNKEY
 ip nhrp network-id 1
 ip nhrp map multicast dynamic
 no ip split-horizon eigrp 100
 no ip next-hop-self eigrp 100
 tunnel source GigabitEthernet0/0
 tunnel mode gre multipoint
!
router eigrp 100
 network 1.1.1.1 0.0.0.0
 network 10.255.0.0 0.0.0.255
 no auto-summary
!
```

## RT02 (Spoke1)
```
interface Tunnel0
 ip address 10.255.0.2 255.255.255.0
 no ip redirects
 ip nhrp authentication DMVPNKEY
 ip nhrp network-id 1
 ip nhrp nhs 10.255.0.1
 ip nhrp map 10.255.0.1 10.0.14.1
 ip nhrp map multicast 10.0.14.1
 tunnel source GigabitEthernet0/0
 tunnel mode gre multipoint
!
router eigrp 100
 network 2.2.2.2 0.0.0.0
 network 10.255.0.0 0.0.0.255
 no auto-summary
!
```

## RT03 (Spoke2)
```
interface Tunnel0
 ip address 10.255.0.3 255.255.255.0
 no ip redirects
 ip nhrp authentication DMVPNKEY
 ip nhrp network-id 1
 ip nhrp nhs 10.255.0.1
 ip nhrp map 10.255.0.1 10.0.14.1
 ip nhrp map multicast 10.0.14.1
 tunnel source GigabitEthernet0/0
 tunnel mode gre multipoint
!
router eigrp 100
 network 3.3.3.3 0.0.0.0
 network 10.255.0.0 0.0.0.255
 no auto-summary
!
```

## 確認
```
show dmvpn                                  ! Hub=Type:Hub(両スポークUP) / Spoke=Type:Spoke
show ip nhrp                                ! 登録 + 解決された対向スポークのマッピング
show ip eigrp neighbors                     ! Tunnel0 上で隣接
show ip route eigrp                         ! 対向スポーク Lo0 の next-hop=対向スポーク(.2/.3)
ping 3.3.3.3 source Loopback0 repeat 5      ! RT02→RT03 (スポーク間ダイレクト誘発)
show dmvpn                                  ! RT02 にスポーク2への dynamic(D)エントリが UP
```

### ポイント（落とし穴の解説）
- **Phase 2 の肝 = ハブの `no ip next-hop-self eigrp 100`**:
  既定では、ハブが EIGRP 経路を別スポークへ広告する際にネクストホップを
  自分 (ハブの tunnel IP) に書き換える → 全トラフィックがハブ経由 (Phase 1)。
  これを無効化すると、スポーク1 は「3.3.3.3 の next-hop = 10.255.0.3 (スポーク2)」
  のまま学習する。CEF がその next-hop を解決しようとして NHRP 解決が走り、
  スポーク1⇔スポーク2 の**ダイレクトトンネル**が動的に張られる。
- **`no ip split-horizon eigrp 100` (ハブ Tunnel0)**: マルチポイントの同一 Tunnel0 で
  受けた経路を同じ IF から広告し返すのを許可する。これが無いと、ハブはスポーク1
  から受けた経路をスポーク2 へ流さず、そもそも対向スポークの経路を学習できない。
  → **split-horizon と next-hop-self の両方**を無効化して初めて Phase 2 が成立する。
- **NHRP**: スポークは `nhs` + `map <hub overlay> <hub NBMA>` でハブを登録。ハブは
  `map multicast dynamic` でスポークを動的収容。対向スポークの NBMA は事前に書かず、
  通信時に NHRP 解決でハブから教わる（だから新スポーク追加でハブ設定の変更が不要）。
- **マルチキャスト**: EIGRP hello のため、スポークは `ip nhrp map multicast <hub NBMA>`、
  ハブは `map multicast dynamic`。これが無いと隣接が張れない。
- **再帰ルーティング回避**: tunnel destination(NBMA) は underlay の default route(→RT04)で
  解決し、Tunnel0 では解決しない。EIGRP は overlay(10.255.0.0/24)+Lo0 のみ広告し、
  underlay の /30 や default は EIGRP に載せない。
- **トンネルは 1 本だけ**: スポーク間ダイレクトは追加トンネルを切るのではなく、
  同じ mGRE `Tunnel0` 上に NHRP が動的トンネルを形成する（mGRE の本質）。

> 採点: ハブの `show dmvpn` で両スポーク UP、各スポークでハブ UP、各スポークが
> 対向スポーク Lo0 を **next-hop=対向スポーク**で学習 (Phase 2 署名)、スポーク間
> Lo0→Lo0 の能動 ping 疎通で判定。RT04 は採点対象外。
