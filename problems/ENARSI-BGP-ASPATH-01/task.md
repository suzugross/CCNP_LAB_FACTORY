# 問題 ENARSI-BGP-ASPATH-01 : AS-path ACL で特定 AS 経由の経路を除外

## シナリオ
RT01 (AS65001) は隣接 RT02 (AS65002) から経路を受け取っている。RT02 はさらに
その先の RT03 (AS65003) からも経路を学習し、それを RT01 に流している。

社内ポリシーで「**AS65003 を中継した経路は受け取らない**」と決まった。
RT01 上で AS-path ベースのフィルタを構成し、AS65003 を経由した経路だけを
RT01 の BGP テーブルから排除せよ。

## トポロジ
```
[Lo102=10.2.0.0/24]                  [Lo103=10.3.0.0/24]
RT01 ─── eBGP ─── RT02 ────── eBGP ───── RT03
AS65001          AS65002 (transit)        AS65003
       10.1.12.0/30        10.1.23.0/30
```

初期状態で RT01 の BGP テーブルには:
- `10.2.0.0/24` (AS-path = `65002`)        ← 受け取りたい
- `10.3.0.0/24` (AS-path = `65002 65003`) ← 受け取りたくない

## 到達目標
- RT01 ↔ RT02 の eBGP セッションは Established で維持。
- RT01 の BGP テーブルに `10.2.0.0/24` が残る。
- RT01 の BGP テーブルから `10.3.0.0/24` が消える（AS65003 を含むため）。

## 制約
- 変更は **RT01 のみ**。RT02 / RT03 は変更不可。
- フィルタリングには **AS-path access-list（`ip as-path access-list ... permit/deny`）+
  `neighbor X filter-list ... in`** を使う。prefix-list や distribute-list ベースの
  解は不可。
- AS-path access-list の番号は **10** を使う。
- 正規表現は適切に書くこと（部分マッチで AS65003 を検出する）。

## アクセス
- RT01: `10.1.10.11` / RT02: `10.1.10.12` / RT03: `10.1.10.13`（SSH, admin/CCNP）

## 採点
```
ansible-playbook playbooks/grade.yml -e problem=ENARSI-BGP-ASPATH-01 --vault-password-file <(printf 'CCNP\n')
```
