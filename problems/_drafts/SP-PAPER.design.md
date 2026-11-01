# SP(SPCOR)の作問方針と紙面問の手本(BL-257)

2026-11-01 ユーザ了承。XR トラック 2 周目(BL-257)で SPCOR 向けの紙面問・ラボ問・知識問を作るときの方針。
§3 のサンプル 5 問は「この雰囲気で」と了承された手本。

## 1. 方針

### 1.1 紙面問(選択式)

- **型**は ENARSI の紙面問と同じ(瞬発・思考・穴埋め・「すべて選べ」・計算)。
  「知識は範囲内・認知は試験超え」と「未提示の前提を消去法で使う」を標準装備にする(既存の作問規約どおり)。
- ★**題材は SPCOR の出題範囲で問われる論点そのもの**(技術の仕組み・設計の判断・出力の読解)。
  **XR と IOS/IOS XE の違いは、SPCOR が問う範囲で使うだけで主題にしない。そればかりにならないようにする**(2026-11-01 ユーザ訂正)。
  図の show 出力は XR のものを使ってよい(XR で設定・確認する論点として問う)。
- **正誤の根拠**は XR トラックの PoC の実測(`poc/xr/*.log`)と公式文書。図に使う show 出力は PoC の記録から抜き出して削るだけにし、手で作らない。
- **版によって変わる挙動・公式文書と実機が食い違う点**は、正誤の根拠にしない(試験側の版では文書どおりに動くかもしれないため)。
  そうした点は解説の補足に留める。
- 問題文は英文、解説は日本語(CLAUDE.md の出題言語のルールどおり)。

### 1.2 ラボ問の予測の見方

- ラボで出るとすれば、出題範囲のうち動詞が「実装」「設定と確認」の項目。「説明」の項目は紙面で受ける。
- 試験のラボも Cisco の配る仮想イメージ(IOL・IOSv・Catalyst 8000V・XRv9000・XRd)で動いている前提で予測する(推測)。
  - 仮想イメージでできないことはラボに出ない(出るなら紙面)と読む。PoC で分かった例= XRv9000 の E-LAN/VPLS と CFM・
    XRd の L2 転送・NSR(RP 1 枚)・FlowSpec の適用・XR の NAT64/MAP-T・MACsec(見込み)。
  - 受験者ごとに機器を立てる費用を考えると、盤面は小さく(XR は 1〜2 台+IOL)、課題は制御プレーン中心
    (設定して show や ping で確かめる)に寄ると見る。今の XR トラックの盤面と同じ形。
  - イメージの癖(XRd が通過する TCP を壊す・IOL-L2 が VLAN の多い盤面で BPDU を落とす等)に当たる題材は、作問側も避けると読む。
- 試験の中身の記憶から問題を起こさない。公開の出題範囲と実機から予測する。

### 1.3 SPCOR の「実装」「設定と確認」項目と CML の対応(2026-11-01 時点)

| 範囲 | CML で | 状態 |
|---|---|---|
| IS-IS・OSPF・BGP・RPL・TS(2.1〜2.6) | ○ | M3〜M6 |
| 高可用性(2.8) | ○ | M7。NSR は不可 |
| MPLS(3.1) | ○ | M8 |
| L3VPN(4.3) | ○ | M9 |
| L2VPN・キャリア イーサネット(4.2) | ○ | E-Line は XR、E-LAN・CFM は Catalyst 8000V(XRT-12) |
| 制御プレーンの保護(1.5) | ○ | M2・M8。BGP の TTL セキュリティ・プレフィックス抑制は未作問。BGPsec は未確認 |
| データプレーンの保護(1.7) | ACL ○・uRPF/RTBH △ | MACsec は不可の見込み |
| マルチキャスト(4.4) | △ | IOL は実績あり。XR は未 PoC |
| QoS(4.5) | △ | IOL は体感ラボ済み。XR は未確認(無ライセンスの XRv9000 は 200 kbps) |
| 自動化(5.7〜5.10) | △ | IOS XE 側は道場済み。XR のテレメトリは未 PoC |

