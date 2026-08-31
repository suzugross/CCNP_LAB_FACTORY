# IPv6 自動アドレッシング TS — 追加 PoC (BL-149 P0) 結果 (2026-08-25)

V6ADDR-TS.design.md §5 の追加 PoC 8項目を IOL 17.15 実機で検証。**全項目成立**。
既存 DHCPv6 PoC (poc/dhcpv6/README.md・BL-034) が扱わなかった RA/ND・異物・ACL・戻り経路を確定。

## 検証環境（poc-v6addr-iol-lab.yaml・コンソール専用）

```
   RT01 (DHCPv6サーバ, Lo0 2001:DB8:1::1)
     │ 2001:DB8:12::/64
   RT02 (GW/リレー)
     │ Et0/1 = 2001:DB8:A::1/64
   [SWA] 多アクセス LAN-A
   ├─ CLA (client)
   └─ ROG (rogue RA / DAD 相手)
```

- 全ノード IOL。MGMT/SSH 不使用、pyATS ターミナルサーバ経由（poc/redist-mp-loop/poc_console.py 流用）。
- day0 admin-down 癖: アドレス無しの CLA/ROG データ IF は起動後コンソールで `no shutdown` 必須。
- 撤収済み（poc_ops.py delete）。再現は import→start→各 IF no shutdown→本手順。

## 結果（8項目）

### 1. `ipv6 nd ra suppress` と `suppress all` の差 ✅
| 形 | 周期 RA | RS への応答（solicited RA） | 故障としての強さ |
|---|---|---|---|
| `ipv6 nd ra suppress`（素） | 止まる | **生きている**（バウンスした CLA が再取得） | 弱い（RS を出す全クライアントは影響ほぼ無） |
| `ipv6 nd ra suppress all` | 止まる | **止まる**（バウンス後 GUA・::/0 とも取得できず） | 強い＝真の「RA 停止」故障 |

→ **ra_suppress 故障は `suppress all` を使う**（ユーザ例②の「RA が止まる」に相当）。素の suppress は
「再起動したら直る／新規クライアントも RS で取れる」ため症状が出にくい。
★**副産物の罠**: `no ipv6 nd ra suppress` では `suppress all` は消えない（`no ... suppress all` が必要）。
解答者が素の no で消そうとすると直らない＝解説/採点の要注意点。

### 2. `ipv6 nd ra lifetime 0` ✅
GUA は**形成される**（プレフィクス＋A フラグは健在）が、**デフォルト経路だけ消える**
（CLA `show ipv6 route ::/0` = `% Route not found`、brief には GUA あり）。
`show ipv6 routers` の Router Lifetime が 0 で判別。→ suppress（全断）とも client_default_missing とも別指紋。

### 3. RDNSS `ipv6 nd ra dns server` ✅（ただし消費は限定的）
- 構文: **bare `ipv6 nd ra dns server 2001:DB8:1::53` は受理**、running-config に載る。
  `... infinite` は不正（`% Invalid input`）。数値 lifetime 形もあるが bare で十分。
- クライアント側: CLA `show ipv6 routers` に `DNS server 2001:DB8:1::53 / Lifetime 600` が出る。
  **ただし実リゾルバには入らない**（`show hosts summary` = `Name servers are 255.255.255.255`）。
- → **W-S（純 SLAAC）の DNS 要件は採点可能だが、判定は client `show ipv6 routers` の
  `DNS server <expected>` 行のみ**（名前解決の実効までは問えない）。
- ★**`show ipv6 routers` は当たり**: 受信 RA を丸ごと表示＝`AddrFlag`(M)/`OtherFlag`(O)/
  `Preference`/`Lifetime`/`Prefix ... onlink autoconfig`/`DNS server` を1コマンドで確認できる。
  クライアント視点の RA 検証の主力に採用。

### 4. 非 /64 プレフィクス広告 ✅
RT02 で `ipv6 nd prefix 2001:DB8:AA::/72 ...`（+ 既定 /64 を no-advertise）を広告すると、
CLA `show ipv6 routers` には `Prefix 2001:DB8:AA::/72 onlink autoconfig`（autoconfig フラグ付き）が
出るのに、**GUA は生成されない**（brief は LL のみ）。IOS は非 /64 で SLAAC しない完全サイレント。
→ nd_prefix_wrong_len の指紋 = routers に prefix あり／brief に GUA なし。

### 5. rogue RA（異物ルータ）✅ ＋ 採点の分水嶺
- ROG に `ipv6 address 2001:DB8:BAD::1/64` + `ipv6 nd router-preference High` を入れると、
  CLA は**偽 GUA `2001:DB8:BAD:...` を追加形成**し、`show ipv6 routers` に
  `Preference=High` の偽ルータが正規（Medium）と並ぶ。外向きは偽デフォルトに吸われる。
