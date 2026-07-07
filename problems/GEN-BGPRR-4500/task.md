# 障害対応 GEN-BGPRR-4500 : BGP Route Reflector / iBGP（4 ルータ）

## 状況
AS-b(RT02/RT03/RT04) は iBGP を **Route Reflector(RT02)** で構成（RT03/RT04 は RT02 の client・client 同士は直接ピアしない・iBGP は Loopback0 ピア）。RT01(AS-a) と RT02 が eBGP。各ルータの **Loopback1 を BGP で広告**（Loopback0/区間は OSPF）。MP-BGP 書式。ある変更作業の後から到達性の不具合が報告されている。

## 受付チケット
> 「**RT03** から **RT04** の Loopback1 (`36.36.36.36/32`) に到達できない」という申告がありました。
>
> 切り分けて原因を特定し、恒久的に復旧してください。原因は 1 か所とは限りません。

## 構成台帳
| ルータ | AS | 役割 | Loopback1(BGP) |
|---|---|---|---|
| RT01 | 65044 | eBGP edge | `84.84.84.84/32` |
| RT02 | 65019 | Route Reflector | `46.46.46.46/32` |
| RT03 | 65019 | RR client | `40.40.40.40/32` |
| RT04 | 65019 | RR client | `36.36.36.36/32` |

※ `show ip bgp summary`(セッション) / `show ip bgp <prefix>`(RR に来ているか・best か・next-hop accessible か) / `show ip route` で切り分けること。**セッションが全て Established・RR に経路が有っても、反射(reflection)が効かなければ client 同士は学習できない**。設定変更後は反射を反映するため `clear ip bgp *` が要る場合がある。

## 完了条件
すべてのルータが、他の全ルータの Loopback1 を RIB に学習している状態。

## 採点
```
ansible-playbook playbooks/grade.yml -e problem=GEN-BGPRR-4500 --vault-password-file <(printf 'CCNP\n')
```
