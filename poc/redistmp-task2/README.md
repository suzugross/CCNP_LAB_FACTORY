# BL-129 PoC — タグ是正後の境界 RIB 次善を OSPF distribute-list in で是正 (2026-08-18)

BL-058 の PoC ラボ(poc/redist-mp-loop/poc-redistmp-iol-lab.yaml・iol-xe-17-15-01 ×6・
コンソールのみ)を POC-BL129-TASK2 として再インポートして実施。**全項目成立 → 実装可**。
ラボは撤収済(YAML から再現可)。ドライバ= poc/redist-mp-loop/poc_console.py。

## 手順と結果

### P0-P1: 前提状態の再現

- broken(day0)でループ再形成を確認(RD が再注入 281856 via RB を誤選択・RA traceroute
  4ホップ周回。鏡像は BL-058 と同じ RB=OSPF勝ち側)。
- Task1(routemap 解・tag 110)を両境界に投入 → RD 正規復帰(307456 via RE)・
  RA ping 100%・**RB に O E2 残存**(via RA・from RC=172.16.12.3・5ホップ迂回)。
  RB の LSDB は RC 発 Type-5 **1枚のみ**(RB は非 ASBR 状態…正確には victim について
  LSA 非生成)。= Task2 が問う Before 状態。

### P2-P4: dl-in 投入(RB)

投入 config(タグ 110 は Task1 の再利用):

```
route-map DENY-TAG-RIB deny 10
 match tag 110
route-map DENY-TAG-RIB permit 20
router ospf 1
 distribute-list route-map DENY-TAG-RIB in
```

- ★★**即時収束・clear 不要**: 投入約1秒後の初回 show で既に
  `Known via "eigrp 1", distance 170 ... via 172.16.11.4(RD)`(hops 3・333056)。
  EIGRP topology に候補が既在のため昇格は瞬時。
- **LSDB は保持**: `show ip ospf database external 192.168.1.0` に Type-5 残存
  (`External Route Tag: 110`)。**RIB からだけ消える**ことの直接証拠。
- traceroute RB→RF: 5ホップ迂回 → **3ホップ直行**(RD→RE→RF)。

### P5: ★★最重要発見= 片側適用は「次善が対向へ移動する」(役割反転)

RB 単独適用の結果、固定的な非対称状態には**ならない**:

1. RB の RIB が D EX 化 → RB が victim の Type-5 を自己生成(ASBR 化)
2. RC(dl-in 無し)が RB 発 O E2 110 を受信 → RC の D EX 170 が負けて **RC が O E2 側に反転**
3. RC は redistribute の対象を失い**自分の Type-5 を取り下げ**(LSDB 全体から RC 発 LSA が消滅)
4. RA の next-hop も RC→RB へ切替(O E2・Tag 110・到達性は無断絶で維持)

= **「片側だけ設定すると次善経路が対向境界に引っ越すだけ」**。原案の解説項目
「対称に設定しなかった場合に何が起きるか」の答えが想定(片側残存)より強い形で確定。
副産物として、**採点は効果ベース(両境界 D EX)だけで対称性を機械的に強制できる**
(片側適用では反転した対向が必ず O E2 になるため)。

### P6: 対称適用(RC にも投入)

- RC も約1秒で D EX 復帰・Type-5 再生成 → **最終状態= 両境界 ASBR・Type-5 2枚**
  (Advertising Router = RB/RC 両方・いずれも Tag 110)。
- RA: O E2 **ECMP 2経路化**(via RB/RC・metric 20 同値)・ping 20/20・traceroute 完走
  (両パス分散)。OSPF 隣接 FULL 維持。
- ★**制約文言への影響**: 想定解自体が「他ルータの LSDB(1→2枚)と RIB(ECMP化)」を
  変化させる。原案の「他ルータの LSDB および RIB に変化を生じさせないこと」は
  **想定解が自ら違反する文言**→「当該プレフィックスの Type-5 LSA / O E2 経路が
  **失われない**こと(喪失禁止)」へ是正必須(design.md 反映済)。

### P7: 可逆性

- `no distribute-list route-map DENY-TAG-RIB in`(RB) → 約1秒で O E2 復帰
  (RC 発 LSA が LSDB に既在のため)。再投入 → 約1秒で D EX 復帰。
  **適用・撤去・再適用の3方向すべて即時・clear 不要**(distance 16秒より速い。
  LSDB→RIB の再調停のみで SPF/EIGRP 再収束を要さないため)。

## 採点用の実機表示形(そのまま regex 化する)

| 観測点 | 表示形 |
|---|---|
| run-config(router ospf 配下) | `distribute-list route-map DENY-TAG-RIB in` |
| run-config(redistribute) | `redistribute eigrp 1 route-map SET-TAG` — ★**17.15 は subnets 暗黙化**(BL-058 知見②と同じ・regex は `(subnets )?`) |
| show ip protocols(ospf節) | `Incoming update filter list for all interfaces is (route-map) DENY-TAG-RIB` — ★eigrp 節にも `not set` の同型行が出るため **`\| section ospf` で絞るか route-map 名まで含める** |
| show ip route <victim>(詳細) | `Known via "eigrp 1", distance 170` ＋ Before は `Tag 110, type extern 2` / `Route tag 110` |
| show ip ospf database external | `External Route Tag: 110`・`Advertising Router:` が最終状態で両境界 |

## 本実装 E2E(2026-08-18・GEN-REDISTMP-9105・--task2 on・撤収/掃除済)

`gen_redist_mp_ts.py --task2 auto|on|off` 実装後のフルサイクル(SSH 採点・通常パイプライン):

| 状態 | 得点 | 内訳 |
|---|---|---|
| broken(day0) | **10/100** | 静的ban5+片境界D EX 5 のみ(ループ・到達性・Task2系 全FAIL) |
| 模範解答(Task1+Task2) | **100/100** | 一発 |
| **Task1 のみ**(dl-in 撤去) | **69/100** | 指紋 -8×2・片境界 D EX -5・最短転送 -10(事前計算と一致。ループ・到達性は PASS のまま=Task2 未実施だけが減点) |
| Task2 再投入 | **100/100** | 復帰 |

回帰= --task2 off で全4モード14seed バイト一致・auto は routemap のみ抽選(3/5)・
非 routemap seed はバイト一致・採点regexの模範解答自己整合 14/14 OK。

## design.md チェックリスト(§9)との対応

1. ✅ 受理・動作(RIB 抑止+LSDB 保持) 2. ✅ clear 不要(即時) 3. ✅ 昇格瞬時
4. ✅ ASBR 2台化で RA 不変(種別・到達性。LSDB/RDB は**増える**→制約文言是正)
5. ✅ 非対称=役割反転(上記 P5) 6. ✅ 表示形採取(上表) 7. 回帰=実装時に実施
