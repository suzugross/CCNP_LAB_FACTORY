# 模範解答 ENCOR-IPV6-SLAAC-STATIC-01

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
interface Ethernet0/1
 no shutdown
 ipv6 address 2001:DB8:13::1/64
 ipv6 address FE80::1 link-local
!
! (1) RT02 Lo へ = 再帰静的(GUA ネクストホップ)
ipv6 route 2001:DB8:B::2/128 2001:DB8:12::2
! (2) RT03 Lo へ = フローティング: 主=RT02経由 / 予備=直結 Et0/1 AD200
ipv6 route 2001:DB8:C::3/128 Ethernet0/0 FE80::2
ipv6 route 2001:DB8:C::3/128 Ethernet0/1 FE80::3 200
! (3) 自社 /48 の未使用分を破棄(Null0)
ipv6 route 2001:DB8:A::/48 Null0
```

## RT02（中継 / RA 送出元）
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
 ipv6 address 2001:DB8:23::/64 eui-64
 ipv6 address FE80::2 link-local
!
! RT01 / RT03 の Loopback へ(リンクローカル完全指定)
ipv6 route 2001:DB8:A::1/128 Ethernet0/0 FE80::1
ipv6 route 2001:DB8:C::3/128 Ethernet0/1 FE80::3
```
※ Et0/1 は GUA を持ち RA 抑止していないので、既定でプレフィックス通知＋デフォルトルータ広告を行う。

## RT03（支店エッジ / SLAAC）
```
ipv6 unicast-routing
!
interface Loopback0
 ipv6 address 2001:DB8:C::3/128
!
interface Ethernet0/0
 no shutdown
 ipv6 address autoconfig default
 ipv6 address FE80::3 link-local
!
interface Ethernet0/1
 no shutdown
 ipv6 address 2001:DB8:13::3/64
 ipv6 address FE80::3 link-local
!
! 上流(RT01/RT02 Loopback)は SLAAC で得た ::/0 で到達 → 個別/手動デフォルトは不要
```

## ポイント / 教育核心
- **SLAAC（`ipv6 address autoconfig`）**：RA のプレフィックス＋EUI-64 で GUA を**自動生成**。
  `default` キーワードを付けると、RA の送信元（=デフォルトルータ）向けに **`::/0` を自動インストール**する
  （RIB では `Known via "ND"`）。手動のデフォルト経路は不要になる。
  受け取りには、送出側（RT02）が **router lifetime > 0 のRAを出している**こと（IOSのルータは既定で広告）が前提。
- **EUI-64（`... /64 eui-64`）**：ホスト部を MAC から自動生成（`...FF:FE...` が入る変形 EUI-64）。
  プレフィックスだけ決めれば host 部は機器任せ。到達確認は予測できる **Loopback** 宛で行うのが定石。
- **直結指定スタティック（`ipv6 route <p> <IF>`）の注意**：ネクストホップを書かず**出口IFだけ**指定する形は、
  RIB には `directly connected` で入るが、**マルチアクセス（Ethernet）では宛先アドレスそのものを
  そのリンク上で ND 解決しようとする**ため、リンク上に居ない remote な `/128`（相手のLoopback等）には届かず
  ブラックホールになる。**真のP2Pリンク（シリアル/トンネル等）専用**と覚える。本問は全 Ethernet なので
  RT01→RT02 Lo は**再帰静的（GUA）**にしている（実機でも直結指定だと ND 失敗で到達不可になることを確認済み）。
- **フローティングスタティック**：同一宛先に AD 違いの2本。**AD の小さい主経路だけが RIB に入り**、
  予備（AD 200）は主経路が消えた時に昇格。`show ipv6 route 2001:DB8:C::3/128` で主経路（Et0/0）のみ・
  予備（Et0/1）が見えなければ正しく float している。
  ※ 実機確認：RT01 Et0/0 を `shutdown` すると RIB の C::3 が **distance 200・via Et0/1 に切替**わる（＝昇格動作OK）。
  なお本問は学習目的を「主経路ダウン時の RIB 昇格」に絞っており、**往復の end-to-end フェイルオーバまでは保証しない**
  （戻り経路が RT01 の主リンク依存のため）。完全な経路冗長には戻り側にも予備経路が要る——という気付きも含めた設計。
- **Null0 破棄経路**：`ipv6 route 2001:DB8:A::/48 Null0`。集約ブロックの**未使用アドレスを捨てて**
  再帰ループや無駄な転送を防ぐ。より具体的な経路（`A::1/128` の local 等）が最長一致で優先されるので、
  実在アドレスへの到達は妨げない。
- **戻り経路**：RT03 は SLAAC デフォルトで上流へ。RT02 が RT01/RT03 Loopback の戻りを持つことで往復成立。

## 確認コマンド
```
show ipv6 interface brief                 ! SLAAC/EUI-64 で付いたGUA・LL を確認
show ipv6 route ::/0                       ! RT03: Known via "ND"(SLAAC由来)
show ipv6 route 2001:DB8:C::3/128          ! RT01: 主経路 Et0/0 のみ(フローティング)
show ipv6 route static                     ! 直結指定(directly connected)/Null0 を確認
ping 2001:DB8:C::3 source Loopback0
```
