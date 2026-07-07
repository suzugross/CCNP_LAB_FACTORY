# 模範解答 : ENCOR-EEM-01

```
event manager applet AUTO-SAVE
 event syslog pattern "%SYS-5-CONFIG_I"
 action 1.0 cli command "enable"
 action 2.0 cli command "write memory"
 action 3.0 syslog msg "Config saved by EEM"
```

## 確認
```
show running-config | section event manager
show event manager policy registered      ! 登録(アクティブ)確認
! 実際に conf t → 何か変更 → exit すると AUTO-SAVE が発火し保存される
```

### ポイント（落とし穴の解説）
- 契機は **`event syslog pattern`**。設定変更は `%SYS-5-CONFIG_I`（"Configured from console by ..."）が
  出るので、これを正規表現パターンで拾う。`event none`（手動）や `event timer`（時間）ではない。
- アクションは複数を **`action <ラベル>`** で順に並べる。ラベル(例 1.0, 2.0)順に実行される。
- 保存は exec コマンド `write memory`（= `copy running-config startup-config`）。
  applet 内から exec を叩くため `cli command` を使う。環境によっては先頭で `cli command "enable"` を入れる。
- `action ... syslog msg "..."` で任意ログを残せる。本問は `Config saved by EEM` を含むこと。

> 採点は running-config の event manager セクションに、
> ①CONFIG 変更を拾う syslog イベント ②設定保存アクション ③指定メッセージのログ
> の 3 要素が揃っているかで判定する。アプレット名・ラベルは任意。
