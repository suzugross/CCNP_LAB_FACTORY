# M11 追補 — イーサネット OAM

ここまでのページでは、サービスを作りました。このページでは、1 つのサービスを見張ります。E-Line 130 は、XE1 と XE3 の間の
LDP の疑似回線で拠点 1 と拠点 3 をつないでいて、据え付けです。プロバイダーは、これが切れたときにすぐ知りたく、またフレームが
渡るのにどれだけかかるかも知りたいと考えています。顧客からの苦情を頼りにせずにです。ラボは引き続き XRT-12 で、
課題 M11-9 がこのページにあたります。

:::topo
nodes:
  CE1: {at: [0, 1], label: "CE1(拠点 1)"}
  XE1: {at: [1.8, 1], label: "XE1(MEP 1)"}
  P1: {at: [3.6, 1], label: "P1"}
  XE3: {at: [5.4, 1], label: "XE3(MEP 3)"}
  CE3: {at: [7.2, 1], label: "CE3(拠点 3)"}
links:
  - [CE1, XE1, "VLAN 130"]
  - [XE1, P1, "疑似回線 130"]
  - [P1, XE3, "疑似回線 130"]
  - [XE3, CE3, "VLAN 130"]
frames:
  - {label: "メンテナンス ドメイン PROV(レベル 4)", nodes: [XE1, P1, XE3]}
:::

## 1. 何が嬉しいのか

### 1.1 誰も気づかない切断

XE3 と P1 の間のリンクが、両方のポートは up のまま、パケットを全部捨て始めたとします。通信事業者の伝送装置の中の故障や、
途中の機器の混雑や設定の誤りです。どのインタフェースも down にならないので、すぐに反応するものはありません。ラボでは、
そういう故障(CML のリンク条件で 100 % の廃棄)を XE3 と P1 の間に入れました。10 秒後も P1 の IS-IS と LDP は隣接を up と
表示し、疑似回線も両端で UP のままでした。その間、顧客の通信は止まっていました。

### 1.2 それまでの手: ルーティング プロトコルか、顧客を待つ

ほかに何も無ければ、プロバイダーが気づくのは次のどちらかです。

- **制御プロトコルが時間切れになる。** IS-IS(保持時間は既定で 30 秒)か LDP が隣接をあきらめ、疑似回線が down になります。
  数十秒かかり、しかも制御のトラフィックも巻き込まれる故障しか拾えません。
- **顧客が電話してくる。** CE どうしは E-Line 越しに ping できますが、CE は顧客のものです。

PE が E-Line 越しに ping することもできません。アタッチメント回線には IP アドレスが無く、中を通るのは顧客のフレーム
だからです。

### 1.3 この技術の答え: サービスそのものに CFM を

**CFM**(Connectivity Fault Management、IEEE 802.1ag)は、イーサネットのサービスそのものに監視点を置きます。E-Line の両端の
**MEP**(メンテナンスの端点)は、顧客のフレームと同じ道を通る小さなイーサネットのフレーム、**連続性チェックの
メッセージ**(CCM)を送り、相手の端の CCM を待ちます。それが途絶えれば、原因が何であれ、MEP はサービスが切れたと分かります。
CFM には、ループバック(イーサネットの ping)とリンクトレース(イーサネットの traceroute)もあります。ITU-T の **Y.1731** は、
同じ MEP の上で、フレームの遅延、遅延の揺らぎ、損失を測ります。

## 2. CFM の仕組み

### 2.1 メンテナンス ドメインとレベル

**メンテナンス ドメイン**は、1 つの立場の者が見張る網の範囲で、0〜7 の **レベル** を持ちます。IEEE 802.1ag は、顧客に
5〜7、サービス プロバイダーに 3 と 4、オペレーターに 0〜2 を勧めています。MEP は、自分のレベルの CFM のフレームを扱い、
それより低いレベルのものは捨て、高いレベルのものは手を付けずに通します。そのためドメインは入れ子にできます。顧客は
CE どうしでレベル 5 の CFM を動かせ、それはプロバイダーのレベル 4 のドメインをそのまま通り抜け、プロバイダーの MEP がそれを
自分のものと取り違えることはありません。

このラボのプロバイダーのドメインは、レベル **4** の **PROV** です。

