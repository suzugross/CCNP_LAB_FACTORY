# DMVPN 完全版 設計メモ — baseline構築問 + gen_dmvpn_ts.py（Phase 3 + IKEv2）

状態: **PoC 完了・実装待ち**（BL-006）/ 起案 2026-07-09 / 同日 TS 生成器方式に再設計・同日 PoC 完了
PoC 結果詳細: [poc/dmvpn-ipsec/README.md](../../poc/dmvpn-ipsec/README.md)
（baseline day0 一発成立・全故障シグネチャ実機確定・PoC ラボ yaml = 模範解答 config）

## 方針（2026-07-09 更新）

**主役は TS 生成器 `gen_dmvpn_ts.py`**。DMVPN は故障レイヤが 7 層
（underlay→GRE→NHRP→IPsec→ルーティング→Phase3→MTU）に積み重なる、リポ内でも
最良の切り分け題材であり、構築問より学習効果が高い（ユーザ提案に同意）。

ただし**構築問（完全版）も“ほぼ無料の副産物”として両取り**する:
- 生成器のベースライン config ＝ 構築問の模範解答。どのみち実機で組んで検証する。
- 修復判定チェック群 ＝ 構築問の採点チェック群（1 つの採点設計が両方で動く）。

## IKE バージョンの決定 = IKEv2

- 公式ブループリント 300-410 v1.1 の該当項目は
  **2.3 Configure and verify DMVPN (single hub)** — 2.3.a GRE/mGRE / 2.3.b NHRP /
  **2.3.c IPsec** / 2.3.d Dynamic neighbor / 2.3.e Spoke-to-spoke。
  **IKE のバージョン指定は無い**（ブループリント全文に IKEv1/IKEv2 の語は登場しない）。
- ENARSI 公式教科書（OCG）**Ch.20 "Securing DMVPN Tunnels"** は
  `crypto ikev2 keyring → ikev2 profile → transform-set(mode transport) →
  ipsec profile → tunnel protection` の **IKEv2 構成**で解説 = 試験対策上の標準。
- リポ住み分け: IKEv1 は ENARSI-IPSEC-VTI-01 / ENARSI-GREIPSEC-MAP-01 で既カバー。
  ENARSI-IPSEC-IKEV2-01 のオブジェクト連鎖を mGRE に載せ替える（solution.md
  「発展: DMVPN への流用」の回収）。

## ベースライン（= DMVPN-PHASE3-01 トポロジ + IKEv2 暗号 + MTU 対策）

- RT01=Hub(NHS) / RT02=Spoke1 / RT03=Spoke2 / RT04=WAN トランジット（変更禁止）
- underlay /30（10.0.14.0/10.0.24.0/10.0.34.0）・overlay Tunnel0 10.255.0.0/24
- EIGRP AS100・NHRP network-id 1 / 認証 DMVPNKEY・Phase 3（redirect/shortcut）
- IKEv2: NGE スイート（AES-GCM-256/PRF SHA384/DH19）・**wildcard keyring**
  （`address 0.0.0.0 0.0.0.0`、spoke-spoke の対向 NBMA が事前不定のため必須）・
  `match identity remote address 0.0.0.0`・ESP **transport mode**・全拠点共通 PSK 1 本
- `ip mtu 1400` + `ip tcp adjust-mss 1360`（3 拠点 Tunnel0）
- `image_family: iosv`・`access: console`（DMVPN 系のコンソール採点実績を踏襲）

## 故障カタログ精査（2026-07-09 ユーザ提案 7 分類の技術検証）

### Tier 1 — 採用（決定的・症状が相互に差別化される）12 種

