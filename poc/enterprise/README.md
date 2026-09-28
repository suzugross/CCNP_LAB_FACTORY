# PoC: エンタープライズ拠点ネットワーク構築ラボ(BL-225・2026-09-27・iol-xe 17.15.1)

設計= [problems/_drafts/ENTERPRISE-BUILD.design.md](../../problems/_drafts/ENTERPRISE-BUILD.design.md)。
ツール= [ecli.py](ecli.py)(IOS は SSH・Linux は ssh+sudo)＋[run.yml](run.yml)(vault から認証情報)。
手順= `steps/e*.yml`・生ログ= `logs/`。

## 段1 盤面 `problems/_POC-ENT1`(8 ノード＋非管理スイッチ SWT)

インベントリが固定名のため役割を割り当てている:

| ノード | 役割 |
|---|---|
| RT01 / RT02 | 境界ルータ(PPPoE クライアント)・TRANSIT 10.20.255.1/.2 |
| RT03 / RT04 | ISP-A / ISP-B の BRAS(PPPoE サーバ・CHAP・IPCP で 198.51.100.10 / 203.0.113.20 を固定払い出し) |
| RT05 | INET(192.0.2.1)。ACL `PMTU-BLACKHOLE`(packet-too-big を捨てる)を持つ |
| RT06 | コア(L3SW 代役)・TRANSIT .3・LAN 10.20.10.1/24 |
| SRV01 | INET-SV 192.0.2.10(nginx: `/ip`=送信元を返す・`/big.bin` 8MB／dnsmasq: www.inet.example) |
| PC01 | 社内端末 10.20.10.10 |

★運用: `bringup_data_ifs: true` は Linux ノードにも IOS の IF 立ち上げを試みて失敗する(provision の rc=2)。ルータは正常。実害なし。

## 結果

| # | 論点 | 実測 |
|---|---|---|
| P1 | PPPoE | **成立**。BRAS= `bba-group pppoe global`＋`virtual-template`(`ip unnumbered Loopback0`・`peer default ip address pool`・`ppp authentication chap`)＋`pppoe enable group global`。クライアント= 物理 IF に `pppoe enable group global`＋`pppoe-client dial-pool-number 1`、`Dialer1` に `ip address negotiated`・`encapsulation ppp`・`dialer pool 1`・`ppp chap hostname/password`。30 秒以内に `show pppoe session` UP・Dialer に IPCP のアドレス。`aaa new-model` なしでローカル username の CHAP で通る |
| P2 | MTU | ★**Dialer に `mtu 1492` が自動で入る**(running-config に出る)。BRAS の Virtual-Access2.1 も 1492。→ **「Dialer の MTU を詰め忘れる」罠は成立しない**。端末から DF 1500 は RT01 が `Frag needed (mtu = 1492)` を返す |
| P3 | MSS | **成立**。INET で packet-too-big を捨てると、MSS 調整なしでは大容量 curl が止まる(20 秒で 0 バイト・packet-too-big を 6 件捨てた)。`ip tcp adjust-mss 1452` で SYN の MSS が 1460→1452 に書き換わり 8MB を約 1 秒で取得。★**採点の罠**: 端末が PMTU を学習済み(DF 付き ping で `Frag needed` を受けた後など)だと、端末自身が MSS 1452 を名乗るので **MSS 調整なしでも通ってしまう**(1 回目の E2b〜E2e はこれで全部成功した)。MSS の検査の直前に端末で `ip route flush cache` が必須 |
| P9 | NAT と ACL の評価順 | **Dialer out= 変換後**(送信元 198.51.100.10 の行に一致)・**Dialer in= 変換前**(宛先 198.51.100.10)・LAN in= 送信元 10.20.10.10・LAN out= 宛先 10.20.10.10。→ 設計の T2(「DNS は DNS サーバだけ」を Dialer 上で送信元の社内アドレスでは書けない)は成立。公式 NAT Order of Operation との照合は裏どりの段で |
| P8 | 採点中の操作 | grade.yml は 1 回の試行で **IOS のチェックを全部集めてから Linux のチェックを順に実行**し、**全 PASS まで試行全体を最大 10 回繰り返す**。切替試験(落とす→待つ→確かめる→戻す)をチェックとして並べると繰り返しのたびに数分かかり、試験中のルータ状態も IOS チェックで取れない。→ **切替試験は grade.yml の外(ops スクリプトの独立した段)で 1 回だけ実行**する |
| P4 | 切替・切り戻し | `frequency 5`・`delay down 10 up 30`・監視対象 /32 を Dialer に固定。**(a) INET の ISP-A 向け IF shutdown**: 通信断 約 16 秒で予備(203.0.113.20)へ・復旧後 約 35 秒で主へ戻る。**(b) INET-SV の iptables で 198.51.100.0/24 を DROP**: 約 20 秒で切替・約 37 秒で戻る。**両方式は同じ振る舞い**→ 採点の切替試験は (b) を ops から使える(待ち 60 秒で足りる)。PPPoE は UP のまま・track だけが検知(`%TRACK-6-STATE: 1 ip sla 1 reachability Up -> Down`)。RT01 は OSPF の既定経路(RT02・metric 110)を学ぶ |
| E6 | 外部から | 模範 ACL なしでは **インターネット側から RT01 のグローバルに SSH(22) が開いており ping にも応答**(要件として意味がある)。WAN-IN 投入後は 22/23/80・ping すべて不応答 |
| — | 模範 ACL の平常 | 設計 §4.2 の WAN-IN/LAN-IN で SLA Up・OSPF FULL・Web/8MB/ping 成功・PC の直接 DNS は LAN-IN seq 80 で拒否(dig は `host unreachable`=ICMP 管理拒否)・445 は seq 50 で拒否 |
| T3 | LAN-IN の OSPF 許可抜け | **成立**。dead timer 満了(約 35 秒)で RT01 の隣接が落ち、コアの既定経路が RT02 へ |
| T1 | WAN-IN の echo-reply 抜け | **成立**。約 11 秒で track Down・**ISP-A は健全なのに ISP-B へ切替**(PC の出口が 203.0.113.20)。echo-reply を戻すと約 45 秒で復帰 |

