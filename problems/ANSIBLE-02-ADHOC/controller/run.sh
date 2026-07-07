#!/usr/bin/env bash
# ===== Lesson 02: アドホックコマンド =====
# playbook を書かずに「1コマンド」で全ルータを操作する。
# 書式:  ansible <対象> -i hosts.ini -m <モジュール> -a "<引数>"
#   <対象>    : インベントリのグループ名（routers）
#   -m        : 使うモジュール（設定を入れるなら cisco.ios.____）
#   -a "..."  : モジュール引数
# __FILL_n__ を埋めて  bash run.sh  で実行する。

# (1) 読み取り系: ios_command で show を打つ（参考・採点対象外。コメントを外して試せる）
# ansible routers -i hosts.ini -m cisco.ios.ios_command -a "commands='show clock'"

# (2) 設定系: 全ルータに snmp location を入れる（これが課題）
ansible routers -i hosts.ini -m cisco.ios.__FILL_1__ \
  -a "lines='snmp-server location __FILL_2__'"
