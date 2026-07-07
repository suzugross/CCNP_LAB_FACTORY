# 問題 ENARSI-BGP-COMM-01 : BGP community でタグ付け→マッチ→local-pref 適用

## シナリオ
顧客 AS65001 のプロバイダ AS65002 では、複数顧客の経路に **community によるタグ付け**
で分類管理を行いたい。RT01 (顧客) は自分の経路 `10.100.0.0/24` に **community
`65002:100`** を付けて広告し、RT02 (プロバイダエッジ) はこのタグを見て **local-pref
を 200 に引き上げる** ポリシーを適用する。

## トポロジ
```
RT01 (AS65001) ─── eBGP ─── RT02 (AS65002)
   Lo100 = 10.100.0.0/24
                  10.1.12.0/30
```

## 到達目標
- eBGP セッション (10.1.12.0/30) は Established で維持される。
- RT01 は `10.100.0.0/24` に community **65002:100** を付与し、RT02 に **届く** こと。
- RT02 は受信したこの community を見て、`10.100.0.0/24` の **local-preference を 200**
  に設定する。

## 制約
- 変更対象は **RT01 と RT02 の両方**。
- community 値 (受験者は固定値を使う): **`65002:100`**
- local-pref 値: **`200`**
- 既存の interface IP / BGP プロセス / `network` 文は変更しない。
- community を「設定するだけ」では update に乗らない（特定のオプションが要る）。
  この点も含めて完成させること。

## アクセス
- RT01: `10.1.10.11` / RT02: `10.1.10.12`（SSH, admin/CCNP）

## 採点
```
ansible-playbook playbooks/grade.yml -e problem=ENARSI-BGP-COMM-01 --vault-password-file <(printf 'CCNP\n')
```
