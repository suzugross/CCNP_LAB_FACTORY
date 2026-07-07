# 問題 GEN-DNSTS-510 : 社内DNS/DHCP 障害復旧（難易度4）

## 障害チケット
> 昨日開通したユーザセグメント **192.168.90.0/24** の利用者から
> 「**PC01 がイントラ（portal.ccnp.local）に届かない／名前が引けない**」と申告。
> 昨日の開通試験ではすべて正常だった。**設計書どおりの状態に復旧**せよ。
> 原因は **1 箇所とは限らない**（サーバとネットワークの両方を疑うこと）。

```
 SRV01 ────── RT01 ────── RT02 ────── PC01
(DNS/DHCP)                          (利用者端末)
 10.99.0.0/30   10.1.12.0/30   192.168.90.0/24 (GW=.1)
```

## 設計書（正・この状態が採点される）
### DNS: `ccnp.local` ゾーン＋`192.168.90.0/24` 逆引き（サーバ=SRV01 10.99.0.2）
| 名前 | 種別 | 値 |
|------|------|----|
| srv01.ccnp.local | A | 10.99.0.2 |
| rt01.ccnp.local | A | 37.37.37.37 |
| rt02.ccnp.local | A | 98.98.98.98 |
| gw.ccnp.local | A | 192.168.90.1 |
| portal.ccnp.local | CNAME | srv01.ccnp.local |
| 192.168.90.1 | PTR | gw.ccnp.local |
- 応答・再帰とも社内 (10.0.0.0/8, 192.168.0.0/16) とローカルホストに許可

### DHCP（サーバ=SRV01 / isc-dhcp-server）
- ユーザLAN `192.168.90.0/24` に配布: レンジ .101〜.150 /
  GW=`192.168.90.1` / DNS=`10.99.0.2` / ドメイン名=`ccnp.local`
- ユーザLAN に DHCP サーバは無く、**RT02 がリレー**する設計

### ルータ
- RT01・RT02 とも SRV01 を DNS に使い、名前で ping できること

## 到達目標
- PC01 が DHCP でアドレス・GW・DNS・検索ドメインを取得し、
  `portal.ccnp.local` の名前解決と ping が成功
- SRV01 で正引き・逆引き・CNAME がすべて引ける（`dig @127.0.0.1`）
- RT01/RT02 から `ping srv01.ccnp.local` が成功

## 調査の道具箱（操作リファレンス。どこが壊れているかは自分で切り分けること）
- SRV01/PC01: SSH `SUZUKI / CCNP`（sudo 可）
- BIND9: 設定 `/etc/bind/`（named.conf.local / named.conf.options / db.*）。
  `named-checkconf` / `named-checkzone <ゾーン> <ファイル>` /
  `sudo journalctl -u named -e` / `dig @127.0.0.1 <名前>`（`dig` の
  status＝NOERROR/NXDOMAIN/SERVFAIL/REFUSED/timeout は最大の手がかり）
- isc-dhcp-server: `/etc/dhcp/dhcpd.conf` / `/etc/default/isc-dhcp-server` /
  `sudo journalctl -u isc-dhcp-server -e` / リース `/var/lib/dhcp/dhcpd.leases`
- PC01: `ip -4 addr show ens3` / `resolvectl dns ens3` / `resolvectl domain ens3` /
  リース再取得 `sudo networkctl reconfigure ens3` /
  キャッシュ掃除 `sudo resolvectl flush-caches`（サーバ側を直した後に）
- 反映: `sudo systemctl restart named` / `sudo systemctl restart isc-dhcp-server`

## 注意
- **設計書の値そのものは正しい**（設計ミスではなく、実装が設計とズレている）
- PC01 の ens2 (10.1.10.0/26) は管理・採点用。変更しないこと
- SRV01 のアドレス・経路（netplan）は正常。触るのはサービス設定のみ

## アクセス・採点
SSH `SUZUKI / CCNP`（MGMT: RT01=10.1.10.11, RT02=.12, SRV01=.13, PC01=.14）。
リース再取得・キャッシュの反映ラグがあるため attempts 多めで:
```
ansible-playbook playbooks/grade.yml -e problem=GEN-DNSTS-510 -e max_attempts=20 \
  --vault-password-file <(printf 'CCNP\n')
```
