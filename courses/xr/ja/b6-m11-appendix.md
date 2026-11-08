# M11 — 付録: E-Tree、G.8032、802.1ah

このラボの IOS XRv 9000 は、L2VPN のうち E-Line(VPWS)しか動かせず、CFM のコマンドもありません。E-LAN、EVPN の
マルチホーム、イーサネット OAM は、M11 の追補にそれぞれのページができ、Catalyst 8000V を PE にしたラボ XRT-12 で実践します。
[E-LAN](b7-m11-e-lan.html)、[EVPN のマルチホーム](b9-m11-multihoming.html)、[イーサネット OAM](bb-m11-ethernet-oam.html)
です。この付録では、ブループリントの 4.2 のうち、どちらのラボでも作らない残りを扱います。IOS XR での書き方は公式文書の形で
示します。

追補のサービスを自分の Catalyst 8000V で試すなら: 8000V は、既定のライセンスの段階では MPLS のコマンド自体がありません。
`license boot level network-advantage addon dna-advantage` を設定して保存し、再起動すると使えるようになります(登録は
要りませんでした)。ラボ XRT-12 では初期設定にこの行が入っていて、8000V は自分でその段階で立ち上がりました。

## 1. E-Tree

E-Tree は、根(root)と葉(leaf)のある E-LAN です。葉どうしは通信できず、葉は根とだけ通信します。動画の配信元を根に、
各拠点を葉にするような使い方です。EVPN では、葉の AC から来たフレームに印を付け、葉の AC へは出さないようにします
(RFC 8317)。IOS XR では、EVI かブリッジ ドメインに `etree leaf` を書くと葉になり、書かないものは根です(公式文書の形)。

## 2. G.8032 と 802.1ah

- **G.8032**(ITU-T のイーサネット リング保護): リング状につないだスイッチで、リンクの 1 本(RPL)を止めてループを防ぎ、
  他のリンクが切れると RPL を開けて迂回します。50 ms 以内の切り替えを目標にしています。リングに 3 台以上が要るので、
  これらのラボでは扱いません。
- **IEEE 802.1ah**(PBB、プロバイダー バックボーン ブリッジ): 顧客のフレームを、プロバイダーの MAC アドレス(B-MAC)の
  フレームで丸ごと包みます(MAC-in-MAC)。サービスは 24 ビットの I-SID で区別するので、VLAN の 4094 の壁を越えられます。
  コアのスイッチは顧客の MAC を覚えずに済みます。EVPN と組み合わせたものが PBB-EVPN(RFC 7623)です。
- **E-Access**: 顧客と、別の事業者の網の境界(ENNI)をつなぐ E-Line です。

:::note
E-Tree はラボでは試していません。
出典: L2VPN and Ethernet Services Configuration Guide for the ASR 9000 と NCS 5500, IOS XR 25.x(2025。E-Tree)。
Catalyst 8000V のデータ シート(2025)。RFC 7623、8317。IEEE 802.1ah。ITU-T G.8032。いずれも 2026 年 11 月に確認しました。
8000V のライセンスの段階は、PoC とラボ XRT-12 によります。
:::
