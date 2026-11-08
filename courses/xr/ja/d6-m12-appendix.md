# M12 — 付録

本文で扱わなかった、ブループリント 1.4 の残りの項目(TE と QoS、IntServ、IPv6 のフロー ラベル)と、1.7.d の MACsec、1.5.f の
BGP FlowSpec をまとめます。ラボでは手を動かしません(XRv 9000 で動かないものと、この単元の盤面に RSVP-TE が無いもの)。
最後に、XRv 9000 で確かめたことと、コマンドの対応を並べます。

## 1. TE と QoS: DS-TE・MAM・RDM・CBTS・PBTS

### 1.1 何が足りないのか

DiffServ は、コアの各ホップで、印ごとの扱いを決めます。ところが、どの道を通るかは IGP の最短経路のままです。音声が
最短経路に集まり、その道の優先キューの上限を超えれば、印があっても守れません。TE(トラフィック エンジニアリング)の
RSVP-TE は、帯域を予約して道を決めますが、ふつうの TE はリンクの帯域を 1 つの塊として扱い、クラスを区別しません。

**DS-TE**(DiffServ-aware TE、RFC 4124)は、TE の帯域の予約をクラスごとに分けます。トラフィックの種類(Class-Type、CT。
最大 8 つ)ごとに、リンクで予約してよい帯域の上限(Bandwidth Constraint、BC。最大 8 つ)を決め、LSP は自分の CT の上限の
中で帯域を予約します。CT と、LSP どうしの割り込みの優先度(preemption)の組を TE-Class と呼び、最大 8 つ持てます(4.2.1 節)。

### 1.2 帯域の上限の決め方: MAM と RDM

BC を CT にどう当てるかの規則(帯域制約モデル)は 2 つ決まっています。

| モデル | 考え方 | 特徴 |
|---|---|---|
| **MAM**(Maximum Allocation Model、RFC 4125) | CT ごとに専用の上限。CTc の予約は BCc まで | 分かりやすく、クラスの間で帯域を奪い合わない。上限の合計がリンクの予約可能な帯域を超えてもよい。使われていない帯域をほかのクラスが使えない |
| **RDM**(Russian Dolls Model、RFC 4127) | 上限を入れ子にする。BC0 = 予約可能な全帯域、CT7 は BC7 まで、CT6 と CT7 の合計は BC6 まで…、全 CT の合計は BC0 まで | 使われていない帯域を、下のクラスが使える。帯域を効率よく使えるが、クラスを守るには割り込み(preemption)が要る |

ASR 9000 のガイドによると、IOS XR の DS-TE には Cisco 独自の方式(prestandard)と IETF の方式があり、どちらも既定の
モデルは RDM です。MAM の設定は、RSVP のインターフェイスの下の `bandwidth mam max-reservable-bw …` です。

### 1.3 クラスで道を選ぶ: CBTS と PBTS

DS-TE で帯域を守った LSP を、クラスごとに別々に張ったとき、どのパケットをどの LSP へ入れるかを決める機能です。

- **CBTS**(Class-Based Tunnel Selection。IOS XE の名前): 同じ宛先への TE トンネルを束ね、トンネルごとに運ぶ EXP の値を
  決めます(`tunnel mpls traffic-eng exp 5` など)。束ね役のトンネル(`exp-bundle master`)に、各トンネルを `exp-bundle member`
  で入れます。入力の QoS のポリシーで EXP を書き換えると、書き換えた後の値で選びます。1 つの EXP の値を複数のトンネルに
  分けることはできません。
- **PBTS**(Policy-Based Tunnel Selection。IOS XR の名前): パケットの分類(precedence・EXP・DSCP など)で `forward-class` を
  付け、`forward-class` の決まったトンネルへ送ります。ASR 9000 のガイドは、`policy-map` での設定はできず `forward-class` で
  設定すること、1 つのトンネルに付けられる `forward-class` は 1 つで、付けないトンネルは 0 になること、L3 のインターフェイス
  だけで使えることを挙げています。

## 2. IntServ と RSVP

**IntServ**(Integrated Services、RFC 1633)は、アプリケーションの流れごとに、資源を予約して扱いを保証する考え方です。
サービスは、遅れの上限を保証する guaranteed と、予測できる程度の扱いの predictive の 2 種類で、
鍵は資源の予約と受け入れの判断(admission control)です。ルータは流れごとの状態を持ちます。

予約の手順が **RSVP**(RFC 2205)です。RSVP は片方向で、受け手が予約を求め(receiver-oriented)、状態は送り直さないと
消える(soft state)プロトコルです。ルーティング プロトコルではなく、ルーティングが決めた道に沿って予約します。

プロバイダーのコアで IntServ を使わないのは、流れの数だけ状態を持つことになり、規模が合わないからです(本文 1.2 節)。
DiffServ はこれを、印の種類ごとの扱いに集約して解きました。RSVP そのものは、TE の LSP の帯域を予約する RSVP-TE として、
コアで使われ続けています(予約するのは顧客の流れではなく、プロバイダーの LSP)。

