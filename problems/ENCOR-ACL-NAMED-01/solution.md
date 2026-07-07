# 模範解答 : ENCOR-ACL-NAMED-01

設定するのは **RT02 のみ**。既存 ACL を作り直さず、シーケンス番号で挿入する。

```
ip access-list extended WEB-FILTER
 5 deny tcp any host 3.3.3.3 eq telnet
```

結果:
```
Extended IP access list WEB-FILTER
    5 deny tcp any host 3.3.3.3 eq telnet
    10 permit ip any any
```

## 確認
```
show ip access-lists WEB-FILTER          ! 5 deny が 10 permit の前にある
show running-config interface Ethernet0/0 ! ip access-group WEB-FILTER in が残存
```

## ポイント（落とし穴の解説）
- **名前付き ACL のシーケンス挿入**: 名前付き ACL の config モードでは、行頭に
  シーケンス番号を付けると**その位置に挿入**できる。`5 deny ...` は seq 10 の前に入る。
- ★**番号を付けないと末尾追加**: 単に `deny tcp any host 3.3.3.3 eq telnet` と打つと
  seq 20（末尾）に入り、`10 permit ip any any` が先にマッチして **deny が一切効かない**。
  これが first-match の落とし穴。採点の「順序」チェックがこれを検出する。
- **作り直しは禁止**: `no ip access-list extended WEB-FILTER` してから書き直すと、適用が
  外れたり既存エントリを失うリスクがある。番号付き挿入なら無停止で安全に編集できる。
- 番号は 1〜9 のいずれでも可（10 未満なら permit より前）。
