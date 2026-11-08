# M12 — データプレーンの保護

前の 2 つのページでは、正しいパケットを扱いで分けました。このページでは、来てはいけないパケットを落とします。送信元を偽った
パケット、プロバイダーの基盤を狙うパケット、攻撃を受けている宛先へのパケットです。ブループリントの 1.7(データプレーンの
セキュリティの実装= uRPF・ACL・RTBH・MACsec)にあたります。BGP FlowSpec(1.5.f)と DDoS(1.6.d)にも触れます。

## 1. 何が嬉しいのか

### 1.1 困りごと: 偽の送信元、基盤への攻撃、攻撃の波

インターネットでは、送信元のアドレスは送る側が自由に書けます。攻撃者は、送信元を他人のアドレスに偽ったパケットを大量に
送ります。受けた側は本当の送り主にたどり着けず、応答のパケットは偽られたアドレスの持ち主へ向かいます(反射の攻撃)。
送信元を偽ったパケットを、自分の顧客から出さない・外から受け入れないのは、プロバイダーの務めです(RFC 3704 の BCP 84)。

プロバイダーの基盤そのもの(ルータのループバックやコアのリンクのアドレス)も狙われます。外から直接届く必要のないアドレスです。

顧客が大量のパケットを浴びたとき(DDoS)、そのパケットは顧客の回線に届く前に、プロバイダーのコアを流れます。顧客の
回線が埋まるだけでなく、コアも混みます。プロバイダーは、なるべく網の入口で捨てたいと考えます。

### 1.2 それ以前の手: 手で書く ACL

M2 の課題 M2-5 では、ゲストのネットワークから来るパケットのうち、送信元を偽ったものを、入力の ACL で落としました。
ACL は確実ですが、手で書くので、顧客のアドレスが変わるたびに書き直しが要ります。顧客が数千あれば、書き間違いと書き忘れが
必ず出ます。

攻撃への対応も、ACL では遅れます。攻撃を受けている宛先を、インターネットとの接続点のルータ全部の ACL に足して回るのは、
攻撃の最中には現実的ではありません。

### 1.3 答え: ルーティングの情報を使って守る

- **uRPF**(Unicast Reverse Path Forwarding): 送信元のアドレスを、自分のルーティング テーブルで確かめます。顧客のアドレスは
  ルーティング テーブルに載っているので、ACL を書かなくても、顧客ごとに正しく判断できます。
- **インフラ ACL**: 外から届く必要の無い基盤のアドレスは数が少なく、変わらないので、ACL で守ります。
- **RTBH**(Remotely Triggered Black Hole): 捨てたいアドレスを 1 か所で登録すると、BGP でそれが網の縁のルータ全部に配られ、
  縁のルータがそのアドレスへの(または、そのアドレスからの)パケットを捨てます。

## 2. 仕組み

### 2.1 uRPF: 送信元をルーティング テーブルで確かめる

ルータはふつう、宛先だけを見て転送します。uRPF は、入ってきたパケットの**送信元**のアドレスでも、ルーティング テーブル
(正確には CEF の FIB)を引きます。

- **厳格**(strict): 送信元へのルートが、パケットが入ってきたインターフェイスを向いていれば通します。「その送信元は、この
  インターフェイスの向こうにいるはず」という確認です。経路が対称な所、つまり 1 本だけで接続している顧客に向きます。
- **緩い**(loose): 送信元へのルートが、どこかにあれば通します。向きは問いません。経路が非対称になりうる所(複数の
  プロバイダーとつながる境界)に使います。どこにもルートの無いアドレス(使われていない番号、私設の番号など)は落ちます。

既定ルートがあると、どのアドレスにも「ルートがある」ことになります。そのため、既定ルートは数えないのがふつうで、数えさせる
ときは `allow-default` を付けます。

XR01 の、CUST1(1 本だけで接続している顧客、198.51.100.0/25)への入口で、3 つの送信元を試しました。送り先は CUST2 で、
CUST2 が受け取った数で、XR01 で落ちたかを見ます(偽った送信元への応答は戻ってこないので、送り側の成功率では分かりません)。