○= 実機で済み、△= CML でできる見込み・未 PoC。2 周目はマルチキャストと XR の QoS・テレメトリを先に PoC する。

### 1.4 知識問

- 可能な限り充実させる(2026-11-01 ユーザ方針)。実機で測れない「説明」の項目(伝送技術・モビリティ・仮想化・
  MPLS QoS のモデル・TE の帯域モデル・SRv6・BGPsec・IPv6 移行など)も知識問で受ける。
- 根拠は裏どりの信頼順(公式文書 → Cisco の公開技術資料と RFC)。実測が無いぶん、公式文書で断定できない記述は出題しない。
- 器は既存の紙面基盤(`gen_paper_mcq`・cloze の知識ベース)に XR/SP の知識ベースを足す形(XR-SPRI.design.md の方針と同じ)。
- 進め方は、プロジェクト内で薄いところを先に教材(読み物)で補い、その上で問題を足す。

## 2. 進め方

1. 単元ごとに読み物を深める(BL-257 の本文どおり)。
2. その単元の PoC の実測から紙面問を起こす(§1.1)。
3. 「説明」の項目と実機で測れない論点は知識問にする(§1.4)。
4. ラボ問は §1.2 の見方で、試験に出そうな形に寄せる。

## 3. 手本(サンプル 5 問・2026-11-01)

正式な出題の手続き(正解が 1 通りに決まることの機械検証・英文と原文の照合)は通していない。雰囲気の手本として残す。
手本にするのは形式(問いの型・図の出し方・根拠の取り方)。題材の配分は §1.1 に従う。Q1(XR の送る側の AS ループ検査)は
XR と IOS の違いに寄った題材で、こうした問いは全体の一部に留める。

### Q1 〔瞬発・単一選択〕 L3VPN, both sites in the same AS

> **Answer this question without connecting to any device.**

Customer A has two sites, both in AS 65101. XR01 (IOS XR) and RT02 (IOS XE) are PEs in AS 65000. CEA1 connects to XR01
and CEA2 connects to RT02 over eBGP. The administrator reports that CEA1 does not have site 2's prefix 10.101.2.0/24.

```
router bgp 65000
 vrf CUST-A
  rd 10.255.0.1:101
  address-family ipv4 unicast
  neighbor 172.16.11.2
   remote-as 65101
   address-family ipv4 unicast
    route-policy PASS in
    route-policy PASS out
```
```
RP/0/RP0/CPU0:XR01#show bgp vrf CUST-A
   Network            Next Hop            Metric LocPrf Weight Path
Route Distinguisher: 10.255.0.1:101 (default for vrf CUST-A)
*> 10.101.1.0/24      172.16.11.2              0             0 65101 i
*>i10.101.2.0/24      10.255.0.12              0    100      0 65101 i

RP/0/RP0/CPU0:XR01#show bgp vrf CUST-A 10.101.2.0/24
BGP routing table entry for 10.101.2.0/24, Route Distinguisher: 10.255.0.1:101
Paths: (1 available, best #1)
  Not advertised to any peer
  Path #1: Received by speaker 0
  Not advertised to any peer
```

Which statement is correct?

A. XR01 sends 10.101.2.0/24 to CEA1, and CEA1 discards it.
B. Configuring `allowas-in` on CEA1 makes CEA1 install 10.101.2.0/24.
C. Configuring `as-override` for neighbor 172.16.11.2 on XR01 makes CEA1 install 10.101.2.0/24 with the AS_PATH 65000 65000.
D. Changing XR01's outbound policy toward CEA1 to one that prepends 65000 makes CEA1 install 10.101.2.0/24.

**正解 C**。XR は送る側で AS ループを検査し、CE の AS を含む経路を送らない(Not advertised to any peer)。
B は届かないので効かない(CEA1 の受信 0)。D は 65101 が残る。根拠= `poc/xr/l3vpnv-d.log`(XRd でも同じ)。

### Q2 〔思考・すべて選べ〕 After an LDP-to-SR migration step

