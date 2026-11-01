# M11 — 付録: E-LAN、マルチホーム、イーサネット OAM

このラボの IOS XRv 9000 は、L2VPN のうち E-Line(VPWS)しか動かせず、CFM のコマンドもありません。この付録では、
それ以外のサービスの仕組みを見ます。設定と出力は、Catalyst 8000V(IOS XE 17.15)を PE にした PoC で取得しました。
IOS XR での書き方は公式文書の形で示します(このラボの XR では動かせません)。8000V で手を動かす追補のラボは、後で足します。

8000V は、既定のライセンスの段階では MPLS のコマンド自体がありません。`license boot level network-advantage addon
dna-advantage` を設定して保存し、再起動すると使えるようになります(登録は要りませんでした)。

## 1. E-LAN: 多地点を 1 つの LAN に

### 1.1 何が嬉しいのか

顧客が 3 つ以上の拠点を同じ VLAN でつなぎたいとき、E-Line で全部の組をつなぐと、拠点が n 個なら n(n−1)/2 本になります。
しかも CE の側で、どの E-Line に送るかを決めることになります。E-LAN では、プロバイダーの網全体が 1 台のスイッチのように
ふるまい、PE が MAC アドレスを覚えて、宛先の拠点へだけフレームを送ります。

### 1.2 VPLS: 疑似回線をフルメッシュに

VPLS では、各 PE がブリッジ ドメインを持ち、同じ VPLS の他のすべての PE と疑似回線を張ります(フルメッシュ)。PE は、
フレームの送信元の MAC を、それが来た AC か疑似回線で覚えます(データ プレーンでの学習)。宛先が分からないフレームと
ブロードキャストは、すべての疑似回線にコピーして送ります。疑似回線から来たフレームを、別の疑似回線へは送りません
(スプリット ホライズン)。フルメッシュなので、ループにはなりません。

:::config Catalyst 8000V(IOS XE 17.15)— VPLS の 1 台分(PoC で 3 台の全メッシュが通った形)
l2vpn vfi context VPLS210                          ## VPLS の 1 つのインスタンス
 vpn id 210                                        ## 疑似回線の VC ID の既定値にもなる
 member 10.255.0.42 encapsulation mpls             ## 相手の PE ごとに 1 本(フルメッシュ)
 member 10.255.0.43 encapsulation mpls
!
interface GigabitEthernet2
 service instance 210 ethernet                     ## AC= EVC
  encapsulation dot1q 210
  rewrite ingress tag pop 1 symmetric
!
bridge-domain 210                                  ## PE の中のスイッチ。AC と VFI をつなぐ
 member GigabitEthernet2 service-instance 210
 member vfi VPLS210
!
:::

### 1.3 EVPN の E-LAN: MAC を BGP で配る

EVPN の E-LAN でも、PE は MAC をデータ プレーンで覚えます。違うのは、覚えた MAC を BGP の**種類 2** の経路(MAC/IP の
広告)で他の PE に配ることです。他の PE は、BGP で受け取った MAC 宛てのフレームを、その MAC を広告した PE へだけ送ります。
宛先が分からないフレームなどを、どの PE へコピーするかは、**種類 3** の経路(包含的マルチキャスト、IMET)で知らせ合います。
PE どうしの疑似回線のフルメッシュは要りません。

```console
XE1#show l2vpn evpn mac
MAC Address    EVI   BD    ESI                      Ether Tag  Next Hop(s)
aabb.cc00.4f00 200   200   0000.0000.0000.0000.0000 0          Gi2:200
aabb.cc00.5000 200   200   0000.0000.0000.0000.0000 0          10.255.0.42
aabb.cc00.5100 200   200   0000.0000.0000.0000.0000 0          10.255.0.43
```

自分の AC で覚えた MAC は `Gi2:200`、BGP で受け取った MAC は広告した PE のループバックが次ホップです。

:::config Catalyst 8000V(IOS XE 17.15)— EVPN の E-LAN の 1 台分(PoC で 3 台が通った形)
l2vpn evpn
 replication-type ingress                          ## BUM は受け取る PE ごとにコピーして送る
 router-id Loopback0
!
l2vpn evpn instance 200 vlan-based                 ## EVI 200(RD・RT は自動)
!
interface GigabitEthernet2
 service instance 200 ethernet
  encapsulation dot1q 200
  rewrite ingress tag pop 1 symmetric
!
bridge-domain 200
 member GigabitEthernet2 service-instance 200
 member evpn-instance 200                          ## ブリッジ ドメインを EVI につなぐ
!
router bgp 65000
 address-family l2vpn evpn
  neighbor 10.255.0.21 activate                    ## RR(PoC では IOS XRd が反映した)
  neighbor 10.255.0.21 send-community both