| XR01 の設定 | 送信元が自分の割り当て(198.51.100.1) | インターネットの番号(203.0.113.99) | どこにもルートの無い番号(10.99.99.1) |
|---|---|---|---|
| なし | 届く | 届く | 届く |
| 厳格 | 届く | **落ちる**(ルートは INET を向く) | **落ちる** |
| 緩い | 届く | 届く(ルートはある) | **落ちる** |
| 緩い(既定ルートあり) | 届く | 届く | **落ちる**(既定ルートは数えない) |
| 緩い+`allow-default` | 届く | 届く | 届く |

### 2.2 インフラ ACL

外から届く必要の無いアドレスを、プロバイダーの網の入口で守る ACL です。Cisco の TAC 文書は、4 つの部分で組むことを勧めています。
①送信元を偽ったものを捨てる、②基盤宛てでも必要なもの(相手との BGP など)を許す、③それ以外の基盤宛てを捨てる、
④通過するパケット(顧客宛て)を許す、です。①は uRPF に任せることもできます。

ACL は、自分宛ての制御のパケットも落とします。②を書き忘れると、相手との BGP のセッションが、保持時間が切れたところで
落ちます(M2-5 で、OSPF の隣接が落ちたのと同じです)。

### 2.3 RTBH: 宛先で捨てる

RTBH の考え方は、「捨てたいアドレスへのルートを、ネクスト ホップが捨て先のルートとして、BGP で全部の縁のルータへ配る」です
(RFC 5635 の 3 節)。

1. 縁のルータ全部に、使っていないアドレス(捨て先。192.0.2.1/32 がよく使われる)から Null0 へのスタティック ルートを
   置いておきます。
2. **起点**のルータ(このラボの RR1)で、攻撃を受けている宛先をスタティック ルートで登録し、目印(タグ)を付けます。
3. 起点のルータは、目印のあるルートを BGP に出すときに、ネクスト ホップを捨て先の 192.0.2.1 に書き換え、コミュニティの印
   (このラボでは 65000:666)と `no-export` を付けます。
4. 縁のルータは、そのルートを受け取ります。/32 なので、顧客のルートより優先されます。ネクスト ホップの 192.0.2.1 は Null0 を
   向くので、その宛先へのパケットは、縁のルータの入口で捨てられます。

`no-export` は、この /32 をほかの AS へ出さないための印です。付け忘れると、細かいルートがインターネットへ漏れます。
RFC 7999 は、BLACKHOLE という印(65535:666)を決め、受け取った側に `no-export` か `no-advertise` を付けることを勧めています。

宛先で捨てると、攻撃は止まりますが、攻撃を受けた宛先は誰からも届かなくなります。攻撃者の目的をプロバイダーが代わりに
果たす形で、そこが RTBH の限界です。

### 2.4 RTBH: 送信元で捨てる

攻撃元のアドレスが分かっていれば、それを同じ仕組みで登録し、縁のルータの入口で**緩い uRPF** を有効にしておきます
(RFC 5635 の 4 節)。攻撃元へのルートが捨て先を向くので、そこから来たパケットは uRPF で落ちます。攻撃を受けた宛先は、
ほかの送信元からは届いたままです。

ここに、IOS と IOS XR の違いがあります。IOS は、送信元へのルートが 192.0.2.1 を経由して Null0 を向いていれば uRPF で
落とします(Cisco のホワイト ペーパー、2005 年)。IOS XR の ASR 9000 は、uRPF で「Null0 への再帰的な参照」をしません
(TAC 文書 116386)。XRv 9000 も同じです。

| XR01 が受け取った攻撃元(203.0.113.66)のルート | XR01 の経路 | INET 側に緩い uRPF を入れたとき |
|---|---|---|
| ネクスト ホップ 192.0.2.1(起点で書き換え) | `via 192.0.2.1/32, recursive` → null0 | **届いてしまう**(10 発とも CUST2 へ) |
| `set next-hop discard`(XR01 の入口のポリシー) | `directly connected, via Null0` | **落ちる**(CUST2 は 0 発) |

