# 障害対応 GEN-L2TS-6158 : EtherChannel（束が組めない / 疎通しない）

## 状況
SW01–SW02 間の 2 本の物理リンク（`Ethernet0/0` / `Ethernet0/1`）を **Port-channel1 に束ね**、データ VLAN62 を流す設計です。構築作業の後、**束が正しく形成されず、通信もできない**との申告が上がっています。

## 受付チケット
> 「SW01 と SW02 の **VLAN62 SVI 間（`10.109.192.1` ⇔ `10.109.192.2`）で ping が通らない**。Port-channel1 を見ても 2 本がうまく束ねられていないようだ。」
>
> 切り分けて原因を特定し、恒久的に復旧してください。**原因は 1 か所とは限りません。**

## 構成台帳
| 機器 | 管理IP(telnet) | SVI |
|---|---|---|
| SW01 | 10.1.10.11 | `10.109.192.1/24` |
| SW02 | 10.1.10.12 | `10.109.192.2/24` |

- 束ねは **両端が動的にネゴシエーションして確立する方式（LACP）** とすること。

## 完了条件
1. Port-channel1 が **LACP で up**し、**`Et0/0`・`Et0/1` 両方が bundled**（SW01・SW02 とも）。
2. **VLAN62 SVI 間（`10.109.192.1` ⇔ `10.109.192.2`）の ping が成功**すること。

## ログイン（telnet）/ 採点
```
telnet 10.1.10.11   # SW01（user SUZUKI / pass CCNP）
telnet 10.1.10.12   # SW02
ansible-playbook playbooks/grade.yml -e problem=GEN-L2TS-6158 --vault-password-file <(printf 'CCNP\n')
```
> 起点：`show etherchannel summary` / `show lacp neighbor` / `show interfaces status`。管理 VLAN(999) には触れないこと。
