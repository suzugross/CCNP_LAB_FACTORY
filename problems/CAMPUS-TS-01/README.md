# CAMPUS-TS-01 運用ガイド（受講者非公開）

3層キャンパスLAN 障害演習ラボ。golden（正常系）を建て、フォールトを1つ注入して
受講者に「症状チケット」（catalog.yml の symptom_ticket）だけを渡す。

## 前提

- CML 2.8.1 (10.1.10.10)・他ラボ全停止推奨（本ラボは 11 VM + 補助3 = 14 ノード）
- ★実施中は同時起動 20 ノード上限（CML Personal）にほぼ達する
- 認証: 機器 SUZUKI/CCNPccnp（本問のみ8字統一・ASA制約）/ Linux suzuki/CCNP

## 操作（1コマンド往復）

```bash
PY=.venv/bin/python3
$PY topologies/campus_ops.py build            # リース→golden生成→起動→ASA bootstrap
$PY topologies/campus_ops.py grade            # 採点（golden で 100 点を確認）
$PY topologies/campus_ops.py inject dhcp_relay_gap   # フォールト注入（1つ）
$PY topologies/campus_ops.py grade            # 対応チェックだけ落ちることを確認
$PY topologies/campus_ops.py reset            # golden へ復帰
$PY topologies/campus_ops.py status           # 状態表示
$PY topologies/campus_ops.py destroy          # 撤収＋リース解放
```

- inject/reset は **差分ノードだけ** day0 差し替え＋wipe＋再起動（2〜4分）。
  asa1 が対象の場合は自動で console bootstrap が再実行される
- fault は catalog.yml の5種: trunk_allowed_mismatch / ospf_mtu_mismatch /
  dhcp_relay_gap / asa_asymmetric_drop / pmtud_blackhole

## タイミングの目安

- build: ブート約5分＋svr1 の cloud-init(apt)数分＋OSPF/HSRP/DHCP収束
  → **build 完了から 10 分ほど置いてから** golden の grade を回すのが安全
- クライアントの DHCP は netplan が永続リトライする（復旧後に自然回復）。
  即時確認したい場合は cli で `sudo networkctl reconfigure ens3`

## 実装メモ

- 生成器: topologies/gen_campus_lab.py（day0/ラボYAML/state.json を _generated へ）
- ASAv は day0 不発（poc/asav/README.md）→ campus_ops.py が console bootstrap
- 採点: problems/CAMPUS-TS-01/grading.yml → campus_ops.py grade が
  IOS/ASA=collect_console.py・Linux=SSH で混成収集 → grade.py（100点）
- 対象外の障害（物理層エラー等・CMLで再現不能）は catalog.yml 末尾に明記
