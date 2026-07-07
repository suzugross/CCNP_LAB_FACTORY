# 問題 ENCOR-EEM-01 : EEM による設定変更時の自動保存

## シナリオ
RT01 では、設定変更後に保存し忘れて再起動で構成が失われる事故が頻発しています。
**設定変更を検知して自動的に保存する**仕組みを、ルータ自身のイベント機構で実装してください。

## 到達目標
- 管理者が設定モードを抜けて running-config が変更された（`%SYS-5-CONFIG_I` のログが出力される）ことを契機に、
- running-config を startup-config へ**自動保存**し、
- `Config saved by EEM` という文字列を含むログメッセージを記録する。

## 制約
- 定期実行（cron / kron など時間ベース）ではなく、**イベント駆動（EEM）**で実装すること。
- 既存のインタフェース設定は変更しないこと。

## 採点
```
ansible-playbook playbooks/grade.yml -e problem=ENCOR-EEM-01 --vault-password-file <(printf 'CCNP\n')
```
