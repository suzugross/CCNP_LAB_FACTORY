# DHCPv6 シリーズ 設計メモ（BL-034）

作成 2026-07-09（IPv6 棚卸しからの具体化）。ENARSI 4.x「IPv4/IPv6 DHCP のトラブルシュート
（クライアント / IOS DHCP サーバ / リレー / オプション）」の **v6 半分が完全空白**を埋める。
SLAAC は ENCOR-IPV6-SLAAC-STATIC-01 で既出 → 本シリーズは **M/O フラグによる方式の使い分け**と
**Prefix Delegation** が核心。

## 全体構成（3フェーズ）

| フェーズ | 内容 | 規模 |
|---|---|---|
| Phase 0 | **✅ 完了 (2026-07-09)** IOL 17.15 実機プローブ — 全項目成立。結果と罠8点は [poc/dhcpv6/README.md](../../poc/dhcpv6/README.md) | 済 |
| Phase 1 | **✅ 完了 (2026-07-09)** ENARSI-DHCPV6-01（4 IOL・難5）— 実機フルサイクル済（未解答0点/模範解答100点×2回）。★ipv6 enable は autoconfig 併存時は不要と実機確認（solution.md 参照） | 済 |
| Phase 2 | ENARSI-DHCPV6-PD-01: Prefix Delegation 構築問（難4） | 半日〜1日 |
| 将来 | TS 生成器 gen_dhcpv6_ts.py（故障カタログは末尾）/ Linux クライアント変種 | 別途 |

方針: 全ノード IOL（クライアントも IOL ルータをホスト役に = SLAAC-STATIC-01 の
`ipv6 address autoconfig default` イディオム踏襲）。Linux(PC01) クライアントは
netplan の v6 挙動という別変数が入るため Phase 1 では使わず、将来変種に回す。

## Phase 1: ENARSI-DHCPV6-01 — 3方式の使い分け（難4-5）

### トポロジ（4 IOL・RT02 のデータIF=3 で次数上限内）

```
                        RT01 (DHCPv6サーバ, Lo0=2001:DB8:1::1)
                          │ Et0/0 = 2001:DB8:12::1/64
                          │
                          │ Et0/0 = 2001:DB8:12::2/64
        ┌──────────── RT02 (GW/リレー) ────────────┐
        │ Et0/1 = 2001:DB8:A::1/64                │ Et0/2 = 2001:DB8:B::1/64
        │                                          │
   LAN-A: CLA (stateless)                     LAN-B: CLB (stateful)
   SLAAC + O-flag → DNSのみDHCPv6             M-flag → アドレスもDHCPv6
```

- **初期投入済み（健全）**: 全 IF アドレス・RT01⇄RT02 の相互静的経路（LAN 向け/戻り）。
  ルーティングは課題にしない（DNSDHCP と同じ「NW土台は健全」パターン）。
- **受験者の課題**（PoC 実証済みの正解構成に更新・2026-07-09）:
  1. RT01: DHCPv6 プール2つ ＋ **Et0/0 は bare `ipv6 dhcp server`（automatic）**。
     - stateless 用: dns-server `2001:DB8:1::53` + domain-name + **`link-address 2001:DB8:A::/64`**
       （これが無いと LAN-A にプールが選択されない＝サイレント故障。教育核心）
     - stateful 用: `address prefix 2001:DB8:B::/64` + DNS + domain（address prefix 自体が選択キー）
     - ★`ipv6 dhcp server <pool>` の名指しは **1 IF 1 つ（2つ目は置換）** → 2 LAN 集約は automatic 必須。
       v4 の giaddr プール選択との対比が学び。
  2. RT02: 両 LAN IF に `ipv6 dhcp relay destination 2001:DB8:12::1`（サーバはオフリンク）。
  3. RT02 Et0/1: `ipv6 nd other-config-flag`（O のみ・M は立てない）。
  4. RT02 Et0/2: `ipv6 nd managed-config-flag`＋**`ipv6 nd prefix 2001:DB8:B::/64 2592000 604800
     no-autoconfig`**（PoC で必要と確定: M-flag でも A-flag は立ったままで SLAAC 併存する）。
  5. CLA: `ipv6 address autoconfig default`（SLAAC）。DNS が DHCPv6 経由で入ることを確認
     （IOS は O-flag を見て INFORMATION-REQUEST を自動送信 — PoC 実証済）。
  6. CLB: **`ipv6 enable`（★これが無いと LL 無しで SOLICIT が出ないサイレス罠・PoC 実証）**
     ＋ `ipv6 address dhcp` ＋ `ipv6 address autoconfig default`（デフォルト経路は RA 由来。
     stateful DHCPv6 はデフォルトを配らないことを PoC で確認）。
