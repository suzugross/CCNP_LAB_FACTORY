# BL-141 PoC — 純粋経路制御(RTCTL) 机上スケッチの実機検証 (2026-08-23)

盤面= poc-rtctl-iol-lab.yaml(5 IOL・コンソールのみ・基線に redistribute/リスト無し)。
ドライバ= poc/redist-mp-loop/poc_console.py を `--title POC-RTCTL` で流用。
**全項目成立 → 実装可**。ラボは撤収済(YAML から再現可)。

## 結果サマリ

| 項目 | 結果 |
|---|---|
| P1 基線 | battery 9経路が RT02/RT03 の完全 ECMP(435200)・RT05 Lo は p2p 化で /24 のまま O 4経路。設計どおり |
| P2 Task1(deny禁止DL) | ✅ 成立。★**トランジット permit 忘れの罠が実在**(下記) |
| P3 Task2(offset-list) | ✅ 単一 next-hop 化・FS 残存・IF shut で**1秒切替**(metric 436200 へ) |
| P4 Task3(1行PL×route-map E→O) | ✅ RT05 に O E2 ×4 のみ・即時 |
| P5 Task4(`distribute-list 20 out ospf 1`) | ✅ **受理・完全動作**。10.50.1/2 のみ D EX・connected 随伴(10.0.15.0)も同時に遮断 |
| P6 Task5(ACL 追記) | ✅ 追記 permit が**約8秒**で反映(clear 不要) |
| P7 到達性 | RT04→10.50.1.1 は無指定 0%・`source 172.16.0.1` で 100%(予測どおり) |
| ボーナス `distribute-list gateway PL in` | ✅ 受理・動作(RT02 経由が全滅)・撤去も即復元 → 要件プール入り可 |

## ★実測知見(設計に効くもの)

1. **distribute-list in の変更は clear 不要だが反映まで約30〜90秒**(自動 graceful resync)。
   offset-list は約15秒・redistribute 側フィルタ(out ospf)の ACL 追記は約8秒と反映が速い。
   採点は最終状態一括なので問題にならないが、解答者向け注意書き(または task.md の
   「反映に最大1〜2分」)の検討余地。
2. **★Task1 の隠し罠が実在**: permit 列挙にトランジット網(10.0.24.0/34.0)を入れ忘れると、
   除外対象でない 10.0.24.0/24 が RT03 経由へ**迂回**(307200→332800)。経路は失われないので
   気づきにくい。要件文は「除外対象以外の経路に影響を与えないこと」・採点は
   10.0.24.0 が via Et0/0 direct であることを regex で見る。
3. **offset は RD にも加算される**(Composite 436200/RD 410600)。offset が小さければ
   RD<FD で FS 維持=即時切替。生成器は「offset ≤ (FD−RD) を保証する値」を出す設計に
   するのが安全(大きすぎると FS が消えクエリ切替になる)。
4. **offset の指紋**: 詳細ビューの `Total delay is 7039 microseconds`(offset/256=39.06µs 加算)
   と `[90/436200]`。offset 側が選ばれた事故検出にも使える。
5. **connected 随伴**: `redistribute ospf 1` は OSPF 走行 IF の connected(10.0.15.0)も
   随伴させる(Total Redist Count: 5)。プロトコル指定 DL の permit 列挙が
   これも遮断するので、「10.0.15.0 を EIGRP 側に見せない」要件は無料で満たせる
   (逆に見せたい要件にすると permit 追記を強いる小ネタになる)。
6. **17.15 の subnets 暗黙化を再確認**: 投入は `redistribute eigrp 100 subnets route-map RM-E2O`、
   run 表示は `redistribute eigrp 100 route-map RM-E2O`。採点 regex は `(subnets )?`。
7. 到達性採点は **source 指定 ping が必須**(トランジット網は E→O フィルタで RT05 に無い)。

## 採点用の実機表示形(そのまま regex 化する)

| 観測点 | 表示形 |
|---|---|
| run(eigrp配下) | `distribute-list 10 in Ethernet0/0` / `distribute-list 20 out ospf 1` / `offset-list 11 in 1000 Ethernet0/1`(★行末に空白が付くことがある) |
| run(ospf配下) | `redistribute eigrp 100 route-map RM-E2O`(subnets 暗黙化) |
| show ip protocols(eigrp節) | IF指定DL= `Ethernet0/0 filtered by 10 (per-user), default is not set`(親行は `not set` のまま)・プロトコル指定= `Redistributed ospf 1 filtered by 20`・offset= `Incoming routes in Ethernet0/1 will have 1000 added to metric if on list 11`・gateway= `Incoming update filter list for all interfaces is  gateway PL-GW3`(★is の後ろ2連空白) |
| show access-lists | `10 permit 172.16.0.0, wildcard bits 0.0.3.255 (4 matches)`(deny禁止チェックは `not_regex: deny`・カウンタ括弧は可変) |
| show ip prefix-list | `ip prefix-list PL-E2O: 1 entries` + `seq 5 permit 172.16.0.0/22 ge 24 le 24`(1行チェックは `1 entries` を regex) |
| show ip route 詳細 | `Known via "eigrp 100", distance 90, metric 436200` / `via Ethernet0/0`(BL-129 知見どおり詳細ビューは via IF名) |

## 投入した模範解答(スケッチ Task1〜5 相当・RT01)

