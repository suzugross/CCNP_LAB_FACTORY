# ENTERPRISE-BUILD — エンタープライズ拠点ネットワーク構築ラボ 設計書

- 起票: 2026-09-27（BL-225）・**状態: 標準構築 完了（2026-09-27・§13.3 でスイッチをコンソール化）**。PoC 段1/段2 = [poc/enterprise/README.md](../../poc/enterprise/README.md)・§11/§12。実装記録 = §13。残り（ハード・TS・世界 B・パック）= BL-229
- 位置付け: **L4 複合構築問**（標準 難5／ハード 難6）。後続で TS モード（難5）
- 対象単元（CURRICULUM）: U-A1 VLAN/トランク・U-A2 EtherChannel（PoC 次第）・U-A3 STP・U-A5 L2 セキュリティ（ハード）・
  U-A6 FHRP・U-B1 static/floating・U-B5 PBR（ハード）・U-D1/U-D2 OSPF・U-H2 IPv4 ACL・U-I1 NTP・U-I2 NAT・U-I3 DHCPv4・U-I7 IP SLA/track。
  PPPoE はブループリント外だが上記単元に関連するため範囲内（着手時に CURRICULUM へ新単元 `U-B?` を足すか判断）
- 方針: **ログインユーザ作成などの管理系は棚上げし、通信（到達性・遮断・名前解決・冗長）を主題にする**
- ★本書のうち **「要PoC」「要裏どり」の付いた挙動は未確認**。CLAUDE.md の 3 ソース確認＋実機で確定させてから要件・採点に入れる。
  確定しなければその論点は捨てる。

---

## 0. 決定事項（2026-09-27 ユーザ承認）

| # | 論点 | 決定 |
|---|---|---|
| D1 | ルータ構成 | **標準＝世界 A（RT×2・各 1 回線）**。世界 B（RT×1 で 2 回線）は別 seed の世界として用意 |
| D2 | DHCP サーバの置き場所 | **サーバ VLAN に IOS の DHCP 専用機（SRV-DHCP）を置き、L3SW がリレー**。プールは解答者が作る。Linux の DHCP サーバ構築はハード |
| D3 | Dialer の戻り通信 | **標準はステートレス ACL**（established・送信元ポート指定）。ステートフル化（reflexive ACL／ZBF）はハード |
| D4 | DNS サーバ | 標準は既設（BIND9 構築済み）。構築はハード |
| D5 | 管理系 | ログインユーザ・AAA・vty 制限は扱わない |

---

## 1. トポロジ

```
                        [INET-SV]  192.0.2.10  ISP DNS(再帰+権威 inet.example)・Web(/ip=送信元を返す)・NTP・大容量ファイル
                            |      192.0.2.0/24
   [EXT-PC] 192.0.2.66 ─ [INET] ── INET→INET-SV 方向で ICMP type3 code4 を捨てる(PMTUD ブラックホール役)
                          /    \
                  [ISP-A]        [ISP-B]         BRAS = PPPoE サーバ(既設)
                     |  PPPoE       |  PPPoE
                  [RT01]         [RT02]          解答者が構築: Dialer・NAT・ACL・IP SLA・OSPF
                     |              |
         ========= VLAN 900 TRANSIT 10.S.255.0/29 =========
                     |              |
                 [L3SW01]=======[L3SW02]         解答者: SVI・HSRP・ACL・リレー・OSPF・STP root
                  |  \  \      /  /  |           (L3SW 間 2 本。LACP で束ねるかは PoC P5 で決定)
              [ASW01]  [ASW02]  [SRVSW]          解答者: VLAN・トランク・RSTP・エッジ保護
               |  |     | | |    | | |
             営業 開発 経理 情シス 複合機 来客    SRV-DNS SRV-APP SRV-DHCP
             (PC-SALES/PC-DEV 等は alpine の DHCP クライアント)
```

### 1.1 ノード一覧（21 ノード）

| ノード | 役割 | イメージ案 | 構築者 |
|---|---|---|---|
| INET | インターネット中継 | iol-xe | 既設 |
| ISP-A / ISP-B | BRAS（PPPoE サーバ・CHAP・IPCP 固定払い出し） | iol-xe | 既設 |
| INET-SV | ISP DNS・Web・NTP・大容量ファイル | ubuntu | 既設 |
| EXT-PC | 外部からの到達試験 | alpine | 既設 |
| RT01 / RT02 | 境界ルータ | iol-xe | **解答者** |
| L3SW01 / L3SW02 | コア | ioll2-xe か IOSvL2（PoC P5） | **解答者** |
| ASW01 / ASW02 / SRVSW | アクセス | 同上 | **解答者** |
| SRV-DHCP | DHCP 専用機（IOS） | iol-xe | **解答者**（プール）※IF アドレスと経路は既設 |
| SRV-DNS | 社内 DNS（BIND9・社内ゾーン＋ISP DNS へ転送） | ubuntu | 既設（ハードでは解答者） |
| SRV-APP | 社内 Web(80/443)・ファイル役(445 待受) | alpine | 既設 |
| PC-SALES / PC-DEV / PC-ACCT / PC-IT / PC-GUEST | 部門端末 | alpine | 既設（DHCP 待ち） |
| PRN01 | 複合機（9100/631 待受・DHCP 予約） | alpine | 既設 |

- 資源見込み: iol-xe×6・L2×5・ubuntu×2（各 2GB）・alpine×8（各 512MB）で RAM 約 18〜20GB。
  **CML 40 ノード枠のうち 21 を使う** → 並行する他ラボは合計 19 ノード以内に抑える必要がある（パックでは大型スロット扱い）。
