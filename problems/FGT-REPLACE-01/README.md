# FGT-REPLACE-01 運用ガイド（受講者非公開）

ASA→FortiGate リプレース体験問（BL-049）。現行 ASA の running-config（紙面）を
読み解いて FGT 3IF に再実装させる。FGT シリーズの卒業試験（難易度4）。
受講者スコープ= fgt1 のみ。ASA はノード起動しない（読解専用の紙面資料）。

## 操作

```bash
PY=.venv/bin/python3
$PY topologies/fgtreplace_ops.py build    # 受講者向け初期化(FGT-LAB 共用リセット・wipeしない)
#   → task.md ＋ running-config.txt を提示(チャットにも全文貼付)
$PY topologies/fgtreplace_ops.py grade    # 採点(単段・約3分)
$PY topologies/fgtreplace_ops.py solve    # 検証用: 模範解答投入
$PY topologies/fgtreplace_ops.py status | stop
```

## 教材の設計（何を体験させるか）

1. **security-level 暗黙許可の移行漏れ**（本問最大の核）: ASA では inside→dmz が
   SL 100→50 で ACL 無しに通る。FGT はポリシーが無ければ通らない。
   Phase 3 の観察3-1 で「ID 1/2 だけ作った時点では LAN→DMZ が落ちる」を体験させ、
   自力で「明示ポリシーが要る」に到達させる（G5 が採点で回収）
2. **static NAT → 1:1 VIP**: ACL に permit icmp があるため port-forward では要件を
   満たせない（S5 の not_contains portforward が回収・考察3）。extip 2.2.2.1 は
   port1 /30 のサブネット外＝オフサブネット VIP（ISP1 の静的経路で成立・PoC 済）
3. **PAT アドレス → ippool**: 「送信元は必ず 2.2.2.10」の要件で `set nat enable`
   だけの解を弾く（S6 の poolname 必須・観察4-2 で session を目視）
4. **移行対象外の判断**: failover/standby IP（FGT なら FGCP だが eval 制約で不可）・
   inspect icmp（FGT は既定ステートフル）・route 4本→1本（connected 化）

## 共用ラボ FGT-LAB

- SD-WAN / FW-BASIC と同一ラボ。**build がもう一方の問題の設定を巻き戻す**
  （UNBUILD は sdwan_ops.py 共用。本問で SRV-VIP / SNAT-POOL の delete を追加済み）
- **ISP1/INET に 2.2.2.0/28 の静的経路が必要**（2026-07-12 に day0 焼き込み済み。
  ラボを yaml から再作成すれば自動で入る。手動確認: ISP1 `show ip route | include 2.2.2`）
- ライセンス運用（wipe 厳禁・再アクティベーション手順）=
  [problems/FGT-SDWAN-01/README.md](../FGT-SDWAN-01/README.md) ＋メモリ ccnp-fortigate

## 採点の注意

- S6/S7/S8 は**ポリシー ID 1/2/3 依存**（task.md に ID 指定あり）。ずれたら
  grade_input.json を目視して手動判定
- G4（ping 2.2.2.1）は **1:1 VIP でないと通らない**＝port-forward 解の検出器
- E1 は「DMZ→FGT ping 成功」＋「DMZ→LAN 全滅」の複合チェック（負の要件を
  単独採点しない）
- S9 は 2点のみ（default route が無いと G1-G5 が全滅するため実質は G で採点済み）
- 実機フルサイクル 2026-07-12: build 0/100 → solve → **100/100 一発**
