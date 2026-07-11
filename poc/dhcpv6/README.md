# DHCPv6 実効性 PoC (BL-034 Phase 0) — 結果 (2026-07-09)

DHCPV6-SERIES.design.md の Phase 0。IOL (iol-xe-17-15-01) 上で DHCPv6 の
stateless / stateful / リレー / プール選択 / PD が**実際に動くか・採点信号が取れるか**を実機測定。
**全項目成立 → Phase 1 / Phase 2 とも実装可**。ただし設計への反映事項が複数ある（下記★）。

## 検証環境（poc-dhcpv6-iol-lab.yaml）

```
                RT01 (DHCPv6サーバ, Lo0 2001:DB8:1::1)
                  │ 2001:DB8:12::/64
                RT02 (GW/リレー)
      Et0/1 ┌─────┴─────┐ Et0/2
   LAN-A: 2001:DB8:A::/64   LAN-B: 2001:DB8:B::/64
   CLA (stateless:          CLB (stateful:
    SLAAC + O-flag)          M-flag + no-autoconfig)
```

- 全ノード IOL。クライアント役も IOL ルータ（`ipv6 address autoconfig` / `ipv6 address dhcp`）。
- MGMT リースは mgmt_alloc.py（.14-.17）。検証後 stop/wipe/remove・リース解放済み。

## 確認事項マトリクス（design.md の PoC 項目 1〜6 ＋ PD）

| # | 項目 | 結果 |
|---|------|------|
| 1 | **O-flag → IOS クライアントが INFORMATION-REQUEST を送るか**（最大の不確実点） | ✅ **送る**。`ipv6 nd other-config-flag`＋client `ipv6 address autoconfig default` で DNS/domain 取得（リレー経由）。SLAAC GUA＋ND デフォルトも同時成立 |
| 2 | `ipv6 address dhcp`（stateful クライアント） | ✅ 動く。ただし★**`ipv6 enable` 必須**（下記罠1） |
| 3 | リレー経由のプール自動選択 | ✅ **`ipv6 dhcp server`（bare = automatic）が存在し機能**。stateless プールは `link-address 2001:DB8:A::/64` 文で、stateful プールは `address prefix` でリレーの link-address とマッチ。POOL-STATELESS 限定のドメイン値が届くことで選択を証明 |
| 4 | M-flag 下の SLAAC 併存（A-flag） | ✅ 併存する（DHCP アドレスと EUI-64 SLAAC アドレスの2本立ちを実機確認）→ 純 stateful には **`ipv6 nd prefix <pfx> 2592000 604800 no-autoconfig` が必要**（適用＋bounce で SLAAC 消滅を確認） |
| 5 | 採点用 show 書式 | ✅ 確定（下記「採点 regex 素材」） |
| 6 | ND フラグの show 文言 | ✅ O-flag=「Hosts use DHCP to obtain other configuration.」／M-flag=「Hosts use DHCP to obtain routable addresses.」（**M 設定時は O 行は表示されない**） |
| 7 | PD（prefix-delegation / general-prefix / 自動経路） | ✅ `/48` 委任・`ipv6 address DELEG 0:0:0:1::1/64`→`2001:DB8:D000:1::1` 派生・サーバに `S 2001:DB8:D000::/48 via <client LL>` **自動インストール**・ping 100%。ただし★罠3 |

## ★実機で判明した罠・設計反映事項

1. **`ipv6 address dhcp` 単体では SOLICIT が出ない（ipv6 enable 必須）**:
   リンクローカルが無く source address selection が失敗
   （debug: `IPv6 DHCP: SAS retured Null falling to link local` / `No source address`）。
   状態は SOLICIT 表示のまま実際は未送信。`ipv6 enable` 追加で即 OPEN。
   → **出題の好トラップ**（エラー無しのサイレント故障。debug でしか原因が見えない）。
2. **`ipv6 dhcp server <pool>` は 1 IF に 1 つ（2つ目は置換）**。複数 LAN をリレーで
   集約するサーバは **bare `ipv6 dhcp server`（automatic）＋プール側マッチ**
   （stateless=`link-address` 文 / stateful=`address prefix`）が正解。
   stateless プールの `link-address` 忘れ = LAN-A だけ DNS が来ないサイレント故障（TS ネタ）。
3. **automatic は直接接続クライアントの IA_PD（PD 要求）に応答しない**（SOLICIT 放置）。
   PD サーバは **named バインド（`ipv6 dhcp server POOL-PD`）必須**。Phase 2 は named 前提で設計。
4. **stateful DHCPv6 はデフォルト経路を配らない**（CLB の RIB に ::/0 無しを確認）。
   デフォルトは RA 由来 → クライアントは `ipv6 address autoconfig default` 併用が定石
   （no-autoconfig で A=0 でも **ND デフォルトは取得される**ことを実機確認。
   アドレスは DHCP・経路は RA という分担が綺麗に成立）。