IOS XR では、RPL の `set next-hop discard` で、受け取ったルートを直接 Null0 に向けます。IOS XR で送信元の RTBH を使うには、
これが要ります。

### 2.5 押さえどころ

- 1 本だけの顧客は厳格、境界は緩い。既定ルートは数えないのが既定(`allow-default` で数える)。
- インフラ ACL は 4 部構成。自分宛ての BGP を許すのを忘れない。
- RTBH は「捨て先を向いた /32 を BGP で配る」。印と `no-export`。宛先で捨てると、その宛先は誰からも届かなくなる。
- 送信元で捨てるには、縁で緩い uRPF。IOS XR では `set next-hop discard` が要る。

## 3. IOS XR で組む

### 3.1 uRPF

:::config fold XR01 — 顧客の入口は厳格、インターネットとの境界は緩い
interface GigabitEthernet0/0/0/2              ## CUST1(1 本だけの接続)
 ipv4 verify unicast source reachable-via rx  ## 厳格= 送信元へのルートがこのインターフェイスを向くこと
!
interface GigabitEthernet0/0/0/3              ## INET(境界)
 ipv4 verify unicast source reachable-via any ## 緩い= どこかにルートがあること。既定ルートは数えない
:::

`allow-default` を足すと、既定ルートも数えます。`allow-self-ping` は、自分のアドレスを送信元にした ping を通すための
指定です。どちらも厳格と緩いの両方に付けられます。

```console
RP/0/RP0/CPU0:XR01#show cef ipv4 interface GigabitEthernet0/0/0/2 detail
...
  IP unicast RPF check is enabled
  RPF mode strict
...
RP/0/RP0/CPU0:XR01#show cef ipv4 drops
...
  RPF drops            packets :              17
```

落とした数は `show cef ipv4 drops` の `RPF drops` に出ます(これも少し遅れて増えます)。

### 3.2 インフラ ACL

:::config fold XR01 — インターネットから、プロバイダーの基盤へのパケットを落とす
ipv4 access-list FROM-INTERNET
 10 permit tcp host 10.0.100.100 host 10.0.100.1 eq bgp   ## ② 相手から自分への BGP
 20 permit tcp host 10.0.100.100 eq bgp host 10.0.100.1   ## ② 自分から張った BGP の戻り
 30 deny ipv4 any 10.0.0.0/16                 ## ③ コアのリンク
 40 deny ipv4 any 10.255.0.0/24               ## ③ ループバック
 50 permit ipv4 any any                       ## ④ 通過(顧客宛て)
!
interface GigabitEthernet0/0/0/3
 ipv4 access-group FROM-INTERNET ingress hardware-count   ## hardware-count で、行ごとの数をハードウェアで数える
:::

```console
RP/0/RP0/CPU0:XR01#show access-lists ipv4 FROM-INTERNET hardware ingress location 0/0/CPU0
 10 permit tcp host 10.0.100.100 host 10.0.100.1 eq bgp
 20 permit tcp host 10.0.100.100 eq bgp host 10.0.100.1 (27 hw matches)
 30 deny ipv4 any 10.0.0.0 0.0.255.255 (8 hw matches)
 40 deny ipv4 any 10.255.0.0 0.0.0.255 (11 hw matches)
 50 permit ipv4 any any (40 hw matches)
```

数は、ACL を当ててからの通算です(この出力は課題の確認の試験のトラフィックも数えています)。INET との BGP のパケットは
20 行目に数えられました。

- `hardware-count` を付けないと、ハードウェアの数は出ません(IPv4 の ACL の既定。IPv6 はいつも数える)。
  `show access-lists ipv4 <名前>`(ハードウェアの指定なし)は、ソフトウェアで処理したパケットだけを数えます。
- ★XRv 9000 26.1.1 では、アドレスをまとめる `object-group` が使えませんでした(`Object groups not supported on this
  platform`)。行で書きます。
