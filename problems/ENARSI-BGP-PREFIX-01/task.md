# 問題 ENARSI-BGP-PREFIX-01 : prefix-list で inbound 経路を選別 (ge/le 表記)

## シナリオ
RT01 (AS65001) は隣接 RT02 (AS65002) から複数のプレフィックスを受け取っている。
社内ポリシーで「**10.10.0.0/16 の中の /24 単位の経路のみ受け入れる**。それ以外
（特に 192.168.x.x 系）は拒否する」と決まった。RT01 上で **prefix-list** を構成して
inbound 経路を選別せよ。

## トポロジ
```
RT01 (AS65001) ─── eBGP ─── RT02 (AS65002)
                  10.1.12.0/30
                                  Lo10  = 10.10.0.0/24    ← 受信したい
                                  Lo11  = 10.10.1.0/24    ← 受信したい
                                  Lo192 = 192.168.0.0/24  ← 拒否したい
```

初期状態で RT01 の BGP テーブルには上記 3 つすべてが見える。

## 到達目標
- RT01 ↔ RT02 の eBGP は Established で維持。
- 受信後の RT01 BGP テーブルには `10.10.0.0/24` と `10.10.1.0/24` が残る。
- `192.168.0.0/24` は **BGP テーブルから消える**。

## 制約
- 変更は **RT01 のみ**。RT02 は変更不可。
- フィルタリングには **`ip prefix-list ... ge/le ...`** を使う。AS-path filter や
  distribute-list、route-map で個別プレフィックスを deny する解は不可。
- prefix-list の **`ge` 表記を使うこと**（マスクの直書きではなく長さ範囲指定）。
- prefix-list はピア inbound に適用する。

## アクセス
- RT01: `10.1.10.11` / RT02: `10.1.10.12`（SSH, admin/CCNP）

## 採点
```
ansible-playbook playbooks/grade.yml -e problem=ENARSI-BGP-PREFIX-01 --vault-password-file <(printf 'CCNP\n')
```
