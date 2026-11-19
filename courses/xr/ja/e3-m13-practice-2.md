# M13 — 実践(2) gNMI とテレメトリ

ラボ **XRT-15** の課題です。ラボから離れた場所でも読めるように、ここに載せています。
取り組むのはラボのワークスペースです。**Tasks** タブに、課題ごとの確認ボタン、段階式のヒント、
通過後に開く模範解があります。コマンド例は意図して示していません。

## M13 — 自動化とアシュアランス

### 課題 M13-3
<p class="tolab"><a href="/_learn?id=XRT-15&amp;step=m13t3">ワークスペースで開く</a> — 読み物: <a href="e15-m13-certificates.html#s2-4">2.4 CA: 署名を信じる起点</a> · <a href="e15-m13-certificates.html#s2-5">2.5 確かめる 4 つ</a> · <a href="e15-m13-certificates.html#s2-6">2.6 相互 TLS と、線ごとの役</a> · <a href="e15-m13-certificates.html#s3-3">3.3 自己署名の証明書と、中間 CA を挟んだ証明書チェーン</a> · <a href="e2-m13-gnmi-telemetry.html#s2-1">2.1 gRPC と gNMI</a> · <a href="e2-m13-gnmi-telemetry.html#s2-3">2.3 ダイヤルインとダイヤルアウト</a> · <a href="e2-m13-gnmi-telemetry.html#s2-5">2.5 TLS と相互 TLS: 誰が何を証明するか</a> · <a href="e2-m13-gnmi-telemetry.html#s3-1">3.1 gRPC サーバ: TLS と相互 TLS</a> · <a href="e2-m13-gnmi-telemetry.html#s3-2">3.2 IOS XR に証明書を置く</a></p>


NMS は gNMI で XR01 を読み取ります。

- XR01 の gRPC サーバを、ポート 57400、NMS の区画(グローバルのルーティング テーブル)で、TLS を使って動作させてください。
- NMS の認証局(`~/pki/ca.pem`)が発行した証明書を提示するクライアントだけを受け付けてください。NMS は `~/pki/client.pem` と
  `~/pki/client.key` を使い、ログインには引き続きラボのアカウントを使います。
- TLS を使わない gRPC は拒否してください。

### 課題 M13-4
<p class="tolab"><a href="/_learn?id=XRT-15&amp;step=m13t4">ワークスペースで開く</a> — 読み物: <a href="e15-m13-certificates.html#s2-5">2.5 確かめる 4 つ</a> · <a href="e15-m13-certificates.html#s2-6">2.6 相互 TLS と、線ごとの役</a> · <a href="e15-m13-certificates.html#s3-2">3.2 確かめる: openssl s_client</a> · <a href="e2-m13-gnmi-telemetry.html#s2-2">2.2 Subscribe: STREAM・ONCE・POLL</a> · <a href="e2-m13-gnmi-telemetry.html#s2-3">2.3 ダイヤルインとダイヤルアウト</a> · <a href="e2-m13-gnmi-telemetry.html#s2-4">2.4 エンコードとセンサー パス</a> · <a href="e2-m13-gnmi-telemetry.html#s2-5">2.5 TLS と相互 TLS: 誰が何を証明するか</a> · <a href="e2-m13-gnmi-telemetry.html#s3-3">3.3 ダイヤルアウト: センサー グループ・宛先グループ・サブスクリプション</a> · <a href="e2-m13-gnmi-telemetry.html#s3-4">3.4 確かめ方</a></p>


前任者は、XR01 のインタフェースのカウンタを、SRV01 のテレメトリの収集役へ、TLS を使った gRPC のダイヤルアウトで、10 秒ごとに、
サブスクリプション `SUB-IF` で流すように設定しました。これまで何も届いていません。

- XR01 のインタフェースのパケットのカウンタが、サブスクリプション `SUB-IF` で、10 秒ごとに収集役へ届くようにしてください。
- TLS は維持してください。XR01 は収集役の証明書を検証する必要があります。
- 収集役は変更しないでください。
