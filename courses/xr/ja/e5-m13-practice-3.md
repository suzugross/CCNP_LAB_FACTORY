# M13 — 実践(3) フローと SNMP

ラボ **XRT-15** の課題です。ラボから離れた場所でも読めるように、ここに載せています。
取り組むのはラボのワークスペースです。**Tasks** タブに、課題ごとの確認ボタン、段階式のヒント、
通過後に開く模範解があります。コマンド例は意図して示していません。

## M13 — 自動化とアシュアランス

### 課題 M13-5
<p class="tolab"><a href="/_learn?id=XRT-15&amp;step=m13t5">ワークスペースで開く</a> — 読み物: <a href="e4-m13-flow-snmp.html#s2-1">2.1 フローとフロー キャッシュ</a> · <a href="e4-m13-flow-snmp.html#s2-2">2.2 タイムアウト: レコードがキャッシュを出るとき</a> · <a href="e4-m13-flow-snmp.html#s2-3">2.3 エクスポート: NetFlow v9 と IPFIX のテンプレート</a> · <a href="e4-m13-flow-snmp.html#s3-1">3.1 IOS XE の Flexible NetFlow</a> · <a href="e4-m13-flow-snmp.html#s3-4">3.4 確かめ方</a></p>


NMS は IPFIX でフローのレコードを集めます。

- PE2 で、顧客 A から入ってくる(GigabitEthernet2)IPv4 の通信を記録してください。各フローのレコードには、送信元と宛先の
  アドレス、プロトコル、送信元と宛先のポート、入力インタフェースと、パケット数とバイト数を含めます。
- レコードは、Loopback0 から、IPFIX で SRV01 のフローの収集役へエクスポートしてください。
- 長く続くフローは、少なくとも 60 秒ごとに報告してください。

### 課題 M13-6
<p class="tolab"><a href="/_learn?id=XRT-15&amp;step=m13t6">ワークスペースで開く</a> — 読み物: <a href="e4-m13-flow-snmp.html#s2-6">2.6 SNMPv2c: コミュニティとアクセス リスト</a> · <a href="e4-m13-flow-snmp.html#s2-7">2.7 SNMPv3: ユーザ、グループ、ビュー、エンジン ID</a> · <a href="e4-m13-flow-snmp.html#s2-8">2.8 トラップとインフォーム</a> · <a href="e4-m13-flow-snmp.html#s3-3">3.3 IOS XR の SNMP</a> · <a href="e4-m13-flow-snmp.html#s3-4">3.4 確かめ方</a></p>


前任者は、NMS のために XR01 に SNMP を設定しました。うまく動いていないことが 2 つあります。

- NMS は、SNMPv2c、コミュニティ `NMS-RO`、読み取り専用で XR01 を読み取ります。このコミュニティを使ってよいのは SRV01 だけです。
  現在、SRV01 には応答がありません。
- XR01 は、リンクがダウンしたときとアップに戻ったときの両方で、SNMPv3(ユーザ `nms-trap`、認証と暗号化)のトラップを
  SRV01 のトラップの受け手へ送る必要があります。現在、トラップの受け手には何も届きません。
- コミュニティ、ユーザ、それらのパスワードは変更しないでください。SRV01 は変更しないでください。
