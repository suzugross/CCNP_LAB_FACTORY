# PoC: DMVPN「壊滅スタート」(BL-208)— IOL iol-xe 17.15・IKEv1・Phase 3・EIGRP

盤面 POC-DMVPNW = IOL 5 台(HUB=RT01・SPOKE=RT02/03/04・ISP=RT05)。採取= `sweep.py`、生ログ= `results-raw.md`、
要点表= `summarize.py`。各ケースは「注入 → 全 Tunnel bounce + clear crypto/nhrp → 75 秒待ち → 観測 → 是正 → 健全復帰確認」。
全ケースで是正後 16 秒で 3 spoke UP に復帰(是正手順に bounce/clear を含むため)。

## 1. 要点表(2026-09-21 実測)

| ケース | 内容 | hub の show dmvpn | ISAKMP(hub⇔RT02) | hub ESP encaps/decaps(RT02) | RT02 の State | 決め手 |
|---|---|---|---|---|---|---|
| P0 | 健全 | 3 UP(D) | QM_IDLE | 増加/増加 | UP | — |
| W1 | hub protection 欠落(profile あり) | **空** | なし | — | **IKE** | hub に ISAKMP SA 無し |
| W2 | hub profile 未定義(protection も無し) | **空** | なし | — | **IKE** | 同上 |
| W3 | hub network-id 欠落 | **空** | **QM_IDLE** | **0 / 増加** | **NHRP** | hub ログ `%DMVPN-5-NHRP_NETID_UNCONFIGURED` |
| W4 | hub tunnel key 欠落(spoke あり) | **空** | **QM_IDLE** | **0 / 増加** | **NHRP** | **痕跡なし**(値の突き合わせのみ) |
| W5 | hub p2p GRE(destination=RT02) | RT02 だけ UP(`never`) | QM_IDLE | 増加 | UP | 他 2 台は上がらない |
| W6 | hub map multicast dynamic 欠落 | 3 UP | QM_IDLE | 増加 | UP | 登録は成立(影響は EIGRP 側) |
| W7 | RT02 isakmp key 欠落 | 2 台 | なし | — | **IKE** | 当該 spoke だけ |
| W8 | RT02 protection 欠落(hub あり) | 2 台 | なし | — | **NHRP** | hub ログ `%CRYPTO-4-RECVD_PKT_NOT_IPSEC … src_addr=<spoke> prot=47`(約 1 分おき) |
| W9 | RT02 network-id 欠落 | 2 台 | なし | — | (RT02 の show dmvpn 自体が空) | spoke で NHRP が無効= nhs detail も空 |
| W10 | RT02 tunnel key 欠落 | 2 台 | QM_IDLE | 0 / 増加 | NHRP | 痕跡なし |
| F1 | RT02 transform `esp-3des` | 3 UP | — | — | — | ★**IOL 17.15 は esp-3des を構文拒否**(`% Invalid input`)= 故障不成立 |
| F2 | hub 外側 ACL で ESP 遮断(UDP 500 許可) | **空** | **QM_IDLE** | **0 / 0** | **NHRP** | encaps も decaps も 0 |
| F3 | RT02 NHRP 認証不一致 | 2 UP + `UNKNOWN … IKE never IX` | QM_IDLE | 0 / 増加 | NHRP | hub ログ `wrong authentication string … (11)` |
| F4 | RT02 NHS トンネル IP 誤り | 2 UP + `UNKNOWN … IX` | QM_IDLE | 0 / 増加 | NHRP | spoke に誤 IP が `NHRP S`・hub ログ `NHRP_ERROR` |
| F5 | RT02 nhs 無し・static map のみ | 2 UP + `UNKNOWN … IX` | QM_IDLE | 0 / 増加 | NHRP(hub が **正しい IP で static**・`never`) | **`show ip nhrp nhs detail` が空**(登録要求を送っていない)・hub ログ `NHRP Encap Error … (7)` |
| F6 | hub の profile に `set pfs group14`(spoke なし) | **空** | **QM_IDLE** | **SA 無し** | **IPSEC** | ログなし |
| F7 | hub `mode gre ip`(destination なし) | 空 | なし | — | IKE | hub Tunnel0 **up/down** |
| F8 | hub transform `mode tunnel`(spoke transport) | **空** | **QM_IDLE** | **SA 無し** | **IPSEC** | ★IOSv・IKEv2 では合意して動いた(BL-006)が **IOL・IKEv1 では Phase 2 不成立** |
| P5x | protection を外して付け直す | — | — | — | — | **自動 shutdown しない**(自動 shutdown は別 profile への付け替え時) |

