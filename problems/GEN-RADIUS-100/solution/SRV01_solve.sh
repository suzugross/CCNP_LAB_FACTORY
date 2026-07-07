#!/bin/bash
# GEN-RADIUS 模範解答投入（自己検品用）
set -e
[ "$(id -u)" = 0 ] || exec sudo -n bash "$0" "$@"

cat > /etc/freeradius/3.0/clients.conf <<'EOF'
# ローカルテスト用（採点も使用・削除禁止）
client localhost {
	ipaddr = 127.0.0.1
	secret = testing123
}
client rt01 {
	ipaddr = 10.99.0.1
	secret = Ccnp-Rad-8102
}
client rt02 {
	ipaddr = 10.1.12.2
	secret = Ccnp-Rad-8102
}
EOF

cat > /etc/freeradius/3.0/mods-config/files/authorize <<'EOF'
noc-hanako Cleartext-Password := "Noc-3863"
	Service-Type = NAS-Prompt-User,
	Cisco-AVPair = "shell:priv-lvl=15"

monitor-op Cleartext-Password := "Desk-6730"
	Service-Type = NAS-Prompt-User,
	Cisco-AVPair = "shell:priv-lvl=1"

SUZUKI Cleartext-Password := "CCNP"
	Service-Type = NAS-Prompt-User,
	Cisco-AVPair = "shell:priv-lvl=15"
EOF

freeradius -XC >/dev/null
systemctl restart freeradius
systemctl is-active freeradius
echo SOLVED
