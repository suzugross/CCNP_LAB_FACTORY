# UM2「Untrustワンアーム構成」CML再現ブループリント

書籍のネットワークデザインパターン **UM2(Untrustゾーン Mediumクラス No.2 / Untrustワンアーム構成)** を、Cisco Modeling Labs(CML)で再現するための設計書です。物理はワンアーム(FWをL3スイッチの腕として配置)、論理はUM1と同一(回線受けVRF / Trust VRF とタグVLANによるマルチVLAN構成)という本書の設計思想をそのまま踏襲しています。

---

## 1. 再現方針と書籍からの変更点

| 項目 | 書籍(UM2) | 本ラボでの再現 | 理由 |
|---|---|---|---|
| L3スイッチ ×2 | VRF対応L3スイッチ | **IOSvL2** ×2(VRF-Lite + HSRPv2) | CML標準ノードでVRF/SVI/トランクを再現可能 |
| ファイアウォール ×2 | Active/Standby型FW | **ASAv** ×2(LANベースFailover) | A/S冗長・NAT・ゾーン分離を忠実に再現 |
| LAG(FW–L3間 / L3–L3間) | 複数物理リンクをLAGで束ねる | **単一リンク+タグVLANトランク**で代替 | ASAvはEtherChannel構成が実質不可のため。論理構成(VLAN多重)は同一 |
| FW間HAリンク | 別論理リンクをL3スイッチ経由で確保(図2.4.3) | ASAv専用物理IF(Gi0/1)を**HA VLAN(245)のアクセスポート**でL3SW経由接続 | ASAのfailover linkはサブIF不可のため専用IFを使用。経路は書籍どおりL3SW経由 |
| 負荷分散装置 LB#1/#2 | DMZゾーンでルーティング+NAT | **省略**(DMZサーバをFW-LB VLANへ直結) | ユーザー選択。VIP VLAN(172.16.250.0/24)は不使用、inbound NATはサーバ実IPへ直接変換 |
| FHRP | FHRP+インターフェーストラッキング | HSRP v2 + `track`(アップリンク監視) | 図2.4.11「トラッキングでプライオリティを下げる」を再現 |
| DCバックボーン | データセンターバックボーン | IOSv ×1 + アンマネージドSW | 接続VLANのL2到達性(FHRP Hello経路)を再現し、外部ホスト(Loopback)も兼務 |

> **書籍のIP表記との対応**: 書籍ではFWに「物理IP+仮想IP」(例: Untrust側 .250/.249+仮想.251)が振られていますが、ASAのA/S Failoverは「Active IP(引き継がれるIP)+Standby IP」の2アドレス方式です。そこで **書籍の仮想IP→ASAのActive IP、書籍のFW#2物理IP→ASAのStandby IP** として写像しています(隣接機器のネクストホップは書籍と同一のIPを向く)。

---

## 2. ゾーンとVLAN設計

書籍 図2.4.5/2.4.7 のVRF整理・VLAN割り当てに対応します。

| VLAN ID | 名称 | ゾーン | サブネット | 用途 / 書籍対応 |
|---|---|---|---|---|
| 10 | BB-CONN | Untrust | 1.1.1.0/29 | DCバックボーン接続VLAN(アクセスリンク、タグなし) |
| 243 | UNTRUST-L3FW | Untrust | 172.16.243.0/24 | Untrustゾーン L3-FW VLAN |
| 244 | TRUST-FWL3 | Trust | 172.16.244.0/24 | Trustゾーン FW-L3 VLAN |
| 245 | FW-HA | – | 172.31.245.0/24 | HA VLAN(FWフェールオーバー専用、L3SWはスイッチングのみ) |
| 254 | DMZ-FWLB | DMZ | 172.16.254.0/24 | DMZゾーン FW-LB VLAN(L3SWはスイッチングのみ、SVIなし) |
| 100 | TRUST-USER | Trust | 172.16.100.0/24 | Trustゾーン ユーザーVLAN |
| – | (割り当てIP) | – | 2.2.2.0/24 | FWに割り当てたグローバルIP(NAT用。実VLANなし) |