- ヒント控えめポリシー: M/O フラグのコマンド・link-address・ipv6 enable は task に書かない。
  要件は「LAN-A はアドレス自動生成＋DNS 配布 / LAN-B はアドレスも中央管理（自動生成アドレス禁止）
  ・両クライアントから RT01 Lo0 到達」と挙動で示す。

### 採点設計（挙動ベース・約12チェック=100点）

| 対象 | チェック | 方式 |
|---|---|---|
| RT01 | stateless プールに DNS/domain あり・address prefix **なし** | `show ipv6 dhcp pool` raw（not_contains 併用） |
| RT01 | stateful プールに `Address allocation prefix: 2001:DB8:B::/64` | raw |
| RT01 | `show ipv6 dhcp binding` に IA_NA・アドレスが `2001:DB8:B:` 配下 | raw regex（リレー実効の証明を兼ねる） |
| RT02 | Et0/1・Et0/2 に relay destination | `show ipv6 dhcp interface` raw |
| RT02 | Et0/1 = O-flag のみ（"DHCP to obtain other configuration" あり / "routable addresses" **なし**） | `show ipv6 interface Et0/1` raw + not_contains |
| RT02 | Et0/2 = M-flag（"Hosts use DHCP to obtain routable addresses"） | raw |
| CLA | GUA が `2001:DB8:A:` 配下・Stateless autoconfig | `show ipv6 interface` raw |
| CLA | DNS `2001:DB8:1::53` を DHCPv6 で取得 | `show ipv6 dhcp interface` raw（PoC で書式確認） |
| CLA | **負の要件**: CLA に IA_NA が無い（stateless なのにアドレスまで貰っていない） | RT01 binding の not_regex |
| CLB | `show ipv6 dhcp interface` OPEN・取得アドレスが `2001:DB8:B:` 配下 | raw |
| CLA/CLB | RA デフォルト経由で RT01 Lo0 へ ping | exec ping |

- 動的アドレスは値が読めない → **プレフィクス regex マッチ**で判定（SLAAC 問の実証イディオム）。
- 負の要件は単独採点しない（QoS 教訓）: CLA の「IA_NA 無し」は CLA の SLAAC 成立チェックと
  同一グループで見る。
- `bringup_data_ifs: true` を立てる（IPv6-only IF の day0 admin-down 対策・OSPFv3 生成器と同じ）。

### PoC 項目（Phase 0・IOL 17.15）— ✅ 全項目実機確認済 (2026-07-09)

| # | 確認事項 | 結果 |
|---|---|---|
| 1 | `ipv6 address autoconfig` のクライアントが **O-flag を見て INFORMATION-REQUEST を送るか**（最大の不確実点） | ✅ 送る（DNS/domain 取得・リレー経由） |
| 2 | `ipv6 address dhcp`（stateful クライアント）が IOL で動くか | ✅ 動く。★`ipv6 enable` 必須（無いと SOLICIT 未送信のサイレント故障） |
| 3 | リレー経由のプール選択 | ✅ bare `ipv6 dhcp server`（automatic）＋ stateless=`link-address` 文 / stateful=`address prefix` で自動選択。名指しバインドは 1 IF 1 つ（置換） |
| 4 | M-flag 環境で `ipv6 nd prefix ... no-autoconfig` が必要か | ✅ 必要（M-flag でも A-flag は既定 ON で SLAAC 併存を実証）。要件化して出題価値に |
| 5 | 採点用 show の書式 | ✅ regex 素材一式確定 → [poc/dhcpv6/README.md](../../poc/dhcpv6/README.md) |
| 6 | ND フラグの `show ipv6 interface` 文言 | ✅ O=2行 / M=`Hosts use DHCP to obtain routable addresses.`（M 時 O 行なし） |