### 2.2 メンテナンス アソシエーションと MEP

ドメインの中で、**メンテナンス アソシエーション**(MA。IOS XE では *service* と呼ぶ)は、見張る 1 つのサービスです。
ここでは E-Line 130 です。MA ごとに MEP があり、それぞれ番号を持ちます(**MEP ID**、MPID)。MEP は、同じ MA の MEP を、
その CCM から覚えます。

MEP には向きがあります。**down MEP** は線の方を向き、CCM をポートから CE の方へ送ります。**up MEP** は機器の内側を向き、
CCM をサービスの中へ、ここでは疑似回線の中を相手の PE へ送ります。プロバイダーの受け持ちの区間(XE1 のアタッチメント回線から
XE3 のアタッチメント回線まで)を見張るには、MEP はアタッチメント回線の上の up MEP にします。このラボ(EFP を LDP の疑似回線に
クロスコネクトする形)では、EFP の上の MEP は up MEP で、出力の `Dir` に `Up` と出ます。EVPN の E-Line では事情が違います(3.3)。

### 2.3 連続性チェック: CCM と寿命

各 MEP は **間隔** ごとに CCM を送ります。相手の MEP はそれを表に持ち、CCM の来ない状態が **間隔の 3.5 倍** 続くと、その行は
期限切れになります。そのとき MEP は、相手の端を失ったと判断します。

| CC の間隔 | 失ったと判断するまで | ラボで、XE3 と P1 の間の黙った故障の後 |
|---|---|---|
| 10 秒(IOS XE の既定) | 35 秒 | 10 秒後も XE1 は MEP 3 を表に持っていた |
| 1 秒 | 3.5 秒 | XE1 から MEP 3 は 3.2 秒までに消え、XE3 からも MEP 1 が同じように消えた |

間隔がそのまま損得です。短くすれば早く気づき、そのぶん CCM を多く送ります。100 ms 以下の間隔は保護の切り替え用で、
サービスの監視には 1 秒がよく使われます。

### 2.4 ループバックとリンクトレース

MEP があれば、PE はサービスの中で ping と traceroute ができます。

```console
XE1#ping ethernet mpid 3 domain PROV service E130
Sending 5 Ethernet CFM loopback messages to 001e.14d8.53bf, timeout is 5 seconds:!!!!!
Success rate is 100 percent (5/5), round-trip min/avg/max = 1/1/3 ms
XE1#traceroute ethernet mpid 3 domain PROV service E130
Tracing the route to 001e.14d8.53bf on Domain PROV, Level 4, service E130, evc E130
Traceroute sent via Gi2:(10.255.0.43, 130), path found via MPDB
                             MAC      Ingress        Ingr Action  Relay Action
  Hops   Host             Forwarded   Egress         Egr Action   Previous Hop
B 1                    001e.f607.b6bf Gi2            IngOk        RlyMPDB
                       Forwarded
! 2                    001e.14d8.53bf                             RlyHit:MEP
                       Not Forwarded                              001e.f607.b6bf
```

ループバックは、相手の MEP の MAC アドレスまで行って戻ります(LBM と LBR)。リンクトレースは、CFM を扱うホップを順に並べます。
XE1 自身(`B`= 転送したブリッジ)、次に MEP 3(`!`)です。P1 は出てきません。疑似回線の中では、P1 はラベルを付け替えるだけで、
イーサネットのフレームを見ないからです。

### 2.5 Y.1731: 遅延を測る

Y.1731 の **遅延の測定**では、一方の MEP が相手に DMM(遅延の測定のメッセージ)を送り、相手は DMR で答えます。タイムスタンプ
から、フレームの往復の遅延が分かります。IOS XE では IP SLA の操作がこれを動かし、統計を取ります。ラボでは毎秒 1 つの DMM を
送り、往復の遅延は 0.7〜1.9 ms ほどでした。

```console
XE1#show ip sla statistics 130 details
Type of operation: Y1731 Delay Measurement
Latest operation return code: OK
 Number of measurements initiated: 29
 Number of measurements completed: 29
Delay:
  Number of TwoWay observations: 24
    Min/Avg/Max TwoWay: 688/1275/1916 (microsec)
Operation time to live: Forever
Operational state of entry: Active
```