- 構築時間見込み: ubuntu の起動が律速で 6〜8 分（CAMPUS-TS-01 実績から推定）。

### 1.2 論理リンク（IF 名は生成器がイメージに合わせて割り当てる）

| 区間 | 種別 | 備考 |
|---|---|---|
| RT01—L3SW01、RT02—L3SW02 | L3SW 側は VLAN 900 のアクセスポート | RT 側はルーテッド IF（`ip nat inside`） |
| RT01—ISP-A、RT02—ISP-B | PPPoE | RT 側 IF は IP なし＋`pppoe-client` |
| L3SW01—L3SW02 | トランク 2 本 | PoC P5 で ioll2 が LACP 可なら「束ねる」を要件に。不可なら 1 本はブロック |
| ASWxx/SRVSW—L3SW01、—L3SW02 | トランク | 三角形。VLAN ごとに片方の上りがブロック |
| 端末—ASW | アクセスポート | エッジ保護の対象 |

---

## 2. アドレス・VLAN 計画（seed で振る。以下は S=20 の例）

| VLAN | 名称 | サブネット | GW(VIP) | L3SW01/02 実 IP | インターネット | 備考 |
|---|---|---|---|---|---|---|
| 10 | 営業 SALES | 10.20.10.0/24 | .1 | .2 / .3 | 可 | |
| 20 | 開発 DEV | 10.20.20.0/24 | .1 | .2 / .3 | 可 | |
| 30 | 経理 ACCT | 10.20.30.0/24 | .1 | .2 / .3 | **不可** | イントラのみ |
| 40 | 情シス IT | 10.20.40.0/24 | .1 | .2 / .3 | 可 | MGMT 到達可・全部門へ ping 可 |
| 50 | 複合機 PRINT | 10.20.50.0/24 | .1 | .2 / .3 | 不可 | PRN01 は .50 を予約 |
| 60 | 来客 GUEST | 10.20.60.0/24 | .1 | .2 / .3 | HTTP/HTTPS/DNS のみ | DNS は ISP DNS を配る・リース 1 時間 |
| 100 | サーバ SERVER | 10.20.100.0/24 | .1 | .2 / .3 | DNS サーバの 53 のみ | SRV-DNS .10・SRV-APP .20・SRV-DHCP .30 |
| 99 | MGMT | 10.20.99.0/24 | .1 | .2 / .3 | 不可 | ASW01 .11・ASW02 .12・SRVSW .13 |
| 900 | TRANSIT | 10.20.255.0/29 | — | .3 / .4 | — | RT01 .1・RT02 .2 |
| 999 | CML 採点用 | — | — | — | — | **トランクの allowed から外す**（STP シリーズの必須規則） |

外部側（既設・固定）:

| 区間 | アドレス |
|---|---|
| ISP-A 払い出し | RT01 Dialer ← **198.51.100.10/32**（IPCP）・BRAS-A Lo 198.51.100.1 |
| ISP-B 払い出し | RT02 Dialer ← **203.0.113.20/32**（IPCP）・BRAS-B Lo 203.0.113.1 |
| ISP-A—INET / ISP-B—INET | 198.51.100.248/30 / 203.0.113.248/30 |
| INET セグメント | 192.0.2.0/24（INET .1・INET-SV .10・EXT-PC .66） |
| 社内ドメイン | `corp.example`（SRV-DNS が権威）／外部ドメイン `inet.example`（INET-SV が権威） |

seed で振るもの: 第 2 オクテット S・VLAN 番号・部門名（3〜4 部門）・**どの部門がイントラのみか**・**来客に許すもの**（HTTP/HTTPS/DNS か、HTTPS/DNS のみ か）・
印刷ポート（9100 のみ／9100+631）・主系回線（ISP-A か B か）・HSRP/root の偶奇の割り当て・世界 A/B。

---

## 3. 要件（問題文に書く内容）

問題文は既存の「要件書形式」（gen_s2svpn・gen_v6addr_build と同じ）で書く。文体は Cisco 語規約（BL-207）。
ヒントは控えめにし、罠（§5）は問題文に書かない。

### 3.1 支給情報（問題文に書く）

- ISP 接続情報: 回線ごとの PPPoE 認証 ID/パスワード（CHAP）・アドレスは IPCP で払い出される旨
- ISP の DNS・NTP サーバ: 192.0.2.10
- 回線監視の対象: 192.0.2.10（ISP 網の先にあることだけ書く）
- 社内サーバのアドレス・社内ドメイン名
- アドレス計画表（§2）
- 触ってはいけないもの: ISP-A/B・INET・INET-SV・EXT-PC・サーバ（DNS・APP）・端末・VLAN 999

### 3.2 通信要件マトリクス（問題文の中心）

| 送信元＼宛先 | 他部門 | SRV-DNS | SRV-APP | SRV-DHCP | 複合機 | MGMT | インターネット |
|---|---|---|---|---|---|---|---|
| 営業・開発 | ✕ | DNS | Web・ファイル | DHCP | 印刷 | ✕ | ◯（危険ポート除く） |
| 経理 | ✕ | DNS | Web・ファイル | DHCP | 印刷 | ✕ | ✕ |
| 情シス | ping のみ | DNS | Web・ファイル | DHCP | 印刷 | SSH・SNMP・ping | ◯（危険ポート除く） |
| 来客 | ✕ | ✕ | ✕ | DHCP | ✕ | ✕ | Web・DNS(ISP DNS) のみ |
| 複合機 | ✕ | ✕ | ✕ | DHCP | — | ✕ | ✕ |
| サーバ | ✕（戻りのみ） | — | — | — | ✕ | ✕ | SRV-DNS の DNS のみ |
| MGMT(スイッチ) | ✕（戻りのみ） | — | syslog | — | ✕ | — | ✕ |