| # | fault キー案 | 注入 | 期待症状（切り分けの核心） | 難 |
|---|-------------|------|--------------------------|----|
| 1 | `u1_underlay_route_missing` | spoke の default route 削除 | tunnel は up/up のまま IKE/NHRP 全滅。最下層が上位全部を隠す（chainTS の系譜） | 3 |
| 2 | `g1_spoke_p2p_gre` | spoke を `tunnel destination` 静的 + p2p GRE に | hub 経由は全部通る。**spoke-spoke 直行だけ永久に張れない** | 4 |
| 3 | `g2_tunnel_key_mismatch` | 片 spoke だけ `tunnel key` 違い | GRE 受信破棄 → その spoke だけ登録不可（サイレント） | 4 |
| 4 | `n1_nhs_map_wrong` | spoke の NHS/静的 map の NBMA 誤り | 登録先不達。show ip nhrp nhs で気づけるか | 3 |
| 5 | `n2_nhrp_auth_mismatch` | NHRP 認証キー不一致 | 登録拒否・show dmvpn 空・**debug nhrp でのみ明示**（サイレント故障枠） | 4 |
| 6 | `n3_multicast_dynamic_missing` | hub の `ip nhrp map multicast dynamic` 削除 | ★差別化最良: **show dmvpn は 2 spokes UP なのに EIGRP neighbor 0**（NHRP と ルーティングの層分離を強制） | 4 |
| 7 | `i1_psk_mismatch` | 片 spoke の PSK 違い | IKEv2 SA 不成立 → NHRP も上がらない（crypto が NHRP より先) | 3 |
| 8 | `i2_transform_mismatch` | 片 spoke の ESP スイート違い | **IKEv2 SA は READY・Child SA だけ失敗** → IKE/IPsec の層切り分け | 4 |
| 9 | `i3_keyring_perpeer` | wildcard を hub アドレス限定 keyring に | **hub-spoke は正常・spoke-spoke の IKE だけ失敗**（構築問の核心罠を TS 化。トラフィックは hub 折返しで通り続けるのが嫌らしい） | 5 |
| 10 | `i4_protection_missing_spoke` | 片 spoke の `tunnel protection` 削除 | その spoke だけ登録不可（hub は暗号必須なので平文 GRE を破棄）。もう片方は正常 | 3 |
| 11 | `r1_split_horizon_on` | hub で `ip split-horizon eigrp 100` 再有効化 | 隣接は全部 UP・**spoke 同士の経路だけ消える**（最頻出・定番） | 3 |
| 12 | `p1_redirect_missing` / `p2_shortcut_missing` | hub redirect / spoke shortcut 削除 | **全到達 OK なのに永久 hub 経由**（ping 誘発→動的エントリ不在で判定。「通るのに要件不達」型） | 4 |

### Tier 2 — PoC で採否確定（2026-07-09 実機・詳細= poc/dmvpn-ipsec/README.md）

- `i5_protection_missing_all`（全拠点平文）: **全部動いてしまう純データプレーン故障**。
  ★uRPF で確立した「既存 TS 生成器はデータプレーン故障検出不能」知見の適用第 1 号。
  判定は `show dmvpn`（Crypt 列）/ `show crypto ipsec sa` 不在で可能な見込み（未実測・
  片側欠落は実証済なので低リスク）。
- `i6_mode_tunnel`（transport→tunnel）: ✅**実機確定**: 不一致時は両端 **Tunnel mode に
  合意して通信継続**（hub 側 sa も `{Tunnel,}` に変わる）。「動くが仕様違反・+20B」型
  → 効果採点（`in use settings ={Transport,` 判定）でのみ採用。
- `m1_ip_mtu_missing`: ❌**TS 故障不成立を実機確定**: 実効境界 1472、1401-1472 の
  DF ping が外側 GRE 断片化で通ってしまう（DF は外側非複製）。→ **構築問の要件に格下げ**
  （run 判定＋ df-bit ping ペア: 正常時 1400 通過/1401 破棄が決定的に取れる）。
- `u2_tunnel_source_wrong`: wildcard keyring だと**別 source からでも普通に動く**
  可能性 → source IF shutdown 系に変えるか、実装時に症状確定（未実測）。

### PoC で実機確定した追加シグネチャ（採点設計に直結）

- `show dmvpn` の **State/Attrb 列が故障の主判定**: 正常 `UP/S,D,DT1,DT2` /
  GRE・NHRP 層の不達 `NHRP` / IPsec 不成立 `IKE`+`IX` / socket 無し `DX`。
- **i3 (per-peer keyring)** = hub-spoke 完全正常・spoke間 ping も 100% 通り続ける
  （永久ハブ折返し）・`IX`+`DX` ペア・spoke間 IKEv2 SA 無し → 難5本命で確定。
- **g1 (p2p GRE)** = 対向スポーク側に `UNKNOWN <tunnel IP> IKE never IX` の残骸。
- **g2 (tunnel key)** = IKEv2 READY のまま State `NHRP` 固着（IKE/GRE の層分離）。
- **n2 (NHRP 認証)** = 完全サイレント（`debug nhrp error` にも出ない）。
  ★故障は day0 注入が原則: 稼働中注入は hub 旧キャッシュで「動いて見える」。

### 不採用（ユーザ案のうち技術的に TS 故障として成立しないもの）

- **network-id 不一致**: NHRP network-id は**ローカル有意でワイヤに乗らない**ため、
  hub/spoke で違っていても登録は成立する見込み（= 壊すつもりが壊れない）。
  PoC で確認の上、成立しなければ「疑わしく見えるが正常」のデコイとして解説行き。
- **holdtime 極短**: フラップ型 = 症状がタイミング依存で非決定的。採点再現性の
  リポ方針に反するため除外。
- **Phase 2 系**（hub の no next-hop-self 忘れ・Phase2 でのサマリ投入）: ベースラインが
  Phase 3 のため対象外。将来 `--phase 2` 軸で回収（DMVPN-POC-01 と整合）。
  なお **Phase 3 では hub のサマリはむしろ推奨機能**であり故障にならない点は解説ネタ。
- **fragmentation before-encrypt / df-bit clear**: IOSv での再現・採点安定性が低い。
  解説での言及に留める。

## 採点設計（修復判定 = 構築問と共通の 9 チェック・100 点・0 点発射込み）

