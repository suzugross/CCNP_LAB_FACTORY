# M13 — 実践(1) モデルで設定する

ラボ **XRT-15** の課題です。ラボから離れた場所でも読めるように、ここに載せています。
取り組むのはラボのワークスペースです。**Tasks** タブに、課題ごとの確認ボタン、段階式のヒント、
通過後に開く模範解があります。コマンド例は意図して示していません。

## 進め方の約束

- 設定するのは **XR01** と **PE2** で、作業はネットワーク管理ステーション(NMS)の **SRV01** の上でも行います。SRV01 には
  ワークスペースのコンソールから、ラボのアカウントでログインします。CE1 は顧客のもので据え付けです。変更しないでください。
- SRV01 の受け手(テレメトリの収集役 telegraf、フローの収集役 nfcapd-lab、トラップの受け手 snmptrapd-lab)は変更しないで
  ください。それらのファイルを読むことや、SRV01 で自分のプログラムを別に起動することは構いません。
- 課題の中にはコマンド例を示しません。各課題は必要な動作を記述しています。SRV01 には道具が入っていますが、使い方は
  自分で調べてください(`--help`、`man`、Cisco のガイド)。NETCONF に限り、スクリプトの雛形を用意してあります。
- **Tasks** タブには課題ごとに **Check** ボタンがあります。デバイスと SRV01 の現在の状態を読み取ります。
  押す前にコンフィギュレーション モードを抜けてください。確認の中には、試験のトラフィックを流したり、リンクをいったん
  落として戻したりして、SRV01 に届いた数を数えるものがあり、1 回に 1〜2 分かかります。
- ヒントは 1 段ずつ開きます(キーワード → 参照先 → コマンド)。開いたヒントは記録されます。
- 各課題には **確かめ方** のボタンもあります。設定が入ったか → 送って数える → 届いた先を見る → 壊していないか、の順に
  確かめる手順の例です。いつ開いても構わず、記録されません。Check を押す前に、自分の手で確かめてみてください。
- **Tasks** タブの **最初からやり直す** は、XR01、PE2、SRV01 をラボの構築直後の状態へ戻します。SRV01 では、ホームのファイル
  (`~/m13` の雛形を含む)と受け手の記録が元に戻り、自分で起動したプログラムは止まります。シェルの履歴は残ります。
- XR01 は **IOS XRd** 26.1.1(IOS XR のコンテナ版)、PE2 は **Catalyst 8000V**(IOS XE 17.15)で動作しています。
  このラボの IOS XR では RESTCONF と NetFlow を使えないため、それらの課題は PE2 で行います。

## トポロジ

| リンク | 両端 | アドレス |
|---|---|---|
| CORE | XR01 GigabitEthernet0/0/0/0 ─ PE2 GigabitEthernet1 | 10.0.12.0/24(XR01 .1、PE2 .2) |
| NMS | SW1(非管理スイッチ): XR01 GigabitEthernet0/0/0/1、PE2 GigabitEthernet3、SRV01 ens3 | 10.0.50.0/24(XR01 .1、PE2 .2、SRV01 .10) |
| ACCESS-A | PE2 GigabitEthernet2 ─ CE1 Ethernet0/0 | 172.16.1.0/24(CE1 .1、PE2 .254) |
| BACKUP-A | XR01 GigabitEthernet0/0/0/2 ─ CE1 Ethernet0/1 | 172.16.2.0/24(XR01 .1、CE1 .2) |

| デバイス | 役割 | プラットフォーム | Loopback0 |
|---|---|---|---|
| XR01 | プロバイダー エッジ | IOS XRd 26.1.1 | 10.255.0.1/32 |
| PE2 | プロバイダー エッジ | Catalyst 8000V、IOS XE 17.15 | 10.255.0.2/32 |
| CE1 | 顧客 A(据え付け) | IOS XE 17.15 | LAN 192.168.100.0/24(Loopback100 192.168.100.1) |
| SRV01 | NMS | Ubuntu 24.04 | —(NMS の区画の 10.0.50.10) |

- XR01 と PE2 は IS-IS インスタンス `CORE`(レベル 2)を動作させています。NMS の区画とループバックはパッシブです。PE2 は
  顧客 A の LAN へのスタティック ルートを持ち、IS-IS に再配送しています。
- CE1 は PE2 を経由して送信します(172.16.1.254 へのデフォルト ルート)。XR01 への予備のリンクは、主のリンクが故障しない限り
  通信を運びません(ディスタンス 250 のデフォルト ルート)。
