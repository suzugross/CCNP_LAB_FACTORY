# 障害対応 GEN-BGPPATH-4410 : BGP 経路選択（デュアルホーム / 4 ルータ）

## 状況
RT01(AS-A) は RT02(AS-B) と RT03(AS-C) の 2 経路で RT04(AS-D) に接続するデュアルホーム構成（全 eBGP・MP-BGP 書式）。

## ポリシー（あるべき姿）
- **RT01 ↔ RT04（`24.24.24.24` / `34.34.34.34`）のトラフィックは PRIMARY=RT02 経由**。RT03 は **バックアップ**（RT02 障害時のみ使用）。
- 到達性自体は保たれているが、**現在は意図した PRIMARY 経路を通っていない**との報告。

## 構成台帳
| ルータ | AS | Loopback |
|---|---|---|
| RT01 | 64685 | `34.34.34.34/32` |
| RT02 | 65158 | `52.52.52.52/32` |
| RT03 | 64876 | `29.29.29.29/32` |
| RT04 | 65325 | `24.24.24.24/32` |

※ どの属性(local-preference / AS-path 等)で制御すべきか、誤りの場所/種類/件数は非公開。`show ip bgp 24.24.24.24` / `show ip route 24.24.24.24` で **best-path とその理由** を確認して切り分けること。

## 完了条件
往き(RT01→RT04Lo)・帰り(RT04→RT01Lo) とも **RT02 経由（単一経路）** で、全 Loopback への到達性は維持されていること。

## 採点
```
ansible-playbook playbooks/grade.yml -e problem=GEN-BGPPATH-4410 --vault-password-file <(printf 'CCNP\n')
```