補足要件（文章で書く）:

- 部門端末の DNS は社内 DNS。インターネットへ直接 DNS を問い合わせることはできないこと（来客を除く）
- 部門端末から社内サーバへの ping は許可
- 危険ポート（25・135〜139・445）はインターネットへ出さない
- インターネット側から自社のグローバルアドレスへの新規接続（ping 含む）に応答しないこと
- 送信元が私設アドレス・ループバックのパケットをインターネット側から受け入れないこと。
  社内側からは、社内サブネット以外を送信元とするパケットをインターネットへ出さないこと

### 3.3 冗長要件

- 主回線は ISP-A（seed）。**ISP 網内の障害で主回線のインターネット到達性が失われた場合**（PPPoE セッションが維持されていても）、
  予備回線へ切り替わること。主回線の復旧後は主回線へ戻ること
- 主回線の障害を検知してから一定時間以内（目安 60 秒）に通信が回復すること
- 各 VLAN の既定ゲートウェイは冗長化すること（仮想アドレスは各サブネットの .1）
- ゲートウェイの Active と STP のルートブリッジは VLAN ごとに同じ機器にすること（奇数 VLAN は L3SW01、偶数 VLAN は L3SW02 など。seed）
- L3SW と RT の間はトランジット VLAN で接続し、経路は OSPF で交換すること。社内側の SVI では OSPF の hello を出さないこと

### 3.4 そのほかの要件

- インターネット上には ICMP を通さない経路がある。大きなファイルの TCP 転送がタイムアウトしないこと
- NTP: RT は ISP の NTP に同期。L3SW は RT に同期。アクセススイッチは L3SW（MGMT VLAN のアドレス）に同期
- DHCP: 全端末 VLAN に配る（ゲートウェイ＝仮想アドレス・DNS・ドメイン名）。仮想アドレスと L3SW の実アドレスは配らない。
  複合機は予約アドレス。来客のリース 1 時間・DNS は ISP DNS
- L2: rapid-pvst。端末ポートは PortFast＋BPDU ガード。未使用ポートは shutdown＋未使用 VLAN。ネイティブ VLAN は未使用番号（seed）。
  トランクで許可する VLAN は必要なものだけ

---

## 4. 模範解答の骨子（生成器の golden・E2E で使う。問題文には出さない）

### 4.1 RT01（世界 A・主回線）

```
interface Ethernet0/1                      ! ISP-A 向け
 no ip address
 pppoe enable group global
 pppoe-client dial-pool-number 1
!
interface Dialer1
 ip address negotiated
 ip tcp adjust-mss 1452                 ! mtu 1492 は PPPoE で自動(PoC P2)
 encapsulation ppp
 dialer pool 1
 ppp chap hostname <ID>
 ppp chap password <PW>
 ip nat outside
 ip access-group WAN-IN in
!
interface Ethernet0/0                      ! TRANSIT
 ip address 10.20.255.1 255.255.255.248
 ip nat inside
 ip access-group LAN-IN in
!
ip sla 1
 icmp-echo 192.0.2.10 source-interface Dialer1
 frequency 5
ip sla schedule 1 life forever start-time now
track 1 ip sla 1 reachability
 delay down 10 up 30
ip route 0.0.0.0 0.0.0.0 Dialer1 track 1
ip route 192.0.2.10 255.255.255.255 Dialer1   ! 監視対象を回線に固定(抜けると切り戻せない=IP SLA TS の実測知見)
!
router ospf 1
 default-information originate metric 10 metric-type 1   ! RT02 は metric 100
!
ip access-list standard NAT-SRC
 permit 10.20.10.0 0.0.0.255
 permit 10.20.20.0 0.0.0.255
 permit 10.20.40.0 0.0.0.255
 permit 10.20.60.0 0.0.0.255
 permit host 10.20.100.10
ip nat inside source list NAT-SRC interface Dialer1 overload
!
ntp server 192.0.2.10
```

- `default-information originate`（always なし）は RIB に OSPF 以外の既定経路がある間だけ広告する。
  track が落ちて static が消えると広告が止まり、L3SW は RT02 の既定経路（metric 100）へ移る。**要PoC P4 で秒数を測る**。
- 世界 B（RT×1・2 回線）は NAT を `route-map NAT-A → match ip address NAT-SRC / match interface Dialer1` の 2 本にし、
  既定経路は track 付き static＋AD を上げた floating static にする。

### 4.2 RT の ACL（ステートレス・標準）

