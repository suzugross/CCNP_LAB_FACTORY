# PoC: FHRP 経路問(BL-228・2026-09-27・IOSvL2 iosvl2-2020)

盤面= `GEN-STP-94010`(gen_stp.py 2 層・build を土台に手で構成・撤収済み)。
VLAN X=125 / Y=151・10.191.v.N(N= スイッチ番号)。SW01・SW02= `ip routing`＋SVI＋HSRP v2(グループ= VLAN 番号・仮想 IP .254)。
SW03= VLAN125 の端末役・SW04= VLAN151 の端末役(`no ip routing`＋`ip default-gateway`)。
STP の root は両 VLAN とも SW02(24576)・SW01 は 28672 → VLAN125 は root と Active(SW01)が**ずれた**状態。

| # | 論点 | 実測 |
|---|---|---|
| P1 | 選出(同時に設定) | priority の高い方が Active(125= SW01 110・151= SW02 110) |
| P2/P4 | 往路・復路の担い手 | 4 本の計数用 ACL(両分配の両 SVI の in/out)で ping 50 回: **往路= SW01 の Vlan125 in と Vlan151 out が 50**・**復路= SW02 の Vlan151 in と Vlan125 out が 50**・他は 0 → 非対称。Standby 側(SW02 は VLAN125 の Standby)も復路を自分の SVI125 から出す |
| P3 | L2 の経路 | SW03 は VLAN125 で SW01 向きが Altn・SW02 向きが Root → SW01(Active)へは SW02 経由。SW01 の SVI151 の MAC は SW02 で SW01 向き・SW04 で SW02 向きに学習= SW01→SW02→SW04 |
| P4b | 片側だけの ACL | 復路が通らない SW01 の Vlan125 out に echo-reply deny → **100% 成功(素通り)** |
| P4c | 復路側の ACL | 同じ deny を SW02 の Vlan125 out に → **0%**(SW02 側で 10 件ヒット) |
| P5 | preempt 無しの priority 上げ | SW02 を 120 にしても Active は SW01 のまま |
| P5b | preempt を足す | SW02 が奪う |
| P7 | 同値・両方 preempt | 低い IP(SW01)が Active のところへ高い IP(SW02)が戻っても**奪わない**(preempt は priority が上回るときだけ) |
| P8 | 同値・preempt 無し・同時に上げる | **実 IP の大きい SW02 が Active** |
| P9 | 同値・preempt 無し・SW01 を先に | **先に上がった SW01 が Active のまま** |
| P10 | 仮想 MAC(v2) | `0000.0c9f.f07d`(グループ 125 = 0x07d) |

注意(IOSvL2):
- `traceroute ... numeric` は構文エラー(IOSvL2 は `numeric` を受けない)→ 担い手の証拠は ACL の計数で取った。
- SVI を shut/no shut した直後は HSRP に戻るまで 25 秒では足りないことがある(Standby 欄が `unknown`)→ 待ちを 60 秒以上に。
- 未接続のポートも up 扱いで `show spanning-tree` に出る(エッジ)。