追加知見: stateful はデフォルト経路を配らない（RA 併用が定石）/ クライアント再始動は
`no ipv6 address dhcp`→再投入が確実 / `domain-name` は複数行追記 / debug 行頭は `IPv6 DHCP:` /
リレーの BULK_LQ 失敗ログは無害ノイズ。詳細は PoC README の★罠 8 点。

## Phase 2: ENARSI-DHCPV6-PD-01 — Prefix Delegation（難4）

### トポロジ（3 IOL）

```
RT01 (ISP/委任サーバ) ── RT02 (CPE, PDクライアント) ── CL03 (社内ホスト, SLAAC)
     Et0/0: 2001:DB8:12::/64      Et0/1: 委任prefix から /64 を自動派生
```

- RT01: `ipv6 dhcp pool` に `prefix-delegation pool DELEG-POOL`（`ipv6 local pool DELEG-POOL
  2001:DB8:D000::/40 48` = /48 を委任）。
- RT02(CPE): WAN 側 `ipv6 dhcp client pd DELEG`、LAN 側 `ipv6 address DELEG ::1/64`
  （general-prefix から派生）＋ RA で CL03 へ SLAAC 配布。
- **教育核心**: ①プレフィクスが ISP→CPE→ホストへ自動で流れる ②委任サーバが委任先への
  **静的経路を自動インストール**する（戻り経路を書かなくて良い理由を体感）。
- 採点: RT01 `show ipv6 dhcp binding` の IAPD / RT02 `show ipv6 general-prefix` /
  CL03 の GUA が `2001:DB8:D0` 配下（regex）/ CL03→RT01 Lo0 ping（自動経路の実効証明）。
- ✅ PoC 済 (2026-07-09): `ipv6 dhcp client pd DELEG`＋`ipv6 address DELEG 0:0:0:1::1/64` で
  /48 委任→派生アドレス→委任経路の自動インストール（`S 2001:DB8:D000::/48 via <client LL>`）
  →ping 100% まで実証。★**PD サーバは named バインド必須**（automatic は直接接続の IA_PD に
  応答しない — PoC 実証）。

## 将来: TS 故障カタログ（gen_dhcpv6_ts.py の種）

Phase 1/2 の健全構成に注入する候補（PoC 知見で更新・2026-07-09）:
`o_flag_missing`（アドレスは付くが DNS が来ない）/ `m_flag_missing`（stateful のはずが SLAAC）/
`relay_missing` / `relay_wrong_dest` / `link_address_missing`（stateless プールの link-address
欠落→LAN-A だけ DNS 不達・サイレント・PoC 実証メカニズム）/ `pool_prefix_mismatch`（address
prefix がリレー link-address と不一致→プール選択されない・サイレント）/ `dns_option_missing` /
`pd_hint_missing` / `autoconfig_not_suppressed`（no-autoconfig 欠落→アドレス2重・PoC 実証）/
`server_pool_binding_wrong`（automatic であるべき所を named で誤プール固定）/
`ipv6_enable_missing`（クライアント LL 無し→SOLICIT 未送信・最凶のサイレント・PoC 実証）。
※ DHCP はデータプレーン寄りの症状が多い → uRPF の教訓どおり RIB 採点でなく
binding/カウンタ/ping 採点で設計する。

## 補遺: DHCPv4 側の残ギャップ（小粒）

ブループリントは「**IOS** DHCP サーバ」を明記するが、現行 v4 資産（GEN-DNSDHCP）は
サーバが Linux(ISC)。IOS 側は `ip dhcp pool`／`excluded-address`／オプション／
`ip address dhcp`（IOS クライアント）が未出題。単一〜2RT の小ドリル
（ENCOR-DHCP-IOS-01・難2-3）で回収可能。優先度低・本シリーズとは独立に着手可。