## 2. 本試験の「最後の 1 層」(ISAKMP active・hub 空)が成立するもの

W3・W4・F2・F5(全 spoke)・F6・F8(+ hub 側に入れた F3)。**spoke の State で層が割れる**:

- `IKE` = Phase 1 未成立(W1/W2/W7/F7)
- `IPSEC` = Phase 1 成立・Phase 2 不成立(F6 PFS・F8 mode)
- `NHRP` = 暗号は通過・NHRP 段階。さらに hub の ESP で割る:
  - encaps 0 / decaps 増加 → hub が受け取って返事をしない(W3 network-id・W4 key・F3 auth・F4/F5 NHS)
  - encaps 0 / decaps 0 → ESP が届いていない(F2 ACL)
  - `show ip nhrp nhs detail` が空 → spoke が登録要求を送っていない(F5 nhs 欠落)

## 3. P2 全部入り → 自然な順で是正

hub(profile 未定義・network-id/key 欠落・p2p GRE・map multicast dynamic 欠落)+ RT02(isakmp key 欠落)+ RT03(profile 未定義)
+ RT04(key 欠落)の全部入りを day0 相当で作り、**設定の是正だけ**(bounce/clear なし)→ **41 秒で 3 spoke UP**。
= IOL・IKEv1 では「古い状態が残って上がらない」は起きない。**是正後も上がらないなら設定に本当の原因が残っている**。

## 4. ★IOL の罠: hub で network-id を外して付け直すと redirect が黙って無効になる

| 手順 | Phase 3 直接トンネル(RT02→RT03) | hub の Traffic Indication 送信 |
|---|---|---|
| 健全 | DT1/DT2 あり | 増える |
| hub で `no ip nhrp network-id` → `ip nhrp network-id`(+ Tunnel bounce) | **なし** | **0 のまま** |
| `ip nhrp redirect` を**そのまま再入力**(no 不要) | あり | 増える |
| day0 で network-id 無し + redirect あり → 後から network-id を足す | あり(罠は起きない) | 増える |
| spoke で network-id 外し/付け直し | あり | — |
| hub で map multicast dynamic 外し/付け直し | あり | — |

- running-config には `ip nhrp redirect` が**表示されたまま**。登録・暗号・EIGRP はすべて正常で、症状は「支店間が永久に hub 経由」だけ。
- ★これのせいで P3a/P3b/P3c 初回(W3 の後に実施)は「フルトンネルで shortcut ができない」と誤判定していた。redirect 再入力後に取り直した結果が §5。
- spoke の `ip nhrp shortcut` は IOL では既定 ON(running-config に出ない)。

## 5. フルトンネル(spoke LAN → hub 折返し → hub で NAT → 8.8.8.8)

| 構成 | インターネット | spoke 間 | 直接トンネル(DT) |
|---|---|---|---|
| hub Tunnel0 に `ip nat inside` のみ | — | 100% | あり |
| 既定経路のみトンネル経由(spoke は NBMA 経路を underlay に保持) | 100% | 100% | あり |
| 両方 | 100% | 100% | あり |
| **素朴**(spoke は hub NBMA の host route だけ・既定経路はトンネル) | 100% | 100% | あり |

- 素朴構成では、他 spoke の NBMA は CEF 上 `recursive via 0.0.0.0/0 → Tunnel0` になるが、IPsec SA は `ip mtu idb Ethernet0/0`・path mtu 1500 で**外側は物理 IF から直接**出る。1400 バイト DF の ping も spoke 間・インターネットとも 100%(hub 経由の二重カプセル化なら通らないサイズ)。
- = **IOL の DMVPN フルトンネルは素朴な構成でも成立**。ユーザの記憶(「DMVPN ではない IPsec VPN のフルトンネルが IOL でうまくいかなかった」)は crypto map 方式の hairpin(復号後に同じ外側 IF から NAT で出す)側の論点と推定 → 未検証。

## 6. BL-210 うんざり ACL(Q1/Q2/E2E・2026-09-21)

