# 模範解答 : ENARSI-BGP-IPV6-01

## 核心
デュアルスタック BGP では **IPv4 と IPv6 は別々のアドレスファミリ（AFI/SAFI）**として
独立してネゴシエートされ、独立して経路を交換する。だから **IPv4 が完全に正常でも
IPv6 だけが全滅する**ことがある。「v4 で ping が通る＝ BGP 健全」は誤り——これが本問の罠。

IPv6 を **端から端まで**（①セッション → ②広告 → ③交換 → ④転送）追うと、3か所に故障がある。

## 故障と是正（3か所）

### F1: RT02 の IPv6 AF で RT01 の activate 欠落 → v6 セッションが Idle
`show bgp ipv6 unicast summary` を RT01 で見ると、`2001:DB8:12::2` が **Idle**。
IPv4 セッションは Established なのに v6 だけ上がらない。原因は RT02 側で
**IPv6 AF の該当ネイバーを activate していない**ため、AFI/SAFI capability が
噛み合わずセッションが成立しない。

```
! RT02
router bgp 65002
 address-family ipv6 unicast
  neighbor 2001:DB8:12::1 activate
```

### F2: RT03 の IPv6 AF に Loopback0 の network 文が欠落 → v6 Lo が広告されない
F1 を直すと v6 セッションは上がるが、RT01 に **`2001:DB8:3::3/128` が来ない**。
RT03 が自分の v6 Lo を **network で広告していない**ため（v4 側には network 文がある）。

```
! RT03
router bgp 65003
 address-family ipv6 unicast
  network 2001:DB8:3::3/128
```

### F3: RT03 で ipv6 unicast-routing が欠落 → v6 を転送できない＋v6 AF が塩漬け
経路は届くようになっても、RT03 が **IPv6 パケットを転送しない**（戻りトラフィックが
成立しない＝ ping が返らない）。`ipv6 unicast-routing` がグローバルに無いため。

```
! RT03
ipv6 unicast-routing
```

★**実機の落とし穴（IOL-XE 17.15）**：`ipv6 unicast-routing` が無い状態で起動すると、
起動時の day0 適用で **IPv6 AF の `neighbor ... activate` 行そのものが受理されず**、
RT03 の v6 セッションが「activate 無し」で塩漬けになる。`ipv6 unicast-routing` を
後から入れても **activate は自動で復活しない**ので、RT03 で activate を**入れ直す**必要がある：

```
! RT03 (unicast-routing を入れた後)
router bgp 65003
 address-family ipv6 unicast
  neighbor 2001:DB8:23::2 activate
```

投入後もセッションが Idle のままなら **`clear bgp ipv6 unicast 2001:DB8:23::2`**
（ハードクリア）で蹴る。Idle には `soft` は効かない。

## 是正後の確認
- RT01 `show bgp ipv6 unicast summary`：`2001:DB8:12::2` が **Established・PfxRcd 2**。
- RT01 `show bgp ipv6 unicast`：`2001:DB8:2::2/128` と `2001:DB8:3::3/128` の両方。
- RT01 `ping 2001:DB8:3::3 source Loopback0` と
  RT03 `ping 2001:DB8:1::1 source Loopback0` が **成功**。
- ★IPv4 は最初から最後まで無傷（`ping 3.3.3.3` は常に成功）。

## つまずきポイント / 実機知見
- **`show ip bgp` では IPv6 は見えない。** IPv6 は必ず `show bgp ipv6 unicast [summary]`
  で見る（`show ip bgp` は v4 専用）。切り分けの入口を間違えると詰む。
- **activate は AF ごと・ネイバーごとに必要。** v4 で activate 済みでも v6 は別途要る。
  片側だけ activate を外すと（本問の F1）、PfxRcd 0 ではなく **セッションが Idle** に
  落ちる（AFI/SAFI capability の不一致）。両側とも無い場合は v4 のみ Established で
  v6 は交換されない。
- **v6 の next-hop は二面性がある。** `show bgp ipv6 unicast` はグローバル next-hop、
  `show ipv6 route` は **link-local**（FE80::…）で載る。正常動作なので驚かないこと。
- **network 文と ipv6 unicast-routing は別レイヤ。** 前者は「BGP に広告するか」、
  後者は「v6 を転送するか」。両方揃わないと E2E が通らない。