- **分水嶺（fix 後の残留）**: 偽ルータ IF を shut すると IOS が**最終 RA(lifetime 0)** を送り、
  CLA のデフォルトルータ一覧からは**数秒で消える**（到達性は即回復）。
  だが**偽 GUA はプレフィクスの valid lifetime 分だけ残留**（バウンスしない限り消えない）。
- → **採点は「偽ルータが `show ipv6 routers` に不在」＋「到達性回復」で行う**。
  偽 GUA の消失を条件にしない（要クライアントバウンス）。恒久対策=RA Guard は BL-146 の裏話へ。

### 6. DAD 衝突 ✅（決定論的）
CLA・ROG 双方に手動 LL `ipv6 address FE80::99 link-local` + `ipv6 address autoconfig` を入れると、
後発側が `%IPV6_ND-4-DUPLICATE`／`IPv6 is stalled, link-local address is FE80::99 [DUP]`。
**LL 自体の衝突なので IPv6 が丸ごとストール**（GUA 生成にも至らない）＝強く決定論的な指紋。
[[ccnp-ipv6-eui64-linklocal]] の「手動 LL が interface-id になる」挙動を衝突生成に利用。
fix = 一方の LL を変える／手動 LL を外して EUI-64 に戻す。

### 7. IPv6 ACL で DHCPv6(UDP 546/547) 遮断 ✅ ＋ 重要な作問制約
- **外科的形**（RT02 Et0/1 in）:
  ```
  ipv6 access-list BLOCK-DHCP6
   deny udp any any eq 547
   deny udp any any eq 546
   permit ipv6 any any     ← これが要
  ```
  → CLA は `Address State is SOLICIT (6)` で停止・DHCP アドレス無し、
  一方 **ND 由来デフォルト経路は生存**（`Known via "ND"`）。「DHCPv6 だけ死ぬ」を実現。
- ★**裏取り**: `permit ipv6 any any` を外した deny のみ ACL にすると、**RA(SLAAC) も死ぬ**
  （CLA `show ipv6 routers` 空・デフォルト経路消失）。**IPv6 ACL の暗黙 permit は NS/NA のみで
  RS/RA は対象外**を実証。→ acl_blocks_dhcpv6 故障は「明示 permit + deny 546/547」の形が必須
  （deny だけだと全断の別故障になる）。解答者の naive な ACL 縮小が SLAAC を巻き込む教育点にもなる。

### 8. サーバの戻り経路欠落 ✅（設計ドラフトの症状文を是正）
RT01 の `ipv6 route 2001:DB8:A::/64 2001:DB8:12::2` を消すと:
- **DHCPv6 のアドレス割当は正常に成立**（CLA `Address State is OPEN`・binding も成立）。
  リレーの制御プレーンは接続済み 12::/64 区間＋LL で完結し、クライアント subnet への route は不要。
- しかし **CLA→RT01 Lo0 の ping = 0%**（RT01 に A::/64 への戻り経路が無く、データプレーンが片方向で死ぬ）。
- → 設計ドラフトの「RELAY-FORW 到達・REPLY が返れない」は**誤り**。正しくは
  **「アドレスは取れる（binding OK）が、到達性が戻り経路欠落で片方向に死ぬ」**。
  アドレスが付くので不注意な解答者は DHCP を正常と誤認し原因を探し違える＝良い罠。

## 生成器・採点への反映（design §3/§4 に反映済み）
- ra_suppress=`suppress all` 固定 / `no ... suppress all` の解錠罠を solution に明記。
- クライアント視点の RA 検証は `show ipv6 routers`（M/O/preference/lifetime/prefix/DNS 一括）。
- DNS-in-SLAAC は `show ipv6 routers` の `DNS server` 行のみで採点。
- rogue_ra は「偽ルータ不在＋到達性」で採点（偽 GUA 残留は当てにしない）。
- dad_conflict の指紋 = `IPv6 is stalled ... [DUP]`＋`%IPV6_ND-4-DUPLICATE`。
- acl_blocks_dhcpv6 は「明示 permit + deny 546/547」で生成（deny のみは全断の別種）。
- server_return_route_missing の症状文 = 「割当 OK・到達不能（片方向）」に是正。
- 反映済み既存知見（BL-034）: `ipv6 enable` 無し=SOLICIT 未送信 / automatic は直結 IA_PD 無応答 /
  no-autoconfig で純 stateful / stateful はデフォルト非配布（RA/静的が唯一）。