```
ip access-list extended WAN-IN             ! Dialer in = NAT 変換前(宛先はグローバル) ※要裏どり P9
 deny   ip 10.0.0.0 0.255.255.255 any
 deny   ip 172.16.0.0 0.15.255.255 any
 deny   ip 192.168.0.0 0.0.255.255 any
 deny   ip 127.0.0.0 0.255.255.255 any
 permit tcp any any established
 permit udp host 192.0.2.10 eq domain any          ! DNS 応答(SRV-DNS の転送と来客。変換前なので宛先で区別できない)
 permit udp host 192.0.2.10 eq ntp any eq ntp
 permit icmp any any echo-reply                    ! 抜くと IP SLA が落ちて誤って切り替わる
 permit icmp any any unreachable
 permit icmp any any time-exceeded
 deny   ip any any log
!
ip access-list extended LAN-IN             ! TRANSIT in = NAT 変換前(送信元は社内アドレス)
 permit ospf any any                               ! 抜くと OSPF 隣接が落ちる
 permit udp host 10.20.255.3 host 10.20.255.1 eq ntp
 permit udp host 10.20.255.4 host 10.20.255.1 eq ntp
 deny   tcp any any eq smtp
 deny   tcp any any range 135 139
 deny   udp any any range netbios-ns netbios-ss
 deny   tcp any any eq 445
 permit udp host 10.20.100.10 any eq domain
 permit tcp host 10.20.100.10 any eq domain
 permit udp 10.20.60.0 0.0.0.255 host 192.0.2.10 eq domain
 deny   udp any any eq domain
 deny   tcp any any eq domain
 permit tcp 10.20.60.0 0.0.0.255 any eq www
 permit tcp 10.20.60.0 0.0.0.255 any eq 443
 deny   ip 10.20.60.0 0.0.0.255 any
 permit ip 10.20.10.0 0.0.0.255 any
 permit ip 10.20.20.0 0.0.0.255 any
 permit ip 10.20.40.0 0.0.0.255 any
 deny   ip any any log
```

### 4.3 L3SW の SVI ACL（例: 営業 VLAN 10 in）

```
ip access-list extended SALES-IN
 permit udp any eq bootpc any eq bootps            ! DHCP DISCOVER/REQUEST(ブロードキャスト。抜くとリレーされない)
 permit udp any host 224.0.0.102 eq 1985           ! 相方の HSRPv2 hello ※要PoC P10(SVI in ACL が HSRP を止めるか)
 permit udp 10.20.10.0 0.0.0.255 host 10.20.100.30 eq bootps   ! 更新(T1)はサーバへユニキャスト
 permit udp 10.20.10.0 0.0.0.255 host 10.20.100.10 eq domain
 permit tcp 10.20.10.0 0.0.0.255 host 10.20.100.10 eq domain
 permit tcp 10.20.10.0 0.0.0.255 host 10.20.100.20 eq www
 permit tcp 10.20.10.0 0.0.0.255 host 10.20.100.20 eq 443
 permit tcp 10.20.10.0 0.0.0.255 host 10.20.100.20 eq 445
 permit icmp 10.20.10.0 0.0.0.255 10.20.100.0 0.0.0.255 echo
 permit tcp 10.20.10.0 0.0.0.255 host 10.20.50.50 eq 9100
 permit icmp 10.20.10.0 0.0.0.255 10.20.40.0 0.0.0.255 echo-reply   ! 情シスからの ping の戻り
 deny   ip any 10.0.0.0 0.255.255.255
 deny   ip any 172.16.0.0 0.15.255.255
 deny   ip any 192.168.0.0 0.0.255.255
 permit ip 10.20.10.0 0.0.0.255 any                ! イントラのみ VLAN はこの行が無い
```

- **戻り通信が必要な VLAN**（サーバ・複合機・MGMT）の in ACL は `permit tcp <自> <部門> established`・
  `permit udp host <DNS> eq domain <部門>`・`permit icmp <自> any echo-reply` の形。
- **SRV-DHCP の応答**は giaddr（SVI の実アドレス .2/.3）宛ての UDP 67→67。サーバ VLAN の in ACL で
  `permit udp host 10.20.100.30 eq bootps 10.20.0.0 0.0.255.255 eq bootps` が要る。
- **MGMT**: スイッチからの syslog（UDP 514 → SRV-APP）・NTP（L3SW の MGMT アドレス宛て）は新規通信なので例外として許可。

### 4.4 SRV-DHCP（IOS）

```
ip dhcp excluded-address 10.20.10.1 10.20.10.3     ! VIP と実アドレス(各 VLAN)
ip dhcp pool SALES
 network 10.20.10.0 255.255.255.0
 default-router 10.20.10.1
 dns-server 10.20.100.10
 domain-name corp.example
ip dhcp pool GUEST
 network 10.20.60.0 255.255.255.0
 default-router 10.20.60.1
 dns-server 192.0.2.10
 lease 0 1
ip dhcp pool PRN01
 host 10.20.50.50 255.255.255.0
 client-identifier 01<MAC>                          ! 要PoC P7(alpine udhcpc の client-id と CML の MAC 固定)
 default-router 10.20.50.1
ip route 0.0.0.0 0.0.0.0 10.20.100.1               ! 既設(応答が giaddr に戻るための経路)
```

### 4.5 L2

- `spanning-tree mode rapid-pvst`・奇数 VLAN は L3SW01 が priority 24576／L3SW02 が 28672、偶数は逆（seed）
- HSRP も同じ向き（Active 側に priority 110＋preempt）
- 端末ポート: `switchport mode access`・`spanning-tree portfast`（edge）・`spanning-tree bpduguard enable`
- 未使用ポート: `shutdown`＋未使用 VLAN。トランク: `switchport trunk native vlan <未使用>`・`allowed vlan` を必要なものだけ（999 を含めない）

---

## 5. 作問の見どころ（交差する罠）— 問題文には書かない

