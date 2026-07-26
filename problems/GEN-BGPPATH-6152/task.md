# 障害対応 GEN-BGPPATH-6152 : BGP 経路選択（デュアルホーム / 4 ルータ）

## 状況
RT01(AS-A) は RT02(AS-B) と RT03(AS-C) の 2 経路で RT04(AS-D) に接続するデュアルホーム構成（全 eBGP・MP-BGP 書式）。

## ポリシー（あるべき姿）
- **RT01 ↔ RT04（`7.7.7.7` / `21.21.21.21`）のトラフィックは PRIMARY=RT02 経由**。RT03 は **バックアップ**（RT02 障害時のみ使用）。
- 到達性自体は保たれているが、**現在は意図した PRIMARY 経路を通っていない**との報告。

## 構成台帳
| ルータ | AS | Loopback |
|---|---|---|
| RT01 | 64881 | `21.21.21.21/32` |
| RT02 | 64902 | `55.55.55.55/32` |
| RT03 | 64989 | `52.52.52.52/32` |
| RT04 | 64851 | `7.7.7.7/32` |

※ どの属性(local-preference / AS-path 等)で制御すべきか、誤りの場所/種類/件数は非公開。`show ip bgp 7.7.7.7` / `show ip route 7.7.7.7` で **best-path とその理由** を確認して切り分けること。

## 完了条件
往き(RT01→RT04Lo)・帰り(RT04→RT01Lo) とも **RT02 経由（単一経路）** で、全 Loopback への到達性は維持されていること。

## 採点
```
ansible-playbook playbooks/grade.yml -e problem=GEN-BGPPATH-6152 --vault-password-file <(printf 'CCNP\n')
```