### VRF設計(両L3スイッチ共通)

| VRF | 収容SVI | 役割(書籍対応) |
|---|---|---|
| **UNTRUST**(回線受けVRF) | Vlan10, Vlan243 | バックボーン回線受け。0.0.0.0/0→接続VLAN、2.2.2.0/24→FW |
| **TRUST**(Trust VRF) | Vlan244, Vlan100 | Trustゾーンのコアスイッチ役。0.0.0.0/0→FW |
| (グローバル/L2のみ) | VLAN 245, 254 | L3インターフェースを作らない(作ると**FWを迂回してゾーン間がルーティングされてしまう**ため — 書籍の注意点) |

---

## 3. IPアドレス設計

### VLAN 10(接続VLAN 1.1.1.0/29)
| 機器 | IP | 備考 |
|---|---|---|
| BACKBONE(IOSv) | 1.1.1.1 | DCバックボーン側ルータ |
| L3SW1 Vlan10(UNTRUST VRF) | 1.1.1.6 | HSRP prio 110(Active) |
| L3SW2 Vlan10(UNTRUST VRF) | 1.1.1.4 | HSRP prio 100 |
| HSRP VIP | **1.1.1.5** | バックボーンからの2.2.2.0/24のネクストホップ |

### VLAN 243(Untrust L3-FW VLAN 172.16.243.0/24)
| 機器 | IP | 備考 |
|---|---|---|
| L3SW1 Vlan243 | .253 | HSRP prio 110 + アップリンクtrack(-30) |
| L3SW2 Vlan243 | .252 | HSRP prio 100 |
| HSRP VIP | **.254** | FWのデフォルトルート先 |
| ASA outside(Active IP) | **.251** | 書籍のFW仮想IPに対応 |
| ASA outside(Standby IP) | .249 | 書籍のFW#2物理IPに対応 |

### VLAN 244(Trust FW-L3 VLAN 172.16.244.0/24)
| 機器 | IP | 備考 |
|---|---|---|
| ASA inside(Active/Standby) | **.254** / .252 | 書籍のFW仮想IP/.FW#2に対応 |
| L3SW1 Vlan244(TRUST VRF) | .250 | HSRP prio 110 |
| L3SW2 Vlan244(TRUST VRF) | .249 | HSRP prio 100 |
| HSRP VIP | **.251** | FWのユーザーVLAN向けルート先 |

### VLAN 254(DMZ FW-LB VLAN 172.16.254.0/24)
| 機器 | IP | 備考 |
|---|---|---|
| ASA dmz(Active/Standby) | **.254** / .252 | サーバのデフォルトGW |
| DMZ-SV(alpine) | .101 | LB省略に伴い直結 |

### VLAN 100(ユーザーVLAN 172.16.100.0/24)
| 機器 | IP | 備考 |
|---|---|---|
| L3SW1 Vlan100(TRUST VRF) | .2 | HSRP prio 110 |
| L3SW2 Vlan100(TRUST VRF) | .3 | HSRP prio 100 |
| HSRP VIP | **.1** | ユーザーのデフォルトGW |
| USER-PC(alpine) | .101 | |

### VLAN 245(HA VLAN 172.31.245.0/24)
| 機器 | IP |
|---|---|
| ASA failover link(primary) | .254 |
| ASA failover link(secondary) | .253 |

### 割り当てIP 2.2.2.0/24(NAT)
| 用途 | 外部IP | 内部IP |
|---|---|---|
| inbound 静的NAT(DMZサーバ公開) | **2.2.2.1** | 172.16.254.101(書籍ではLB VIP 172.16.250.1) |
| outbound PAT(ユーザーVLAN発) | **2.2.2.10** | 172.16.100.0/24 |
| 外部疎通試験用ターゲット | 198.51.100.1(BACKBONEのLo0) | – |

