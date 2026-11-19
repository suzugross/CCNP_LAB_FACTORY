# J0 — 付録

## 1. Junos OS と Junos OS Evolved

Juniper は、Junos の名で 2 つの OS を出しています。**Junos OS** は FreeBSD のカーネルの上でコマンド シェルを動かす OS で、
MX・EX・SRX のシリーズのようなルータ・スイッチ・ファイアウォールで出会います。**Junos OS Evolved** は Linux の上で動き、
ACX・PTX と一部の QFX が使います。CLI と設定はどちらも同じなので、このトラックのページはどちらにも当てはまります。
機能や既定が違う所では、ページでそう断ります。

どちらかは `show version` で分かります。

```console
admin@jun01> show version | match Junos
Junos: 26.2R1.7-EVOI20260619095247-evo-builder-1
JUNOS-EVO OS 64-bit [junos-evo-install-ptx-fixed-x86-64-26.2R1.7-EVOI20260619095247-evo-builder-1]
```

リリース名の `EVO` が Junos OS Evolved の印です。

## 2. このラボの仮想ルータ

ラボの Junos のルータは **vJunos-Evolved** です。Junos OS Evolved の無償の仮想版で、containerlab で動かしています。
そこで目にするもののいくつかは、Junos そのものでなく仮想ルータから来ています。

- **PTX である。** Juniper は vJunos-Evolved を PTX10001-36MR をもとに作っていて、`show version` は `Model: ptx10001-36mr` と
  出します。ポートが `et-` であるのも、PTX で違う既定(BGP のデフォルト ポリシーなど)が当てはまるのも、このためです。
- **ライセンスの知らせ。** OSPF を commit すると `warning: requires 'OSPF' license` が出て、`show ospf neighbor` の頭に
  `Warning: License key missing` が出ます。Juniper の vJunos-Evolved のガイドは、ライセンスは要らず、ライセンスの知らせは
  無視してよいとしています。OSPF は動きます。
- **制限。** 転送できるのは毎秒数千パケットまでで、Juniper は対応しない機能を挙げています。その中に VRRP とマルチキャストが
  あります。それらが要る単元では別のルータを使います。
- **管理ネットワークは独立したルーティング インスタンス。** コンテナの起動時の設定に `set system management-instance` が入っていて、
  管理ポート `re0:mgmt-0` はインスタンス `mgmt_junos` に入っています。その経路は `inet.0` とは別の `mgmt_junos.inet.0` にあるので、
  ラボで変える経路は、あなた自身の接続を運ぶ経路ではありません。
- **ポートは少し遅れて現れる。** コンテナがルータを healthy と報告してから 1 分ほどは、`et-0/0/0` がまだありません
  (`error: device et-0/0/0 not found`)。その間も設定はできます。設定はポートが現れるのを待ちます。
- **内部のユニット。** ポートには、ファミリー `multiservice` のユニット `16386`(VLAN タグ付きのポートでは `32767`)が出ます。
  ルータが自分で作るもので、設定も使用もしません。
- **テーブルがもう 2 つ。** `show route` には、direct の経路の写しを持つ `inet.2` と `inet.3` も並びます。J0 では使いません。
- **最初の commit。** `show system commit` のいちばん古い行(`by root via other`)は、コンテナが読み込んだ起動時の設定です。

## 3. 1 枚の早見表

| したいこと | IOS | IOS XR | Junos |
|---|---|---|---|
| 設定に入る | `configure terminal` | `configure` | `configure`(`private`・`exclusive`) |
| 設定の中から show を打つ | `do show …` | `do show …` | `run show …` |
| 入れる前に変更を見る | — | `show configuration` | `show \| compare` |
| 入れる | 打つたびに | `commit` | `commit`(`check`・`confirmed n`・`comment`・`and-quit`) |
| コマンドの形で出す | `show running-config` | `show running-config` | `show configuration \| display set` |
| commit を並べる | — | `show configuration commit list` | `show system commit` |
| 変更を 1 つ戻す | — | `rollback configuration last 1` | `rollback 1` のあと `commit` |
| インターフェースにアドレス | インターフェースの下で `ip address` | インターフェースの下で `ipv4 address` | `set interfaces <ポート> unit <n> family inet address <a/長さ>` |
| インターフェースを止める | `shutdown` | `shutdown` | `set interfaces <ポート> disable` |
| インターフェースの状態の一覧 | `show ip interface brief` | `show ipv4 interface brief` | `show interfaces terse` |
| ルーティング テーブル | `show ip route` | `show route` | `show route table inet.0` |
| インターフェースで OSPF を動かす | `network …` か `ip ospf … area` | エリアの下に `interface` | `set protocols ospf area <a> interface <ユニット>` |
| OSPF へ再配送する | `redistribute …` | `redistribute …` | export ポリシー(後の単元) |

## 4. 調べる場所

- ルータの上: どの語の後ろでも `?`。語を含むコマンドは `help apropos <語>`。
- Juniper の文書はガイドごとにまとまっています。この単元の裏にあるのは『CLI User Guide for Junos OS』『Interfaces Fundamentals
  for Junos OS』『Junos OS Routing Protocols Overview』『Routing Policies, Firewall Filters, and Traffic Policers User Guide』です。

:::note
出典: Juniper Networks『vJunosEvolved Deployment Guide』(2025-11-11)のもとにしたルータ・ライセンス・限り・対応しない機能、
『CLI User Guide for Junos OS』(2026-06-18)の Junos OS の FreeBSD カーネル、『Junos OS Evolved Release 26.2R1 Release Notes』
(2026-10-22)の Junos OS Evolved の機種。IOS XR の列は IOS XR トラックによる。出力は vJunos-Evolved
(Junos OS Evolved 26.2R1.7)で取ったものです。
:::
