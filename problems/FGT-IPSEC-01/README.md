# FGT-IPSEC-01 運用ガイド（受講者非公開）

Cisco IOS(sVTI) ⇄ FortiGate(route-based) の IKEv2 サイト間 VPN interop ラボ
（BL-048）。受講者スコープ= fgt1 + RBR の2台。難易度3。

## 操作

```bash
PY=.venv/bin/python3
$PY topologies/fgtipsec_ops.py build    # 初期化: FGT全問題設定を巻き戻し+WAN基盤据付・RBRのVPN設定撤去
#   → problems/FGT-IPSEC-01/task.md を提示(チャットにも全文貼付)
$PY topologies/fgtipsec_ops.py grade    # 採点(単段・約4分)
$PY topologies/fgtipsec_ops.py solve    # 検証用: 両側へ模範解答投入
$PY topologies/fgtipsec_ops.py status | stop
```

## 共用ラボ FGT-LAB での位置づけ

- BL-048 で支社サイトを増設: INET Gi0/3(198.51.101.1/30) — RBR(iosv) — pcC(alpine
  192.168.20.10・day0 焼き込み済・httpd「BRANCH SERVER」)。ISP1/ISP2 に
  198.51.101.0/30 への静的経路を追加済み（wr mem 済）
- **INET は物理構成ロックのため wipe→day0 焼き直しで Gi0/3 を追加**した
  （day0=旧running-config吸い上げ+Gi0/3。IOSvノードへのIF追加は今後もこの手順）
- FGT の build は共用 UNBUILD（SD-WAN/BASIC/本問すべて巻き戻し）+ 本問据付
  （port1 IP + デフォルトルート）。RBR の build は VPN 関連のみ no で撤去
- ライセンス運用= [problems/FGT-SDWAN-01/README.md](../FGT-SDWAN-01/README.md)

## ★eval 制約（本問 PoC で確定・作問全般に影響）

- **暗号は DES 系のみ**（LENC ビルド: des-md5/sha1/sha256/sha384/sha512。
  AES は parse error）→ 本問はこれを教材化（Phase 3 の計画崩し）
- **ファイアウォールポリシー最大3本**（4本目 = `-4 reached the maximum number
  of entries`）→ 全 FGT 問題の設計上限として遵守すること
- **トンネル IF は「IF 3個上限」に数えられない**（route-based VPN 成立の根拠）
- FGT はトンネル IF 参照ポリシーが無いと IKE ネゴ拒否
  （`no policy configured for the gateway`・対向には NO_PROPOSAL_CHOSEN が飛ぶ）

## 採点の注意

- S5/S6 はポリシー ID 1/2 依存（task.md に ID 指定）。E4 カウンタは G チェックの
  採点トラフィックで進む（checks 順序で担保）
- 実機フルサイクル 2026-07-12: build 0/100 → solve → 100/100（下記参照）