## 3. IOS XE での CFM の設定

### 3.1 設定

3 つの部分からなります。CFM を全体で有効にすること、ドメインとそのサービス、そしてアタッチメント回線の上の MEP です。
E-Line の EFP は、すでに EVC `E130` の名前が付いていて(`service instance 130 ethernet E130`)、サービスはそれで EFP を見つけます。

:::config fold Catalyst 8000V(IOS XE 17.15)— E-Line 130 の CFM と Y.1731 の遅延測定の XE1 の分(XE3 は MPID 3 で IP SLA なし)
ethernet cfm global                                ## ルータ全体で CFM を有効に。無いと MEP は無効のまま
ethernet cfm domain PROV level 4                   ## プロバイダーのドメイン
 service E130 evc E130                             ## E-Line 130 の MA。xconnect の EVC には VLAN を書かない
  continuity-check                                 ## CCM を送る
  continuity-check interval 1s                     ## 3.5 秒で失ったと判断(既定の 10 秒なら 35 秒)
!
interface GigabitEthernet2
 service instance 130 ethernet E130                ## E-Line の EFP(据え付け)
  cfm mep domain PROV mpid 1                       ## up MEP。MEP ID は拠点の番号
!
ip sla 130
 ethernet y1731 delay DMM domain PROV evc E130 mpid 3 cos 0 source mpid 1   ## MEP 1 から MEP 3 へ DMM。CoS 0
ip sla schedule 130 start-time now life forever    ## 終わりなく動かす
!
:::

### 3.2 出力の読み方

`show ethernet cfm maintenance-points local` は、この PE の MEP の一覧です。`CC` の列は、その MEP が CCM を送っているかを
示します。`Y` か、CFM が全体で有効になっていないときの `I`(無効)です。

```console
XE1#show ethernet cfm maintenance-points local
MPID Domain Name                                 Lvl   MacAddress     Type  CC
1    PROV                                        4     001e.f607.b6bf XCON  Y
```

`show ethernet cfm maintenance-points remote` は、CCM から覚えた MEP の一覧です。期限が切れた行は消え、そのとき
`show ethernet cfm errors` に失ったことが出ます。

```console
XE1#show ethernet cfm maintenance-points remote
MPID  Domain Name                                 MacAddress          IfSt  PtSt
 Lvl  Domain ID                                   Ingress
 RDI  MA Name                                     Type Id             SrvcInst
      EVC Name                                                        Age
      Local MEP Info
3     PROV                                        001e.14d8.53bf      Up    Up
 4    PROV                                        Gi2:(10.255.0.43, 130)
 -    E130                                        XCON N/A            130
      E130                                                            0s
      MPID: 1 Domain: PROV MA: E130
Total Remote MEPs: 1
```

`Ingress` は CCM の届いた場所です。Gi2 の E-Line の、10.255.0.43 への VC ID 130 の疑似回線からです。

### 3.3 うまくいかないとき

| 間違い | ラボで見えたこと |
|---|---|
| `ethernet cfm global` が無い | MEP はあるが `CC` が `I` で、相手の MEP を一度も覚えない |
| CC の間隔が既定のまま | 黙った故障に気づくのは 35 秒後(ラボでは 10 秒後も表に残っていた) |
| xconnect なのに `service … evc … vlan <n>` | 拒否される。service の行の VLAN はブリッジ ドメインのサービス用(PoC で確認) |
| Y.1731 が動いている間に相手の端を失う | 操作は `Latest operation return code: Internal error` で止まり、MEP 3 が戻っても再開しなかった。設定モードの `ip sla restart 130` で再開した |

PoC では、EVPN-VPWS の E-Line の EFP に置いた up MEP は成立しませんでした(片方の端が CCM を出さない)。QFP 系のプラットフォーム
の IOS XE の CFM の章(C8000v を名指ししている)には、その制約があります。EVPN の EFI は EVC に関連付けられない、EVPN の場面で
EFP に置けるのは down MEP だけ、up MEP は EFI から相手の拠点へ CFM のパケットを送れない、というものです。このラボが LDP の
疑似回線を見張るのはそのためです。

:::try
誰も気づかない切断を起こします。課題 M11-9 の後に行ってください。

