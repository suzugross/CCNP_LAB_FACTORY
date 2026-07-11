# FGT-SDWAN-01 設計メモ（BL-046・体感構築ラボ）

2026-07-11 起草。ユーザ要望「受験者が可能な限り、理解を深めながら構築を進める
ことができる体験型ラボ」。QoS 体感シリーズ（数値で見る→対策で救う）の SD-WAN 版。

## コンセプト: 段階構築 × 観察チェックポイント

従来の「仕様書どおり組んで最後に採点」ではなく、**フェーズごとに
『観察 → 記録 → 考察 → 次の設定』を繰り返す**構成にする。task.md には各フェーズに
📋観察チェックポイント（打つべき diagnose コマンドと見るべき数値）と
🤔考察課題（答えは採点後レビューで開示）を埋め込む。

## トポロジ（6 VM + ext-conn）

```
USER-PC(alpine) ── port4 [FGT] port1 ──(WAN1/203.0.113.0/30)── ISP1(iosv) ──┐
    172.16.20.0/24        │   port2 ──(WAN2/203.0.114.0/30)── ISP2(iosv) ──┤
                          │                       10.11.0.0/30・10.12.0.0/30│
              port3=GUI(System Bridge・mgmt_alloc)                      [INET](iosv)
                                                                            │
                                                              SRV(alpine) 198.51.100.0/24
```

- FGT: port1=WAN1(.2) / port2=WAN2(.2) / port3=GUI(10.1.10.x) / port4=LAN(172.16.20.1)
- ISP1: Gi0/0=203.0.113.1 / Gi0/1=10.11.0.1↔INET
- ISP2: Gi0/0=203.0.114.1 / Gi0/1=10.12.0.1↔INET
- INET: Gi0/0=10.11.0.2 / Gi0/1=10.12.0.2 / Gi0/2=198.51.100.1(サーバセグメント)
- SRV: 198.51.100.100（httpd「SDWAN LAB SERVER」・SLAプローブ先も=エンドツーエンド計測）
- FGT ポリシーは **NAT enable**（選択された WAN の IP に SNAT → 戻りが同一 ISP を
  通る＝経路対称・切替時も自然）。ISP/INET は /30 とサーバセグメントの静的のみ

## 学習フェーズ設計（task.md の骨格）

| Phase | 構築内容 | 📋観察チェックポイント | 🤔考察 |
|---|---|---|---|
| 1 | WAN×2 のIF・個別静的ルート・LAN・通常ポリシー(NAT) | ECMP時のセッション分布 `diagnose sys session list` | 静的2本だけだと何が困る?(品質を見ない) |
| 2 | SD-WAN zone/member 化（既存staticを置換） | `diagnose sys sdwan member` | zone化でポリシーのIF指定はどう変わる? |
| 3 | Performance SLA（icmp→SRV・latency/loss閾値） | `diagnose sys sdwan health-check status` で**素の遅延を記録**(基準値) | プローブはどのIFから何本出ている? |
| 4 | SD-WAN rule（mode sla: WAN1優先・SLA違反でWAN2） | `diagnose sys sdwan service` でrule状態とメンバー順位 | rule無しの既定動作(implicit)との違いは? |
| 5 | **体感**: operator が WAN1 に遅延/ロス注入 | SLA数値悪化→違反検知→**pingを流したままメンバー切替**→復帰 | なぜ既存セッションが切れない? 閾値はどう決める? |

- Phase 5 は operator（出題側）が sdwan_ops.py inject/restore で CML リンク
  コンディショニングを操作。受験者は観察と切り分けに専念
- GUI（Network > SD-WAN の SLA グラフ）も観察対象に含める（体感の主役）

## 採点設計（100点・console 収集）

- 機能: client→SRV HTTP 到達(VIA sdwan)・SLA 両メンバー alive・rule のメンバー選択
- 状態/設定: zone にメンバー2・health-check 定義(server=198.51.100.100)・
  rule の mode sla・ポリシーが sdwan zone を srcintf/dstintf に使用・NAT enable
- **効果採点**（QoS規約流用）: 劣化注入状態で ①切替後メンバー=WAN2 ②client ping
  無損失(10発≥8) の複合チェック → grade 時に ops が注入→採点→復元
- 0点発射チェック必須

## ★PoC 結果（2026-07-11 実機・フルサイクル完遂）

**核心サイクル全実証**: 平常(両WAN latency1.6ms・port1選択) → WAN1に250ms/loss3%注入
→ **20秒でport1=dead判定・port2へ自動切替** → 劣化解除後も loss移動窓が残る間は
port2維持(慎重なフェイルバック=考察課題の宝) → 窓クリア後 **port1へ自動復帰**。
クライアント連続ping **80発中78受信(切替瞬間の2発のみ損失)**。

### ★確定した制約（トポロジ設計を支配）

1. **eval ライセンスは「設定可能インターフェース総数3個」の絶対キャップ**
   （4本目の物理NICはQEMUレベルで非認識・VLANサブIF/loopbackの追加も
   `object set operator error, -4` で拒否）→ **port1=WAN1 / port2=WAN2 /
   port3=LAN兼管理GUI** の3IF構成が唯一解。クライアント(pcA)は port3 と同一
   セグメント(10.1.10.0/24・mgmt_alloc で FGT=.11 / PCA=.12 の2リース)
2. **稼働中のCMLリンク抜去は vNIC ごと喪失**（ゲスト再起動でも戻らない・
   CML側 stop→start でのみ再注入）→ 配線替えは必ずノード停止後
3. health-check 名に **ハイフン不可**（`SLA-SRV`→reserved エラー。`SLASRV` に）
4. 確認コマンドは `diagnose sys sdwan service4`（`service` は ambiguous）
5. wipe=ライセンス消失。**本ラボは fgt1 を wipe しない**（buildは config 初期化
   方式: 全設定を CLI で巻き戻し → sdwan_ops.py に unbuild 実装）

### 検証済み構文（7.6.3・そのまま模範解答の種）

- IF: port1 203.0.113.2/30・port2 203.0.114.2/30・port3 10.1.10.11/24(+https)
- sdwan: `set status enable` / members 1=port1 gw .113.1, 2=port2 gw .114.1 /
  health-check SLASRV: server 198.51.100.100, protocol ping, interval 1000,
  members 1 2, sla 1 (latency-threshold 100, packetloss-threshold 5,
  link-cost-factor latency packet-loss)
- service 1 TOSRV: mode sla, sla SLASRV id 1, priority-members 1 2, src/dst all
- route: `config router static / edit 1 / set sdwan-zone virtual-wan-link`
- policy: srcintf port3 / dstintf virtual-wan-link / nat enable
- 注入: virl2 `link.set_condition(bandwidth=10000, latency=250, jitter=10,
  loss=3.0)` / 復旧 `link.remove_condition()`（ライブ適用可・即効）

## 出題形態

- UM2 同様 build 形式＋操作は console/GUI 併用。難度3-4（体験価値が主目的）。
  ENCOR Describe レベルの底上げ教材。トポロジ: FGT+ISP1+ISP2+INET+pcA+pcB+SW3
  +System Bridge（6VM）。据付=ISP/INET/pcA/pcB、受講者スコープ=FGT のみ