> **Answer this question without connecting to any device.**

The core runs IS-IS level 2 in a ring: XR01–RT01 (metric 10), RT01–RT02 (10), RT02–RT03 (100), RT03–XR01 (100).
SR-MPLS is enabled on all routers, and LDP was running on all routers. RT01 and RT03 (IOS XE) have the same configuration:
`mpls ldp sync` under `router isis`, and `mpls ip` on every core interface.
As one step of the migration, an operator applied `no mpls ldp` on XR01 and committed. No other change was made.

```
RP/0/RP0/CPU0:XR01#show running-config router isis
router isis CORE
 address-family ipv4 unicast
  metric-style wide
  segment-routing mpls sr-prefer
 !
 interface GigabitEthernet0/0/0/0
  address-family ipv4 unicast
   mpls ldp sync
 !
 interface GigabitEthernet0/0/0/1
  address-family ipv4 unicast
   mpls ldp sync
```
```
RP/0/RP0/CPU0:XR01#show isis database verbose   (output trimmed)
XR01.00-00          * 0x0000000a   0x5bcd        1165 /*            0/0/0
  Metric: 16777214   IS-Extended RT01.00
  Metric: 16777214   IS-Extended RT03.00
RT01.00-00            0x00000008   0x7767        1163 /1200         0/0/0
  Metric: 16777214   IS-Extended XR01.00
  Metric: 10         IS-Extended RT02.00
RT02.00-00            0x00000005   0x3b0a        942  /1199         0/0/0
  Metric: 10         IS-Extended RT01.00
  Metric: 100        IS-Extended RT03.00
```

Which statements are true? **Select all that apply.**

A. Removing `mpls ldp sync` from both IS-IS interfaces on XR01 returns the metrics in XR01's LSP to 10 and 100.
B. Removing `mpls ip` from RT01's interface toward XR01 returns the metric toward XR01 in RT01's LSP to 10.
C. At this point, VRF CUST-A traffic between CEA1 (behind XR01) and CEA2 (behind RT02) is dropped.
D. Adding `segment-routing mpls sr-prefer` to IS-IS on XR01 returns the metrics in XR01's LSP to 10 and 100.
E. RT03's LSP advertises the maximum metric toward XR01.

**正解 A・B・E**。C は 16777214 でも SPF に残り、お客さまの ping は 100%(表に出ない故障)。D は既に入っている。
根拠= `poc/xr/sr-c6.log`〜`sr-c8.log`。

### Q3 〔思考・計算〕 TI-LFA repair label stack

> **Answer this question without connecting to any device.**

```
        XR01 ───10─── RT01
         │              │
        100            10
         │              │
        RT03 ──100─── RT02
```

All link metrics are symmetric. The SRGB on every router is 16000–23999, and PHP is in use.
Prefix-SID indexes: XR01 = 1, RT01 = 11, RT02 = 12, RT03 = 13. Adjacency-SIDs: RT03→RT02 = 23, RT02→RT01 = 26.
XR01 has `fast-reroute per-prefix` and `fast-reroute per-prefix ti-lfa` on both core interfaces.

For destination 10.255.0.11/32 (RT01), which backup path does XR01 pre-install to protect against a failure of the link XR01–RT01?

A. via RT03, labels imposed {16011}
B. via RT03, labels imposed {16012 16011}
C. via RT03, labels imposed {16013 16012 16011}
D. via RT03, labels imposed {23 16011}
E. No backup path is installed. The prefix is unprotected.

**正解 B**。RT03 から RT01 へは RT02 経由と XR01 経由が同点(110)なので素の LFA(A)は使えない。RT02 が P と Q を兼ねる。
XR01–RT03 を 10 にした盤面では {ImplNull 23 16011}(adj-SID が要る形)。根拠= `poc/xr/sr-e3.log`。

### Q4 〔思考・単一選択〕 EVPN-VPWS, up on one side only

> **Answer this question without connecting to any device.**

