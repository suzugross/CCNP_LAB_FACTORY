# 組み立て順 — 4 つを同じ 5 つの段で

前のページで、4 つのサービスの違いは「入れ物が何か」と「その番号をどう伝えるか」の 2 つだと分かりました。
このページでは、同じことを設定の側から見ます。4 つとも、**同じ 5 つの段を同じ順で**組めます。違うのは各段に書く中身です。

設定例は前のページと同じ盤面のもので、PoC で入れて動いた running-config から切り出しています。IOS XE は XE1(拠点 1)、
IOS XR は XR01(拠点 4)です。

## 1. 何が嬉しいのか

### 1.1 困りごと: どこから書けばいいか分からない

サービスを 1 つ足すとき、設定は `router bgp`、`vrf`、`l2vpn`、`interface`、`bridge-domain` のようにあちこちに散らばります。
単元ごとの課題では、そのうち 1 か所を足すか直すだけだったので、「全部で何をどの順に書くか」を通して組む機会がありませんでした。

散らばったまま覚えると、書き忘れたときに、どこで止まっているのかも分かりません。

### 1.2 この答え: 下から順に 5 つの段

サービスの設定は、下の段が上の段を支える形になっています。下から順に書き、段ごとに確かめれば、
止まったときに「どの段か」がすぐに分かります。

| 段 | 何をするか | L3VPN | VPWS(LDP) | VPLS | EVPN(E-LAN) |
|---|---|---|---|---|---|
| 0 土台 | 相手の PE のループバックまで、ラベル付きの道を作る | IGP と LDP(または SR)。4 つとも共通 | ← | ← | ← |
| 1 PE 同士 | 相手を見つける手段を用意する | RR への iBGP に VPNv4 | なし(段 2 で名指し) | なし(段 2 で名指し) | RR への iBGP に L2VPN EVPN |
| 2 入れ物 | サービスの入れ物を作る | VRF(RD、RT) | xconnect(相手を名指し) | VFI(相手を名指し)とブリッジ ドメイン | EVI とブリッジ ドメイン |
| 3 収容 | お客さまの IF を入れ物につなぐ | サブインタフェースを VRF に入れ、CE と経路を交換 | AC を xconnect に | AC をブリッジ ドメインに | AC をブリッジ ドメインに |
| 4 確かめる | 下の段から順に見る | 5 節の表 | | | |

段 0 はコアの設計で、サービスごとに作るものではありません。サービスを足すたびに書くのは、段 1 から 3 です。
しかも段 1 は、BGP を使うサービスで最初の 1 回だけです。

## 2. 段 0: 土台を確かめる

サービスを書く前に、相手の PE のループバックへラベル付きの道があることを確かめます。ここが欠けていると、上の段が全部
正しくても通りません。この盤面で P1 の XR01 向きの IF から `mpls ip` を外すと、L3VPN は経路が届いたまま ping が 0% になり、
XE1 と XR01 の間の疑似回線は down になりました。

```console
XE1#show mpls forwarding-table 10.255.0.42 32
Local      Outgoing   Prefix           Bytes Label   Outgoing   Next Hop
Label      Label      or Tunnel Id     Switched      interface
22         18         10.255.0.42/32   0             Gi1        10.0.41.51
XE1#traceroute mpls ipv4 10.255.0.42/32
  0 10.0.41.41 MRU 1500 [Labels: 18 Exp: 0]
L 1 10.0.41.51 MRU 1500 [Labels: implicit-null Exp: 0] 7 ms
! 2 10.0.42.42 2 ms
```

`Outgoing Label` が数字(この例では 18)か `Pop Label` なら道があります。`No Label`(IOS XR では `Unlabelled`)なら、
道はラベルなしで、サービスは通りません。`traceroute mpls` は道の各ホップのラベルを示します。IOS XR から打つには、
送る側と応える側の両方に `mpls oam` が要ります(M8)。

## 3. 段 1: PE 同士(BGP を使うサービスだけ)