## 設計への反映(段1)

- 模範の `ip mtu 1492` は不要(Dialer が自動で `mtu 1492`)。「MTU 詰め忘れ」を罠・誤解法から外す。MSS(`adjust-mss`)は残す
- MSS の採点は、端末の `ip route flush cache` 直後の新規接続で行う
- 切替試験は grade.yml の外で 1 回(ops の段)。上流断は INET-SV の iptables で作る

## 段2 盤面 `problems/_POC-ENT2`(8 ノード・2026-09-27)

★段1 のラボは作業マシン再起動の前後で CML から撤収されていた(全ラボ・リース台帳も空)。段1 の結果はログに残っており欠損なし。P6 は段2 で実施。

| ノード | 役割 |
|---|---|
| SW01 / SW02 | L3SW(ioll2-xe 17.15.1)。SVI 10/20/100/900・HSRPv2(奇数 SW01・偶数 SW02)・リレー・OSPF・STP root |
| SW03 | アクセス(ioll2)。PC01=VLAN10・PC02=VLAN20・RT01=VLAN100 |
| RT01 | SRV-DHCP(IOS DHCP サーバ・10.20.100.30・GW=VIP .1) |
| RT02 | 境界代役(TRANSIT .1・外側 192.0.2.1・OSPF 既定経路・`ntp master 3`・P6 試験) |
| PC01 / PC02 | ubuntu 端末(netplan `dhcp-identifier: mac`・DHCP の経路/DNS は使わず静的経路) |
| SRV01 | 外部ホスト 192.0.2.10(nginx+dnsmasq) |

トランクは native 666・allowed 10,20,99,100,900(MGMT 999 を載せない)。ioll2 は telnet(`ecli.py` の `m: telnet`)。

## 結果(段2)

| # | 論点 | 実測 |
|---|---|---|
| P5 | ioll2 の L3 | `ip routing`・SVI・HSRPv2(preempt/priority)・`ip helper-address`・OSPF(`passive-interface default`)・VLAN ごとの STP priority すべて受理・動作。SW03 のブロックは VLAN ごとに逆側 |
| P5 | ioll2 の LACP | **動く**。SW01-SW02 の 1 本を `channel-group 1 mode active` → Po1(SU)・Et0/0(P)。HSRP/OSPF 影響なし |
| P5 | ioll2 の port-security | 動く(Secure-up・MAC 学習) |
| P5 | ioll2 の DHCP snooping/DAI | ★**snooping は受理されるが DHCP を一切捕まえない**(統計 転送 0/破棄 0・binding 0。option 82 の問題ではない= リレー側 trust-all でも同じ)。**DAI は binding が無いので全 ARP を捨てる**(DHCP Drops)→ 端末が GW に届かない。→ **E14(snooping+DAI)は ioll2 では出題不可**(IPv6 FHS と同じ傾向)。IOSvL2 は未確認 |
| — | ioll2 の構文 | `spanning-tree portfast edge` は `% Invalid input`(旧構文 `portfast` のみ。STP シリーズ既知) |
| — | DHCP リレー | 両 L3SW の SVI がリレーし、端末は GW=VIP・DNS・サーバアドレスを受け取る。ubuntu(`dhcp-identifier: mac`)の client-id は **`01`+MAC**(IOS の binding 表示 `0152.5400.xxxx.xx`) |
| T12 | SVI in ACL と HSRP | **成立**。相方の hello `10.20.10.2(1985) -> 224.0.0.102` が ACL で捨てられ(ログに出る)両方 Active。外すと 15 秒以内に Standby |
| T6 | リレー応答の宛先 | **成立**。DHCP サーバの応答は **SVI の実アドレス(.2/.3)宛て**・VIP 宛ては 0。サーバ VLAN の in ACL で VIP 宛てだけ許すと応答 8 件が捨てられアドレスが付かない。★RT01 の GW は VIP なので **SW02 の giaddr(.3)宛ての応答も Active の SW01 の Vlan100 を通る** |
| T4 | SVI in ACL に DHCP 行なし | **成立**。送信元 0.0.0.0 の DISCOVER が捨てられ(4 件)アドレスが付かない |
| T5 | 更新ユニキャストだけ落とす | ★**症状が見えない**。リース 2 分で 4 分観察してもアドレスは消えない(サーバの DISCOVER が 25 件に増え、裏で同じアドレスを取り直している)。→ **罠から外す** |
| P7 | 複合機の予約 | **成立**。CML でインターフェースの `mac_address` を設定→ `client-identifier 01<MAC>` の host プールで予約アドレス(Manual・Infinite)。★MAC は**起動済みノードでは変更不可**(`Physical configuration of node is locked`)・**wipe 後なら可**→ 生成器ではトポロジ定義に `mac_address` を書く。★予約は動的リースが残っていると `% A binding already exists in DEV pool.` で拒否(先に clear。DHCP シリーズ既知) |
| P6 | reflexive ACL | **動く**。内部発の Web 8MB・DNS・ping が反射エントリで戻り、外部から RT02 の SSH・社内への ping は閉じる。★**evaluate と同じ ACL に `log` 付き行は置けない**(`% Reflect/Eval and log ... ACE cannot be configured in same ACL`) |
| P6 | ZBF / CBAC | ★**iol-xe 17.15 には無い**(`zone`・`ip inspect`・`parameter-map type inspect` が Unrecognized)。→ H4 は reflexive ACL に限る(ZBF は cat8000v 等が要る) |
| P11 | NTP 同期時間 | `ntp server` 設定から **約 3 分でサーバ選択**(`*~10.20.255.1`・reach 3・stratum 4)。ただし **6 分後も `Clock is unsynchronized`**。→ 採点は「`*` で選択済み・reach が 0 でない」で見る(synchronized は要求しない) |
| P10 | 制御プレーンと in ACL | SVI の in ACL は HSRP hello を捨てる(T12)・RT の in ACL は OSPF hello を捨てる(段1 T3)。どちらも成立 |

