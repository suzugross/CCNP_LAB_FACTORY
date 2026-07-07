#!/bin/bash
# GEN-DNSDHCP 模範解答投入（自己検品用）
# usage: SRV01_solve.sh <PC01のens3 MAC (xx:xx:xx:xx:xx:xx)>
set -e
[ "$(id -u)" = 0 ] || exec sudo -n bash "$0" "$@"
MAC="${1:?usage: SRV01_solve.sh <PC01 ens3 MAC>}"

# --- BIND9: ゾーン宣言・ゾーンファイル・オプション ---
cat > /etc/bind/named.conf.local <<'EOF'
zone "ccnp.local" { type master; file "/etc/bind/db.ccnp.local"; };
zone "94.168.192.in-addr.arpa" { type master; file "/etc/bind/db.192.168.94"; };
EOF

cat > /etc/bind/db.ccnp.local <<'EOF'
$TTL 3600
@       IN SOA srv01.ccnp.local. admin.ccnp.local. ( 2026070301 3600 600 86400 3600 )
@       IN NS  srv01.ccnp.local.
srv01   IN A   10.99.0.2
rt01    IN A   70.70.70.70
rt02    IN A   46.46.46.46
pc01    IN A   192.168.94.62
portal  IN CNAME srv01
EOF

cat > /etc/bind/db.192.168.94 <<'EOF'
$TTL 3600
@       IN SOA srv01.ccnp.local. admin.ccnp.local. ( 2026070301 3600 600 86400 3600 )
@       IN NS  srv01.ccnp.local.
62      IN PTR pc01.ccnp.local.
EOF

cat > /etc/bind/named.conf.options <<'EOF'
acl internal { 127.0.0.0/8; 10.0.0.0/8; 192.168.0.0/16; };
options {
        directory "/var/cache/bind";
        recursion yes;
        allow-query { internal; };
        allow-recursion { internal; };
        forwarders { 8.8.8.8; 8.8.4.4; };
        dnssec-validation no;
        listen-on { any; };
        listen-on-v6 { any; };
};
EOF

named-checkconf
named-checkzone ccnp.local /etc/bind/db.ccnp.local
named-checkzone 94.168.192.in-addr.arpa /etc/bind/db.192.168.94
systemctl restart named

# --- isc-dhcp-server: スコープ・オプション・PC01 予約 ---
cat > /etc/dhcp/dhcpd.conf <<EOF
default-lease-time 3600;
max-lease-time 7200;
authoritative;

# 待受IF(ens3)自身のサブネット宣言（無いと dhcpd が起動しない）
subnet 10.99.0.0 netmask 255.255.255.252 { }

subnet 192.168.94.0 netmask 255.255.255.0 {
  range 192.168.94.101 192.168.94.150;
  option routers 192.168.94.1;
  option domain-name-servers 10.99.0.2;
  option domain-name "ccnp.local";
}

host pc01 {
  hardware ethernet $MAC;
  fixed-address 192.168.94.62;
}
EOF
sed -i 's/^INTERFACESv4=.*/INTERFACESv4="ens3"/' /etc/default/isc-dhcp-server
systemctl restart isc-dhcp-server
systemctl is-active named isc-dhcp-server
echo SOLVED