The design for an EVPN-VPWS service with EVI 110: XR01 (10.255.0.1) uses AC-ID 1 for its attachment circuit, and XR02
(10.255.0.21) uses AC-ID 4. XR03 is the route reflector for l2vpn evpn. RD and RT are assigned automatically.
Exactly one parameter in the network differs from the design.

```
RP/0/RP0/CPU0:XR02#show l2vpn xconnect
XConnect                   Segment 1                       Segment 2
Group      Name       ST   Description            ST       Description            ST
------------------------   -----------------------------   -----------------------------
EL         CE4-CE1    DN   Gi0/0/0/1.111          UP       EVPN 110,9,None        DN

RP/0/RP0/CPU0:XR02#show l2vpn xconnect group EL xc-name CE4-CE1 detail | include "state is|EVPN:"
Group EL, XC CE4-CE1, state is down; Interworking none
  AC: GigabitEthernet0/0/0/1.111, state is up
  EVPN: neighbor None, PW ID: evi 110, ac-id 9, state is down ( local ready )

RP/0/RP0/CPU0:XR01#show l2vpn xconnect group EL xc-name CE1-CE4 detail | include "state is|EVPN:"
Group EL, XC CE1-CE4, state is up; Interworking none
  AC: GigabitEthernet0/0/0/2.110, state is up
  EVPN: neighbor 10.255.0.21, PW ID: evi 110, ac-id 4, state is up ( established )

RP/0/RP0/CPU0:XR01#show bgp l2vpn evpn rd 10.255.0.21:110
   Network            Next Hop            Metric LocPrf Weight Path
Route Distinguisher: 10.255.0.21:110
*>i[1][0000.0000.0000.0000.0000][4]/120
                      10.255.0.21                   100      0 i
```

Which parameter differs from the design?

A. On XR01, `source` is not 1.
B. On XR01, `target` is not 4.
C. On XR02, `source` is not 4.
D. On XR02, `target` is not 1.
E. The route targets of EVI 110 differ between XR01 and XR02.
F. XR03 does not reflect XR01's route to XR02.

**正解 D**。`PW ID: evi 110, ac-id N` の N は相手側の AC-ID(target)。XR01 の BGP に AC-ID 4 が届いている → C ではない、
XR01 は 4 を待って UP → B ではない、9 は target → 設計の 1 と違う。E・F は「違いは 1 か所」の前提で消える。
根拠= `poc/xr/l2vpn-h.log`(h-4・h-5)。

### Q5 〔穴埋め〕 Shared services and Internet access on IOS XR

> **Answer this question without connecting to any device.**

For each of the blanks ① through ④, select one term from choices A through G. No term is used in two blanks.
Some terms fit no blank.

```
route-policy SVC-EXPORT
  if destination in (10.99.1.0/24) then
    set extcommunity rt (65000:900) ［①］
  endif
  pass
end-policy
!
vrf SVC
 address-family ipv4 unicast
  export route-policy SVC-EXPORT
  export route-target
   65000:999
!
vrf CUST-A
 address-family ipv4 unicast
  import from default-vrf route-policy DEFAULT-ONLY ［②］
  export to default-vrf route-policy CUST-A-PUBLIC ［③］
```

XR01 exports 10.99.1.0/24 from VRF SVC with RT 65000:900 in addition to the VRF's export RT 65000:999.
Without ［①］, the route leaves with 65000:900 only.
VRF CUST-A takes a default route from the global table. With ［②］, the route is also sent to the other PE as a VPNv4 route.
Without it, only CEA1 receives it.
CUST-A's public prefixes are copied into the global table. With ［③］, the prefixes that CUST-A learned from the other PE are copied too.
An export route-policy cannot ［④］ a route. A route that the policy does not pass still leaves the VRF with the VRF's route targets.

A. additive　B. allow-imported-vpn　C. advertise-as-vpn　D. stop　E. change the route targets of　F. as-override　G. route-reflector-client

**正解 ①A ②C ③B ④D**。E は誤り(export のポリシーは RT を変えられる。① がその例)。
根拠= `poc/xr/l3vpn-*.log`(XRT-09 の PoC)とコマンド リファレンス。
