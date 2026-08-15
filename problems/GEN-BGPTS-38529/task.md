# 障害対応 GEN-BGPTS-38529 : BGP 到達性（トランジット AS / 4 ルータ）

## 状況
3 つの AS をまたぐ BGP ネットワーク。AS-b(RT02/RT03) がトランジットで、内部は OSPF＋iBGP(Loopback ピア)で構成されている。BGP は **MP-BGP（`address-family ipv4 unicast`）書式**で組まれている（ルータにより従来書式と混在する場合がある）。ある変更作業の後から到達性の不具合が報告されている。

## 受付チケット
> 「**RT04** から **RT01** の Loopback (`94.94.94.94/32`) に到達できない」という申告がありました。
>
> 切り分けて原因を特定し、恒久的に復旧してください。原因は 1 か所とは限りません。

## 構成台帳
| ルータ | AS | Loopback |
|---|---|---|
| RT01 | 65466 | `94.94.94.94/32` |
| RT02 | 65509 | `22.22.22.22/32` |
| RT03 | 65509 | `71.71.71.71/32` |
| RT04 | 65102 | `19.19.19.19/32` |

- eBGP: RT01-RT02 / RT03-RT04　iBGP: RT02-RT03(Loopback)　OSPF: AS-b 内

※ `no bgp default ipv4-unicast` 構成では `address-family ipv4 unicast` 配下の `neighbor activate` や `network` も確認すること。区間アドレス・原因の場所/種類/件数は非公開。

## 完了条件
すべてのルータが、他の全ルータの Loopback を RIB に学習している状態。

## 採点
```
ansible-playbook playbooks/grade.yml -e problem=GEN-BGPTS-38529 --vault-password-file <(printf 'CCNP\n')
```