## 設計への反映(段2)

- L3SW/アクセスは **ioll2 で確定**(L3・HSRPv2・リレー・OSPF・LACP・port-security が動く)。L3SW 間は LACP で束ねる要件を入れてよい
- **E14(DHCP snooping＋DAI)はハードから外す**(ioll2 で snooping 非機能)。IOSvL2 で効くかは未確認(必要なら別 PoC)
- **H4 は reflexive ACL**(ZBF/CBAC は iol-xe に無い)。evaluate の ACL に log 行を置けない制約を模範解に反映
- **T5 は罠から外す**(症状が見えない)。T4・T6・T12 は誤解法 E2E に使う
- 端末は ubuntu(`dhcp-identifier: mac`)。複合機の予約は **トポロジ定義で MAC を固定**＋`client-identifier 01<MAC>`
- NTP の採点は選択済み(`*`)＋reach で見る
- portfast は旧構文(`spanning-tree portfast`)で書く(ioll2 は `edge` 不可)

## 段3 `problems/_POC-ENT3`（2026-09-27・ioll2 の `no ip routing`）

盤面: SW01（L3SW 役・VLAN 40/110 の SVI）─ SW02（アクセス SW 役・VLAN 40 の管理 SVI＋`ip default-gateway 10.9.40.1`）／RT01（VLAN 110 の端末役）。両 SW とも day0 で `no ip routing`。

| # | 論点 | 実測 |
|---|---|---|
| R1 | day0 の `no ip routing` と管理 | **受理され、管理 VLAN 999 は生きる**（telnet 可・採点ホストへ ping 可）。`show ip route` は `Default gateway is 10.9.40.1` 表示 |
| R1 | day0 の `vlan` 定義 | ★**ioll2 も VTP サーバモードでは day0 の `vlan` が消える**（IOSvL2 と同じ）→ day0 で VLAN を作るなら先に `vtp mode transparent`。手で作れば残る |
| R2〜R4 | ルーティング無効時の default-gateway | ★**効かない**。SW02 は別サブネット宛ての ARP を **VLAN 999（採点用の管理 SVI）側に出し**、管理 LAN 上の外部機器（MAC `0027.e32f.468c`）が**プロキシ ARP で応答**→ 通信は管理 LAN へ流れて消える（L3SW 側は `ip routing` 有効で両サブネットに到達できるのに、SW02→VLAN 110 端末・端末→SW02 とも不通）。公式ガイドもルーティング無効時の手段として default gateway と並べてプロキシ ARP を挙げている。実機のアクセス SW は SVI が 1 つなので表に出ないが、本ラボは全機器に採点用の管理 SVI があるため 2 つになる |

結論: **アクセススイッチを `no ip routing` にする案は不採用**（通信が実 LAN 側へ出ていく）。アクセススイッチは ioll2 の既定（ルーティング有効）のまま、既定の静的経路で管理 SVI を他サブネットへ通す（現行の GEN-ENT）。→ ユーザ提案で**スイッチを管理 IF なし（コンソール採点）**にし、全スイッチ `no ip routing` を実現（設計 §13.3・E2E 0→100・入れ忘れ 48）。