---

## 4. 物理構成(結線表)

書籍 図2.4.1/2.4.3 のワンアーム+HA別リンク構成に対応します。

| リンク | A端 | B端 | 種別 / 許可VLAN |
|---|---|---|---|
| L1 | BACKBONE Gi0/0 | BB-SW port0 | 1.1.1.0/29 |
| L2 | BB-SW port1 | L3SW1 Gi0/0 | アクセス VLAN10 |
| L3 | BB-SW port2 | L3SW2 Gi0/0 | アクセス VLAN10 |
| L4 | L3SW1 Gi0/1 | FW1 Gi0/0 | **トランク 243,244,254**(ワンアームの腕) |
| L5 | L3SW2 Gi0/1 | FW2 Gi0/0 | **トランク 243,244,254** |
| L6 | L3SW1 Gi0/2 | FW1 Gi0/1 | アクセス VLAN245(FW HA) |
| L7 | L3SW2 Gi0/2 | FW2 Gi0/1 | アクセス VLAN245(FW HA) |
| L8 | L3SW1 Gi0/3 | L3SW2 Gi0/3 | **トランク 100,243,244,245,254**(L3SW間) |
| L9 | L3SW1 Gi1/0 | USER-PC eth0 | アクセス VLAN100 |
| L10 | L3SW2 Gi1/0 | DMZ-SV eth0 | アクセス VLAN254 |

トランクの割り当ては書籍のタグVLAN設計どおりです: アップリンクはアクセス(接続VLANのみ)、L3SW–FW間トランクはFW隣接VLAN(243/244/254 ※HAは専用IF)、L3SW間トランクはFW隣接VLAN+ユーザーVLAN。

---

## 5. ルーティング / NAT設計

書籍 図2.4.8 に対応します。

**L3スイッチ(スタティック)**

| VRF | 宛先 | ネクストホップ |
|---|---|---|
| UNTRUST | 0.0.0.0/0 | 1.1.1.1(接続VLAN) |
| UNTRUST | 2.2.2.0/24 | 172.16.243.251(FW) |
| TRUST | 0.0.0.0/0 | 172.16.244.254(FW) |

**ASA(FW)**

| 宛先 | ネクストホップ | 書籍対応 |
|---|---|---|
| 0.0.0.0/0 | outside 172.16.243.254 | 回線受けVRF(VIP) |
| 172.16.100.0/24 | inside 172.16.244.251 | ユーザーVLAN → Trust VRF(VIP) |
| (サーバVLAN/VIP VLAN→LB) | – | LB省略のため不要(DMZは直結) |

**BACKBONE**: `2.2.2.0/24 → 1.1.1.5`(L3SWのVIP)

**NAT(ASA)**: inbound `2.2.2.1 → 172.16.254.101`(static)、outbound `172.16.100.0/24 → 2.2.2.10`(dynamic PAT)。outside着信ACLで DMZサーバ宛の ICMP/HTTP のみ許可。

---

## 6. 冗長設計(正常時/障害時)

正常時は書籍どおり **L3SW1とFW1がActive**(HSRP prio 110 + preempt / ASA primary)。

- **インバウンド**: BACKBONE → L3SW1回線受けVRF → FW1 →(DMZ宛)VLAN254のサーバ /(Trust宛)L3SW1 Trust VRF → ユーザーVLAN
- **アウトバウンド**: その逆。ワンアームなので全パケットがL3SW1の腕(トランク)を折り返すヘアピン経路になります(図2.4.10)。

**障害シナリオ(書籍の3パターンを再現可能)**

