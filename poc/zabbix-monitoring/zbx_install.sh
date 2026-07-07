#!/bin/bash
# Zabbix 7.0 LTS + PostgreSQL + nginx を Ubuntu 24.04 に自動インストール(PoC計測用)
# 将来 cloud-init の runcmd / ゴールデンイメージ化にそのまま流用する想定。
set -e
export DEBIAN_FRONTEND=noninteractive
log() { echo "[$(date -Is)] $*"; }

log "STEP1: zabbix-release 導入"
wget -q https://repo.zabbix.com/zabbix/7.0/ubuntu/pool/main/z/zabbix-release/zabbix-release_latest_7.0+ubuntu24.04_all.deb -O /tmp/zabbix-release.deb
dpkg -i /tmp/zabbix-release.deb >/dev/null
apt-get update -qq

log "STEP2: パッケージインストール"
apt-get install -y -qq zabbix-server-pgsql zabbix-frontend-php \
  zabbix-nginx-conf zabbix-sql-scripts zabbix-agent2 postgresql >/dev/null

log "STEP3: DB作成・スキーマ投入"
sudo -u postgres psql -qc "CREATE USER zabbix WITH PASSWORD 'zabbix';" || true
sudo -u postgres createdb -O zabbix zabbix || true
zcat /usr/share/zabbix-sql-scripts/postgresql/server.sql.gz | sudo -u postgres psql -q zabbix >/dev/null

log "STEP4: 設定"
sed -i 's/^# DBPassword=.*/DBPassword=zabbix/' /etc/zabbix/zabbix_server.conf
sed -i 's/^#\s*listen\s\+8080;/        listen 8080;/; s/^#\s*server_name\s\+example.com;/        server_name _;/' /etc/zabbix/nginx.conf
systemctl restart zabbix-server zabbix-agent2 nginx php8.3-fpm
systemctl enable -q zabbix-server zabbix-agent2 nginx php8.3-fpm

log "STEP5: 動作確認"
sleep 5
curl -s -o /dev/null -w "frontend HTTP %{http_code}\n" http://127.0.0.1:8080/
systemctl is-active zabbix-server nginx postgresql
log "DONE"