L3VPN と EVPN は、相手の PE を BGP で見つけます。PE は RR(RR1)と iBGP を張り、使うアドレス ファミリを有効にします。
RR1 の側は据え付けで、4 台の PE を RR のクライアントにしています(この節の最後の設定例)。

:::config XE1(IOS XE)— RR への iBGP
router bgp 65000
 bgp router-id 10.255.0.41
 no bgp default ipv4-unicast                      ## 近隣に IPv4 のユニキャストを勝手に有効にしない。使うファミリだけを明示する
 neighbor 10.255.0.52 remote-as 65000              ## RR(RR1)。PE 同士は直接張らない
 neighbor 10.255.0.52 update-source Loopback0      ## ループバックから張る。段 0 の道の終点と同じアドレス
 !
 address-family vpnv4                              ## L3VPN の経路(RD 付きの IPv4 とラベル)
  neighbor 10.255.0.52 activate
  neighbor 10.255.0.52 send-community both         ## RT は拡張コミュニティに載る。送らないと相手が輸入できない
 exit-address-family
 !
 address-family l2vpn evpn                         ## EVPN の経路(種類 1〜4)。E-LAN と EVPN-VPWS の両方が使う
  neighbor 10.255.0.52 activate
  neighbor 10.255.0.52 send-community both
 exit-address-family
:::

:::config XR01(IOS XR)— RR への iBGP
router bgp 65000
 bgp router-id 10.255.0.1
 address-family vpnv4 unicast                      ## IOS XR は、使うファミリをまず全体で有効にする
 !
 neighbor 10.255.0.52
  remote-as 65000
  update-source Loopback0
  address-family vpnv4 unicast                     ## 近隣ごとにも有効にする。iBGP の VPNv4 にはポリシーは要らない
:::

XR01 は E-LAN に加わらないので、`l2vpn evpn` のファミリは書いていません。

RR1 の側は次のとおりです。PE ごとに近隣を書き、`route-reflector-client` で「ここから受けた経路をほかの PE へ配る」と指定します。
RR1 には VRF も `mpls ip` もありません。経路を配るだけで、パケットは運ばないからです(前のページの 3.5 節)。

:::config RR1(IOS XE)— ルート リフレクタ(据え付け)
router bgp 65000
 bgp router-id 10.255.0.52
 no bgp default ipv4-unicast
 neighbor PE peer-group                            ## 4 台の PE に同じ設定を当てるための束(ピア グループ)
 neighbor PE remote-as 65000
 neighbor PE update-source Loopback0
 neighbor 10.255.0.1 peer-group PE
 neighbor 10.255.0.41 peer-group PE
 neighbor 10.255.0.42 peer-group PE
 neighbor 10.255.0.43 peer-group PE                ## PE を足すときは、この行と下の activate の行を足す
 !
 address-family vpnv4
  neighbor PE send-community both
  neighbor PE route-reflector-client               ## クライアント(PE)から受けた経路を、ほかのクライアントへ配る
  neighbor 10.255.0.1 activate
  neighbor 10.255.0.41 activate
  neighbor 10.255.0.42 activate
  neighbor 10.255.0.43 activate
 exit-address-family
 !
 address-family l2vpn evpn                         ## XR01 は E-LAN に加わらないので、このファミリには入れない
  neighbor PE send-community both
  neighbor PE route-reflector-client
  neighbor 10.255.0.41 activate
  neighbor 10.255.0.42 activate
  neighbor 10.255.0.43 activate
 exit-address-family
:::

VPWS(LDP)と VPLS には、この段がありません。相手の PE は段 2 で入れ物の中に名指しし、書いた相手と targeted LDP の
セッションが自動で張られます。

## 4. 段 2 と 3: 入れ物と収容

入れ物(段 2)と収容(段 3)は、サービスごとに形が違います。1 つずつ、同じ書き順で並べます。

### 4.1 L3VPN

入れ物は VRF です。RD は経路を PE ごとに区別するための値で、RT は「どの VRF の経路か」を示す荷札です。
RT 65000:100 を輸出し、同じ値を輸入する PE 同士が、同じ L3VPN の仲間になります。

