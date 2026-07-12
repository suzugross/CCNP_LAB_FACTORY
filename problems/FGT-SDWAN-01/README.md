# FGT-SDWAN-01 運用ガイド（受講者非公開）

FortiGate SD-WAN の体験型構築ラボ（BL-046）。受講者スコープ= fgt1 のみ。
劣化→検知→自動迂回→復帰のライフサイクルを CML リンクコンディショニングで体感させる。

## 操作

```bash
PY=.venv/bin/python3
$PY topologies/sdwan_ops.py build    # 受講者向け初期化(SD-WAN/WAN設定の巻き戻し・wipeしない)
#   → problems/FGT-SDWAN-01/task.md を提示(チャットにも全文貼付)
$PY topologies/sdwan_ops.py inject   # Phase5 体感デモ: WAN1 に 250ms/loss3% 注入
$PY topologies/sdwan_ops.py restore  # 劣化解除
$PY topologies/sdwan_ops.py grade    # 3段階採点(注入→復旧も自動・約8分)
$PY topologies/sdwan_ops.py solve    # 検証用: 模範解答投入
$PY topologies/sdwan_ops.py status | stop
```

## ★ライセンス運用（最重要）

- fgt1 は **eval ライセンス済み**（S/N FGVMEVS16KSRTP62・IF 3個上限・1vCPU/2GB）
- **wipe / factoryreset / ラボ削除 = ライセンス消失**。destroy verb は意図的に無い
- 消失時の再アクティベーション: ①FortiCloud で旧トライアル機器を削除
  ②fgt-lab.yaml を import・ext-conn NAT を一時接続 ③CLI で
  `execute vm-license-options account-id/password`（ユーザ自身が console 投入）
  ④GUI → FortiCloud 認証 → 自動アクティベート ⑤`execute vm-license-options reset`
  詳細= [problems/_drafts/FGT-SDWAN.design.md](../_drafts/FGT-SDWAN.design.md) /
  メモリ ccnp-fortigate

## 構成メモ

- CML ラボ名= **FGT-LAB**（BL-047 で改名・FGT問題シリーズ共用。port2 経路に
  無管理 SW2 と dmz1 を追加したが L2 透過で本問無影響 — 改修後フル回帰 100/100 済）。
  **FGT-FW-BASIC-01 と fgt1 を共用**: どちらの build ももう一方の設定を巻き戻す
- pcA/pcB/dmz1/pcC は day0 で IP/httpd 焼き込み済み（2026-07-12 修正）→ 再起動で自己復旧
- BL-048 で支社サイト増設（INET Gi0/3 — RBR — pcC・FGT-IPSEC-01 用・本問無関係）
- 6 VM + SW/bridge: fgt1 / ISP1 / ISP2 / INET (iosv) / pcA(USER-PC) / pcB(SRV)
- LAN 兼管理= 10.1.10.0/24（mgmt_alloc リース: FGT1=.11 / PCA=.12・
  problem=FGT-SDWAN-01 で台帳登録済み）
- 劣化注入は CML link conditioning（fgt1 port1↔ISP1 リンク）。ops が管理
- 採点実測: 効果チェック込みで全自動（E3 フェイルバックは loss 移動窓のため
  最大4分リトライ）