!
:::

IOS XR では、`l2vpn` → `bridge group` → `bridge-domain` の下に AC と `evi <EVI>` を書き、`evpn` → `evi <EVI>` の下に
`advertise-mac` を書きます(公式文書の形)。このラボの IOS XRv 9000 は、ブリッジ ドメインのコミットを
`VPLS Bridge domains not supported on this platform` で拒否しました。

## 2. EVPN のマルチホーム

### 2.1 何が嬉しいのか

拠点のスイッチを 2 台の PE に収容すれば、PE やリンクの障害に強くなります。ところが、ふつうの L2 では、2 本のリンクの
片方はスパニング ツリーで止まります。EVPN のマルチホームでは、2 台の PE が 1 つの**イーサネット セグメント**(ES)を
共有し、CE からは 1 台の相手に見えます。CE は 2 本のリンクを LACP で 1 本に束ね、両方を同時に使えます(all-active)。

### 2.2 仕組み

- **ESI**: ES の識別子。2 台の PE が同じ値を設定します。
- **種類 4 の経路**(ES の経路): 同じ ES の PE が互いを見つけ、BUM を CE へ送る役(DF)を 1 台に決めます。
  両方が送ると、CE に同じフレームが 2 つ届くからです。
- **種類 1 の経路**(ES ごと): 遠い PE はこれで、その ES に 2 台の PE がいると知ります。片方の PE で覚えた MAC でも、
  両方の PE へ振り分けて送れます(**エイリアシング**)。PE のリンクが切れると、その PE は種類 1 の経路を取り消し、遠い PE は
  その ES のすべての MAC について一度に次ホップを外します。

PoC では、遠い XE3 は、SW1(2 台の PE に束で収容)の MAC を ESI 付きで、次ホップ 2 つで持ちました。XE1 の SW1 向きの
リンクを落とすと、XE3 は数秒で XE1 を次ホップから外しました。

```console
XE3#show l2vpn evpn mac
MAC Address    EVI   BD    ESI                      Ether Tag  Next Hop(s)
aabb.cc80.4e00 200   200   0300.0000.0000.0100.0001 0          10.255.0.41
                                                               10.255.0.42
```

ただし、CE 役の IOL-L2 はリンクが落ちたことを受け取れません(CML の IOL の制約)。SW1 は LACP が切れるまで XE1 側にも
振り続け、既定の速さでは 30 秒以上、`lacp rate fast` にしても約 18 秒、通信が止まりました。実機ではリンク断がすぐ伝わります。

:::config Catalyst 8000V(IOS XE 17.15)— all-active のマルチホームの 1 台分(PoC で 2 台の PE に束が組めた形)
l2vpn evpn ethernet-segment 1
 identifier type 3 system-mac 0000.0000.0001       ## ESI(種類 3= MAC から作る)。2 台の PE で同じ値
 redundancy all-active                             ## 8000V では all-active だけ(single-active は構文に無い)
!
interface Port-channel1
 lacp device-id 0000.0000.0001                     ## 2 台の PE が CE に同じ LACP の ID を見せる= CE は 1 本の束を組む
 evpn ethernet-segment 1
 service instance 200 ethernet
  encapsulation dot1q 200
  rewrite ingress tag pop 1 symmetric
!
interface GigabitEthernet3
 channel-group 1 mode active                       ## CE へのリンク
!
bridge-domain 200
 member Port-channel1 service-instance 200
!
:::

IOS XR では、`evpn` → `interface Bundle-Ether1` → `ethernet-segment` の下に `identifier type 0 <ESI>` と、必要なら
`load-balancing-mode single-active` を書きます(公式文書の形)。

## 3. E-Tree

E-Tree は、根(root)と葉(leaf)のある E-LAN です。葉どうしは通信できず、葉は根とだけ通信します。動画の配信元を根に、
各拠点を葉にするような使い方です。EVPN では、葉の AC から来たフレームに印を付け、葉の AC へは出さないようにします
(RFC 8317)。IOS XR では、EVI かブリッジ ドメインに `etree leaf` を書くと葉になり、書かないものは根です(公式文書の形)。
PoC では試していません。

## 4. イーサネット OAM: CFM と Y.1731

### 4.1 何が嬉しいのか

E-Line の CE から見えるのは「ping が通るか通らないか」だけです。プロバイダーは、顧客に売った区間が切れていないか、
遅延が約束の範囲かを、顧客のトラフィックとは別に確かめたいところです。IEEE 802.1ag の **CFM** は、イーサネットの区間の
両端に監視点を置いて、死活を見張り、ループバックとリンクトレースで切り分けます。ITU-T **Y.1731** は、その上で遅延や
損失を測ります。