1. **L3SW1アップリンクdown**(図2.4.11/2.4.12): 接続VLANのHSRPがフェールオーバー。加えて `track 1`(Gi0/0監視)でVlan243のHSRP priorityを-30し、回線受けVRFのActiveをL3SW2へ移行。FW1はActiveのまま、L3SW1–L3SW2間トランク経由で通信継続。
2. **L3SW1全体down**(図2.4.13/2.4.14): 全HSRPがL3SW2へ、ASAはfailover linkの死活+インターフェース監視でFW2がActiveに昇格。全経路がL3SW2側へ切り替わる。
3. **FW1–L3SW1間リンクdown**: 書籍ではLAGが残るため無停止ですが、本ラボは単一リンク代替のためASAのインターフェース監視でFW2へフェールオーバーします(書籍との差分)。

---

## 7. 構築手順

1. CMLで `um2_cml_lab.yaml` をインポート(Lab → Import)。
2. ラボを起動。IOSv/IOSvL2/ASAvにはday-0コンフィグ投入済み。
3. ASAvのfailoverペア形成を確認: FW1で `show failover`(FW2はday-0で secondary 指定済み。初回同期に1〜2分)。
4. alpineノードに手動でIPを設定(day-0が効かない場合):
   - USER-PC: `ip addr add 172.16.100.101/24 dev eth0 && ip route add default via 172.16.100.1`
   - DMZ-SV: `ip addr add 172.16.254.101/24 dev eth0 && ip route add default via 172.16.254.254`、簡易HTTP: `httpd -p 80 -h /tmp`(BusyBox)
5. リソース目安: ASAv 2GB×2 + IOSvL2 768MB×2 + IOSv 512MB + alpine 256MB×2 ≒ **約6.5GB RAM**。

## 8. 検証手順(試験項目)

| # | 試験 | 操作 | 期待結果 |
|---|---|---|---|
| 1 | outbound疎通 | USER-PCから `ping 198.51.100.1` | 成功(BACKBONE Lo0)。BACKBONEで `show ip nat?` 不要、送信元は2.2.2.10に変換 |
| 2 | inbound疎通 | BACKBONEから `ping 2.2.2.1` / `telnet 2.2.2.1 80` | 成功(DMZ-SVへ静的NAT) |
| 3 | ゾーン分離 | USER-PC→DMZ-SV直宛(172.16.254.101)ping | FW経由で到達(inside→dmz)。L3SWだけで折り返さないこと |
| 4 | 正常時経路 | L3SW1 `show standby brief`, FW1 `show failover` | L3SW1が全VLANでActive、FW1がActive |
| 5 | アップリンク障害 | BB-SW〜L3SW1のリンクを停止 | Vlan10/Vlan243のHSRPがL3SW2へ。試験1/2が数秒断で復帰。FW1はActiveのまま |
| 6 | L3SW1全体障害 | L3SW1を電源断 | HSRP全てL3SW2へ、FW2がActive昇格。試験1/2復帰(USER-PCはL3SW2配下のDMZ-SVで代替確認可 ※USER-PCはL3SW1直結のため断) |
| 7 | FWフェールオーバー | FW1で `no failover active` または電源断 | FW2がActive昇格、セッション再開 |
| 8 | 復旧 | 障害箇所復旧 | HSRP preemptでL3SW1へ切り戻り。ASAはpreemptしない(手動 `failover active`) |

---

## 9. 機器コンフィグ(全文)

初期コンフィグはYAMLに埋め込み済みです。主要部の抜粋と解説:

### L3SW1(IOSvL2)— L3SW2は本文§3の値で対称