5. **クライアントの再始動は `no ipv6 address dhcp`→再投入が確実**。
   `clear ipv6 dhcp client` は backoff 中だと再 SOLICIT しないことがある。
   shut/no shut は ADDR_SHUTDOWN→IDLE になり **次の RA まで再開しない**（RA 既定 200 秒
   → 検証時は `ipv6 nd ra interval 15` で加速可能）。採点は再始動に依存しない設計にする。
6. **`domain-name` は複数行＝追記**（ドメインサーチリスト）。値の変更は古い行の `no` が必要。
7. **IPv6-only IF の day0 admin-down（IOL 癖）再確認**: アドレス無しクライアント IF も同様
   → 実装時は problem.yml `bringup_data_ifs: true` 必須（OSPFv3 生成器と同じ）。
8. デバッグ観察の注意: 行プレフィクスは `IPv6 DHCP:`（`DHCPv6` では引っかからない）。
   リレー設定後に `IPv6 DHCP_BULK_LQ`（bulk lease query の TCP 547 リトライ失敗）が
   周期的にログを吐くが**無害**（誤診しないこと）。

## 採点 regex 素材（実機出力から確定）

| 対象 | show | 信号 |
|------|------|------|
| サーバ pool | `show ipv6 dhcp pool` | `Link-address prefix: 2001:DB8:A::/64` / `Address allocation prefix: 2001:DB8:B::/64 valid` / `DNS server: <v6>` / `Domain name: <name>` / stateful のみ `(N in use, M conflicts)`・`Active clients: N`（**stateless はカウントされない**→効果採点はクライアント側で） |
| サーバ binding | `show ipv6 dhcp binding` | stateful: `IA NA:` ＋ `Address: 2001:DB8:B:` / PD: `IA PD:` ＋ `Prefix: 2001:DB8:D000::/48` |
| リレー | `show ipv6 dhcp interface EtX` | `is in relay mode` / `Relay destinations:` ＋次行に宛先 |
| RA フラグ | `show ipv6 interface EtX` | O: `Hosts use stateless autoconfig for addresses.`＋`Hosts use DHCP to obtain other configuration.` / M: `Hosts use DHCP to obtain routable addresses.`（M 時 O 行なし） |
| クライアント状態 | `show ipv6 dhcp interface EtX` | `is in client mode` / `Address State is OPEN` / `Configuration parameters:` 配下 `DNS server:`・`Domain name:`・`Address: 2001:DB8:B:` |
| クライアント address | `show ipv6 interface brief EtX` | プレフィクス regex（`2001:DB8:A:` は EUI-64 由来 / `2001:DB8:B:` はランダム ID 由来。値は毎回変わる→**プレフィクスのみで判定**） |
| デフォルト経路 | `show ipv6 route ::/0` | `Known via "ND", distance 2` |
| PD（CPE 側） | `show ipv6 general-prefix` | `acquired via DHCP PD` ＋ `2001:DB8:D000::/48 Valid lifetime` |
| PD（委任経路） | サーバ `show ipv6 route static` | `S   2001:DB8:D000::/48` ＋ `via FE80::` |
| 負の要件 | `show ipv6 interface brief` | SLAAC 併存禁止＝ B:: 配下が 1 アドレスのみ（EUI-64 パターン `A8BB:CCFF` 不在でも判定可） |

## Phase 1 設計への反映（design.md 側に反映済みの要旨）

- サーバ要件は **automatic（bare `ipv6 dhcp server`）＋ stateless プールの `link-address`** を核に
  （「1 IF 1 プール」の置換挙動と合わせ、v4 の giaddr 選択との対比が教育核心）。
- LAN-B 要件に **no-autoconfig（純 stateful）** と **`autoconfig default` 併用のデフォルト取得**を追加。
- CLB 側課題に **`ipv6 enable` 罠**を残す（ヒント控えめ・debug で気付かせる）。
- 将来 TS 故障カタログ追加: `link_address_missing`（LAN-A だけ DNS 不達）/
  `autoconfig_not_suppressed`（アドレス2重）/ `server_pool_binding_wrong`（named で誤プール固定）/
  `ipv6_enable_missing`（SOLICIT 未送信・サイレント）。

## 再現手順

1. リース: `python3 topologies/mgmt_alloc.py allocate --repo . --problem POC-DHCPV6 --nodes RT01,RT02,CLA,CLB`
   （YAML は .14-.17 決め打ち。異なる IP が出たら YAML 側を合わせる）
2. 投入: virl2_client で `import_lab(poc-dhcpv6-iol-lab.yaml)` → `lab.start()` → SSH 開通 約2分
3. 起動後: 全データ IF を `no shutdown`（day0 admin-down 癖）
4. サーバ/リレー/クライアント設定はプローブ手順どおり SSH 投入（本 README の各節）
5. 撤収: stop/wipe/remove → `mgmt_alloc.py release --repo . --problem POC-DHCPV6`
