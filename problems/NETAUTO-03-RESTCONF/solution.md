# 模範解答 : ネット自動化道場 03（RESTCONF入門）

## STEP 0: 機器側の有効化（コンソール）

```
configure terminal
 ip http secure-server
 ip http authentication local
 restconf
end
```

確認: `show platform software yang-management process`（pubd/dmiauthd 等が Running）。

## 穴の答え（全候補）

| id | 答え | 意味 |
|----|------|------|
| sh_yang_module | **ietf-interfaces** | IF設定の標準YANGモジュール。URL は `/restconf/data/<モジュール>:<コンテナ>` |
| py_get_method | **get** | 読み取り（show 相当）。冪等・安全 |
| py_accept | **json** | `application/yang-data+json` = RESTCONF の JSON メディアタイプ |
| py_put_method | **put** | URL の指すリソースを payload で丸ごと作成/置換 |
| py_if_type | **softwareLoopback** | `iana-if-type` モジュールの Loopback 種別。PUT で新規作成時は必須 |
| py_content_type | **json** | 書き込み時は Content-Type で payload 形式をサーバへ伝える（無いと 400） |

完成形は `controller_solution/` の3ファイル。

## 要点解説

- **PUT の payload はモジュール名で包む**: `{"ietf-interfaces:interface": {...}}`。
  URL のキー（`interface=Loopback100`）と payload 内の `"name": "Loopback100"` は一致必須。
- **201 と 204 の違い**: 201=リソースが新規作成された / 204=既存リソースを置換した。
  同じスクリプトを2回流すと 2回目は 204 になる（PUT の冪等性）。
- **GET で返る `ietf-ip:ipv4`** のようにキーに別モジュール名が付くのは YANG の augment
  （ietf-ip モジュールが ietf-interfaces を拡張して IP 情報を差し込んでいる）。
- **RESTCONF は 443 に同居**するため専用ポート開放は不要。NETCONF（次回）は 830/TCP。

## 採点基準（100点）

| チェック | 点 |
|----------|----|
| `restconf` が running-config にある | 20 |
| `ip http secure-server` が有効（`no ip http secure-server` は不可） | 20 |
| Loopback100 に 172.16.100.1/32 | 30 |
| Loopback100 の description = CONFIGURED-BY-RESTCONF | 30 |