- ★`ABF` という名前の ACL は、予約語として拒まれました。
- IOS XR の ACL は、MPLS のラベルの付いたパケットには効きません。コア側のインターフェイスでは使えないということです。

### 3.3 RTBH の起点

起点のルータ(RR1)で、目印のタグの付いたスタティック ルートを、RPL で書き換えて BGP に出します。

RTBH の設定は 2 台にまたがります(この節の RR1 と、3.4 節の XR01)。図は、経路が RR1 から XR01 へ届き、その後に来た攻撃の
パケットが捨てられるまでの順です。図の番号にカーソルを置くと(スマホでは押すと)、その部分の設定が出ます。

:::walk
legend: 線の上は BGP で配る経路と、その属性。橙は書き換えた属性。
rows:
  - panel: RR1
    sub: 起点
    items:
      - ref: 1
        head: "**捨てたい宛先を登録する** `router static`"
        then: ["`198.51.100.130/32 Null0 tag 666`  目印のタグ 666 を付ける"]
      - ref: 2
        head: "**BGP に出す** `redistribute static route-policy RTBH-TRIGGER`"
        match:
          - ["if tag eq 666", true, 当たる]
          - ["else", false, "ほかのスタティック ルートは drop"]
        then:
          - "→ `set next-hop 192.0.2.1`  捨て先へ書き換える"
          - "→ `set community (65000:666, no-export)`  縁で拾う印と、ほかの AS へ出さない印"
  - {wire: "[[=198.51.100.130/32]] [[!NH 192.0.2.1]] [[!65000:666 no-export]] _iBGP で縁へ"}
  - panel: XR01
    sub: 境界(INET との境)
    items:
      - ref: 3
        head: "**受け取るときに調べる** `route-policy FROM-RR in`"
        say: ["RR1(10.255.0.52)からの経路を、入口の RPL で調べる"]
        match:
          - ["if community matches-any RTBH", true, "65000:666 に当たる"]
        then: ["→ `set next-hop discard`  直接 Null0 へ。ほかの経路は `pass` でそのまま"]
      - say: ["~経路表と CEF: 198.51.100.130/32 は directly connected, via Null0(null0 adjacency)"]
      - say: ["[[IP → 198.51.100.130]] ~INET から来た攻撃のパケット", "~XR01 の入口で捨てられ、CUST2(PE2 の先)には届かない"]
  - aside: "③を書かないと(RR1 の書き換えだけ)"
    say:
      - "~XR01 の経路は 192.0.2.1 経由で Null0 を向く(PE2 と同じ)"
      - "~送信元で捨てる RTBH(緩い uRPF)は、IOS XR では Null0 を再帰でたどらないので効かない(2.4 節)"
:::

:::config RR1 — タグ 666 のスタティック ルートを、捨て先を向いたルートとして配る
route-policy RTBH-TRIGGER                     ## ②
  if tag eq 666 then                          ## 目印の付いたスタティック ルートだけ
    set next-hop 192.0.2.1                    ## 捨て先へ書き換える(縁のルータ全部に 192.0.2.1/32 → Null0)
    set community (65000:666, no-export)      ## 縁で拾う印と、ほかの AS へ出さない印
    pass
  else
    drop                                      ## ほかのスタティック ルートは出さない
  endif
end-policy
!
router static
 address-family ipv4 unicast
  192.0.2.1/32 Null0                          ## ② 自分にも捨て先を置く(書き換えたネクスト ホップを解決するため)
  198.51.100.130/32 Null0 tag 666             ## ① 捨てたいアドレスを登録する
!
router bgp 65000
 address-family ipv4 unicast
  redistribute static route-policy RTBH-TRIGGER  ## ②
:::

IOS の縁のルータ(このラボの PE2)は、受け取ったルートのネクスト ホップ 192.0.2.1 を、Null0 へのスタティック ルートで
解決します。