```
access-list 10 permit 172.16.0.0 0.0.3.255
access-list 10 permit 10.10.1.0 0.0.0.255
access-list 10 permit 10.10.5.0 0.0.0.255
access-list 10 permit 10.10.9.0 0.0.0.255
access-list 10 permit 10.0.24.0 0.0.0.255      ! ←忘れると罠(知見2)
access-list 10 permit 10.0.34.0 0.0.0.255
access-list 11 permit 10.10.1.0 0.0.0.255
access-list 12 permit 10.10.5.0 0.0.0.255
access-list 20 permit 10.50.1.0 0.0.0.255
access-list 20 permit 10.50.2.0 0.0.0.255
access-list 20 permit 10.50.3.0 0.0.0.255      ! Task5 で追記
ip prefix-list PL-E2O seq 5 permit 172.16.0.0/22 ge 24 le 24
route-map RM-E2O permit 10
 match ip address prefix-list PL-E2O
router eigrp 100
 distribute-list 10 in Ethernet0/0
 distribute-list 20 out ospf 1
 offset-list 11 in 1000 Ethernet0/1
 offset-list 12 in 1000 Ethernet0/0
 redistribute ospf 1 metric 10000 1000 255 1 1500
router ospf 1
 redistribute eigrp 100 subnets route-map RM-E2O
```

## 本実装 E2E(2026-08-23・GEN-RTCTL-9102・撤収/掃除済)

`gen_route_ctrl.py` 実装後のフルサイクル(SSH 採点・通常パイプライン・quota 台帳は
汚さないため `ansible-playbook playbooks/grade.yml` 直叩き):

| 状態 | 得点 | 内訳 |
|---|---|---|
| broken(基線) | **21/100** | 基線4+T1罠6+T1 ECMP3+監査8 = **事前計算と完全一致**(T2 topo は `1 Successor` 条件で落ちる設計) |
| 模範解答(fix.json) | **100/100** | 一発収束 |
| 誤解法(T4 を route-map 置換・効果は同一) | **94/100** | T4 制約チェックのみ FAIL(`distribute-list 56 out ospf 1` 不在+`route-map` 検出)=解法強制の実証 |
| 復元 | **100/100** | |
| `--mode free` の採点定義(同盤面) | **100/100** | 縛り指紋チェックが消え T2 効果へ配点移動(合計100維持) |

★実装時に踏んだバグ(生成器へ反映済み): 経路詳細ビュー(`show ip route <net>`)には
**`via <IP>` が現れない**(`via <IF名>`+`* <IP>, from <IP>` 形)。next-hop IP の採点は
素の contains で行う(BL-129 知見「詳細ビューは via IF名」の再確認)。

## v2(BL-143) 追加 PoC(2026-08-23・同ラボ再インポートで実施・撤収済)

タスクプール化・PL集合形抽選(design §11)の新要素を全て実機確認。**全部成立**。

| 項目 | 結果・表示形 |
|---|---|
| `distribute-list prefix <PL> in <IF>`(EIGRP) | ✅ 受理・効きは ACL 版と同一(resync 窓も同様)。run= `distribute-list prefix PL-FEED-IN in Ethernet0/0`・protocols= `Ethernet0/0 filtered by (prefix-list) PL-FEED-IN (per-user)` |
| OSPF 側プロトコル指定 DL out | ✅ `distribute-list 77 out eigrp 100`(run 表示同形)・protocols= `Redistributed eigrp 100 filtered by 77`(ospf 節)。効き= 対象1本のみ通過・connected 随伴も遮断 |
| 混在マスク Lo(/25・/26・/22)の EIGRP 広告 | ✅ Lo のマスクどおり広告(172.22.9.0/25 等)。`network 172.22.0.0 0.0.255.255` の広域 network 文で全部拾える |
| RT05 の表示形(採点 regex の根拠) | **対象集合のマスクが均一**(全/24 や /22 1本)→ 行に /len 無し(`O E2     172.22.88.0 [110/20]`・ヘッダに /22)。**混在**→ variably subnetted で全行 /len 付き(`O E2     172.22.9.0/25 [110/20]`) |
| PL 集合形 3 種の意味 | ✅ `x/22 ge 24 le 26`= /24+/25+/26 通過・/22 自身と圏外 /24 遮断/`x/22`(exact)= /22 のみ/`x/22 ge 25`= /25+/26 のみ(/24 遮断) |

## v2 本実装 E2E(2026-08-23・2ラボ・撤収/掃除済)

新要素を狙い撃ちした `--force` インスタンス2本のフルサイクル(SSH 採点):

| ラボ | 強制変種 | 結果 |
|---|---|---|
| GEN-RTCTL-9201 | pair24(/23 正解形)×pl_dl(prefix-list 版 DL)×rm_pl×**o2e=rm(route-map 指定・DL 禁止)**×group_exception/bind・順序 t3→t4→t5→t1→t2 | broken **21**(事前計算一致)→模範解答 **100** |
| GEN-RTCTL-9202 | longer_only(ge 25・混在マスク Lo day0)×acl_named×**ospf_dl_out(OSPF 側プロトコル指定 DL)**×proto_dl×two_opposite/free | broken **21**→模範解答 **100** |

selfcheck 500 seeds(canonical PL の意味評価一致・重複なし・配点 settle=100)・
順序パターン 58 種・pl_shape/手段の分布ほぼ均等。quad24/mixed_len/exact は
表示形 PoC(上表)+selfcheck 意味検査でカバー(quad24 は v1 E2E 済み構造)。

## design.md チェックリスト(§9 末尾の未検証リスク)との対応

1. ✅ `distribute-list out ospf 1` 受理・動作・表示形採取
2. ✅ offset-list IF指定 in の並列フィードでの効き(+FS/1秒切替/RD加算の注意)
3. ✅ Task1 列挙と Task2 offset の共存(相互干渉なし・最終状態一括で全効果同居)
4. ✅ 各 Task の効果が意図どおり(一意性の機械検証は生成器実装時の selfcheck で)
