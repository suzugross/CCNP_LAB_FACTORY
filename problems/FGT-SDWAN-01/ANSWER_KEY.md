# FGT-SDWAN-01 ANSWER KEY（受講者非公開）

**模範解答（全文）= [poc/fortigate/golden-sdwan-fgt.cfg](../../poc/fortigate/golden-sdwan-fgt.cfg)**
（FortiOS 7.6.3 実機検証済 2026-07-11・`sdwan_ops.py solve` がそのまま投入）。
設計・PoC 全記録= [problems/_drafts/FGT-SDWAN.design.md](../_drafts/FGT-SDWAN.design.md)。

## 採点実測（PoC 時・パックとしてのフルサイクルは grade 実行記録参照）

- 効果採点の実測: 劣化注入 **20秒で port1=dead → port2 切替**・クライアント
  連続 ping **78/80**（切替瞬間の2発のみ）・回復後 loss 移動窓クリアで自動復帰
- grade は3段階（平常 → 注入35秒後 → 復旧後リトライ最大4分）で全自動

## 考察課題の答え

- **考察1**: ①デフォルトルート（この段階では未設定）②ファイアウォールポリシー
  （FGT は許可ポリシーが無い限り転送しない）
- **考察2-1**: ゾーン指定ならメンバー追加（3本目の回線）時にポリシーを触らずに
  済む。IF 個別指定はポリシー爆発の元（ASA/IOS の ACL 運用と同じ悩みの解）
- **考察2-2**: この時点では ECMP（等コスト分散）。品質は一切見ていない —
  「切れない限り使い続ける」= 遅い回線に当たったユーザは不幸のまま
- **考察3**: interval 1000ms・**メンバー両方の IF から各1本**（source は各 WAN の
  自 IP）。実サーバ宛てにする意味= ISP GW までではなく**エンドツーエンドの品質**を
  測る（ISP 内部や先方側の劣化も検知できる）
- **考察4**: 基準値 ~1.6ms の約60倍。閾値を基準値近くにすると通常の揺らぎで
  SLA 違反が頻発しフラッピングする（閾値は「業務が痛む値」から逆算する）
- **考察5-1**: ルーティング収束と違い、FGT は**両経路とも常に生きている**前提で
  セッションテーブルの出口だけ差し替える（NAT 併用で戻りも追従）。dead 判定
  （プローブ数発分・数秒）だけが空白になる
- **考察5-2**: packet-loss は**プローブ履歴の移動窓**で計算されるため、劣化が
  消えても窓から過去のロスが抜けるまで SLA 違反が続く。これが**フェイルバックの
  ダンピング**として働き、瞬間回復→再劣化を繰り返す回線でのフラッピングを防ぐ

## 実機の落とし穴（受講者がハマったら）

| 症状 | 原因/処方 |
|---|---|
| health-check 名で parse error | **名前にハイフン不可**（SLA-SRV→×・SLASRV→○） |
| `edit LAN20` 等の新規 IF が `-4 discard` | ★**eval ライセンスは IF 総数3個の絶対上限**（VLAN/loopback も不可）。本ラボは3IFで完結する設計 |
| `diagnose sys sdwan service` が ambiguous | `service4`（IPv4）が正 |
| member 追加で「in use」系エラー | 対象 IF がポリシー/静的ルートから参照中。先に参照を外す（Phase 順に組めば当たらない） |
| ログインできない（正しいPWなのに） | 3連続失敗で**60秒ロックアウト**。待ってから1回ずつ |
| 設定が全部消えた | `execute factoryreset` 禁止（**ライセンス消失**→README の再アクティベーション手順） |

## operator 手順

```bash
PY=.venv/bin/python3
$PY topologies/sdwan_ops.py build     # 受講者向け初期化(FGTのSD-WAN/WAN設定を巻き戻し)
$PY topologies/sdwan_ops.py grade     # 3段階採点(劣化注入・復旧込み全自動・約8分)
$PY topologies/sdwan_ops.py inject    # Phase5 の体感デモ用(手動劣化)
$PY topologies/sdwan_ops.py restore   # 劣化解除
$PY topologies/sdwan_ops.py solve     # 検証用: 模範解答投入
$PY topologies/sdwan_ops.py stop      # 停止(destroy は無い: ライセンス保全)
```

- **fgt1 は絶対に wipe しない**（eval ライセンス消失）。ラボ削除してしまった場合:
  fgt-sdwan-lab.yaml を import → README の再アクティベーション手順
  （FortiCloud 旧機器削除 → account-id/password → GUI ログイン）
- Phase 5 のデモは inject → 受講者観察（2〜3分）→ restore → フェイルバック
  観察（1〜3分）の流れ。grade でも同じサイクルが自動実行される
