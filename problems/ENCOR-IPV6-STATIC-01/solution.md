# 模範解答 ENCOR-IPV6-STATIC-01

## RT01
```
ipv6 unicast-routing
!
interface Loopback0
 ipv6 address 2001:DB8:A::1/128
!
interface Ethernet0/0
 no shutdown
 ipv6 address 2001:DB8:12::1/64
 ipv6 address FE80::1 link-local
!
! (1) RT02 Lo へ = 再帰静的(GUA ネクストホップのみ)
ipv6 route 2001:DB8:B::2/128 2001:DB8:12::2
! (2) RT03 Lo へ = 出口IF + リンクローカル(完全指定)
ipv6 route 2001:DB8:C::3/128 Ethernet0/0 FE80::2
```

## RT02（中継）
```
ipv6 unicast-routing
!
interface Loopback0
 ipv6 address 2001:DB8:B::2/128
!
interface Ethernet0/0
 no shutdown
 ipv6 address 2001:DB8:12::2/64
 ipv6 address FE80::2 link-local
!
interface Ethernet0/1
 no shutdown
 ipv6 address 2001:DB8:23::2/64
 ipv6 address FE80::2 link-local
!
! (3) RT01 Lo へ = 出口IF + リンクローカル(完全指定)
ipv6 route 2001:DB8:A::1/128 Ethernet0/0 FE80::1
! (4) RT03 Lo へ = 再帰静的(GUA ネクストホップのみ)
ipv6 route 2001:DB8:C::3/128 2001:DB8:23::3
```

## RT03
```
ipv6 unicast-routing
!
interface Loopback0
 ipv6 address 2001:DB8:C::3/128
!
interface Ethernet0/0
 no shutdown
 ipv6 address 2001:DB8:23::3/64
 ipv6 address FE80::3 link-local
!
! (5) デフォルト経路 ::/0 = 出口IF + リンクローカル(完全指定)。RT01/RT02 双方へこの 1 本で到達。
ipv6 route ::/0 Ethernet0/0 FE80::2
```

## ポイント / 教育核心
- **リンクローカル・ネクストホップには出口IFが必須**：`ipv6 route 2001:DB8:C::3/128 FE80::2`
  のように出口IFを書かずにリンクローカルだけを指定すると、IOS は
  `% Interface has to be specified for a link-local nexthop`
  で拒否する。リンクローカルアドレスは**リンクごとにしか一意でない**ため、
  どのリンクへ出すのかをルータが決められない。**必ず `<出口IF> FE80::x` の完全指定**にする。
- **手動リンクローカルの意義**：自動生成（EUI-64, `FE80::A8BB:CCFF:FE00:...`）のままだと
  値が読みにくく静的経路に書きづらい。`ipv6 address FE80::x link-local` で覚えやすい値に固定すると、
  完全指定静的経路の保守性が上がる。本問はこの手動値を静的経路から参照している。
- **再帰静的（GUA）vs 完全指定（リンクローカル）**：
  - 再帰静的 `ipv6 route <dst> <GUA>` … ネクストホップ GUA を**別途 RIB で解決**してから転送（直結 GUA があれば解決可）。
  - 完全指定 `ipv6 route <dst> <IF> FE80::x` … 出口IFが確定しているので解決が一段で済む。
    P2P/リンクローカル運用で定番。
- **デフォルト経路 `::/0`**：スタブ的な RT03 は個別経路を並べず `::/0` 1 本で上流（RT02）へ。
  IPv4 の `0.0.0.0/0` に相当。ここでもネクストホップはリンクローカルなので**出口IF必須**。
- **`ipv6 unicast-routing` 必須**：これが無いと中継 RT02 がパケットを転送せず、
  直結以外への ping が落ちる（静的経路は RIB に入っても転送されない）。
- **戻り経路**：往復で初めて ping が成立する。例として RT01→RT03 が通るには、
  RT03 側に RT01 Lo（`2001:DB8:A::1`）への戻り（=デフォルト経路）が必要。

## 確認コマンド
```
show ipv6 interface brief          ! FE80::x と GUA の確認
show ipv6 route static             ! 静的経路の方式(IF/ネクストホップ)を確認
ping 2001:DB8:C::3 source Loopback0
```
