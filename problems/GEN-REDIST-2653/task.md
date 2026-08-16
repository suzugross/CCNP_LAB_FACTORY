# 問題 GEN-REDIST-2653 : 相互再配送 OSPF⇄EIGRP トラブルシュート（難易度5）

## 状況
OSPF ドメインと EIGRP ドメインを **境界2台(RT02,RT03)** が相互再配送している。
**会社ポリシーで EIGRP の AD は internal 90 / external 95 に固定(変更不可)**。
全ルータが全 Loopback へ**最短かつループ無し**で到達する状態へ復旧してください。

## トラブルチケット（代表症状）
> **EIGRP側(RT04)から OSPF側の Loopback (`82.82.82.82`)へ到達できない。**

## ルータ / Loopback / 役割
| ルータ | Loopback0 | ドメイン |
|--------|-----------|----------|
| RT01 | `82.82.82.82/32` | OSPF |
| RT02 | `3.3.3.3/32` | OSPF/EIGRP境界 |
| RT03 | `55.55.55.55/32` | OSPF/EIGRP境界 |
| RT04 | `7.7.7.7/32` | EIGRP |

## 到達目標
- 全ルータ間で全 Loopback に到達（reachability）。
- **再配送由来の次善経路・ループが無い**（ドメイン内宛先 RT01/RT04 へ最短）。
- 原因の種類・場所は伏せています。`show ip route [ospf|eigrp]` / `show ip protocols` /
  `show route-map` などで切り分け。AD は変更不可（タグ/フィルタで制御）。

## アクセス・採点
SSH `SUZUKI / CCNP`（mgmt は割当順に 10.1.10.11〜）。
```
ansible-playbook playbooks/grade.yml -e problem=GEN-REDIST-2653 --vault-password-file <(printf 'CCNP\n')
```
