# 障害対応 ENCOR-LAG-TS-01 : EtherChannel（束が組めない / 疎通しない）

## 状況
スイッチ SW01–SW02 間は 2 本の物理リンク（`Ethernet0/0` / `Ethernet0/1`）で接続され、
**1 本の論理リンク（Port-channel1）に束ねて** データ VLAN30 を流す設計です。
ところが構築作業の後、**束が正しく形成されず、VLAN30 の通信もできない**との申告が上がっています。

## 受付チケット
> 「SW01 と SW02 の **VLAN30 SVI 間（`10.30.30.1` ⇔ `10.30.30.2`）で ping が通らない**。
> Port-channel1 を見ても、思ったように 2 本が束ねられていないようだ。」
>
> 切り分けて原因を特定し、恒久的に復旧してください。**原因は 1 か所とは限りません。**

## 構成台帳
| 機器 | 管理IP(telnet) | VLAN30 SVI |
|---|---|---|
| SW01 | 10.1.10.11 | `10.30.30.1/24` |
| SW02 | 10.1.10.12 | `10.30.30.2/24` |

- SW01–SW02 間：物理 2 本（`Et0/0` / `Et0/1`）を Port-channel1 に束ねる想定。
- 束ねは **両端が互いにネゴシエーションして動的に確立する方式（LACP）** とすること。

## 完了条件
1. Port-channel1 が **LACP で up**し、**`Et0/0` と `Et0/1` の両方が bundled** であること（SW01・SW02 とも）。
2. その状態で **VLAN30 SVI 間（`10.30.30.1` ⇔ `10.30.30.2`）の ping が成功**すること。

## ログイン（telnet）/ 採点
```
! telnet 10.1.10.11      # SW01 （user SUZUKI / pass CCNP）
! telnet 10.1.10.12      # SW02

ansible-playbook playbooks/grade.yml -e problem=ENCOR-LAG-TS-01 --vault-password-file <(printf 'CCNP\n')
```
> ※ 切り分けの起点：`show etherchannel summary` / `show lacp neighbor` / `show interfaces status`。
> 管理用インタフェース・管理 VLAN には触れないこと。
