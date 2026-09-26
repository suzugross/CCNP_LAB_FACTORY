# PoC: IP マルチキャスト(BL-217・2026-09-22・iol-xe / ioll2-xe 17.15.1)

ラボ: `problems/_POC-MCAST`(IOL 8 台+ioll2 1 台・再利用可)。ツール= [mcli.py](mcli.py)(ルータ SSH/スイッチ telnet)＋[run.yml](run.yml)。
手順= `steps/m1〜m5.yml`(m4b= RP 復旧後のやり直し)・生ログ= `logs/`。照合表= [curriculum/U-F-mcast.sources.md](../../curriculum/U-F-mcast.sources.md)。

盤面: RT01(送信元 10.0.12.1)─ RT02(送信元側 DR)┬ RT03(RP 3.3.3.3)─ RT04 ┐ ─ SW01(VLAN 100)─ RT06/RT07(受信者= `ip igmp join-group`)
                                                  └ RT05 ─────────────── RT04/RT08 ┘   受信 LAN に RT04(.4)と RT08(.8)
★運用: ioll2 は SSH 不可→ lab_up の SSH 待ちで SW01 だけ失敗するが、ルータは起動済み・SW01 は telnet で操作できる。

| M | 論点 | 実測 |
|---|---|---|
| M1 | `ip multicast-routing` | `distributed` 無しで受理・動作(running も `ip multicast-routing `) |
| M2 | IGMP 既定 | version 2・query 60 秒・**querier timeout 120 秒**・max response 10 秒・robustness 2・last member query count 2・interval 1000 ms |
| M3 | PIM hello | Query Intvl 30・neighbor Expires は最大 1:45 付近(holdtime 105)・J/P interval 60 秒 |
| M4 | DR と querier | 受信 LAN: **DR= RT08(IP 最大)・querier= RT04(IP 最小)**。`ip pim dr-priority 10` で RT04 が DR に |
| M5 | SPT 切替 | 既定= 即時(受信側 DR の (S,G) に `JT`・送信元側 DR に `FT`・RP に `T`)。`ip pim spt-threshold infinity`(受信側)では (*,G) のみで (S,G) を作らない(RP だけ SPT) |
| — | 受信側 DR の RPF が LAN 側 | DR(RT08)の RP への RPF が受信 LAN 上の RT04 → DR の (*,G) は OIL Null・`SJPC`、RT04 が Join を受けて LAN へ転送 |
| M12 | Assert | 受信 LAN に RT04 と RT08 が (S,G) を転送 → AD・メトリック同値で **IP 最大の RT08 が勝ち**(OIF フラグ `A`)・RT04 は `PJ` |
| M22 | IGMPv2 Leave | 離脱から約 2〜3 秒で group が消える(LMQ 1 秒×2)・snooping の entry も消える |
| M9 | SSM | `ip pim ssm default`+IGMPv3 の (S,G) 参加 → (S,G) のみ `sTI`・RP に状態なし・送信成功。**v2 で 232/8 に参加→ IGMP にも載らない**。**ssm default 無し→ v3 の (S,G) 参加でも (*,232.1.1.1) の ASM 扱い** |
| M10 | RPF | 等コスト 2 本 → **IP 最大の 10.0.45.5** を選ぶ。`ip multicast multipath` で選択が変わる(ハッシュ)。`ip mroute` で `RPF type: multicast (static)` |
| — | BSR | Cisco の C-RP priority 既定 **0**。同 priority はハッシュ最大(`show ip pim rp-hash`)・**priority 値が小さい方が勝つ**(RT05 に 10 → RT03 が選ばれる)。BSR priority 0・hash mask 0 |
| M7 | Auto-RP | mapping agent は **IP 最大の RP**(5.5.5.5)を選ぶ。**sparse-mode のみで listener なし→ MA の先に discovery が届かない**・`ip pim autorp listener` で届く。ルータは既定で 224.0.1.40 に参加(Loopback0・`SJCL`)。RP が無いと (*,224.0.1.40) は `DCL`(D= dense) |
| M6 | RP の優先 | Auto-RP(動的)> static(override なし)・`override` で static が勝つ。★**static の範囲が狭く(239.1.1.0/24)ても動的(224/4)が勝った** |
| M13 | Register | 受信者なし: 送信元側 DR の (S,G) `PFT`・OIL Null / RP の (S,G) `P`(Register-Stop) |
| M8 | bidir | `ip pim bidir-enable` は既定で**無効**(設定すると running に出る)。★ACL 名 `BIDIR` は `% Ambiguous command`(キーワードと衝突)→ 番号 ACL で可。表示= `(*,G)` のみ・flags `B`・`Bidir-Upstream:` 行・(S,G) なし・`show ip pim interface df` で IF ごとの DF。mapping に `Bidir Mode` |
| M15 | anycast RP+MSDP | 両 RP に Lo1 100.100.100.100・`ip msdp peer … connect-source Loopback0`・`originator-id`。Register を受けた RP の (S,G) に `A`・他方の RP の SA cache に `(S,G), RP <originator>, Peer <peer>`・その (S,G) に `M` |
| M16 | boundary | `ip multicast boundary <ACL>`(受信 LAN)で deny したグループは **IGMP groups にも載らない** |
| M18 | ioll2 snooping | 既定有効・`show ip igmp snooping groups`(v2/v3・v3 は送信元も)・mrouter は PIM ルータのポートを dynamic 学習・querier は `show ip igmp snooping querier`。★**`ip igmp profile` / `ip igmp filter` は ioll2 に無い**(Invalid)→ 文書ベース。`ip igmp snooping querier` は受理 |
| — | 誤り | 検証中に全ルータの static RP が消えていた(bidir の後始末の no 形が既存 RP も消した可能性)→ m4 の M13/M8 は無効・m4b でやり直し |

未実測(C 群)= PIM snooping・IPv6 MLD/PIMv6 anycast・rp-announce-filter・PIM を外した経路の RPF(holdtime 内で判定できず)。