| # | 罠 | 表れ方 | 確認 |
|---|---|---|---|
| T1 | Dialer in で echo-reply を捨てる | IP SLA が失敗し、主回線が健全でも予備へ倒れる（冗長のチェックと出口 IP のチェックが落ちる） | 要PoC |
| T2 | 外側 in は NAT 変換前・外側 out は変換後 | 「DNS は DNS サーバだけ」を Dialer 上で書くと送信元がグローバルになり一致しない | 要裏どり P9（公式 NAT Order of Operation）＋実機 |
| T3 | RT の LAN-IN に OSPF の許可が無い | 隣接が落ち、既定経路も社内経路も消える | 定説・要PoC |
| T4 | SVI in ACL が DHCP ブロードキャストを捨てる | リレーされずアドレスが付かない | 要PoC |
| T5 | 更新（T1）がサーバへのユニキャスト | 初回は付くが更新で失敗する（採点時間内に出るか要検討。リース短縮で誘発） | 要PoC |
| T6 | リレー応答は SVI の実アドレス宛て | サーバ VLAN の in ACL で VIP 宛てしか許可していないと応答が戻らない | 要PoC |
| T7 | UDP の戻りは established で拾えない | DNS 応答・SNMP 応答が戻らない | 定説 |
| T8 | 情シスからの ping の戻り | 部門 in ACL の `deny 10/8` が echo-reply を捨てる | 定説 |
| T9 | 来客の DNS 例外 | 出口の「53 は DNS サーバだけ」で来客の名前解決が止まる | 定説 |
| T10 | MSS 調整が無い | ping・小さい HTTP は通るのに大容量 curl だけ止まる | 要PoC P2/P3 |
| T11 | 監視対象の /32 を回線に固定していない | 切り替え後、監視 ping が予備回線経由で成功して主回線へ戻ってしまう（揺れる） | IP SLA TS の実測知見を再確認 |
| T12 | SVI in ACL と HSRP hello | 相方の hello を捨てて両方 Active になる | 要PoC P10 |

---

## 6. 採点設計

### 6.1 採点の段取り

1. **静的収集**: 各機器の `show running-config`・`show ip route`・`show standby brief`・`show spanning-tree`・`show ip nat translations`・`show track`・`show ntp associations`
2. **端末からの疎通**: 端末ごとに `udhcpc` の結果（アドレス・GW・DNS）→ 疎通マトリクスの許可・拒否を `ping -c2 -W1`・`curl -m5`・`nc -z -w3`・`dig +time=2`
3. **外部から**: EXT-PC から RT のグローバルアドレスへ 22/23/80/443・ping。社内アドレスへの到達
4. **MSS**: PC-SALES で INET-SV の大容量ファイル（数 MB）を `curl -m30` で取得
5. **冗長（動的）**: 採点器が INET の ISP-A 向け IF を shutdown → 60 秒待つ → PC-SALES から `curl http://192.0.2.10/ip` が ISP-B のアドレスを返す → 復旧 → 待つ → ISP-A のアドレスへ戻る。
   **採点器が操作するのは既設ノード（INET）だけ**。操作の仕組みは要PoC P8（無ければ grade の前後処理を ops スクリプトに持たせる）

### 6.2 チェック一覧（配点は目安・計 100）

| 群 | 内容 | 配点 |
|---|---|---|
| A PPPoE/NAT | 両回線のセッション確立・Dialer のアドレス・PAT の変換（各部門の送信元で出口 IP が主回線） | 10 |
| B 冗長 | 平常時は主回線・上流断で予備へ・復旧で戻る・track/SLA の存在 | 15 |
| C DHCP | 全端末が正しいサブネット／GW／DNS・来客は ISP DNS・複合機は予約アドレス | 10 |
| D 名前解決 | 部門端末で社内名・外部名が引ける／来客は外部名のみ／部門端末から ISP DNS 直接は不可 | 10 |
| E 疎通(許可) | マトリクスの ◯ の代表組合せ（Web・ファイル・印刷・MGMT の SSH/SNMP・情シスの ping・インターネット） | 15 |
| F 疎通(拒否) | マトリクスの ✕ の代表組合せ・危険ポート・経理のインターネット・来客の社内。**同じ端末の E が成立した時だけ加点** | 15 |
| G 境界 | 外部から応答しない・MSS（大容量 curl）・なりすまし（ACL 監査） | 10 |
| H L2/L3 | root＝HSRP Active・エッジ保護・未使用ポート・ネイティブ VLAN・999 がトランクに無い・OSPF passive・NTP 同期 | 10 |
| I 許可しすぎ | `acl_model.py` の `acl_vectors` で部門/サーバ/RT の ACL を意味評価（実通信で拾えない組合せ。例: 営業→開発 TCP/445・来客→サーバ UDP/53・サーバ→部門 TCP SYN） | 5（減点方式でも可） |

- NTP 同期は数分かかる。採点は `show ntp associations` の設定と到達性（reach）で見て、synced は必須にしない（要PoC）。
- ioll2 を使う場合、L2 の採点は telnet 経路（STP シリーズと同じ）。

---

## 7. モード

| モード | 難 | 差分 |
|---|---|---|
| 標準構築 | 5 | §3 の全要件。ISP・INET・サーバ・端末は既設 |
| ハード構築 | 6 | 標準＋次から seed で 2〜3 個: **H1** SRV-DNS を白紙の ubuntu で構築（BIND9: 社内ゾーン正引き・逆引き・ISP DNS への forwarder・再帰は社内のみ）／**H2** DHCP を白紙の ubuntu で構築（Kea か ISC）／**H3** 部門別の出口振り分け（営業→ISP-A・開発→ISP-B・相互予備。PBR＋`verify-availability`＋track）／**H4** Dialer in のステートフル化（reflexive ACL か ZBF。PoC P6）／**H5** アクセス SW の DHCP snooping＋DAI（PoC P5）／**H6** `hardmode.py` のノイズ ACL を既設 ACL として混ぜる |
| TS | 5 | golden に故障を 2〜3 個注入（CAMPUS-TS-01 の往復方式）。故障候補= §5 の T1〜T12 を故障として注入（echo-reply 削除・OSPF 許可削除・リレー応答の遮断・Dialer out への置き間違い・MSS 削除・/32 固定削除・HSRP/root 不一致・来客 DNS 例外削除・ネイティブ VLAN 不一致・allowed vlan 漏れ） |

