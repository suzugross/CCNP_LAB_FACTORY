# 問題 GEN-DNSDHCP-100 : 社内DNS(BIND9)構築＋DHCPリレー（難易度3）

## シナリオ
新オフィスのユーザセグメント **192.168.38.0/24** を開設します。サーバセグメントの
**SRV01 (Ubuntu 24.04)** を社内 DNS/DHCP サーバとして構築し、ユーザ端末 **PC01** が
「電源を入れれば IP が付き、名前でイントラサーバに届く」状態に仕上げてください。

```
 SRV01 ────── RT01 ────── RT02 ────── PC01
(DNS/DHCP)                          (利用者端末)
 10.99.0.0/30   10.1.12.0/30   192.168.38.0/24 (GW=.1)
```

## 構成（初期状態で投入済み・変更不可）
- ルーティング(OSPF)・各 IF の IP は設定済み（RT02 E0/1 = 192.168.38.1 がユーザLANのGW）
- SRV01: ens3 = `10.99.0.2/30`。**bind9 / isc-dhcp-server / dnsutils 導入済み（未設定）**
- PC01: ens3 は DHCP クライアント設定済み（サーバ側が正しく動けば自動でリースを取る）

## 要件
### A. 社内 DNS（SRV01 / BIND9）
台帳のとおり `ccnp.local` ゾーン（正引き）と `192.168.38.0/24` の逆引きゾーンを提供する:

| 名前 | 種別 | 値 |
|------|------|----|
| srv01.ccnp.local | A | 10.99.0.2 |
| rt01.ccnp.local | A | 59.59.59.59 |
| rt02.ccnp.local | A | 99.99.99.99 |
| pc01.ccnp.local | A | 192.168.38.79 |
| **intranet.ccnp.local** | **CNAME** | srv01.ccnp.local |
| 192.168.38.79 | PTR | pc01.ccnp.local |

- 問い合わせ応答・再帰は **社内 (10.0.0.0/8, 192.168.0.0/16) とローカルホストのみ**許可

### B. DHCP（SRV01 / isc-dhcp-server）
- 対象: ユーザLAN `192.168.38.0/24`、配布レンジ **.101〜.150**
- 配布オプション: GW=`192.168.38.1` / DNS=`10.99.0.2` / ドメイン名=`ccnp.local`
- **PC01 は予約（固定割当）**: 常に `192.168.38.79` を受け取ること（MAC は PC01 で確認）

### C. ネットワーク（RT01 / RT02）
- ユーザLAN に DHCP サーバは存在しない。**PC01 の DHCP 要求が SRV01 に届き、応答が
  返る**構成にすること（どの機器に何を入れるかは自分で判断）
- RT01・RT02 自身も SRV01 で名前解決できること（例: `ping srv01.ccnp.local` が成功）

## 到達目標（最終状態）
- PC01 が電源投入だけで `192.168.38.79/24`・GW・DNS・検索ドメインを取得
- PC01 から `intranet.ccnp.local` の名前解決と ping が成功
- SRV01 で正引き・逆引き・CNAME がすべて引ける
- RT01/RT02 から名前で ping が通る

## サーバ操作ガイド（NW 機器と勝手が違う所だけ。設定値は上の要件から組み立てること）
SRV01/PC01 へは SSH `SUZUKI / CCNP`（sudo 可）。基本サイクルは
**「ファイル編集 → 構文チェック → サービス再起動 → 状態確認」**。

### BIND9（設定は /etc/bind/ 配下）
- ゾーンの宣言（どのゾーンをどのファイルで持つか）: `/etc/bind/named.conf.local`
- 全体オプション（allow-query 等）: `/etc/bind/named.conf.options`
- ゾーンファイルは `/etc/bind/db.<名前>` を作る流儀。**$TTL・SOA・NS が無いと
  ゾーンはロードされない**（雛形として `/etc/bind/db.local` が使える）
- 逆引きゾーン名は `<第3オクテット>.<第2>.<第1>.in-addr.arpa` 形式
- 検証と反映:
  - `named-checkconf`（named.conf 構文） / `named-checkzone <ゾーン名> <ファイル>`
  - `sudo systemctl restart named` → `systemctl status named`
  - 動作確認 `dig @127.0.0.1 <名前>`、ログ `sudo journalctl -u named -e`
- ゾーンファイルを直したら SOA のシリアル値を増やすのが作法

### isc-dhcp-server
- 配布定義: `/etc/dhcp/dhcpd.conf`（既定ファイルにコメント形式の記述例が豊富。
  スコープは `subnet ... { }`、固定割当は `host ... { }` 宣言）
- 待受 IF の指定: `/etc/default/isc-dhcp-server` の `INTERFACESv4`
- ★ハマりどころ: **dhcpd は「待受 IF 自身のサブネット」の subnet 宣言が無いと起動を
  拒否する**（中身は空でよい）。起動失敗の理由は `sudo journalctl -u isc-dhcp-server -e`
- 反映: `sudo systemctl restart isc-dhcp-server`。リース状況: `/var/lib/dhcp/dhcpd.leases`

### PC01（利用者端末の視点で確認）
- MAC 確認: `ip link show ens3` / 取得 IP 確認: `ip -4 addr show ens3`
- DHCP で受けた DNS・ドメイン: `resolvectl dns ens3` / `resolvectl domain ens3`
- リース再取得を急ぐとき: `sudo networkctl reconfigure ens3`（放置でも数分内に再試行）

## 注意
- PC01 の ens2 (10.1.10.0/26) は管理・採点用。**ens2 側は変更しないこと**
- SRV01 のアドレス・経路は設定済み。SRV01 で触るのは**サービス設定のみ**
- 外部名（例: www.google.com）の解決可否は採点対象外

## アクセス・採点
SSH `SUZUKI / CCNP`（MGMT: RT01=10.1.10.11, RT02=.12, SRV01=.13, PC01=.14）。
DHCP リースの反映待ちがあるため attempts 多めで:
```
ansible-playbook playbooks/grade.yml -e problem=GEN-DNSDHCP-100 -e max_attempts=20 \
  --vault-password-file <(printf 'CCNP\n')
```
