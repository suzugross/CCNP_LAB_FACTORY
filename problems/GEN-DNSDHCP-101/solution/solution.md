# GEN-DNSDHCP 模範解答（採点者用）

## サーバ側（SRV01）
`SRV01_solve.sh <PC01のens3 MAC>` が全設定を投入する（内容がそのまま模範解答）。
要点:
- `/etc/bind/named.conf.local` … `ccnp.local`（正引き）と `94.168.192.in-addr.arpa`
  （逆引き）の zone 宣言
- `/etc/bind/db.ccnp.local` … SOA/NS + A(srv01, rt01, rt02, pc01) + CNAME(portal)
- `/etc/bind/db.192.168.94` … PTR 62 → pc01.ccnp.local.
- `/etc/bind/named.conf.options` … allow-query/allow-recursion を社内
  (10.0.0.0/8, 192.168.0.0/16, 127.0.0.0/8) に限定・forwarders 8.8.8.8
- `/etc/dhcp/dhcpd.conf` … 待受IFサブネットの空宣言 + 192.168.94.0/24 スコープ
  (range .101-.150, routers .1, dns 10.99.0.2, domain ccnp.local)
  + host 宣言で PC01 を 192.168.94.62 に固定
- `/etc/default/isc-dhcp-server` … INTERFACESv4="ens3"

## ネットワーク側（fix.json = fix_generated.yml で投入可）
- RT02 `interface Ethernet0/1` に `ip helper-address 10.99.0.2`
  （ユーザLANのブロードキャスト DHCP をユニキャストで SRV01 へリレー）
- RT01/RT02 に `ip name-server 10.99.0.2`（+`ip domain lookup`）

## 採点後レビュー観点
- helper-address を「LAN 側 IF（giaddr になる IF）」に付けたか。SRV01 側 IF や
  グローバルに付けても機能しない点が定番の落とし穴。
- dhcpd の「待受IFのサブネット宣言必須」に気づけたか（journalctl を読む力）。
- 予約 IP をレンジ外に置く設計（レンジ内予約は重複配布の温床）。
- CNAME 先を A で持つ srv01 に張ったか（CNAME→CNAME 連鎖や A 直書きは減点対象外だが
  台帳どおりが原則。intranet を A で書くと CNAME チェックは FAIL）。
- 補足: 外部名の解決は forwarders 経由（SRV01 は mgmt 側から internet 到達可）。
  PC01 から外部への ping は NAT が無いため通らない（名前解決だけは通る）。
