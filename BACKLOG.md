# BACKLOG — 実装したい課題の管理台帳

「今は見送るが、あとで実装したい」ものをここで一元管理する。

## 運用ルール

- 1行1件をテーブルに追記。詳細な設計メモがあるものは `problems/_drafts/*.design.md` に置きリンクする。
- **状態**: `未着手` → `PoC中` → `実装中` → `完了`（完了したら「完了アーカイブ」表へ移動）
- **優先**: `高` / `中` / `低`（着手したい順の目安）
- 着手時はこの表の状態を更新してから作業を始める。

## 課題一覧

| ID | 題名 | 分野 | 優先 | 状態 | 概要 / 詳細リンク |
|----|------|------|------|------|-------------------|
| BL-001 | GEN-AAAGRP: IOS AAA サーバグループ構築問（難4） | ENCOR/AAA | 高 | 未着手 | FreeRADIUS 2台を自動構築し、IOS側の named サーバグループ・非標準ポート・サーバ別キー・ローカルDBフォールバックを3フェーズ挙動採点（正常/片系断/全断）。→ [problems/_drafts/GEN-AAAGRP.design.md](problems/_drafts/GEN-AAAGRP.design.md) |
| BL-002 | BGP 残強化（confederation / IPv6 AF 等 Phase3 候補） | ENARSI/BGP | 中 | 未着手 | gen_bgp_complex_ts.py の Phase3 拡張候補。既存メモリ(ccnp-bgp-complex-gen)参照 |
| BL-003 | LAG（EtherChannel）問題 | ENCOR/L2 | 中 | 未着手 | 問題バックログ既知分。IOSvL2 前提 |
| BL-004 | 既存BGP問の AF 方式化バックログ | ENARSI/BGP | 低 | 未着手 | BGP は以後 AF 方式が標準（規約化済）。旧問の順次改修 |
| BL-005 | ENCOR-EIGRP-BUILD-01 要件7フィルタ強化 | ENCOR/EIGRP | 低 | 未着手 | RT03 のみ到達可へ絞る宿題 |
| BL-006 | DMVPN + IPsec 合体問 | ENARSI/VPN | 中 | 未着手 | sVTI×IKEv1/v2・crypto map 版は完成済。残りは DMVPN との合体 |
| BL-007 | Linuxサーバラボ次候補（BINDマスター/スレーブ・chrony+rsyslog・FRR） | Linux×NW | 低 | 未着手 | ゾーン転送/serial、EEM連携運用複合、FRRでLinuxをBGPピア化 |
| BL-008 | NETAUTO-04-NETCONF: ncclient で get-config/edit-config（難2-3） | 自動化/NETCONF | 高 | 未着手 | N3(RESTCONF)と同じ題材をXML+SSH(830)で対比。cat8000v×1。netconf-yang起動待ち・VRF越し830要実機確認 → [problems/_drafts/NETAUTO-DOJO.design.md](problems/_drafts/NETAUTO-DOJO.design.md) |
| BL-009 | NETAUTO-01-NETMIKO: Python+netmiko で show収集→設定投入（難1-2） | 自動化/Python | 中 | 未着手 | IOL 3台で軽い。★.venv に netmiko の pip 追加が前提作業 → 同設計メモ |
| BL-010 | NETAUTO-02-DATA: JSON/YAML/Jinja2 の読み書き（難1-2） | 自動化/データ | 中 | 未着手 | ラボ不要（オフライン・隙間時間向け）。生成物diff方式の採点は要設計 → 同設計メモ |
| BL-011 | NETAUTO-05-PYATS: pyATS/Genie で状態取得・差分検知（難3） | 自動化/検証 | 低 | 未着手 | 採点系のGenieを学習者側に降ろす。IOLで可 → 同設計メモ |

## 完了アーカイブ

| ID | 題名 | 完了日 | 備考 |
|----|------|--------|------|