---

## 8. 実装計画（着手後）

| 段 | 内容 |
|---|---|
| P0 | PoC（§9）。ユーザ指示があるまで開始しない |
| P1 | 生成器 `topologies/gen_enterprise.py`（`--mode build --level std|hard`・`--world a|b`・seed）→ `problems/GEN-ENT-<seed>/`（problem.yml・task.md・grading・golden・answers）。既設部分の day0 と Linux の初期化スクリプト |
| P2 | 採点（§6）。拒否チェックの対成立・acl_vectors・動的冗長の前後処理（`ent_ops.py` に持たせる可能性） |
| P3 | selftest（seed を振って要件・golden・採点の整合を机上で全数検査）→ 実機 E2E: 白紙の基線 → golden 100 → 誤解法の降格（下表） |
| P4 | パック組込み（ジャンル `entbuild`・大型スロット・既定抽選外）・CATALOG・CURRICULUM・units.yml |
| P5 | ハード・TS・世界 B |

誤解法の E2E（降格の確認）:

| 誤解法 | 期待 |
|---|---|
| Dialer in で echo-reply を許可しない | B が落ちる |
| DNS の制限を Dialer out に書く | D/F が落ちる（T2 が PoC で確定した場合） |
| MSS 調整なし | G の大容量 curl が落ちる |
| 部門 SVI を `permit ip any any` で済ませる | F・I が落ちる |
| root と HSRP Active の向きが逆 | H が落ちる |
| 監視対象の /32 固定なし | B の切り戻しが揺れる（T11 が再現した場合） |

---

## 9. PoC 項目（未着手・ユーザ指示待ち）

| # | 確認すること | 決まるもの |
|---|---|---|
| P1 | iol-xe の PPPoE サーバ（bba-group・virtual-template・CHAP・IPCP 固定払い出し）とクライアント（Dialer・dial-pool）が成立するか | 本問の成否 |
| P2 | Dialer の MTU を詰めない時の挙動（CML のリンクが 1508 バイトのフレームを通すか） | MSS 要件の書き方 |
| P3 | INET で ICMP unreachable を捨てた時、`adjust-mss` の有無で大容量 curl の成否が分かれるか（Linux 側の PMTU 探索の既定も確認） | G の採点 |
| P4 | IP SLA（source-interface Dialer）＋track＋static＋`default-information originate` の取り下げ・復帰にかかる秒数 | B の待ち時間 |
| P5 | L3SW を ioll2 と IOSvL2 のどちらにするか（SVI ACL in/out・HSRPv2・DHCP リレー・OSPF・LACP・DHCP snooping/DAI・port-security）。ioll2 は長時間稼働で BPDU 欠落の前例（BL-219）、IOSvL2 は起動後の SVI 固着の前例あり | イメージ・L3SW 間の束ね |
| P6 | iol-xe で reflexive ACL／ZBF（self zone を含む）が使えるか | H4 |
| P7 | alpine の udhcpc の client-id（option 61）の既定と、CML でインターフェースの MAC を固定できるか | 複合機の予約方式（不可なら静的 IP に落とす） |
| P8 | 採点の途中で既設ノードを操作して待ち、判定して戻す仕組みが既存の採点系にあるか（gen_ipsla_ts の流用可否） | B の実装 |
| P9 | NAT と ACL の評価順（外側 in＝変換前・外側 out＝変換後） | T2 を要件・誤解法に使うか |
| P10 | SVI の in ACL が HSRP hello・OSPF hello（RT の LAN-IN）を捨てるか | T3/T12 |
| P11 | NTP 同期にかかる時間（採点で synced を要求できるか） | H の NTP |

### 9.1 裏どり計画（CLAUDE.md の信頼順）

| 論点 | 1. Cisco 公式／実機 | 2. 解説サイト | 3. 問題集 |
|---|---|---|---|
| PPPoE クライアント／サーバ | PPPoE Client / PPP over Ethernet の Configuration Guide＋P1 | PPPoE 記事 | 該当があれば |
| NAT と ACL の評価順 | NAT Order of Operation＋P9 | NAT 記事 | 該当があれば |
| IP SLA／track／既定経路の取り下げ | IP SLA Configuration Guide・OSPF `default-information originate`＋P4 | IP SLA 記事 | 該当があれば |
| `ip tcp adjust-mss`・PPPoE の MTU | Command Reference＋P2/P3 | MTU/MSS 記事 | — |
| SVI の ACL と DHCP リレー・HSRP | DHCP relay / HSRP Configuration Guide＋P10 | ACL/HSRP 記事 | 該当があれば |
| reflexive ACL／ZBF | Security Configuration Guide＋P6 | ZBF 記事 | — |

食い違いは上位が勝つ。公式と実機が食い違ったらユーザ判断まで出題しない。

---

## 10. 流用できる既存資産

- `gen_campus_lab.py`／`campus_ops.py`（CAMPUS-TS-01）: ubuntu の BIND9・端末・コアの組み方と build→grade の往復、TS の故障注入方式
- `gen_dnsdhcp_build.py`: BIND9／ISC DHCP のテンプレート（H1/H2）
- `gen_stp.py`／`stp_model.py`: rapid-pvst・root 配置・エッジ保護の採点、IOSvL2 の bringup
- `acl_model.py`（`acl_vectors`）: ACL の意味評価
- `hardmode.py`: ノイズ ACL（H6）
- `gen_ipsla_ts.py`: IP SLA／track の構成と採点、監視対象の /32 固定の知見
- `gen_s2svpn.py`／`gen_v6addr_build.py`: 要件書形式の問題文
- STP シリーズの必須規則: トランクの allowed から MGMT 999 を外す