```console
PE2#show ip cef 198.51.100.130 255.255.255.255 detail
198.51.100.130/32, epoch 0, flags [rib only nolabel, rib defined all labels]
  recursive via 192.0.2.1
    attached to Null0
```

### 3.4 境界のルータ: set next-hop discard

XR01 で、RR1 から受け取ったルートのうち印の付いたものを、直接 Null0 に向けます。

:::config fold XR01 — 印の付いたルートを直接捨てる
community-set RTBH                            ## ③
  65000:666
end-set
!
route-policy FROM-RR                          ## ③
  if community matches-any RTBH then
    set next-hop discard                      ## 直接 Null0 へ。送信元の uRPF もこれで落ちる
  endif
  pass                                        ## ほかのルートはそのまま受け取る
end-policy
!
router bgp 65000
 neighbor 10.255.0.52                         ## RR1
  address-family ipv4 unicast
   route-policy FROM-RR in                    ## ③
:::

```console
RP/0/RP0/CPU0:XR01#show bgp ipv4 unicast 198.51.100.130/32
...
  Local
    10.255.0.52 (discarded) from 10.255.0.52 (10.255.0.52)
      Origin incomplete, metric 0, localpref 100, valid, internal, best, group-best
      Received Path ID 0, Local Path ID 1, version 8
      Community: 65000:666 no-export
RP/0/RP0/CPU0:XR01#show route 198.51.100.130/32
Routing entry for 198.51.100.130/32
  Known via "bgp 65000", distance 200, metric 0, type internal
  ...
    directly connected, via Null0
RP/0/RP0/CPU0:XR01#show cef 198.51.100.130/32
198.51.100.130/32, version 27, null0 adjacency, internal 0x5000001 0x40 (ptr 0x1063ed48) [1], 0x400 (0x107d55d8), 0x0 (0x0)
...
```

`(discarded)` は、BGP がこのパスのネクスト ホップを捨て先として扱っていることを示します(表の一覧では状態の欄に `N`)。
この出力は、起点がネクスト ホップを書き換えずに印だけを付けたときのものです(ネクスト ホップは RR1 のまま)。ASR 9000 の
ガイドによると、受け取ったネクスト ホップに届かなくても、この経路はベスト パスの候補になります。また、L3VPN の iBGP の
ルートには使えません。

### 3.5 確かめ方

| 見たいこと | コマンド |
|---|---|
| uRPF が入ったか・落とした数 | `show cef ipv4 interface <IF> detail`・`show cef ipv4 drops` |
| ACL の行ごとの数 | `show access-lists ipv4 <名前> hardware ingress location 0/0/CPU0` |
| 起点が配ったルート | 起点で `show bgp ipv4 unicast <アドレス>`(ネクスト ホップと印) |
| 縁で捨てる形になったか | `show bgp ipv4 unicast <アドレス>`(`discarded`)・`show route`・`show cef <アドレス>`(`null0`) |
| インターネットへ漏れていないか | 隣の AS(このラボの INET)で `show ip bgp <アドレス>` |
| 本当に落ちたか | 宛先の機器が受け取った数(このラボでは CUST2 の `show ip traffic` の echo) |

### 3.6 ほかの道具: ABF と FlowSpec

**ABF**(ACL Based Forwarding)は、ACL の行にネクスト ホップを書いて、一致したパケットをルーティング テーブルと関係なく
送ります。攻撃を受けている宛先へのパケットを、捨てる代わりに、洗浄の装置(スクラビング センター)へ寄せる、といった
使い方です。

:::config XR01 — 攻撃を受けている宛先へのパケットを、洗浄の役(CUST1 の側)へ寄せる
ipv4 access-list TO-SCRUB
 10 permit ipv4 any host 198.51.100.130 nexthop1 ipv4 172.20.1.1   ## 一致したら 172.20.1.1 へ送る
 20 permit ipv4 any any                       ## 残りはふつうに転送
!
interface GigabitEthernet0/0/0/3
 ipv4 access-group TO-SCRUB ingress hardware-count
:::

