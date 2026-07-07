# 模範解答 : ENARSI-DMVPN-BGP-01 (DMVPN Phase 2 + BGP コア 相互再配送, 暗号なし)

> RT01=ハブ(NHS/再配送境界) / RT02,RT03=スポーク / RT04=WAN(固定) / RT05=DCコア(固定)。
> tunnel source は各エッジの underlay 物理 IF（`GigabitEthernet0/0`）。

## RT01 (Hub) — DMVPN + eBGP + 相互再配送
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
! 先に BGP を定義してから EIGRP 側の redistribute bgp を書く
router bgp 65001
 bgp log-neighbor-changes
 neighbor 10.0.15.2 remote-as 65000
 redistribute eigrp 100
!
router eigrp 100
 network 1.1.1.1 0.0.0.0
 network 10.255.0.0 0.0.0.255
 redistribute bgp 65001 metric 1000000 100 255 1 1500
 no auto-summary
!
```
> ★`redistribute bgp 65001` の AS は**ローカルの BGP プロセス AS (65001)**。
> DC 側の AS (65000) ではない（再配送は「自分の」BGP プロセスから行う）。

## RT02 (Spoke1) / RT03 (Spoke2) — DMVPN のみ
```
interface Tunnel0
 ip address 10.255.0.2 255.255.255.0          ! RT03 は 10.255.0.3
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
 network 2.2.2.2 0.0.0.0                       ! RT03 は 3.3.3.3
 network 10.255.0.0 0.0.0.255
 no auto-summary
!
```

## 確認
```
show dmvpn                                    ! Hub=両スポークUP / Spoke=hubUP
show ip route eigrp                           ! 対向スポークLo(next-hop=対向スポーク) + 172.20.20.0/24(D EX)
show ip bgp summary                           ! 10.0.15.2 Established
ping 3.3.3.3 source Loopback0 repeat 5        ! RT02->RT03 スポーク間ダイレクト
ping 172.20.20.1 source Loopback0 repeat 5    ! 支店->DC
! RT05 側: show ip route bgp で 2.2.2.2/3.3.3.3 が B、ping 2.2.2.2 source 172.20.20.1
```

### ポイント（落とし穴の解説）
- **相互再配送の方向は 2 つ**:
  - `router bgp 65001 / redistribute eigrp 100` … EIGRP(支店 Lo)→BGP。DC が `2.2.2.2`/`3.3.3.3`
    を BGP で学習する（**上り**）。BGP 再配送は seed metric 不要。
  - `router eigrp 100 / redistribute bgp 65001 metric ...` … BGP(DC LAN)→EIGRP。スポークが
    `172.20.20.0/24` を EIGRP 外部(D EX)で学習する（**下り**）。
    **EIGRP への再配送は seed metric が必須**（無いと経路が入らない）。
- **★`redistribute bgp <AS>` の AS はローカル BGP プロセス番号 (65001)**:
  再配送は「自分の」BGP プロセスから行うので、ここは自 AS の `65001`。
  DC 側 (peer) の `65000` を書くと、その BGP プロセスは自機に存在しないため
  コマンドが通らず（IOS が拒否）、下り再配送が一切効かない。混同しやすい落とし穴。
- **なぜ route-map 無しでループしないか**: 再配送点が**ハブ 1 か所だけ**なので、各プレフィックスの
  RIB ソースが AD で一意に決まる（DC LAN=eBGP 20 / 支店 Lo=EIGRP内部 90）。
  `redistribute eigrp` は RIB が EIGRP の経路だけ、`redistribute bgp` は RIB が BGP の経路だけを
  対象にするため、DC LAN が EIGRP 経由で BGP へ戻る…という相互フィードバックは起きない。
  （再配送点が 2 か所以上だと AD 操作や route-map / tag でループ防止が必要になる。）
- **DMVPN Phase 2 の肝**（[[]] DMVPN-POC-01 と同じ）: ハブ Tunnel0 の
  `no ip split-horizon eigrp 100`（対向スポーク経路を同 IF へ反射）＋
  `no ip next-hop-self eigrp 100`（next-hop をハブに書き換えない）の**両方**で、
  スポーク間ダイレクトトンネルが成立する。
- **DC 向けトラフィックはハブ経由が正**: スポークが学ぶ `172.20.20.0/24` の next-hop はハブ
  (`10.255.0.1`)。これはハブが**再配送で自ら起こした**経路なので next-hop はハブのまま
  （no-next-hop-self はスポーク間の中継経路にのみ効く）。DC はハブの背後なので妥当。
- **tunnel destination(NBMA) は underlay の default route で解決**し、再帰させない。EIGRP は
  overlay と Lo0 のみ、underlay/default は載せない。

> 採点: DMVPN セッション(両スポークUP/hubUP)、Phase2 署名(対向スポーク next-hop)、
> ハブ-DC eBGP Established、DC が支店 Lo を BGP 学習(上り)、支店が DC LAN を EIGRP 学習(下り)、
> 支店間ダイレクト ping、支店⇔DC 双方向 ping で判定。RT04/RT05 は設定変更を採点しない。