---

## 11. PoC の反映（2026-09-27 段1）

| 項目 | 結果 | 設計の変更 |
|---|---|---|
| P1 PPPoE | iol-xe で BRAS・クライアントとも成立。CHAP はローカル username で可 | なし |
| P2 MTU | **Dialer に `mtu 1492` が自動で入る** | §4.1 の `ip mtu 1492` を削除。「MTU 詰め忘れ」は罠にしない |
| P3 MSS | ブラックホールで MSS 調整なしは止まる・`adjust-mss 1452` で通る。**端末が PMTU を学習済みだと調整なしでも通る** | §6.1 の MSS 検査は端末の `ip route flush cache` 直後に行う |
| P4 切替 | 切替 16〜20 秒・切り戻し 35〜37 秒（delay down 10 up 30） | §3.3 の「目安 60 秒」はそのまま。採点の待ちは各 60 秒 |
| P8 採点中の操作 | grade.yml は IOS チェックを先に全部集め、全 PASS まで試行全体を最大 10 回繰り返す | §6.1 の 5.「冗長（動的）」は **grade.yml の外の ops の段で 1 回**。上流断は INET-SV の iptables（INET の IF 断と同じ振る舞いを確認） |
| P9 評価順 | Dialer in＝変換前・out＝変換後・LAN in/out＝社内アドレス | T2 は成立（公式との照合は裏どりで） |
| T1 / T3 | どちらも成立（echo-reply 抜けで健全な主回線から予備へ・OSPF 許可抜けで隣接断） | 誤解法 E2E にそのまま使う |
| E6 | ACL なしでは外部から RT のグローバルに SSH が開く | 要件の意味を確認 |

## 12. PoC の反映（2026-09-27 段2）

| 項目 | 結果 | 設計の変更 |
|---|---|---|
| P5 L2 イメージ | ioll2 で L3（SVI・HSRPv2・リレー・OSPF）・LACP・port-security が動く。**DHCP snooping は受理されるが DHCP を捕まえない**（binding 0）→ DAI は全 ARP を捨てる | §1.1 の L3SW/アクセスは **ioll2 に確定**。§1.2 の L3SW 間 2 本は **LACP で束ねる要件**にする。§7 の **H5（snooping＋DAI）を削除**（IOSvL2 は未確認） |
| P6 ステートフル化 | reflexive ACL は動く（evaluate の ACL に log 行は置けない）。**ZBF・CBAC は iol-xe に無い** | §7 の H4 を **reflexive ACL のみ**に。ZBF は境界を cat8000v にする別案として保留 |
| P7 予約 | CML のトポロジ定義で `mac_address` を固定すれば `client-identifier 01<MAC>` で予約できる（起動後は変更不可・wipe 後は可） | 生成器で複合機の MAC を固定する。端末は alpine でなく **ubuntu**（`dhcp-identifier: mac`。framework に alpine の family が無い）→ §1.1 の資源見込みを再計算（ubuntu×8 で約 16GB） |
| P10 制御プレーン | SVI の in ACL は HSRP hello を捨てる（T12 成立）。RT の in ACL は OSPF hello を捨てる（段1 T3） | §4.3 の HSRP 許可行の「要PoC」を外す |
| P11 NTP | 約 3 分でサーバ選択（`*`）・6 分でも unsynchronized | §6.2 の NTP は「選択済み＋reach」で採点 |
| T4 / T6 / T12 | 成立（DHCP 行なし→ DISCOVER 破棄／応答は SVI 実アドレス宛て→ VIP 宛てだけ許すと破棄／HSRP 両 Active） | 誤解法 E2E に使う |
| T5 | **症状が見えない**（ubuntu は裏で同じアドレスを取り直す） | §5 の T5 を削除 |
| 構文 | ioll2 は `spanning-tree portfast edge` 不可 | 模範解は `spanning-tree portfast` |

PoC 残り: なし（IOSvL2 の snooping/DAI は H5 を復活させたい時だけ）。次は §8 の P1（生成器）。


## 13. 実装記録（2026-09-27・標準構築）

| 項目 | 内容 |
|---|---|
| 生成器 | `topologies/gen_enterprise.py --seed N`（→ `problems/GEN-ENT-N`）。`--selftest N`= 模範 ACL を show 形式に描画して採点ベクタと全件照合＋VLAN 重複・配点（合計 100・最低 1）・golden の網羅 |
| 運用 | `topologies/ent_ops.py`: `<ID>`/`pregrade`（採点前フック）・`renew`・`solve [NODE...]`（golden を telnet 投入・ログイン再試行つき） |
| 盤面 | 20 ノード= INET・ISPA・ISPB・RT01・RT02・DHCP01（iol-xe）＋SW01〜05（ioll2）＋SRVINET・SRV01・SRV02・PC01〜06（ubuntu）。PC06（複合機）の MAC は `lab.macs` で固定 |
| seed 軸 | 第 2 オクテット・VLAN 番号（8 セグメント＋TRANSIT＋ネイティブ）・業務 3 部門の名前・イントラのみの部門・HSRP/root の振り分け・主回線（A/B）・払い出しアドレス・PPPoE 認証情報・社内ドメイン・印刷ポート・ACL 命名規約（4 型）・OSPF プロセス番号 |
| 採点（60） | 端末のプローブ（`/usr/local/bin/ccnp-probe`・seed の値で初期化時に焼く。遮断は同じ端末の許可と対で判定）／DHCP の取得内容（リースファイル）／採点前フックの結果（BASE/EXT/FAIL/BACK）／L2・L3 の状態（HSRP・`show spanning-tree root`・etherchannel・`show interfaces trunk`・OSPF の passive・NTP の関連付け）／ACL の適用位置と意味評価（`acl_vectors` の `acls:` 形＝1 チェックで複数 ACL） |
| 採点系の追加 | `collect_telnet.py`: `exec: shell` を ssh で実行（ラボ指紋も照合）／`grade.yml`: `pre_grade`（試行ループの前に 1 回）／`gen_cml_lab.py`: `lab.macs`／`acl_model.py`: `acls:` 形・`log-input` を無視／`inventory.yml`: 新ノード名 |

