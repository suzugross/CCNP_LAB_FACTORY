# 問題 ENARSI-BGP-MED-01 : 2 リンク並列 eBGP で MED により inbound パスを誘導

## シナリオ
RT01 (AS65001) は同じプロバイダ RT02 (AS65002) と **2 本** のリンク (primary / backup) で
接続している。両リンクで eBGP セッションを張り、RT01 はサービスプレフィックス
`10.100.0.0/24` を両セッションで RT02 に広告している。今は MED が両方とも 0 で、
RT02 から見て primary / backup どちらが best path に選ばれるかが運用ポリシーで保証されない。

RT01 側から **MED 属性** を使い、RT02 が常に **primary リンク経由** を best path として
選ぶように仕向けよ（inbound 制御）。

## トポロジ
```
                primary (10.1.12.0/30)
RT01 (AS65001) ═══════════════════ RT02 (AS65002)
   │    Lo100 = 10.100.0.0/24            │
   │                                    │
   └─── backup (10.1.122.0/30) ──────────┘
```

- 同じルータペアに対して **2 本の eBGP セッション** が並列で張られている。
- RT02 から見ると、`10.100.0.0/24` への eBGP パスが 2 本（primary / backup）見える。

## 到達目標
- 両 eBGP セッションは Established で維持される。
- RT02 の BGP テーブル / RIB において、`10.100.0.0/24` の **best path** が
  **primary リンク経由 (next-hop=10.1.12.1)** になる。
- best path に選ばれている entry の **metric (MED) = 10** であること。

## 制約
- 変更は **RT01 のみ**。RT02 は変更不可。
- 誘導には **MED (Multi-Exit Discriminator)** を使う。weight / local-preference /
  AS-path prepend は使用しない。
- MED の値:
  - primary 経路 (10.1.12.2 ピア向け outbound) = **10**
  - backup 経路 (10.1.122.2 ピア向け outbound) = **200**
- BGP プロセスや既存の `network` 文は変更しない。

## アクセス
- RT01: `10.1.10.11` / RT02: `10.1.10.12`（SSH, admin/CCNP）

## 採点
```
ansible-playbook playbooks/grade.yml -e problem=ENARSI-BGP-MED-01 --vault-password-file <(printf 'CCNP\n')
```
