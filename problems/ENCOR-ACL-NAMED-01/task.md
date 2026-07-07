# 問題 ENCOR-ACL-NAMED-01 : 名前付きACLにシーケンス番号でACEを挿入

## シナリオ
RT02 には既に名前付き拡張ACL **`WEB-FILTER`** があり、RT01 向けインタフェース
(`Ethernet0/0`) に **inbound** で適用されています。現在の中身は次の 1 行だけです。

```
ip access-list extended WEB-FILTER
 10 permit ip any any
```

ここに、**サーバ `3.3.3.3` 宛の Telnet (TCP 23) を遮断**するルールを追加してください。
ただし運用ルール上、**既存の ACL を消して作り直すことは禁止**です。
**シーケンス番号を使って必要なエントリだけを追加**してください。

## トポロジ
```
RT01 ──(OSPF area0)── RT02 ──(OSPF area0)── RT03 [server 3.3.3.3]
     10.0.12.0/30          10.0.23.0/30
```
- RT01: Lo0 1.1.1.1 / RT02: Lo0 2.2.2.2 / RT03: Lo0 3.3.3.3（保護対象サーバ）
- OSPF (プロセス1 / area0) は全ルータ設定済み・全到達可能。
- WEB-FILTER は RT02 の `Ethernet0/0` に inbound 適用済み。

## 到達目標 — RT02 のみ
1. `WEB-FILTER` に **サーバ `3.3.3.3` 宛の Telnet を deny** するエントリを追加する。
2. 追加したエントリが**実際に効く**ようにする（＝既存の `permit ip any any` より
   **先に評価される**位置に入れる）。
3. 既存の `permit ip any any` は残すこと（ACL を作り直さない）。

## 制約
- 設定するのは **RT02 のみ**。RT01 / RT03 は変更しない。
- ★ ACL は上から順に評価され、最初に一致したエントリで処理が決まる
  (first-match)。番号を付けずに追加すると末尾に入り、`permit ip any any` が
  先にマッチして deny が効かない。**シーケンス番号で挿入位置を制御すること。**

## アクセス（SSH, SUZUKI / CCNP）
- RT01: `10.1.10.11` / RT02: `10.1.10.12` / RT03: `10.1.10.13`

## 採点
```
ansible-playbook playbooks/grade.yml -e problem=ENCOR-ACL-NAMED-01 --vault-password-file <(printf 'CCNP\n')
```