:::config XE1(IOS XE)— L3VPN の拠点 1
vrf definition A                                   ## 段 2: 入れ物
 rd 10.255.0.41:100                                ## RD は PE ごとに変える(この盤面は「ループバック:100」)
 address-family ipv4
  route-target export 65000:100                    ## この VRF の経路に付ける荷札
  route-target import 65000:100                    ## この荷札の付いた経路を取り込む
 exit-address-family
!
interface GigabitEthernet2.100                     ## 段 3: 収容。CE1 の VLAN 100 を拾うサブインタフェース
 encapsulation dot1Q 100
 vrf forwarding A                                  ## このサブインタフェースを VRF A に入れる(アドレスより先に)
 ip address 172.16.1.254 255.255.255.0
!
router bgp 65000
 address-family ipv4 vrf A                         ## 段 3: CE と経路を交換する。ここで学んだ経路が VPNv4 に出る
  neighbor 172.16.1.1 remote-as 65001
  neighbor 172.16.1.1 activate
:::

:::config XR01(IOS XR)— L3VPN の拠点 4
vrf A                                              ## 段 2: 入れ物。RT は VRF の下に書く
 address-family ipv4 unicast
  import route-target
   65000:100
  !
  export route-target
   65000:100
!
interface GigabitEthernet0/0/0/1.100               ## 段 3: 収容
 vrf A
 ipv4 address 172.16.4.254 255.255.255.0
 encapsulation dot1q 100
!
route-policy PASS                                  ## IOS XR の eBGP は、ポリシーが無いと経路を送りも受けもしない(M5)
  pass
end-policy
!
router bgp 65000
 vrf A
  rd 10.255.0.1:100                                ## IOS XR の RD は BGP の下に書く(IOS XE は VRF の下)
  address-family ipv4 unicast
  !
  neighbor 172.16.4.1                              ## 段 3: CE4 との eBGP
   remote-as 65004
   address-family ipv4 unicast
    route-policy PASS in
    route-policy PASS out
:::

### 4.2 VPWS(LDP の疑似回線)

入れ物は xconnect です。中身は 2 つの端だけで、一方は AC(お客さまの IF)、もう一方は相手の PE への疑似回線です。
相手の PE と VC ID(IOS XR では PW ID)を名指しします。VC ID は両端で同じ値にします。

:::config XE1(IOS XE)— 拠点 1 から拠点 4 への E-Line
interface GigabitEthernet2
 service instance 130 ethernet                     ## 段 3: AC。このポートで VLAN 130 のフレームを拾う
  encapsulation dot1q 130
  rewrite ingress tag pop 1 symmetric              ## 入るときにタグを外し、出るときに付け直す
!
l2vpn xconnect context CE1-CE4                     ## 段 2: 入れ物(名前は自由)
 member GigabitEthernet2 service-instance 130      ## 一方の端= AC
 member 10.255.0.1 130 encapsulation mpls          ## もう一方の端= XR01 への疑似回線(VC ID 130)。これが名指し
:::

:::config XR01(IOS XR)— 拠点 4 から拠点 1 への E-Line
interface GigabitEthernet0/0/0/1.130 l2transport   ## 段 3: AC。l2transport= L3 の IF ではなく AC として使う
 encapsulation dot1q 130
 rewrite ingress tag pop 1 symmetric
!
l2vpn
 xconnect group SVC                                ## 段 2: 入れ物をまとめる名前(自由)
  p2p CE4-CE1
   interface GigabitEthernet0/0/0/1.130            ## 一方の端= AC
   neighbor ipv4 10.255.0.41 pw-id 130             ## もう一方の端= XE1 への疑似回線。PW ID は両端で同じ
:::

### 4.3 VPLS

入れ物は 2 つ組です。VFI(相手の PE との疑似回線の束)と、ブリッジ ドメイン(PE の中の 1 台のスイッチ)です。
ブリッジ ドメインに AC と VFI の両方を入れると、お客さまのポートと疑似回線が同じスイッチにつながります。