### 13.1 実機 E2E（GEN-ENT-41225・primary=ISP-B）

| 段 | 結果 |
|---|---|
| 白紙の基線 | **3/100**（外部からの到達試験が PPPoE 不在で偽 PASS → フックに移し「外へ出られるときだけ判定」に修正） |
| 模範解（1 回目） | 86/100。原因= 正規表現の `$` を複数行モードなしで書いた誤り（trunk・ACL 適用）／NTP の同期完了を要求していた（INET→RT→L3SW→ASW は段ごとに数分。構築直後は reach 0 が正常）→ 関連付け（設定）の確認へ |
| 模範解（修正後） | **100/100**（切替試験= BASE 203.0.113.55 → FAIL 198.51.100.40 → BACK 203.0.113.55・EXT=CLOSED） |
| 誤解法 3 点同時 | **63/100**: 主回線 RT の WAN ACL から echo-reply 削除（健全な主回線から予備へ倒れる= 冗長 3 チェック・主回線送出・境界 ACL 意味評価が落ちる）／両 RT の adjust-mss 削除（大容量転送が落ちる）／部門 SVI の ACL を全許可（遮断プローブと両 L3SW の ACL 意味評価が落ちる） |

### 13.2 実機知見（E2E）

- ★**ioll2 は既定で `ip routing` が有効**で、`ip default-gateway` は使われない（アクセススイッチの管理 SVI が他サブネットへ応答できない）。実機の Catalyst アクセススイッチと既定が逆なので、**要件書の制約欄に環境の事実として明記**し、模範解は既定の静的経路（`ip route 0.0.0.0 0.0.0.0 <VIP>`）。
- ★**ioll2 はリンクの無いポートも Et0/0〜3/3 の 16 本すべて提示**する（IOL ルータとは違う）→「未使用ポートの閉塞」を要件にできる（BL-229 ⑤）。
- 端末（ubuntu）の DHCP 取り直し直後は、systemd-resolved がすぐには安定しないことがある（1 回目のプローブで社内名だけ NONE）。採点は試行ループで吸収される。
- 模範解の telnet 投入で、ログインが一時的に失敗することがある（EOF）→ `ent_ops.login` に再試行。

### 13.3 スイッチのコンソール化と `no ip routing`（2026-09-27・ユーザ指示）

- 経緯: 当初はアクセススイッチに既定の静的経路を入れる模範解＋「ioll2 は既定で ip routing 有効」の注記で回避していた。
  実機（Catalyst 9300 の IOS XE 17.15 ルーティング設定ガイド: "By default, IP routing is disabled on the device"）に合わせるため
  day0 で `no ip routing` を試したが、**ルーティング無効の ioll2 は別サブネット宛ての ARP を採点用の管理 SVI（VLAN 999）側へ出し、
  管理 LAN の外部機器がプロキシ ARP で応答**して `ip default-gateway` が効かなかった（PoC 段3）。原因は「採点用の管理 SVI で SVI が 2 つになる」こと。
- 対応（ユーザ提案= コンソール経由）: **スイッチは管理 IF/SVI を持たない**（problem.yml `console_nodes`）。採点は `via: console` のチェックだけ CML コンソールで収集し、
  ルータは telnet・端末は ssh のまま。模範解の投入もスイッチはコンソール（`ent_ops.push_console`）。
- 生成器: 全スイッチの day0 に `no ip routing`（実機の既定）。L3SW は解答者が `ip routing` を入れる。アクセススイッチは `ip default-gateway` のみ。
  要件書から VLAN 999・Et3/3 の制約と IOL の注記を削除し、「スイッチはコンソールで操作」を明記。
- 採点系の追加: `build_topology.yml`（`console_only` をノード変数に）・`baseline_switch.cfg.j2`（`console_only` なら管理 VLAN/SVI を出さない）・
  `gen_cml_lab.py`（`console_nodes` は管理 IF と管理スイッチへの結線を作らない）・`collect_console.py`（`collect_nodes()` 切り出し・接続の再試行 `connect_retry`）・
  `collect_telnet.py`（`via: console` を collect_console へ）・`_grade_attempt_telnet.yml`（CML 認証の環境変数）。MGMT IP の割り当ては従来どおり（使わないだけ）。
- **実機 E2E（GEN-ENT-52725・primary=ISP-A）**: 基線 **0**（外部試験の偽 PASS 解消を確認）→ 模範解 **100** → 誤解法「L3SW の `ip routing` 入れ忘れ」**48**。
  ルーティング無効のアクセススイッチへ情シスから ping・telnet が `ip default-gateway` だけで届くことを確認。
- ★実機知見: 模範解の投入直後、ログの多い SW01 だけコンソール接続が「enable 状態にできない」で 3 試行とも失敗（数分後は成功）→ `collect_console.connect_retry`（失敗時のみ 3 回・10 秒間隔）で解消。