### 4.2 仕組み

- **メンテナンス ドメイン**(MD)とレベル(0〜7): 顧客、プロバイダー、事業者が、それぞれのレベルで監視します。
- **メンテナンス アソシエーション**(MA): 1 つのサービス(ここでは 1 本の E-Line)。
- **MEP**: 区間の端の監視点。**CCM** を定期的に送り、相手の CCM が途絶えると障害と判断します。
- **ループバック**(LBM/LBR)と**リンクトレース**(LTM/LTR): ping と traceroute のイーサネット版です。

PoC では、8000V の 2 台の間の LDP の疑似回線の E-Line の両端に MEP を置きました。相手の MEP を学習し、ループバックは
5/5、リンクトレースは相手の MEP まで届き、Y.1731 の遅延の測定(DMM)は双方向で 0.69〜1.92 ms でした。相手の AC を落とすと、
相手の MEP は表から消え、`show ethernet cfm errors` に `Lifetime Expired` が出ました。

:::config Catalyst 8000V(IOS XE 17.15)— E-Line の端の MEP と Y.1731 の遅延(PoC で通った形)
ethernet cfm ieee
ethernet cfm global
ethernet evc E130                                  ## サービス(EVC)の名前
!
ethernet cfm domain CUST level 5                   ## 顧客のレベル 5 の MD
 service E-LINE-130 evc E130                       ## MA。xconnect の EVC には VLAN を付けない(付けるのはブリッジ ドメイン用)
  continuity-check
  continuity-check interval 1s                     ## CCM を 1 秒ごとに送る
!
interface GigabitEthernet2
 service instance 130 ethernet E130                ## AC を EVC E130 に結び付ける
  encapsulation dot1q 130
  rewrite ingress tag pop 1 symmetric
  cfm mep domain CUST mpid 41                      ## この端の MEP(相手は 43)
!
l2vpn xconnect context E130
 member GigabitEthernet2 service-instance 130
 member 10.255.0.43 130 encapsulation mpls
!
ip sla 10
 ethernet y1731 delay DMM domain CUST evc E130 mpid 43 cos 0 source mpid 41   ## 相手の MEP 43 へ DMM を送り、往復の遅延を測る
 frequency 10
ip sla schedule 10 start-time now life forever
:::

EVPN-VPWS の E-Line の端の MEP は、PoC では片側が CCM を出さず、成立しませんでした。公式文書の CFM の章には、EVPN の
EFI を EVC に関連付けられないという制約があります。

このラボの IOS XRv 9000 26.1.1 には、`ethernet cfm` のコマンドそのものがありません(パッケージに含まれていません)。
IOS XR での書き方は、`ethernet cfm` → `domain <名前> level <n>` → `service <名前> xconnect group <G> p2p <名前>` と、AC の
サブインタフェースの `ethernet cfm` → `mep domain … service … mep-id <n>` です(公式文書の形)。Y.1731 は `ethernet sla` です。

## 5. G.8032 と 802.1ah

- **G.8032**(ITU-T のイーサネット リング保護): リング状につないだスイッチで、リンクの 1 本(RPL)を止めてループを防ぎ、
  他のリンクが切れると RPL を開けて迂回します。50 ms 以内の切り替えを目標にしています。リングに 3 台以上が要るので、
  このラボでは扱いません。
- **IEEE 802.1ah**(PBB、プロバイダー バックボーン ブリッジ): 顧客のフレームを、プロバイダーの MAC アドレス(B-MAC)の
  フレームで丸ごと包みます(MAC-in-MAC)。サービスは 24 ビットの I-SID で区別するので、VLAN の 4094 の壁を越えられます。
  コアのスイッチは顧客の MAC を覚えずに済みます。EVPN と組み合わせたものが PBB-EVPN(RFC 7623)です。
- **E-Access**: 顧客と、別の事業者の網の境界(ENNI)をつなぐ E-Line です。

:::note
出典: L2VPN and Ethernet Services Configuration Guide for the ASR 9000 と NCS 5500, IOS XR 25.x(2025。VPLS、EVPN、マルチホーム、
E-Tree)。Interface and Hardware Component Configuration Guide for the ASR 9000, 25.x(イーサネット OAM)。IOS XE 17 の MPLS
Configuration Guide(VPLS、EVPN のシングル ホームとマルチホーム)と Application Services Configuration Guide(QFP の
プラットフォームの CFM。C8000v を含む)。Catalyst 8000V のデータ シート(2025)。RFC 4762、7432、7623、8317。IEEE 802.1ag、
802.1ah。ITU-T G.8013/Y.1731、G.8032。いずれも 2026 年 11 月に確認しました。8000V の設定と出力、時間は PoC での測定によります。
:::