:::config XE1(IOS XE)— VPLS の拠点 1
l2vpn vfi context VPLS210                          ## 段 2: 疑似回線の束
 vpn id 210                                        ## VPLS の番号。全 PE で同じ値(疑似回線の VC ID になる)
 member 10.255.0.42 encapsulation mpls             ## 名指し: XE2
 member 10.255.0.43 encapsulation mpls             ## 名指し: XE3。ほかの全 PE を並べる
!
interface GigabitEthernet2
 service instance 210 ethernet                     ## 段 3: AC
  encapsulation dot1q 210
  rewrite ingress tag pop 1 symmetric
!
bridge-domain 210                                  ## 段 2: PE の中のスイッチ
 member GigabitEthernet2 service-instance 210      ## 段 3: AC をスイッチのポートに
 member vfi VPLS210                                ## 疑似回線の束もスイッチのポートに
:::

名指しなので、全 PE がほかの全 PE を `member` に並べます。拠点を 1 つ足すと、既存のすべての PE に 1 行ずつ足すことになります。

### 4.4 EVPN の E-LAN

入れ物は VPLS と同じくブリッジ ドメインで、VFI の代わりに EVI(EVPN のインスタンス)を入れます。相手の PE は書きません。
RT が仲間を決め、この盤面のように書かなければ「AS 番号:EVI」(65000:200)が自動で付きます。

:::config XE1(IOS XE)— EVPN の E-LAN の拠点 1
l2vpn evpn                                         ## EVPN の全体の設定(最初の 1 回だけ)
 replication-type ingress                          ## BUM を相手の PE ごとにコピーして送る。無いと EVI が Incomplete で何も通らない
 router-id Loopback0
!
l2vpn evpn instance 200 vlan-based                 ## 段 2: EVI。RD と RT は自動(10.255.0.41:200、65000:200)
!
interface GigabitEthernet2
 service instance 200 ethernet                     ## 段 3: AC
  encapsulation dot1q 200
  rewrite ingress tag pop 1 symmetric
!
bridge-domain 200                                  ## 段 2: PE の中のスイッチ
 member GigabitEthernet2 service-instance 200      ## 段 3: AC をスイッチのポートに
 member evpn-instance 200                          ## EVI をスイッチにつなぐ(VPLS の member vfi の位置)
:::

VPLS の設定と並べると、違いは `member vfi` が `member evpn-instance` に変わり、相手の PE の一覧が消えて、代わりに段 1 の
BGP が要るところだけです。拠点を足しても、既存の PE の設定は変わりません。

### 4.5 EVPN-VPWS

E-Line を BGP で作る形です。入れ物は「点と点」の EVI で、相手の PE は書かず、両端の番号(source と target)を
互いに逆にして書きます。

:::config XE2(IOS XE)— 拠点 2 から拠点 3 への EVPN-VPWS
interface GigabitEthernet2
 service instance 140 ethernet                     ## 段 3: AC
  encapsulation dot1q 140
  rewrite ingress tag pop 1 symmetric
!
l2vpn evpn instance 140 point-to-point             ## 段 2: 点と点の EVI(RT は自動 65000:140)
 vpws context CE2-CE3
  service target 3 source 2                        ## 自分の端は 2、相手の端は 3。XE3 は「target 2 source 3」
  member GigabitEthernet2 service-instance 140
:::

LDP の疑似回線(4.2 節)と比べると、`member 10.255.0.1 130 encapsulation mpls`(相手の PE を名指し)が、
`service target 3 source 2`(端の番号だけ)に変わります。どの PE が端 3 を持っているかは、BGP の種類 1 の経路で分かります。

## 5. 段 4: 下から確かめる

書き終えたら、下の段から順に確かめます。上の段の表示がおかしくても、原因が下の段にあることがよくあるからです。