この ACL を当てて INET から 198.51.100.130 へ 20 発送ると、10 行目が 20 発に一致し(`20 hw matches (next-hop: addr=172.20.1.1,
vrf name=default)`)、XR01 の CUST1 側のインターフェイスから 20 発出ていきました。RTBH で 198.51.100.130 を Null0 に向けて
いても、ABF が先に効きました。

**BGP FlowSpec**(RFC 8955)は、「宛先・送信元・プロトコル・ポートなどの条件」と「捨てる・速さを絞る・印を付け替える・
別の VRF へ寄せる」という動作の組を、BGP で配ります。RTBH が「アドレスで丸ごと捨てる」のに対し、FlowSpec は「この宛先の、
この UDP のポートだけ」のように細かく切れます。規則を作って配る側を controller、受け取って自分のハードウェアに入れる側を
client と呼びます。

RR1(XRd)を controller、XR01 を client にすると、規則(198.51.100.129 宛ての ICMP を 0 bps に)は XR01 に届き、
`show flowspec ipv4 detail` に `Traffic-rate: 0 bps` と出ましたが、パケットは落ちませんでした。XRv 9000 は client として
規則を当てられません(Cisco Community の回答と同じ。公式の対応表にも FlowSpec はありません)。仕組みと設定の形は付録に
まとめます。

:::try
ABF で、攻撃を受けている宛先へのパケットを、捨てる代わりに寄せてみます。課題 M12-5 を終えた後に行い、最後に必ず元に戻します。

1. XR01 で、課題 M12-4 で INET 側に当てた ACL に、`45 permit ipv4 any host 198.51.100.130 nexthop1 ipv4 172.20.1.1` を足して
   コミットします。
2. XR01 で `show interfaces GigabitEthernet0/0/0/2 | include packets output` を見てから、INET で
   `ping 198.51.100.130 source Loopback0 repeat 20 timeout 1` を実行し、もう一度見ます。ACL の数も見ます。
3. 45 行目を消してコミットします。

結果の例: 20 発の送信の前後で、GigabitEthernet0/0/0/2 の `packets output` は 26 から 46 に増え、45 行目は
`(20 hw matches) (next-hop: addr=172.20.1.1, vrf name=default)` でした。INET の ping の成功率は 0 です(洗浄役の CUST1 は
このアドレスを持たないので応答しない)。RTBH で Null0 に向けた宛先でも、ABF が先に効きました。
:::

## 実践

ラボ **XRT-14** で課題 M12-4 と M12-5 に取り組みます。

<p class="tolab"><a href="/_learn?id=XRT-14">ワークスペースでラボ XRT-14 を開く</a> — <a href="d5-m12-practice-3.html">課題 M12-4、M12-5</a></p>

:::note
このページの出力は、前のページと同じ盤面で取得しました。
出典: RFC 3704(2.2〜2.5 節)、RFC 8704(3 節)、RFC 5635(3 節・4 節)、RFC 7999(2・3・5 節)、RFC 3882、RFC 8955。ASR 9000 の IP Addresses and
Services Command Reference と Configuration Guide(IOS XR 24.x。`ipv4 verify unicast source reachable-via`、厳格と緩い、`ipv4 access-group … hardware-count`、
object-group、ABF)、ASR 9000 の Routing Configuration Guide(IOS XR 7.10.x。RTBH と `set next-hop discard`)と Cisco 8000 の RPL のコマンド
リファレンス、ASR 9000 の BGP FlowSpec の章(IOS XR 24.x)、Cisco の TAC 文書「Protecting Your Core: Infrastructure Protection Access Control Lists」
(43920)と 116386(ASR 9000 の uRPF と RTBH)、Cisco のホワイト ペーパー「Remotely Triggered Black Hole Filtering—Destination Based and Source Based」
(2005 年)。いずれも 2026 年 11 月に確認。次の項目は、PoC の盤面(XRT-14 と同じ形)での実測によるものです。uRPF の表、ACL の数と object-group・
予約語、RTBH の 2 つの形と送信元の uRPF、ABF、FlowSpec が当たらないこと。
:::
