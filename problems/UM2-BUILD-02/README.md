# UM2-BUILD-02 運用ガイド（受講者非公開）— ワンアームLB変種

UM2-BUILD-01 の姉妹問。LB を FW と同じ「腕1本のワンアーム」（Gi0/0 に dot1q
254/251 多重）で収容する形。DMZ-SV は L3SW2 Gi1/0（access 251）収容で SRV-SW 無し。
**教材の核 = インライン形との対比**（トラッキング要否が構造で変わる・ANSWER_KEY 参照）。

## 操作

```bash
PY=.venv/bin/python3
$PY topologies/um2_ops.py --variant onearm build    # スケルトン起動（10ノード）
#   → 受講者に problems/UM2-BUILD-02/task.md を提示（チャットにも全文貼付）
$PY topologies/um2_ops.py --variant onearm grade    # 採点（100点・console収集・約5分）
$PY topologies/um2_ops.py --variant onearm solve    # ★検証専用: 模範解答を6台へ自動投入
$PY topologies/um2_ops.py --variant onearm status
$PY topologies/um2_ops.py --variant onearm destroy
```

- 10 CMLノード（VM 8台）。★**BUILD-01 と同時起動不可**（CML Personal 20ノード上限）
- **実機フルサイクル済（2026-07-11・出題可）**: 0点発射 0/100 → solve → **100/100**
  ＋ LB腕断デモ実証（track 無しで上下同時切替・inbound 10/10 無損失・preempt 復帰）
- 模範解答・設計根拠: [ANSWER_KEY.md](ANSWER_KEY.md) /
  [problems/_drafts/UM2.design.md](../_drafts/UM2.design.md) /
  [poc/um2/README.md](../../poc/um2/README.md)
