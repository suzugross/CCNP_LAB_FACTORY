# UM2-BUILD-01 ANSWER KEY（受講者非公開）

**模範解答（全文）= [poc/um2/poc-um2-lab.yaml](../../poc/um2/poc-um2-lab.yaml) の
各ノード configuration**（実機検証済み: 0点発射→solve投入→100/100収束・2026-07-11）。
`um2_ops.py solve` がこれをそのまま console 投入する。

## 採点実測

- 未構築（スケルトン直後）: **0/100**（複合チェック化により負の要件の空取り無し）
- 模範解答投入後: **100/100**（フェールオーバー同期約1分＋HSRP収束後）
- 既知の一過性: G1 はコールドスタートの ARP 解決チェーンで先頭数発落ちることが
  ある → 10発中7発以上で判定（採点2回目以降は10/10）

## 構築のポイント（機器別）

### L3SW1/L3SW2
- `vtp mode transparent` → VLAN 10/100/243/244/245/254 作成 → `ip routing`
  （★サーバセグメントは LB 配下のみ。VLAN 251 を L3SW に作る必要は無い）
- VRF: UNTRUST(Vlan10,243) / TRUST(Vlan244,100)。**SVI を作るのは 4 VLAN のみ**。
  245/254 に SVI を作ると FW/LB を迂回してゾーンが崩壊する（本設計の核心・減点対象）
- HSRPv2・1号機 110+preempt。Vlan243 のみ `standby 43 track 1 decrement 30`
  （track 1 = Gi0/0 line-protocol）。110-30=80 < 100 で Untrust だけ移る算数に注意
- ★ハマり処方箋: **SVI が up なのに HSRP が `Init (interface down)` のままの場合は
  SVI を shut/no shut**（IOSvL2 の癖。特にアクセスポートのみをメンバーに持つ
  Vlan10/Vlan100 で発生しやすい。受講者が対話設定した場合はほぼ出ない）

### FW1（プライマリ）
- 初回 enable でウィザード（8文字以上）→ CCNPccnp
- ワンアーム: Gi0/0 本体 no shut + サブIF .243(outside/0)/.244(inside/100)/.254(dmz/50)
- failover: unit primary / FOLINK=Gi0/1 / interface ip 172.31.245.254 standby .253 /
  key CCNPccnp / `failover`
- **`monitor-interface outside/inside/dmz` が R4 の要**（サブIFは既定 Not-Monitored。
  無いと腕リンク断で切り替わらず黒穴 — 実機実証済み）
- NAT: static 172.16.250.1⇔2.2.2.1（object NAT）・PAT 172.16.100.0/24→2.2.2.10
  （host オブジェクトへの dynamic = PAT）
- ACL は**実IP（172.16.250.1）宛**で書く（8.3+。マップIP 2.2.2.1 で書くと全落ち）
- `inspect icmp`（R8）・ルート4本・`prompt hostname priority state` 推奨

### FW2（セカンダリ）
- **failover 最小設定のみ**（Gi0/0,0/1 no shut + unit secondary + FOLINK 3行 + key +
  `failover`）→ 全設定が Active から自動複製される（hostname も FW1 になるのは正常）

### LB1/LB2（★書籍準拠のインライン形・2026-07-11 変更）
- 上流= Gi0/0 の dot1q サブIF（タグ254・ip nat outside）/ 下流= Gi0/1 物理IF
  （タグ無し・サーバセグメント・ip nat inside）
- HSRP: 上流 VIP 172.16.254.251（grp54）/ 下流 VIP 172.16.251.1（grp51・サーバGW）。
  LB1=110+preempt
- **VIP 終端 = `ip nat inside source static 172.16.251.101 172.16.250.1`**（両系同一）
- デフォルトルート → 172.16.254.254（FW dmz）
- **相互トラッキングは IP SLA reachability で行う**（R7 の要）:
  `ip sla 1 icmp-echo 172.16.254.254`（上流ヘルス）/ `ip sla 2 icmp-echo 172.16.251.101`
  （下流ヘルス）→ `track 10/20 ip sla N reachability` → grp51 が track10、grp54 が track20
  を decrement 30 で参照。
  ★**`track N interface ... line-protocol` では不成立**（実機実証）: CML の仮想リンクは
  対向側リンク断が伝播しないため、スイッチ側障害を line-protocol が検知できず
  「上流だけ LB2・下流は LB1」に割れて黒穴になる。IP SLA 方式なら上下が揃って切替
  （実測: 上流腕断→約20秒で両グループ LB2・inbound 10/10 無損失）。
  実LBのヘルスチェックに相当し、設計的にもこちらが正

## 完成条件5「実IP直宛が成立しない」の解説（考察課題の答え）

サーバ発の戻りパケットは LB の static NAT で**必ず送信元が VIP(172.16.250.1) に
変換される**。実IP(172.16.251.101)宛に張ったセッションは戻りのアドレスが一致せず
成立しない（FW のステートフル検査でも不一致）。= 「LB 配下のサーバは VIP 経由で
アクセスする」が設計上の正。実LB(routed mode+SNAT)と同じ挙動の再現。

## 障害デモ手順（operator 用・全て実機検証済み）

| デモ | 操作 | 期待挙動 |
|---|---|---|
| アップリンク障害（図2.4.11） | L3SW1 `int Gi0/0 → shut` | Vl243 のみ priority 80→L3SW2 Active。Trust 系は L3SW1 残留。通信無損失 |
| FW フェールオーバー | L3SW1 `int Gi0/1 → shut`（腕断） | monitor-interface 発動→ `Primary - Failed / Secondary - Active`。無損失 |
| 冗長喪失（潜在障害） | L3SW1 Gi0/3 `trunk allowed vlan remove 245` | **通信は正常のまま**・スプリットブレインも起きない（データIFハローで mate 検出）。`show failover` の精読で発見する系 |
| LB 切替 | L3SW1 `int Gi1/1 → shut`（上流腕断） | **SLA トラッキングで上下 HSRP が揃って LB2 へ**（約20秒）・inbound 10/10 無損失 |
| 切り戻し | 復旧後、HSRP は preempt で自動。ASA は手動 `failover active` | – |

## 運用メモ

- 採点: `um2_ops.py grade`（全ノード console 収集・約5分）。solve は検証専用
- FOLINK はローカルリンク up のままでも経路断があり得る（表示 `FOLINK (up)` を
  鵜呑みにしない）— 切り分けは `show failover history` と mate 状態