- SRV01 は、NMS の区画の上で XR01 と PE2 に直接届き、それぞれのループバックへはそれらを経由して届きます。

SRV01 が提供するもの:

| サービス | 待ち受け | 書き込み先 |
|---|---|---|
| テレメトリの収集役(telegraf): gRPC のダイヤルアウト、TLS のみ | TCP 57500 | `/var/log/telegraf/mdt.json`(1 行に 1 つの JSON) |
| フローの収集役(nfcapd-lab): NetFlow v9 と IPFIX | UDP 4739 | `/var/cache/nfdump/lab/`(1 分ごとに新しいファイル。`nfdump` で読む) |
| トラップの受け手(snmptrapd-lab): SNMPv3、ユーザ `nms-trap`、authPriv のみ | UDP 162 | `/var/log/snmptrapd-lab.log` |

| SRV01 のファイル | 内容 |
|---|---|
| `~/pki/ca.pem` | NMS の認証局(NMS-LAB-CA)の証明書。以下の証明書はこの認証局が発行しました。 |
| `~/pki/client.pem`、`~/pki/client.key` | gNMI 用の、NMS のクライアント証明書と鍵(CN `nms-gnmi`)。 |
| `~/m13/nc_edit.py` | 課題 M13-1 用の NETCONF の雛形(ncclient)。`__FILL__` の所を埋めて使います。 |
| `~/m13/rc_customer_lo.py` | 課題 M13-2 用の、NMS チームの RESTCONF のスクリプト。編集しないでください。 |

- テレメトリの収集役の証明書は、NMS-LAB-CA が、名前 `collector.nms.lab` とアドレス 10.0.50.10 に対して発行したものです。
- XR01 の SNMP のエンジン ID は固定してあり(`snmp-server engineID local`)、トラップの受け手はそれを知っています。
  変更しないでください。

## M13 — 自動化とアシュアランス

### 課題 M13-1
<p class="tolab"><a href="/_learn?id=XRT-15&amp;step=m13t1">ワークスペースで開く</a> — 読み物: <a href="e0-m13-netconf-yang.html#s2-1">2.1 YANG: 設定と状態のモデル</a> · <a href="e0-m13-netconf-yang.html#s2-2">2.2 IOS XR の 3 つのモデルの系統</a> · <a href="e0-m13-netconf-yang.html#s2-3">2.3 NETCONF: SSH の上のセッション、RPC、データストア</a> · <a href="e0-m13-netconf-yang.html#s2-4">2.4 candidate・commit・confirmed commit</a> · <a href="e0-m13-netconf-yang.html#s3-1">3.1 IOS XR で NETCONF を有効にする</a> · <a href="e0-m13-netconf-yang.html#s3-2">3.2 Python(ncclient)から NETCONF セッションを張る</a> · <a href="e0-m13-netconf-yang.html#s3-3">3.3 NETCONF の変更はどこに出るか</a></p>


NMS チームは、XR01 を NETCONF で管理します。

- XR01 が、NETCONF の標準のポートで、SSH 上の NETCONF を NMS の区画(グローバルのルーティング テーブル)で受け付けるように
  してください。
- SRV01 から NETCONF で、XR01 に Loopback100 を追加してください。説明は `NMS-MANAGED`、アドレスは 10.255.100.1/32 です。
  この変更は CLI で行わないでください。XR01 のコミット履歴に、NETCONF による変更として残る必要があります。

### 課題 M13-2
<p class="tolab"><a href="/_learn?id=XRT-15&amp;step=m13t2">ワークスペースで開く</a> — 読み物: <a href="e0-m13-netconf-yang.html#s2-5">2.5 RESTCONF: 同じモデルを HTTPS で</a> · <a href="e0-m13-netconf-yang.html#s2-6">2.6 外部のスクリプトを読む</a> · <a href="e0-m13-netconf-yang.html#s3-4">3.4 IOS XE で RESTCONF を有効にする</a> · <a href="e0-m13-netconf-yang.html#s3-5">3.5 確かめ方</a></p>


NMS チームのスクリプト `~/m13/rc_customer_lo.py` は、RESTCONF で PE2 に顧客 A のサービス用のループバックを追加します。
現在、このスクリプトは失敗します。

- スクリプトを変更せずに最後まで実行できるよう PE2 を準備し、スクリプトを 1 回実行してください。
- スクリプトが使うアカウントは、PE2 のローカル アカウントにしてください。
- PE2 は平文の HTTP を開かないでください。