| 項目 | 実測 |
|---|---|
| out 方向 ACL(短い・IKE/ESP/ICMP permit)を稼働中に適用 | DMVPN は生きる。hit は **esp**(post-encryption)と isakmp。`permit gre` は 0 hit= 外側 out ACL は暗号化後の ESP を見る |
| ★out 方向 ACL を **day0 から**適用(E2E) | **全断**。EDGE-OUT の `deny ip any any log` に `denied 187 242.0.203.0 -> 113.2.255.255` / `denied 0.0.0.0` のような**壊れた読み取り**= IOL は Ethernet の out ACL を ARP フレームにも(ずれた offset で)当てて落とす → ARP 未解決で何も通らない。ARP キャッシュが温かい間だけ動く(Q1 が動いた理由)。**IOL で out 側の壁は使わない** |
| `N remark …` の seq 付き remark | day0 で受理・run に seq 付きで出る。`show ip access-lists` には出ない |
| 埋まっている seq への挿入 | `% Duplicate sequence number / % Failed to add ace` |
| `ip access-list resequence X 10 10` | エントリだけが 10,20,… に振り直され **remark は消える**。カウンタは保持 |
| resequence 後の挿入位置 | エントリ位置 × 10 で数える(remark を数えると 1 つ後ろ= catch-all の後ろに入って**食われる**。Q2 で自分が踏んだ) |
| `range 135 139` の表示 | `range msrpc 139`(acl_model の PORT_NAMES に msrpc 等を追加) |
| resequence 後の正しい位置(catch-all の直前)へ esp 挿入(Q2b) | **bounce なしで 62 秒**で 3 spoke UP |
| `permit udp … eq non500-isakmp`(4500)を外す(Q2b・reset あり) | 16 秒で UP= **NAT 無しでは 4500 は非故障**(囮・埋め草に使える) |
| E2E GEN-DMVPNW-50001 --hard acl_wall(missing・packed・both= 全 spoke に囮の in 壁) | 5 → 30 → `resequence` + `485 permit esp` で 100(bounce なし)。spoke の囮壁は無害 |
| ★同一 ACE の重複(shadowed の是正で同じ行を前に入れる) | `% Duplicate entry exists at sequence N`= IOS は内容が同じ ACE を 2 つ持てない。削除禁止なので正解は**対向を絞った別の行**(DMVPN= `permit esp 198.51.100.0 0.0.0.15 host hub` / DHCP= `permit udp host 0.0.0.0 eq bootpc host 255.255.255.255 eq bootps` / 再配送= `permit ospf host peer host me`) |
| 打ちづらい名前(Q3) | `pR3sh4red-K3y#7`(PSK)・`Ts-aEs256_Sha2.v1`・`IPsec.Prof_DmVPN-1`・`Sec_Edge-IN.v2`(ACL)・`nH0rP-k1`(NHRP 8 字)= すべて受理 |
| 大小違いの profile 参照 `tunnel protection ipsec profile DMVPN-Prof`(未定義) | **黙って無視**(エラーなし・run に残らない・既存の参照が生きる)= 独立の故障種にはならない |
| ★C5 ノイズの Loopback(全拠点で同じ 192.0.2.x) | EIGRP が最大 IP の Loopback を RID に選び**全拠点で RID 重複→経路が捨てられる**(4242 hard all で 75 点)。対策= `eigrp router-id <tunnel ip>` を明示＋ノイズ IP はノードごとに別 |
| E2E GEN-DHCPTS-9101 --hard acl_wall(shadowed・normal) | 55(DISCOVER が `deny ip 0.0.0.0 0.255.255.255 any` に食われる・カウンタのみ) → `35 permit udp host 0.0.0.0 eq bootpc host 255.255.255.255 eq bootps` で 100 |
| E2E GEN-RDFIELD-8801 --wall(missing・packed・EIGRP 側) | 35(`denied eigrp peer -> me`・hello は final deny) → 再配送だけ是正 50 → resequence+`permit eigrp any any` で 100 |
| E2E GEN-DMVPNW-777 --hard acl_wall,names,decoys | 5 → 全是正で 100(打ちづらい名前・囮 3 種で採点・fix とも問題なし) |
| E2E GEN-DMVPNW-4242 --hard all | 2 → 壁以外 30 → 壁 75(★RID 重複) → router-id 明示で 100 |
| E2E GEN-DMVPNW-40021 --hard acl_wall(wrong_proto・normal) | 5 → 壁以外是正 30(ISAKMP QM_IDLE・hub 空・ESP 0/0・`%SEC-6-IPACCESSLOGNP: list EDGE-IN denied 50 <spoke> -> hub`) → `545 permit esp any host hub` 挿入で 100(bounce なし) |