| # | 観点 | 方法 |
|---|------|------|
| 1 | Hub `show dmvpn`: スポーク 2 登録 UP | raw |
| 2 | Hub `show crypto ikev2 sa`: 2 本 READY | raw（IKEV2-01 実績） |
| 3 | 実効スイート AES-GCM-256/SHA384/DH19 | `show crypto ikev2 sa detailed` raw |
| 4 | ESP **transport mode** | `show crypto ipsec sa` raw（`Transport,`） |
| 5 | EIGRP で全 Loopback 相互学習・hub↔spoke 到達 | 既存 DMVPN 問流用 |
| 6 | Phase 3: spoke間 ping 誘発 → 動的エントリ UP | PHASE3-01 の能動 ping 方式流用 |
| 7 | spoke 間 IKEv2 SA が動的に確立 | raw |
| 8 | spoke-spoke IPsec SA の encaps/decaps 増加 | ping 前後カウンタ比較 |
| 9 | Tunnel0 ip mtu 1400 / adjust-mss 1360 | run 判定 |

- 負の要件を単独採点しない（QoS 教訓）— #7/#8 は正の観測で判定。
- 0 点発射チェック（誘発 ping）をカウンタ判定より前に置く（uRPF イディオム）。

## 実装ステップ

1. ~~**PoC（poc/dmvpn-ipsec/）**~~ ✅ **完了 (2026-07-09)**: baseline day0 一発成立・
   要検証 5 点＋ボーナス 3 故障（g2/n2/i4）まで実機確定。
   network-id 不一致=非故障・MTU=構築要件格下げ・mode 齟齬=効果採点型で確定。
2. ~~**ENARSI-DMVPN-IPSEC-01（構築問）**~~ ✅ **完了 (2026-07-09)**: 実機フルサイクル済
   （0点発射 0/100 → 模範解答 100/100）。13 チェック・設定仕様書形式 task。
3. ~~**gen_dmvpn_ts.py（topologies/）**~~ ✅ **完了 (2026-07-09)**: 12 故障で確定。
   実機サイクル: n2(35→fix→100)・i3(70→fix→100)・r1(45→100)・p1(ライブ実証)。他 8 故障は
   PoC で症状実証済（出題前に実機 1 サイクル推奨）。
4. ✅ **ユーザ実戦由来の故障 2 種を追加 (2026-07-10・計 14 故障)**。いずれも実機フルサイクル済:
   - `n4_multicast_map_tunnelip`（難4）: victim spoke を旧来 3 行構文にし
     `ip nhrp map multicast` の複製先を**トンネル IP に誤記**（ユーザが構築問で実際に
     踏んだ事故）。ユニキャスト(登録/IKE)全部正常・EIGRP 隣接だけ retry limit フラップ。
     実機 45→fix→100。n2(登録も死ぬ・35点) との差分プロファイルが切り分け教材。
   - `r2_underlay_in_eigrp`（難4）: hub の EIGRP をクラスフル `network 10.0.0.0` にし
     underlay まで広告 → スポークが**ハブの NBMA をトンネル経由で再帰学習**。
     実機 60→fix→100。★mGRE では `%TUN-5-RECURDOWN` は**出ない**（p2p GRE 専用）。
     実機の指紋 = **約 15 秒周期の EIGRP "Peer Termination received" フラップ** ＋
     `show ip route <hub NBMA>` が `via Tunnel0`（トンネルの出口がトンネルの中）。

## ★実装フェーズで発見した追加の実機知見 (GEN-DMVPN-7801, 2026-07-09)

- **`ip nhrp authentication` は最大 8 文字**。9 文字以上は day0 パースで黙って拒否され
  故障ごと蒸発する（PoC の DMVPNKEY はちょうど 8 字で偶然セーフだった）。
  生成器は 6 字ワード＋2 桁で必ず 8 字に。n2 の誤キーも「同長 8 字の末尾 2 桁スワップ」方式。
- **IOSv 15.9 では `ip nhrp map multicast dynamic`(hub) と `ip nhrp shortcut`(spoke) は
  暗黙デフォルト**（run 非表示・省略しても動作する）→ 故障候補 n3/p2 は非故障のため
  カタログから削除（14→12 故障）。`ip nhrp redirect` は非デフォルトで p1 は真の故障
  （ライブ実証: redirect 除去→永久ハブ経由・shortcut 空・復元で即 DT1/DT2）。
- **`show dmvpn` の State 列は DX/IX 残骸でも `UP` を表示**する → 動的直結の採点は
  State だけでなく **Attrb 列 `D(T[12])?(?!\w)`** まで正規表現で拘束（DX/IX を排除）。
  構築問 grading.yml と生成器の両方に適用済み。

## 変種・発展（実装後に BACKLOG 化）

- `--phase 2` 軸（next-hop-self/サマリ故障の回収）・IKEv1 変種・FVRF 版（CCIE 寄り）
- IPv6 オーバーレイ軸は BL-037 と合流