## 3. IPv6 のフロー ラベル

IPv6 のヘッダには 20 ビットの **フロー ラベル** があります(RFC 6437)。送り手が、同じ流れのパケットに同じ値を付ける
欄です。

- 0 は「ラベルを付けていない」という意味です。
- 流れは、(フロー ラベル、送信元のアドレス、宛先のアドレス)の 3 つ組で見分けます。途中のルータは、TCP や UDP の
  ポートを読まずに(拡張ヘッダの奥まで読まずに)流れを見分けられます。
- 主な使い道は、等コストの道(ECMP)やリンクの束への振り分けのハッシュです。そのため、値はばらつくように選ぶことが
  求められます。
- 途中のノードは、0 でない値を変えてはなりません(やむを得ないセキュリティの理由を除く)。

QoS の印(DSCP)とは別の欄で、フロー ラベルが扱いを決めるわけではありません。ブループリントが QoS の項目に挙げるのは、
IntServ のような流れの扱いのために作られた欄だからです。

## 4. MACsec

**MACsec**(IEEE 802.1AE)は、となりの機器との間のイーサネットのフレームを、1 ホップごとに暗号化して改ざんを防ぎます。
鍵は MKA(MACsec Key Agreement)で交換します。IPsec と違い、IP より下の、イーサネットのフレームを暗号化します。

ASR 9000 のガイドの設定の形は次のとおりです。対応はシャーシ・ラインカードで決まります(ハードウェアに依存する)。

- `key chain <名前>` → `macsec` → `key <ID>` → `key-string … cryptographic-algorithm aes-128-cmac` → `lifetime …`
- `macsec-policy <名前>`(暗号の方式・ポリシー)
- インターフェイスの下に `macsec psk-keychain <key chain> policy <macsec-policy>`
- 確かめるのは `show macsec mka session` です。

XRv 9000 26.1.1 には、`key chain` の下の `macsec` はありましたが、`macsec-policy` も、インターフェイスの `macsec` もありません
でした(構文に無い)。公式のリリース ノートの対応表にも MACsec はありません。

## 5. BGP FlowSpec

本文 3.6 節の続きです。FlowSpec の規則は、BGP の新しいアドレス ファミリー(IPv4 flowspec)の NLRI として運ばれます。NLRI は
条件(宛先・送信元のプレフィックス、プロトコル、ポート、ICMP の型、DSCP、パケット長など。RFC 8955 の 4.2.2 節の 12 種類)で、
動作は拡張コミュニティ(速さの上限= 0 なら捨てる、VRF への寄せ、DSCP の付け替えなど。7 節)です。

IOS XR では、規則を QoS と同じ MQC の形で書き(`class-map type traffic` と `policy-map type pbr`)、`flowspec` の下で配ります。
このラボで試した形は次のとおりです(RR1 が規則を作って配り、XR01 が受け取る)。

:::config RR1(XRd)と XR01 — FlowSpec の規則を配る・受け取る(試した設定。XRv 9000 は規則を当てられない)
class-map type traffic match-all FS-ATTACK   ## 条件(RR1)
 match destination-address ipv4 198.51.100.129 255.255.255.255
 match protocol icmp
 end-class-map
!
policy-map type pbr FS-POLICY                ## 動作(RR1)
 class type traffic FS-ATTACK
  drop                                       ## 速さの上限 0 として配られる
 !
 class type traffic class-default
 !
 end-policy-map
!
flowspec                                     ## 規則を配る(RR1)
 address-family ipv4
  service-policy type pbr FS-POLICY
!
router bgp 65000                             ## RR1 と XR01 の両方で、ipv4 flowspec を有効にする
 address-family ipv4 flowspec
 neighbor 10.255.0.1                         ## (RR1 側。XR01 側は neighbor 10.255.0.52 の下に address-family ipv4 flowspec)
  address-family ipv4 flowspec
   route-reflector-client
!
flowspec                                     ## 受け取った規則を当てる(XR01)
 address-family ipv4
  local-install interface-all
:::

XR01 は規則を受け取り(`show bgp ipv4 flowspec` に `Dest:198.51.100.129/32,Proto:=1/72`、`show flowspec ipv4 detail` に
`Traffic-rate: 0 bps`)ましたが、パケットは落ちませんでした。ASR 9000 のガイドは、QoS が FlowSpec より先に効くこと、MPLS の
トラフィックには効かないことを挙げています。

## 6. XRv 9000 で確かめたこと

