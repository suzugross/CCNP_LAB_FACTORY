# PoC: IPv6 First-Hop Security on ioll2-xe — BL-146 準備 (2026-09-03 実施・全項目クリア)

ラボ: CML `POC-FHS`(4 ノード・**2026-09-05 削除済**・必要なら `poc_ops.py import` → `start` で再作成)
= SWB(**ioll2-xe 17.15.1**・VLAN10 アクセス×3) / RT02(正規GW: RA Medium+O flag+stateless DHCPv6 `example.net`) /
CLB(`ipv6 address autoconfig default`) / ROG(不正: RA **High**+偽 `2001:DB8:33:BAD::/64`+不正 DHCPv6 `evil.example`)。
コンソール収集のみ(`poc/redist-mp-loop/poc_console.py --title POC-FHS`)。
★CVAC 罠: IP 無し IF(CLB/ROG/RT02 Et0/0)は admin-down 起動 → コンソールで no shutdown。

## 結果サマリ(全て ✅)

| # | 項目 | 結果 |
|---|------|------|
| P0 | 基線(FHS なし) | CLB= ルータ2件(ROG=High が既定GW)・偽 GUA 付与・DHCPv6 情報は **ROG 勝ち**(DNS BAD::53 / evil.example) |
| P1 | CLI 実装 | `ipv6 nd raguard policy` / `ipv6 dhcp guard policy` / `device-tracking policy` / `ipv6 source-guard policy` 全て存在。**旧 `ipv6 snooping` は無い**(17.x は SISF=device-tracking に統合) |
| P2 | RA Guard(ポート role) | HOST を Et0/1,0/2・ROUTER を Et0/0 に attach → CLB は **RT02 のみ**・偽 GUA 消滅。カウンタ= `show device-tracking counters interface Et0/2` の Dropped `RA guard: NDP RA [n] reason: Message unauthorized on port` |
| P3 | DHCPv6 Guard | CLIENTS(role client) を Et0/2 → ROG の REPLY が落ち CLB は RT02 の DNS/ドメインを取得。カウンタ= `DHCP Guard: DHCPv6 REP [n] reason: Message type is not authorized by the policy on this port, device-role mismatch` |
| P4 | device-tracking(バインディング表) | `device-tracking policy TRACK`(security-level guard 既定)を `vlan configuration 10` に attach → `show device-tracking database` に ND 由来 4 件(LL×3+CLB GUA・Et/vlan/REACHABLE) |
| P5 | ★VLAN スコープ罠 | HOST ポリシーを **vlan configuration 10 に attach**(ポート側なし)→ **正規 GW の RA も落ちる**(Et0/0 Dropped RA・CLB は LL のみ)。=「守り過ぎ」故障の素材 |
| P6 | ポート>VLAN 優先 | 上記に Et0/0 だけ ROUTER を port attach → RT02 RA 通過・ROG は VLAN HOST で引き続き遮断。**ポートポリシーが VLAN ポリシーに勝つ** |
| P7 | 代替解 | `router-preference maximum medium`(role router)を VLAN attach → ROG(High)だけ落ち RT02(Medium)通過。Dropped 理由= `Preference flag error` |

## RA guard ポリシー副モードの選択肢(17.15.1 実測)
`device-role {host|router|monitor|switch}` / `hop-limit {min|max}` / `managed-config-flag {on|off}` / `other-config-flag {on|off}` /
`match ra prefix-list` / `match ipv6 access-list` / `router-preference maximum {low|medium|high}` / `trusted-port`。
DHCP guard= `device-role {client|server}` / `trusted-port`。source-guard= `deny|permit|trusted|validate`。
`show running-config` は既定値(device-role host / security-level guard)を**表示しない**=採点は show policy 側で。

## 作問への含意(BL-146 ラボ側)
- **ioll2-xe で FHS 三種(RA Guard/DHCPv6 Guard/device-tracking)が完全動作**。source-guard は未検証(バインディング表は取れているので成立見込み)。
- 盤面= gen_v6addr_ts `--board rogue` の SWB を **非管理→ioll2 管理スイッチ(target_nodes 入り)**に置換すれば 8 ノード(RT01/RT02/CLA/CLB/ROG/SWB+MGMTSW+EXTC)。
  採点は `access: telnet`(ioll2 は SSH 不可)＋ IOL ルータの initial に `line vty 0 4 / transport input ssh telnet` を追記(baseline は ssh のみ)。
- 故障候補(TS 形)= 未適用(素の rogue)/ VLAN スコープ over-block(P5) / role 逆(ROUTER を端末ポート・HOST を GW ポート) / DHCP guard の role client を GW ポートに(正規 DHCPv6 遮断) / trusted-port 不在 / router-preference 上限が正規より低い / match prefix-list 誤り。
- 構築形(要件で顔が変わる)= 「ROG に触れない」制約下で ①ポート role 方式 ②VLAN+pref 上限方式 ③prefix-list 一致方式 のどれを要求するか。
