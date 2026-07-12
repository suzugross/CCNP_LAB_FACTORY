# FGT-FW-BASIC-01 運用ガイド（受講者非公開）

FortiGate の基本 FW 設計（3ゾーン・オブジェクト・ポリシー・SNAT/VIP・暗黙deny）の
体験型構築ラボ（BL-047）。受講者スコープ= fgt1 のみ。難易度2（FGT 入門の1問目）。

## 操作

```bash
PY=.venv/bin/python3
$PY topologies/fgtbasic_ops.py build    # 受講者向け初期化(SD-WAN/BASIC 両設定の巻き戻し・wipeしない)
#   → problems/FGT-FW-BASIC-01/task.md を提示(チャットにも全文貼付)
$PY topologies/fgtbasic_ops.py grade    # 採点(単段・約3分)
$PY topologies/fgtbasic_ops.py solve    # 検証用: 模範解答投入
$PY topologies/fgtbasic_ops.py status | stop
```

## 共用ラボ FGT-LAB（★FGT-SDWAN-01 と共用）

- CML ラボ名 **FGT-LAB**（旧 FGT-SDWAN-01 を BL-047 で改修・改名）。
  port2 経路に無管理 SW2 を挿入し dmz1(alpine) を追加（SW2 は L2 透過で
  SD-WAN 問に無影響 — 改修後に劣化採点込み 100/100 回帰済み）
- **どちらの問題も build がもう一方の設定を巻き戻す**（UNBUILD は sdwan_ops.py で共用）
- 本問では ISP2 が DMZ の L2 セグメントに同居（203.0.114.1・別サブネットで無害・
  task.md で「触るな」と明示済み）
- alpine 3台（pcA/pcB/dmz1）は **day0 で IP/httpd を焼き込み済み**（2026-07-12 修正。
  それ以前は旧PoC残骸 day0 のため再起動で設定消失するバグがあった）。
  再起動しても自己復旧する。dmz1= 172.16.10.10 httpd「DMZ SERVER」
- ライセンス運用（wipe 厳禁・再アクティベーション手順）=
  [problems/FGT-SDWAN-01/README.md](../FGT-SDWAN-01/README.md) 参照

## 採点の注意

- S5/S6/S7 は **ポリシー ID 1/2/3 依存**（task.md に ID 指定あり）。受講者が
  作り直して ID がずれたら grade_input.json を目視して手動判定
- E1 は「DMZ→FGT ping 成功」＋「DMZ→LAN 全滅」の複合チェック（負の要件を
  単独採点しない）
- S1 は not_contains "set allowaccess"（port1 の管理面閉鎖が要件）
- 実機フルサイクル 2026-07-12: build 0/100 → solve → **100/100**
