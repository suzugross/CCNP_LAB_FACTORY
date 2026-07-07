#!/bin/bash
# GEN-DNSTS サーバ側修復（自己検品/解答開示用）: 健全設定へ全量復元
set -e
[ "$(id -u)" = 0 ] || exec sudo -n bash "$0" "$@"

cat > /etc/bind/db.ccnp.local <<'CCNP_EOF'
$TTL 300
@       IN SOA srv01.ccnp.local. admin.ccnp.local. ( 2026070401 3600 600 86400 60 )
@       IN NS  srv01.ccnp.local.
srv01   IN A   10.99.0.2
rt01    IN A   37.37.37.37
rt02    IN A   98.98.98.98
gw      IN A   192.168.90.1
portal  IN CNAME srv01.ccnp.local.
CCNP_EOF

cat > /etc/bind/db.192.168.90 <<'CCNP_EOF'
$TTL 300
@       IN SOA srv01.ccnp.local. admin.ccnp.local. ( 2026070401 3600 600 86400 60 )
@       IN NS  srv01.ccnp.local.
1       IN PTR gw.ccnp.local.
CCNP_EOF

cat > /etc/bind/named.conf.local <<'CCNP_EOF'
zone "ccnp.local" { type master; file "/etc/bind/db.ccnp.local"; };
zone "90.168.192.in-addr.arpa" { type master; file "/etc/bind/db.192.168.90"; };
CCNP_EOF

cat > /etc/bind/named.conf.options <<'CCNP_EOF'
acl internal { 127.0.0.0/8; 10.0.0.0/8; 192.168.0.0/16; };
options {
        directory "/var/cache/bind";
        recursion yes;
        allow-query { internal; };
        allow-recursion { internal; };
        dnssec-validation no;
        listen-on { any; };
        listen-on-v6 { any; };
};
CCNP_EOF

cat > /etc/dhcp/dhcpd.conf <<'CCNP_EOF'
default-lease-time 600;
max-lease-time 7200;
authoritative;

# 待受IF(ens3)自身のサブネット宣言（無いと dhcpd が起動しない）
subnet 10.99.0.0 netmask 255.255.255.252 { }

subnet 192.168.90.0 netmask 255.255.255.0 {
  range 192.168.90.101 192.168.90.150;
  option routers 192.168.90.1;
  option domain-name-servers 10.99.0.2;
  option domain-name "ccnp.local";
}
CCNP_EOF

sed -i 's/^INTERFACESv4=.*/INTERFACESv4="ens3"/' /etc/default/isc-dhcp-server

named-checkconf
systemctl restart named
systemctl restart isc-dhcp-server
systemctl is-active named isc-dhcp-server
echo FIXED
