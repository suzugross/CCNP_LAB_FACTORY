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
| BL-012 | GEN-DOJO-PREFIX: ip prefix-list 道場（ドリル型・Phase1） | ENARSI/filter | 高 | 未着手 | 2台(feeder+target)・1出題K課題を意味的突き合わせで採点（`show ip bgp prefix-list` オンボックス採点・定義のみで適用不要）→ [problems/_drafts/DOJO-LISTS.design.md](problems/_drafts/DOJO-LISTS.design.md) |
| BL-013 | GEN-DOJO-ASPATH: as-path access-list 道場（Phase2） | ENARSI/filter | 高 | 未着手 | feeder流用＋local-as replace-as/prepend で AS_PATH合成、`show ip bgp filter-list` 採点。local-as の IOL 挙動は先行PoC → 同 design.md |
| BL-014 | GEN-DOJO-ACL: ACL 道場（Phase3） | ENCOR/ACL | 高 | 未着手 | acl_model.py（テストパケットベクタ意味評価器）＋grade.py 新チェック種 `acl_vectors:`。TGENルータのヒットカウンタは自己確認専用 → 同 design.md |
| BL-015 | MPLS: PE-CE eBGP 化（応用問03 → gen `--pece ebgp` 軸） | ENARSI/MPLS | 高 | 未着手 | vrf 内 eBGP で再配布レス化（02 との対比が核心）。同一AS変種で as-override/allowas-in。手組み03→gen移植の順 → [problems/_drafts/MPLS-SERIES.design.md](problems/_drafts/MPLS-SERIES.design.md) |
| BL-016 | MPLS: RT 非対称ハブ&スポーク構築問 | ENARSI/MPLS | 中 | 未着手 | export/import 独立の威力（spoke間はhub経由のみ）。hub CE 折返しの IOL 挙動は要 PoC → 同 design.md |
| BL-017 | MPLS: RT 混線 TS 故障（l4_rt_cross_import）追加 | ENARSI/MPLS | 中 | 未着手 | 重複prefixだと症状が非決定的→redistribute connected を base v2 軸で足し PE-CE リンク漏えいで決定的に検出 → 同 design.md |
| BL-018 | MPLS: VPNv4 RR 軸（gen `--ibgp rr`, 専用RRノード13台） | ENARSI/MPLS | 中 | 未着手 | フルメッシュ→RR。故障=client旗/RR activate/cluster-id。chainTS の「client旗1つでは壊れない」教訓の VPNv4 版確認 → 同 design.md |
| BL-019 | chainTS swap モード l3_subnets_missing 再検証 | ENARSI/再配送 | 高 | 未着手 | iol-xe 17.15 の subnets 暗黙定発見の波及。故障として不成立の疑い→90秒以上待って単体検証、不成立なら差替え → 同 design.md |
| BL-020 | gen_mpls_ts --faults 3 の実機1サイクル | ENARSI/MPLS | 中 | 未着手 | 3層連鎖（下位が上位を隠す）の組合せ未検証。seed 7200 相当で注入→切り分け→100点まで → 同 design.md |
| BL-021 | MPLS 小粒（LDP MD5 / 01・02 params 化 / MSS 効果採点 / 遠期: InterAS・6PE） | ENARSI/MPLS | 低 | 未着手 | 詳細は design.md の BL-021 節 → 同 design.md |

## 完了アーカイブ

| ID | 題名 | 完了日 | 備考 |
|----|------|--------|------|
