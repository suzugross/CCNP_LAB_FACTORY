# 問題 ENARSI-BGP-WEIGHT-01 : eBGP デュアルホームで weight による primary 経路選択

## シナリオ
RT01 (AS65001) は 2 つの ISP に dual-home している。両 ISP は同じサービスプレフィックス
`10.100.0.0/24` を anycast で広告してくる。会社方針で **primary は RT02 (AS65002)** を
使い、RT03 (AS65003) は backup として扱いたい。**RT01 上だけ**で、属性 **weight** を
用いて primary 経路を強制せよ。

## トポロジ
```
                      Lo100=10.100.0.0/24 (anycast)
                        │
RT01 (AS65001) ── eBGP ─ RT02 (AS65002, primary)
   │
   └────────── eBGP ─── RT03 (AS65003, backup)
                        │
                      Lo100=10.100.0.0/24 (同じプレフィックス)
```

- RT01 ↔ RT02: `10.1.12.0/30` (RT01=.1 / RT02=.2)
- RT01 ↔ RT03: `10.1.13.0/30` (RT01=.1 / RT03=.2)
- 両 ISP は `network 10.100.0.0 mask 255.255.255.0` で同じプレフィックスを広告済み。

## 到達目標
- RT01 が両 ISP と eBGP セッション (Established) を確立。
- RT01 の RIB における `10.100.0.0/24` のベストパスが **RT02 経由** (next-hop=10.1.12.2) になる。

## 制約
- 変更は **RT01 のみ**。RT02 / RT03 は変更不可。
- 経路選択には **weight** を使うこと。local-preference や AS-path prepend、MED は使用しない。
- RT02 ピアの weight = **200** を指定する (受信側でローカルに設定する属性)。
- BGP プロセスの AS = **65001**、router-id は **1.1.1.1** を使う。

## アクセス
- RT01: `10.1.10.11` / RT02: `10.1.10.12` / RT03: `10.1.10.13`（SSH, admin/CCNP）

## 採点
```
ansible-playbook playbooks/grade.yml -e problem=ENARSI-BGP-WEIGHT-01 --vault-password-file <(printf 'CCNP\n')
```
