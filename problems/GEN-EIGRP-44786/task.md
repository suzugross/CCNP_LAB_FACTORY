# 問題 GEN-EIGRP-44786 : EIGRP 複合トラブルシュート（難易度5）

## 状況
単一 AS **100** の EIGRP 網（IPv4）で到達性障害。全ルータが全 Loopback へ
相互到達する状態へ復旧してください。

## トラブルチケット（代表症状・1件）
> **RT01 から RT03 の Loopback (`10.44.44.44`) へ到達できない。** 原因は1か所とは限りません。

## ルータ / Loopback 台帳（mgmt は割当順）
| ルータ | Loopback0 | mgmt(SSH) |
|--------|-----------|-----------|
| RT02 | `10.91.91.91/32` | 10.1.10.11 |
| RT07 | `10.79.79.79/32` | 10.1.10.12 |
| RT05 | `10.82.82.82/32` | 10.1.10.13 |
| RT01 | `10.19.19.19/32` | 10.1.10.14 |
| RT04 | `10.9.9.9/32` | 10.1.10.15 |
| RT03 | `10.44.44.44/32` | 10.1.10.16 |
| RT06 | `10.58.58.58/32` | 10.1.10.17 |

## 到達目標 / 切り分け
- 全ルータが全 Loopback を `show ip route eigrp` で学習し相互到達。
- トポロジ・故障の種類・場所・件数は非公開。有効化方式: 全機 **named mode**（`router eigrp CCNP` / `address-family ipv4 unicast autonomous-system 100`）。
- 切り分け: `show ip eigrp neighbors` / `show ip eigrp interfaces` / `show ip protocols` /
  `show ip route eigrp` / `show running-config | section eigrp`。
- ヒント（EIGRP の勘所）: **hello/hold の不一致では隣接は落ちない**。隣接不形成は
  K値・認証・passive・ACL・network 欠落など。設定変更後に隣接が戻らない時は
  `clear ip eigrp neighbors`。中継機が **stub** だと下流が丸ごと落ちる。

## アクセス・採点
SSH `SUZUKI / CCNP`（mgmt は割当順に 10.1.10.11〜）。
```
ansible-playbook playbooks/grade.yml -e problem=GEN-EIGRP-44786 --vault-password-file <(printf 'CCNP\n')
```