| 段 | IOS XE | IOS XR | 見るところ |
|---|---|---|---|
| 0 土台 | `show mpls forwarding-table <相手の Lo> 32` | `show mpls forwarding prefix <相手の Lo>/32` | 出ていくラベルが数字か Pop |
| 1 PE 同士 | `show bgp vpnv4 unicast all summary`、`show bgp l2vpn evpn summary` | `show bgp vpnv4 unicast summary` | RR との行が確立し、受け取った数が 0 でない |
| 2 L3VPN | `show bgp vpnv4 unicast all labels`、`show ip route vrf A` | `show bgp vpnv4 unicast labels`、`show route vrf A` | 相手の拠点の経路が VRF に入り、ラベルが付いている |
| 2 名指し | `show mpls ldp neighbor`(Targeted)、`show l2vpn atom vc` | `show l2vpn xconnect` | 相手の PE との targeted のセッションと、疑似回線の UP |
| 2 EVPN | `show l2vpn evpn evi <EVI> detail`、`show l2vpn evpn vpws vc id <EVI> detail` | — | Peers の行に相手の PE、State が Established |
| 3 収容 | `show bgp vpnv4 unicast vrf A summary`、`show bridge-domain <BD>` | `show l2vpn xconnect detail` | CE との eBGP、AC の up、遠くの MAC |
| 通し | CE から相手の拠点へ ping | | |

## 6. 止まったときの見当

これまでの単元で実際に起こした書き忘れを、止まる段で並べます。どれも、その段の表示で見つかります。

| 段 | 書き忘れ・食い違い | 表れ方 | 測った単元 |
|---|---|---|---|
| 0 | 相手の PE への道にラベルが無い | L3VPN は経路が届いたまま通らない。疑似回線は down(IOS XR は `DN`、IOS XE は相手から `pw-tx-fault`) | このページの盤面 |
| 2 | L3VPN の RT の輸入が相手の輸出と合っていない | 輸入を間違えた PE の VRF にだけ相手の経路が入らない。反対側には入るので、片側だけ見えて通じない | このページの盤面 |
| 2 | EVPN の `replication-type ingress` が無い | EVI が `State: Incomplete` のままで、何も通らない | M11 追補 |
| 2 | VPLS の VPN ID の打ち間違い | その PE の疑似回線が上がらない(相手のラベルが届かない) | M11 追補 |
| 2 | EVPN-VPWS の target の取り違え | 片側だけ UP に見えるなど、表示が左右で食い違う | M11 |
| 3 | IOS XR の eBGP に `route-policy` が無い | CE との近隣は上がるが、経路を送りも受けもしない | M5、M6 |
| 3 | AC の `rewrite` の付け忘れ(IOS XR の LDP の疑似回線) | AC の MTU が 1504 になり、`Error: MTU mismatched` で down | M11 |
| 3 | AC の `rewrite` の付け忘れ(VPLS) | 疑似回線は UP なのに、その拠点だけ通じない | M11 追補 |

`rewrite` の付け忘れは、サービスや OS によって表れ方が変わります。down になって分かる場合と、UP のまま通らない場合が
あります。上がっているのに通らないときは、段 3 の AC のタグの扱いを最初に疑います。

## 7. IOS XE と IOS XR の書き方の対応

| 段 | IOS XE | IOS XR |
|---|---|---|
| 1 | `router bgp` → `address-family vpnv4` → `neighbor … activate` | `router bgp` → `address-family vpnv4 unicast`(全体)→ `neighbor` → `address-family vpnv4 unicast` |
| 2 L3VPN | `vrf definition A` → `rd`、`route-target` | `vrf A` → `import/export route-target`。RD は `router bgp` → `vrf A` → `rd` |
| 3 L3VPN | サブインタフェースに `vrf forwarding A`。`address-family ipv4 vrf A` で CE と近隣 | サブインタフェースに `vrf A`。`router bgp` → `vrf A` → `neighbor`、eBGP は `route-policy` が必須 |
| 2 VPWS | `l2vpn xconnect context` → `member <相手> <VC ID> encapsulation mpls` | `l2vpn` → `xconnect group` → `p2p` → `neighbor ipv4 <相手> pw-id <ID>` |
| 3 L2 | `service instance <n> ethernet` → `encapsulation dot1q`、`rewrite` | `interface <IF>.<n> l2transport` → `encapsulation dot1q`、`rewrite` |
| 2 E-LAN | `bridge-domain` → `member vfi`/`member evpn-instance` | この盤面の IOS XRv 9000 はブリッジ ドメインを使えない(M11 付録) |