1. XE1 で `show ethernet cfm maintenance-points remote` を実行し、MEP 3 があることを確かめます。
2. CML で、XE3 と P1 の間のリンクに 100 % の廃棄のリンク条件を入れます(リンクの Link Conditions タブ)。XE1 では 1〜2 秒ごとに
   同じコマンドを繰り返し、P1 では `show isis neighbors` を実行します。
3. 10 秒ほどでリンク条件を外します。XE1 で `show ip sla statistics 130 details` を実行し、設定モードで `ip sla restart 130` を
   実行して、もう一度統計を見ます。
4. 比べるために、両方の PE の `continuity-check interval 1s` を消して、1〜3 を繰り返します。終わったら行を戻します。

ラボでの結果: 1 秒なら、MEP 3 は 3 秒ほどで消え、そのとき P1 はまだ XE3 を IS-IS の隣接に持っていました。既定の間隔では、
10 秒後も MEP 3 は表に残っていました。切断の後、Y.1731 の操作は restart するまで `Internal error` のままでした。
:::

### 3.4 IOS XR では

IOS XR では、CFM を `ethernet cfm` → `domain PROV level 4` → `service E130 xconnect group <グループ> p2p <名前>` の下に、
`continuity-check interval 1s` とともに書き、MEP はアタッチメント回線のサブインタフェースに `ethernet cfm` →
`mep domain PROV service E130 mep-id 1` と書きます。IOS XE と違い、IOS XR はサービスに `continuity-check` を書くまで
CCM を送りません。Y.1731 の測定は `ethernet sla` のプロファイル(`type cfm-delay-measurement`)で、MEP の下で当てます
(`sla operation profile <P> target mep-id <n>`)。このトラックの IOS XRv 9000 には `ethernet cfm` そのものがありません。

## 4. コマンド名の対照

| IOS XE では | IOS XR では |
|---|---|
| `ethernet cfm global` | —(`ethernet cfm` はドメインを収める設定モード) |
| `ethernet cfm domain <D> level <n>` → `service <S> evc <EVC>` | `ethernet cfm` → `domain <D> level <n>` → `service <S> xconnect group <G> p2p <P>` |
| `continuity-check interval 1s`(既定は 10 秒) | `continuity-check interval 1s`(書くまで送らない) |
| `service instance <n> ethernet <EVC>` → `cfm mep domain <D> mpid <n>` | サブインタフェース → `ethernet cfm` → `mep domain <D> service <S> mep-id <n>` |
| `ping ethernet mpid <n> domain <D> service <S>` | `ping ethernet cfm domain <D> service <S> mep-id <n> source interface <IF>` |
| `ip sla <n>` → `ethernet y1731 delay DMM …` | `ethernet sla` → `profile <P> type cfm-delay-measurement` |
| `show ethernet cfm maintenance-points remote` | `show ethernet cfm peer meps` |

## 実践

ラボ **XRT-12** で、課題 M11-9 に取り組んでください。これで M11 の追補は終わりです。E-Tree、G.8032、802.1ah は付録で
扱います。

<p class="tolab"><a href="/_learn?id=XRT-12">ワークスペースでラボ XRT-12 を開く</a> — <a href="bc-m11-practice-6.html">課題</a></p>

:::note
出典: Application Services Configuration Guide, Cisco IOS XE 17.x(Configuring Ethernet CFM for Cisco QFP-Based Platforms。
C8000v を名指しし、既定の間隔 10 秒と EVPN の制約を載せている)。IP Addressing Configuration Guide, Cisco IOS XE 17.x
(Configuring IP SLAs Metro-Ethernet 3.0 (ITU-T Y.1731) Operations)。Interface and Hardware Component Configuration Guide for
the ASR 9000, IOS XR 24.x(Configuring Ethernet OAM)と ASR 9000 の Ethernet OAM のコマンド リファレンス。IEEE 802.1ag
(メンテナンス レベル、間隔の 3.5 倍の寿命)、ITU-T G.8013/Y.1731。いずれも 2026 年 11 月に確認しました。出力、検知の時間、
`ethernet cfm global` が無いときのふるまい、止まった Y.1731 の操作は、ラボ XRT-12(Catalyst 8000V 17.15.1a)での測定によります。
:::
