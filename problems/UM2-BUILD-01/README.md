# UM2-BUILD-01 運用ガイド（受講者非公開）

書籍デザインパターン UM2「Untrustワンアーム構成」を 1 から構築させる問題。
受講者スコープ = L3SW×2（VRF/VLAN/SVI/HSRPv2/track）＋ FW×2（ワンアーム
サブIF/failover/NAT/ACL/inspection）＋ LB×2（サブIF/HSRP/VIP 終端 NAT）。
BACKBONE / USER-PC / DMZ-SV は据付（day0 設定済み・変更禁止）。

## 操作

```bash
PY=.venv/bin/python3
$PY topologies/um2_ops.py build      # スケルトン起動（FW=工場出荷・IOS=最小day0）
#   → 受講者に problems/UM2-BUILD-01/task.md を提示（チャットにも全文貼付）
$PY topologies/um2_ops.py grade      # 採点（100点・全ノードconsole収集・約5分）
$PY topologies/um2_ops.py solve      # ★検証専用: 模範解答を6台へ自動投入
$PY topologies/um2_ops.py status
$PY topologies/um2_ops.py destroy
```

- 10 CMLノード（VM 8台・RAM約7GB）・MGMT/リース不要（console 完結）
- 実機フルサイクル済（2026-07-11）: 未構築 0/100 → solve → **100/100**
- 採点は何度でも実行可（副作用なし）。フェールオーバー形成直後は同期に約1分
- 模範解答・設計根拠: [ANSWER_KEY.md](ANSWER_KEY.md) /
  [problems/_drafts/UM2.design.md](../_drafts/UM2.design.md) /
  [poc/um2/README.md](../../poc/um2/README.md)