| 項目 | 公式の文書 | このラボ(XRv 9000 26.1.1) |
|---|---|---|
| 無ライセンスの速さ | 「全インターフェイスで 200 Kbps に制限」(スマート ライセンスの章)。CML のページは実測 168 kbps | 約 4 Mbps 通った(送り手の IOL の生成量が上限) |
| 分類とマーキング | 対応表に「Bi-directional Policing and Marking」 | 効く。カウンタは 10〜30 秒遅れる |
| ポリサ | 同上 | 効く。2 速度 3 色の数が相手の CE の数と一致 |
| 階層のポリサ | 対応表に「Hierarchical Policers」 | (試していない) |
| シェーパ・優先キュー | 対応表に無い。データシート(2018 年)は「H-QoS」。データ プレーンの章に優先 1・通常 7 のキュー | 量は絞れる。キューは 1 個分ほど |
| WRED | 記述なし | 設定は入るが数が 0 |
| 1 クラスの印 | ASR 9000 のガイド「1 クラスに set は 2 つまで」 | 3 種類目でコミットを拒む |
| uRPF | データシートに記述あり | 厳格・緩い・`allow-default` が効く |
| ACL・ABF | 対応表に「IPv4 and IPv6 ACL」「ACL Based Forwarding」 | 効く。`hardware-count` で数える。object-group は不可 |
| RTBH の `set next-hop discard` | ASR 9000 のガイドにあり | 効く。送信元の uRPF も落とす |
| uRPF と Null0 への再帰 | ASR 9000 の TAC 116386「再帰的に参照しない」 | 同じ(192.0.2.1 経由では落とさない) |
| MACsec | 記述なし | 構文に無い |
| FlowSpec の client | 記述なし(コミュニティの回答は「controller だけ」) | 受け取るが当たらない |

公式と実機が食い違った 2 つ(無ライセンスの速さ、シェーパ)は、版と環境(CML)によるかもしれません。課題の正しさの根拠には
使っていません。

## 7. コマンドの対応(IOS XE と IOS XR)

| すること | IOS XE | IOS XR |
|---|---|---|
| クラスの終わり | (書かない) | `end-class-map` |
| ポリシーの終わり | (書かない) | `end-policy-map` |
| 積むラベル全部の EXP | `set mpls experimental imposition 5` | 同じ |
| 装置の中の印 | `set qos-group 5` | 同じ(入力だけ)。出力で `match qos-group 5` |
| ポリサの速さ | `police cir 256000 pir 512000`(bps) | `police rate 256 kbps peak-rate 512 kbps` |
| 超えた分の付け替え | `exceed-action set-dscp-transmit af22` | `exceed-action set dscp af22` |
| 優先キュー | `priority`(LLQ) | `priority level 1`(とポリサ) |
| ポリシーが入った形 | `show policy-map interface` | `show qos interface <IF> input`・`output` |
| 数 | `show policy-map interface` | `show policy-map interface <IF> input`・`output` |
| 数を消す | `clear counters <IF>` | `clear qos counters interface <IF> input`・`output` |
| 厳格な uRPF | `ip verify unicast source reachable-via rx` | `ipv4 verify unicast source reachable-via rx` |
| 緩い uRPF | `ip verify unicast source reachable-via any` | `ipv4 verify unicast source reachable-via any` |
| ACL の行ごとの数 | `show ip access-lists`(既定で数える) | `ipv4 access-group … hardware-count` → `show access-lists ipv4 <名前> hardware ingress location …` |
| RTBH の縁 | 捨て先へのスタティック ルート+受け取ったネクスト ホップ | 同じか、RPL の `set next-hop discard` |
| TTL を伝えない | `no mpls ip propagate-ttl` | `mpls ip-ttl-propagate disable` |
| explicit null | `mpls ldp explicit-null` | `mpls ldp address-family ipv4 label local advertise explicit-null` |

:::note
出典: RFC 4124(4.1.1 節・4.2.1 節)、RFC 4125(3 節)、RFC 4127(4 節)、RFC 1633(2.1 節)、RFC 2205(1 節)、RFC 6437(2 節)、RFC 8955
(4.2.2 節・7 節)。IOS XE の MPLS TE Path Calculation and Setup Configuration Guide の「MPLS Traffic Engineering Class-based Tunnel Selection」、
ASR 9000 の MPLS Configuration Guide(IOS XR 24.x)の「Implementing MPLS Traffic Engineering」(PBTS・DS-TE)、ASR 9000 の System Security
Configuration Guide(IOS XR 24.x)の「Configure MACSec」、ASR 9000 の Routing Configuration Guide(IOS XR 24.x)の「Implementing BGP Flowspec」、
IOS XRv 9000 の Installation and Configuration Guide とリリース ノート(25.1.1)とデータ シート(2018 年)、CML の IOS XRv 9000 のページ。
いずれも 2026 年 11 月に確認。表の「このラボ」の列と FlowSpec・MACsec の結果は、PoC の盤面(XRT-14 と同じ形)での実測によるものです。
IOS XE の `no mpls ip propagate-ttl` と `mpls ldp explicit-null` は M8 と同じ形で、このラボでは PE2 の explicit null だけを試しました。
:::