```
vrf definition UNTRUST
 address-family ipv4
vrf definition TRUST
 address-family ipv4
!
vlan 10,100,243,244,245,254
!
track 1 interface GigabitEthernet0/0 line-protocol
!
interface GigabitEthernet0/0          ! アップリンク(アクセス)
 switchport mode access
 switchport access vlan 10
interface GigabitEthernet0/1          ! FW1への腕(トランク)
 switchport trunk encapsulation dot1q
 switchport trunk allowed vlan 243,244,254
 switchport mode trunk
interface GigabitEthernet0/2          ! FW1 HAリンク(アクセス245)
 switchport mode access
 switchport access vlan 245
interface GigabitEthernet0/3          ! L3SW間トランク
 switchport trunk encapsulation dot1q
 switchport trunk allowed vlan 100,243,244,245,254
 switchport mode trunk
interface GigabitEthernet1/0          ! ユーザー収容
 switchport mode access
 switchport access vlan 100
!
interface Vlan10                      ! 回線受けVRF
 vrf forwarding UNTRUST
 ip address 1.1.1.6 255.255.255.248
 standby version 2
 standby 10 ip 1.1.1.5
 standby 10 priority 110
 standby 10 preempt
interface Vlan243
 vrf forwarding UNTRUST
 ip address 172.16.243.253 255.255.255.0
 standby version 2
 standby 43 ip 172.16.243.254
 standby 43 priority 110
 standby 43 preempt
 standby 43 track 1 decrement 30     ! 図2.4.11 インターフェーストラッキング
interface Vlan244                     ! Trust VRF
 vrf forwarding TRUST
 ip address 172.16.244.250 255.255.255.0
 standby version 2
 standby 44 ip 172.16.244.251
 standby 44 priority 110
 standby 44 preempt
interface Vlan100
 vrf forwarding TRUST
 ip address 172.16.100.2 255.255.255.0
 standby version 2
 standby 1 ip 172.16.100.1
 standby 1 priority 110
 standby 1 preempt
!
ip route vrf UNTRUST 0.0.0.0 0.0.0.0 1.1.1.1
ip route vrf UNTRUST 2.2.2.0 255.255.255.0 172.16.243.251
ip route vrf TRUST 0.0.0.0 0.0.0.0 172.16.244.254
```

※ VLAN 245/254 にはSVIを作らない(書籍の注意: 何も考えずL3インターフェースを作ると全パケットがL3SWだけでルーティングされ、FWを迂回してしまう)。

### FW1(ASAv・primary)

```
interface GigabitEthernet0/0
 no shutdown
interface GigabitEthernet0/0.243
 vlan 243
 nameif outside
 security-level 0
 ip address 172.16.243.251 255.255.255.0 standby 172.16.243.249
interface GigabitEthernet0/0.244
 vlan 244
 nameif inside
 security-level 100
 ip address 172.16.244.254 255.255.255.0 standby 172.16.244.252
interface GigabitEthernet0/0.254
 vlan 254
 nameif dmz
 security-level 50
 ip address 172.16.254.254 255.255.255.0 standby 172.16.254.252
interface GigabitEthernet0/1
 no shutdown
!
failover lan unit primary
failover lan interface FOLINK GigabitEthernet0/1
failover link FOLINK GigabitEthernet0/1
failover interface ip FOLINK 172.31.245.254 255.255.255.0 standby 172.31.245.253
failover
!
route outside 0.0.0.0 0.0.0.0 172.16.243.254 1
route inside 172.16.100.0 255.255.255.0 172.16.244.251 1
!
object network OBJ-DMZ-SERVER
 host 172.16.254.101
 nat (dmz,outside) static 2.2.2.1
object network OBJ-PAT-ADDR
 host 2.2.2.10
object network OBJ-TRUST-NET
 subnet 172.16.100.0 255.255.255.0
 nat (inside,outside) dynamic OBJ-PAT-ADDR
!
access-list OUTSIDE-IN extended permit icmp any host 172.16.254.101
access-list OUTSIDE-IN extended permit tcp any host 172.16.254.101 eq www
access-group OUTSIDE-IN in interface outside
!
policy-map global_policy
 class inspection_default
  inspect icmp
```

FW2はfailover最小構成のみ(`failover lan unit secondary` ほか)で、起動後にFW1から全設定が同期されます。

### BACKBONE(IOSv)

```
interface Loopback0
 ip address 198.51.100.1 255.255.255.255
interface GigabitEthernet0/0
 ip address 1.1.1.1 255.255.255.248
 no shutdown
ip route 2.2.2.0 255.255.255.0 1.1.1.5
```
