# STP-SERIES — STP シリーズ設計 (BL-076・L2 空白の本丸)

- 起点: 2026-07-29 ユーザ指摘「本プロジェクトの弱点 = L2(STP)」→ 棚卸しで確定
  (STP 主役問ゼロ・CAMPUS-TS-01 の脇役のみ)。同日「CCIE ラボにも STP は出るか」
  → 出る(CCIE EI blueprint 1.x campus L2: Rapid-PVST+/MST・PortFast/BPDU guard/
  Root guard/Loop guard・priority/cost チューニング)。**この方針(CCIE の出方に整合)で準備**。

## 1. シリーズ構成(3段・実技先行)

| # | 問題 | 難 | CCIE での出方との対応 |
|---|------|----|----------------------|
| ① | ENCOR-STP-BUILD-01: root 配置設計 + 保護機能(3SW 三角×2VLAN・rapid-pvst 統一・VLAN 毎 root primary/secondary・access へ portfast+bpduguard・想定ブロックポートの検証) | 3 | Deploy 型(仕様どおり正確に組む) |
| ② | gen_stp_ts.py: STP TS 生成器(故障= root乗っ取り(priority)/trunk へ portfast/bpduguard 発火 err-disabled 放置/cost・port-priority 改変で意図しない経路/mode 不一致(pvst⇄rapid)/MST region 不一致) | 4-5 | Operate 型(大シナリオ内で静かに壊れる) |
| ③ | STP-MST-01: MST 設計問(region 名/revision/instance マッピング指定・仕様書完全準拠形・REDIST-POLICY/DHCPTS で確立した監査スタイル) | 4-5 | CCIE らしさの本丸(精密性トラップ) |

- プラットフォーム: **ioll2-xe ×3〜4・telnet 採点**(LAG 問で確立済のパス)。
  ioll2 profile: データ 15 ポート(Et0/0..Et3/2)・mgmt=Et3/3。
- 発展合流: CAMPUS-TS-01 への STP 故障軸追加 / LAG(BL-003)との複合。

## 2. 決定性の設計原則(採点が壊れないための約束)

- **bridge ID の MAC 依存を排除**: 全問で priority を明示配布(root 4096 / secondary 8192 /
  その他 32768)。tie-break が MAC に落ちる構成は作らない → ブロックポート位置が
  seed から決定的に導出できる。
- リンクコストは IOL Ethernet(10M)の既定 cost=100 で均一 → パス優劣は priority と
  ホップ数だけで決まる(cost 改変は故障側の道具)。
- 三角形が最小完全形(閉路がないと STP は無意味)。ノイズ拡張は arena 同様の接ぎ木。

## 3. 採点設計

- 構造: `show spanning-tree [vlan X]` を Genie 構造化(★PoC で IOL 出力の適合確認)
  → root bridge ID / 各ポートの role(Root/Desg/Altn)・state を find/match。
- 効果: SVI 間 ping + **「どのリンクが転送に使われているか」**(mac address-table /
  ブロックポートの state) — RIB が無い L2 では「転送パスの実効」をこれで代替。
- 保護機能: err-disabled 検出(`show interfaces status err-disabled`)・
  bpduguard/portfast の config 監査(regex)。
- 負の要件(例: 「SW03 が root になってはならない」)は正の root 確認とペアにする
  (既存教訓: 負の要件単独採点は偽陽性)。

## 4. PoC 項目(リスク3点+α)

| # | 確認 | 方法 |
|---|------|------|
| P1 | rapid-pvst の構文・動作・VLAN 毎 root 分離 | day0 焼き込み→show |
| P2 | ブロックポート位置の決定性(priority のみで固定できるか) | SW03 の per-VLAN ALTN 位置を机上予測→実機一致確認 |
| P3 | bpduguard → err-disabled の発火と検出コマンド | trunk 対向ポートに bpduguard を仕込み boot 時発火 |
| P4 | MST: region 設定(name/revision/instance map)・不一致時の boundary 挙動・是正後の合流 | telnet で mode 切替+region 投入 |
| P5 | Genie `show spanning-tree` パーサの IOL 出力適合 | 収集 stdout を grade.py 機構でオフラインパース |
| P6 | ioll2 の `spanning-tree portfast` 系構文(edge 形か旧形か) | 実機 ? 補完 |

**★PoC 実施済(2026-07-29)・P1〜P6 全クリア** → 結果と確定指紋は [poc/stp/README.md](../../poc/stp/README.md)。
要点: ①priority 明示でブロックポート完全決定化 ②bpduguard/err-disabled 採点可 ③MST 不一致指紋= `Bound(RSTP)` ④Genie 両モード適合 ⑤**旧構文 `spanning-tree portfast`(edge 不可)** ⑥**必須設計規則= データ trunk の allowed vlan 絞りで mgmt VLAN999 を演習 STP から隔離**(さもないと mgmt 断・実測済) ⑦config 投入は pexpect 直叩き(プロンプト regex 確立)。
PoC ラボ `problems/_POC-STP` は再利用可。**→ 準備完了。次は §5 手順2(①構築問)から即着手できる。**

## 5. 実装順(着手時)

1. PoC(上記・半日未満) → 2. ①構築問(1セッション・実機フルサイクル) →
3. ②生成器(故障カタログは PoC 知見で確定) → 4. ③MST 設計問。
