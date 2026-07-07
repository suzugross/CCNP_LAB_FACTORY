# 回答ワークスペース（ENARSI-AUTO-BGP-01・BGPリソースモジュール）

RT01(AS65001) と RT02(AS65002) の **両方** を Ansible で構成し、互いの Loopback を eBGP で交換する。

## 穴一覧（計5）
| 穴 | ファイル | 入れる値の意味 |
|----|----------|----------------|
| ① | tasks `cisco.ios.____` | BGPグローバル(AS/router-id/neighbor)用リソースモジュール |
| ③ | tasks `cisco.ios.____` | BGP address-family(network)用リソースモジュール |

## 手順
```bash
cd lab/ENARSI-AUTO-BGP-01
ansible-playbook site.yml          # 1回目 changed / 2回目 changed=0
```
