# 設計書: gen_chain_ts.py — 12台・連鎖故障トラブルシュート生成器（方向性(2)）

status: **設計（実装前）** / 作成 2026-07-06
前提: /26化＝最大30ノード・mgmt_alloc.py リース台帳・AF方式標準（conventions.md）

---

## 1. コンセプト — 「連鎖」を故障テンプレートでなくレイヤ構造から生成する

従来のTS生成器（OSPF/BGP複合等）は故障が**互いに独立**で、show を見れば個別に
特定できる。本生成器の目的は **「Aを直すと初めてBの症状が見える」多段故障**＝
本物の障害対応で起きる「玉ねぎ剥き」を再現すること。

核となる着想: 連鎖テンプレートを手書きするのではなく、**1本のターゲットフロー
（West端末 → East網のプレフィックス群）に対して、依存レイヤごとに1故障ずつ置く**。
下位レイヤの故障は上位レイヤの症状を物理的に隠すため、**マスキングは配置から
自動的に生まれる**。これにより seed 生成・組合せ爆発・再現性を全て満たす。

```
L1: IGPアンダーレイ（隣接が上がらない）      ← これが壊れていると L2 以降は観測不能
L2: BGP制御プレーン（セッション/反射）        ← これが壊れていると L3 の経路は流れない
L3: 経路・ポリシー（再配送/フィルタ/ループ）   ← これが壊れていると L4 は評価不能
L4: フォワーディング/戻り経路（NHS/片方向）    ← 最後に残る「pingが片方向だけ通らない」
```

- `--chain-depth {2..4}`: 何レイヤ分置くか（深さ=難易度。既定3）
- 各レイヤの故障はカタログから seed 選択し、**必ずターゲットフローの経路上**に置く
- 加えて「おとり」（無害な設定の癖・timers等）を `--decoys N` で散布可能

## 2. トポロジ（12台・IOL・次数≤3・mgmtプール30個の実証を兼ねる）

```
  West OSPFドメイン        コア AS65001 (OSPF area0 + iBGP RRクラスタ)      East EIGRPドメイン
                                RT03 ──── RT05
  RT10 ── RT11 ══ RT01(bw) ──┤    (RR1)      ├── RT02(be) ══ RT07 ── RT08
 (端末) (W-agg)   境界W      RT04 ──── RT06     境界E       (再配送E1)│
                     │        (RR2)              │                    │
                     └────── RT12(観測点leaf) ───┘          RT09 ─── RT12? …
```

確定配線（次数≤3遵守・全12台）:

| ノード | 役割 | 接続 |
|--------|------|------|
| RT10 | West端末セグメント（Lo=ユーザLAN 172.20.0-1.0/24） | RT11 |
| RT11 | Westアグリゲーション（OSPF area 1 ABRはRT01） | RT10, RT01 |
| RT01 | 境界W（bw）: OSPF(a0/a1)+iBGP client+**West経路をBGPへ再配送** | RT11, RT03, RT04 |
| RT03 | RR1（クラスタ 0.0.0.1） | RT01, RT05, RT04(RR間iBGPはLo経由=リンク不要だが物理はこの3本) |
| RT04 | RR2 | RT01, RT03, RT06 |
| RT05 | コア中継（client・観測点1） | RT03, RT06, RT02 |
| RT06 | コア中継（client・観測点2） | RT04, RT05, RT02 |
| RT02 | 境界E（be）: iBGP client+**EIGRP⇄BGP相互再配送点1** | RT05, RT06, RT07 |
| RT07 | 再配送点2（EIGRP⇄BGP・**2点再配送=ループ素材**） | RT02, RT08, RT09 |
| RT08 | East内部（EIGRP・East LAN 172.21.0-1.0/24） | RT07, RT09 |
| RT09 | East内部2（EIGRP・迂回路提供） | RT07, RT08 |
| RT12 | コアleaf観測点（clientでない=RR反射の検証点） | RT01, RT02 |

- 12台＝mgmtリース12個（.11-.20 + .31-.32）→ **/26化後初の10台超の実運用実証**
- East境界が RT02/RT07 の2点再配送（BGP⇄EIGRP）＝再配送ループの正規素材
- RT12 は RT01/RT02 に直結する非clientのiBGPピア→ RR設定不備の症状観測点
- ターゲットフロー: **RT10(172.20.x) ⇄ East LAN(172.21.x)**。採点の主役は端点間到達性

## 3. 設計書（task.md に明記する「正しい姿」= 復旧目標）

gen_bgp_complex_ts と同じ思想で、受験者には**設計書への復旧**を求める（ヒントは
設計書事実のみ・故障位置や台数は伏せる）:

1. OSPF: area0=コア6台+境界、area1=West（RT01がABR）。全Lo0がOSPFで可視
2. iBGP: AS65001、RR=RT03/RT04（クラスタ冗長）、client=RT01/02/05/06、RT12は非client
   で RR とだけピア。**AF方式**（no bgp default ipv4-unicast＋activate）
3. West経路(172.20.0-1.0/24)は RT01 が OSPF(area1)→BGP 再配送、タグ 65001:100
4. East経路(172.21.0-1.0/24)は EIGRP→BGP 再配送（RT02/RT07 の2点・冗長）。
   **相互再配送はタグ+deny で還流防止**（tag 100/200 方式）
5. 端点間到達性: RT10⇄RT08 の LAN 間 ping 成功・経路はループフリー

## 4. レイヤ別故障カタログ（初期実装: 各レイヤ3-4種・計13種）

**L1 (IGP/隣接)** — West側 or コア内のフロー経路上リンクに1つ:
| ID | 内容 | 症状 |
|----|------|------|
| l1_area_mismatch | RT11-RT01 の area 番号不一致 | West全滅 |
| l1_ospf_auth | 片側のみ md5 認証 | 同上 |
| l1_mtu_mismatch | 片側 ip mtu 1400（EXSTART固着） | 同上（隣接が FULL にならない典型） |
| l1_passive_if | コア内1リンク passive-interface | コア内で経路迂回/一部Lo不可視 |

**L2 (BGPセッション/反射)**:
| ID | 内容 | 症状（L1修復後に露出） |
|----|------|------|
| l2_rr_client_break | RR1・RR2両方で対象clientのclient旗除去 | そのclientの経路が他へ流れない |
| l2_wrong_update_source | clientのRRピアで update-source 欠落 | セッションIdle |
| l2_activate_missing | AF方式の activate 欠落 | **セッションUPなのに経路ゼロ**（AF標準化の目玉） |
| l2_cluster_id_dup | RT12向け経路がクラスタID重複で捨てられる系 | 非client観測点だけ経路欠落 |

**L3 (経路/ポリシー/ループ)**:
| ID | 内容 | 症状（L2修復後に露出） |
|----|------|------|
| l3_redist_tag_leak | RT07 の deny タグ漏れ→**再配送ループ**（netmodelのloop_freeで採点） | 経路は見えるのにTTL超過/不安定 |
| l3_redist_filter_gone | RT02 の EIGRP→BGP で route-map 誤 deny | East /24 の片方欠落 |
| l3_dlist_accident | コアで distribute-list が West経路を遮断 | West→East 片方向のみ成立 |
| l3_wrong_metric_type | 再配送 metric 欠落（EIGRP側に経路が入らない） | 戻り経路不在 |

**L4 (フォワーディング/戻り)**:
| ID | 内容 | 症状（L3修復後に露出） |
|----|------|------|
| l4_nhs_missing | 境界の NHS 欠落（コアがeBGP...ではなく再配送NH到達不能を再現: OSPFからNHセグメント除外） | 経路はbestなのに転送不能 |
| l4_return_static_shadow | East内の誤static（/25 more-specific）が戻りを黒穴へ | 行きOK・戻りNG |

- 実装は既存生成器から移植可能なものが多い（ospf系=gen_ospf_complex_ts、
  rr/activate/nhs系=gen_bgp_complex_ts、再配送タグ系=gen_redist_ripospf_ts/mutual）
- 全故障に fix.json（正確な復旧手順・セッション再作成系は healthy_neighbor_lines 教訓を適用）

## 5. 採点設計（100点・大域不変条件を主役に）

| 区分 | 配点 | 内容 |
|------|------|------|
| 端点間到達性 | 30 | RT10⇄RT08 LAN間 ping 両方向（source指定）＋traceroute経路妥当性 |
| 大域不変条件（netmodel） | 30 | **loop_free**（全プレフィックス）/ West・East経路の全ルータ可視 / 冗長度（RR片系停止相当のセッション健全性） |
| 設計書適合 | 25 | RRクラスタ構成・RT12非client・タグ 65001:100/200 付着・AF方式のactivate完備 |
| プロトコル健全性 | 15 | OSPF FULL隣接数・iBGP Established 数・EIGRP隣接 |

- ポイント: **「直った順」に部分点が増える**構造（L1修復→隣接点が入る→L2修復→
  セッション点＋一部経路点→…）。受験者は採点を途中実行して進捗を確認できる
- `show ip route bgp` regex は **エントリ行マッチ**（`B\*? +<net>[ /]`）教訓を全面適用

## 6. CLI・生成物

```
gen_chain_ts.py --repo . --seed N [--chain-depth 3] [--decoys 1] [--flow west-east]
→ problems/GEN-CHAIN-<seed>/ (problem.yml / initial×12 / task.md / grading.yml / fix.json / solution.md)
```

- 3層分離（build_model → 故障=モデル変換 → render）を踏襲
- 簡易伝播シミュレータ（gen_bgp_complex_ts のRR反射規則を拡張: 再配送を含む）で
  「本当に連鎖マスキングになっているか」を生成時に自己検査（L2故障の症状が
  L1故障下で不可視であること等）→ 満たさない組合せは reroll

## 7. 実機検証計画

1. baseline（--chain-depth 0）で 100点 ＝ 12台トポロジ・設計書自体の健全性
2. depth3 の代表 seed: broken採点（低得点＋レイヤ別の部分点が理論値と一致）
   → fix.json を**レイヤ順に段階適用**し、各段階でスコアが設計どおり増えることを確認
   → 全適用で 100点
3. **順序逆転テスト**（本生成器の存在意義）: fix を L3→L1 の逆順で適用しても
   最終 100点になること（採点は結果主義・順序は自由だが症状の見え方が変わる）
4. depth2/depth4 各1シード
- 12台の boot は 15-20分級 → サイクル数を絞り、故障単体の検証は可能な限り
  オフライン（伝播シミュレータ）で済ませる

## 8. リスク・未決事項

- **12台のCMLリソース**: RAM は余裕（IOL×12 ≈ 12GB < 空き47GB）。ブート時間が主コスト
- EIGRP⇄BGP 再配送ループの実機挙動（AD/metric の絡み）は L3 カタログ実装時に
  単体で1回実機確認するのが安全（4台ミニトポで先行検証可）
- クラスタID重複故障（l2_cluster_id_dup）は初版から外す選択肢あり（挙動が
  微妙な既知領域。初版は確実な12種で開始し、実機確認後に追加）
- 生成器名/問題ID: gen_chain_ts.py / GEN-CHAIN-<seed>（exam=ENARSI, difficulty=5）

## 9. 工数見積り

| 作業 | 目安 |
|------|------|
| モデル+render 骨格（12台・設計書・baseline） | 1セッション |
| L1-L4 カタログ+fix+伝播自己検査 | 1-2セッション |
| 採点（netmodel統合含む）+オフライン検証 | 1セッション |
| 実機検証（baseline→depth3→逆順→depth2/4） | 2-3サイクル（boot長のため） |

関連: [[ccnp-bgp-complex-gen]] [[ccnp-global-invariant-grader]] [[ccnp-redist-ripospf-gen]] [[ccnp-mgmt-lease-allocator]]

---
## 実機検証結果 (2026-07-06・12台×3ブートサイクル)

**達成**: baseline 100点 / depth3(area不一致+RR旗3枚+redistribute-internal欠落) を
day0焼込み→fresh provision→broken 37点→fix.json一括→**100点**。故障単独実効性も
確認(L2単独=57点/L3単独=64点・シグネチャが相互に異なりマスキング関係も理論通り)。
12台リースは .11-.20+.31-.32 = **/26化後初の10台超実運用**。

**実機で発覚し設計変更した点(重要)**:
1. **E2B再配送経路のBGP NH解決性**: EIGRP側リンク(172.30.x)がNHのままだとRRで
   "inaccessible→no best"となり反射されない → 境界のEIGRP側リンクをOSPF area0へ
   **passive広告**する設計に(設計書事実として明記)。
2. **OSPFのLoopback /32罠**: West LAN(Lo)が/32広告されPL-WESTに不一致 →
   `ip ospf network point-to-point` 必須。
3. **IA広告がADでiBGPを殺す**: West LANがIAで全域flood(AD110)されると境界で
   iBGP(AD200)がRIB-failure(17)→B2E不発 → RT01で `area 1 range ... not-advertise`
   ＝「West LANの伝搬はBGPが唯一の経路」の設計に(BGP層が実効を持つ要)。
4. **`bgp redistribute-internal`**: IOS既定でiBGP→IGP再配送禁止。設計に必須化し、
   その欠落自体を代表L3故障に採用。
5. **RR反射規則で1victimのclient旗除去は無効**(client経路→全員/非client経路→client
   に反射されるため)。壊れるのは非client→非client のみ → l2_rr_client_break は
   **RT01+RT07+RT09の3victim版**に変更。RT12(非client)にWest/East両方の観測チェックを
   追加して盲点封鎖。
6. **tag deny漏れはループしない**(E2Bホワイトリストが還流を止める) → L3故障を
   `l3_redist_internal_missing` に差替え。tag+denyは多重防御として設計書に残置。
7. **traceroute はttl上限必須**(`probe 1 ttl 1 10`)。全ホップ無応答でCLI応答待ちに
   なり採点自体が死ぬ。故障注入型では特に致命的。

**実機検証済み故障**: l1_area_mismatch / l2_rr_client_break(3victim) /
l3_redist_internal_missing。**未実機の故障**(出題前に実機1サイクル推奨):
l1_ospf_auth, l1_mtu_mismatch, l2_update_source_missing, l2_activate_missing,
l3_e2b_filter_gone, l3_b2e_metric_missing, l4_static_shadow, l4_return_dlist。

**残作業**: depth2/4のシード検証 / fix逆順適用テスト / --decoys 実装 /
本物の再配送ループ故障の設計(4台ミニトポでAD/metric挙動を先行検証してから)。

## 全故障カタログ実機検証 (2026-07-06・ホットインジェクション方式1サイクル)

baseline稼働ラボへ「単独注入→採点→復旧」を全カタログに実施。**全11故障が実効**:

| 故障 | 単独スコア | シグネチャ |
|------|-----------|-----------|
| l1_area_mismatch | 44(旧regex時) | OSPF FULL/ドメイン到達/全ping FAIL |
| l1_ospf_auth | 41 | 同上 |
| l1_mtu_mismatch | 41 | 同上。**FULL明示regexがEXSTART固着を検知**(contains時代は盲点) |
| l2_rr_client_break(3victim) | 57 | セッションEstablishedのままRT12反射×2とWest伝搬が死ぬ |
| l2_wrong_neighbor_ip | 56 | セッション不成立(RT03 summary検知) |
| l2_activate_missing | 56 | 同上(AF未activate) |
| l3_redist_internal_missing | 64 | BGP層全緑・EastだけWest不在 |
| l3_e2b_filter_gone | 92 | East LAN2のみ欠落(ピンポイント) |
| l3_b2e_metric_missing | 64 | redist_internalと同族(戻り不在) |
| l4_static_shadow | 72 | LAN1黒穴＋static残置チェック二重検出 |
| l4_return_dlist | 72 | LAN1選択遮断＋タグ消失 |

**このサイクルで没にした故障**: l2_update_source_missing — iBGP Loピアは片側の
update-source が無くても**相手側からのTCP接続で成立する**(inbound は neighbor 一致で
受理・実機100点のまま) → l2_wrong_neighbor_ip に差替え済。

**ホットインジェクション時の注意**(day0焼き込みでは不要):
- mtu故障は既存FULL隣接を落とさない → IFバウンス(shut/no shut)で固着を再現
  (`clear ip ospf process` はプロンプト応答が ansible ad-hoc と相性悪い)
- 採点系コマンドは必ずリポジトリ直下 cwd で(ansible.cfg 依存)

status: **実装完了・全故障実機検証済・出題可**（パックは depth3 形態で保存）。
残: depth2/4シード・fix逆順テスト・--decoys・真の再配送ループ故障。

---
## 拡張ロードマップ検討 (2026-07-06・レビュー済み実機知見を前提)

### 現状の変動軸と限界
seed変動=値(Lo/セグメント)＋故障選択(L1×3・L2×3・L3×3・L4×2 → depth3で27連鎖、
depth2/4含め約90パターン)。**トポロジ構造と設計書が固定**のため、5〜10回解くと
「見る場所のチェックリスト化」が起きるのが唯一の陳腐化要因。

### 軸A: 故障カタログ拡張（低コスト・即効）
1. **--decoys 実装**(設計済み・未実装): 無害ノイズ(timers/ACL残骸/description異常)散布。
   実務の「ノイズの海」再現。採点無関係なので検証コスト極小
2. **実証済みパターンの移植**: password_mismatch / max_prefix_low(hard clear教訓込み) /
   send_community_missing — gen_bgp_complex_ts で実機検証済みの故障をL2/設計適合層へ
3. **★NH解決性故障**: 境界の172.30.x passive広告を除去 → RRで inaccessible/no best。
   本生成器の開発中に実機で踏んだ現象そのもの＝「経路はあるのにbestが立たない」高級L2.5故障
4. 【要ミニトポ先行検証】真の再配送ループ(E2Bホワイトリスト除去+タグdeny除去の複合、
   またはAD操作) / EEMによる間欠フラップ故障(時限断=CCIE級。EEM焼込みは基盤実証済)

### 軸B: 連鎖構造の進化（チェックリスト化への対抗・中コスト）
1. **同一レイヤ複数故障**(--faults-per-layer): 症状の重ね合わせで単純な下→上の
   一本道でなくなる
2. **分岐連鎖**: 冗長ペア(RT07/RT09)に別種の故障を1つずつ → 片方直すと
   「半分だけ復旧」になり、冗長性の理解を強制。partial-ping(成功率50%)の採点は
   ECMPハッシュ依存で不安定なため、採点は経路状態側で判定すること
3. カタログ増加時は設計書§6の伝播シミュレータを実装し、マスキング成立を生成時検査

### 軸C: トポロジ構造の seed 化（高コスト・構造陳腐化への根治）
1. **ミラー軸**(West⇄East入替) ×2 / **IGP入替軸**(OSPF側⇄EIGRP側) ×2 /
   **iBGPモード軸**(rr|fullmesh|confed) — bgp_complex_ts の48変種方式の踏襲
2. 前提リファクタ: 採点・故障カタログのノード名直書き(RT01等)を役割参照
   (WEST_EDGE/RRS/E_BOUNDARY)へ — 現構造でも半日で可能
3. コスト注意: **構造バリアントごとに baseline 実機1サイクルが必須**
   (本開発で机上設計が4連続で覆った実績が根拠)。軸は直交2^n で増えるため、
   変種追加は「出題頻度が上がってから」で十分
4. 規模拡大(East第2ドメイン/West二重化/L2アクセス層+IOSvL2): 30ノード枠・
   disjoint_paths不変条件など未使用の道具はあるが、boot時間と検証コストが線形増。
   優先度は低（連鎖の質はノード数でなく依存構造で決まる）

### 推奨順序
① 軸A-1,2,3（1セッション＋実機1サイクル）→ ② 軸B-1,2 → ③ 軸C（役割リファクタ→
ミラー軸から）→ ④ 軸A-4（ミニトポ先行検証と併せて）。
自動実機検証の省力化として、新seedの夜間バッチ検証(cron+provision→fix→grade→teardown)
も選択肢（リース台帳が複数ラボ対応済のため技術的障害なし）。

## 軸A実装完了 (2026-07-06・実機1サイクル済)

- **カタログ 11→15故障**: L2 += password_mismatch(56)/max_prefix_low(56)、
  L3 += nh_passive_missing(66・East方向だけ崩壊する固有シグネチャ)、
  L4 += send_community_missing(96・RT12 Eastタグのみ-4のピンポイント)。全て単独注入で実機検証済
- **--decoys N 実装**(既定2): 無害おとり5種(LEGACY ACL/未適用route-map/QUARANTINE
  prefix-list/威嚇的neighbor description/snmp location)。定義のみ・未適用の静的検査＋
  実機baseline 100点で不活性を確認。solution.md に「修正不要」として明記される
- **★ホット注入の新教訓**: 片側MD5(password)は確立済TCPセッションを即座に落とさない
  (hold-timer切れ/リセットまで生存)→ホット検証時はセッションリセット併投が必須。
  day0焼き込みでは起動時から確立不能のため出題形態では決定的に有効

## 軸B実装完了 (2026-07-06・実機2サイクル済)

- **--faults-per-layer {1,2}**: 同一レイヤ複数故障。排他グループ(flag.excl)で
  RT01セッション系4故障の同時選択を禁止(60seed検査で違反0)。width2実機:
  6故障同時(L1:mtu+area / L2:rrclient+password / L3:redist_internal+nhpassive)
  = **broken 32点 → fix.json 13エントリ一括 → 100点**
- **--branch-fault**: L3枠を「分岐連鎖」に置換。冗長境界ペアを**別種の方法で**
  各個撃破(br_bgp_password / br_eigrp_as_mismatch。割当も seed 変動)。
  実機段階検証: **21(broken) → 44(連鎖部L1+L2修復=症状がEast系統全滅へ変化)
  → 89(片枝RT07修復=到達性・反射・タグ全緑なのに冗長性2チェックだけ残る)
  → 100(RT09修復)** — 「疎通OK≠復旧完了」の教材構造を実機で実証
- eigrp_as_mismatch の fix は「no router eigrp 65101 → 正常ブロック再構築」
  (healthy_eigrp_block()で設計状態を一元生成 = bgp gen の healthy_neighbor_lines 教訓の踏襲)
- 検証用ツール: solution/fix.json をノード単位で段階適用する
  scratchpad/apply_fix_stage.py 方式（fix_generated.yml は全量一括用）

現在の生成能力: depth×width×branch×15故障×おとり = 数百通りの実機検証済みパターン空間。
残: 軸C(構造seed化・役割リファクタ前提) / depth2/4シード / fix逆順 / ループ・EEMフラップ系。

## 軸C第1弾実装完了: --ibgp {rr,fullmesh} (2026-07-06・実機1サイクル済)

- **役割リファクタ**: L2故障の victim ピアを crit_peers(m) で導出
  (rr=両RR「反射の入口」/ fullmesh=両East境界「直結が生命線」)。
  wrong_neighbor_ip の誤IPも rr_phys_ip / any_phys_ip でモード対応
- **fullmesh モード**: BGP話者9台×8ピア=36セッション・client行なし。
  L2カタログ: rr_client_break→(rrのみ) / mesh_session_missing(fullmeshのみ・
  RT01の境界2ピア定義欠落) / victim系4故障は急所ピアへ自動リターゲット。
  採点: RT12チェックから反射属性(Originator/Cluster)要求を除去。
  設計書/台帳/title もモード追随。--branch-fault は rr 限定ガード
  (fullmeshでは境界のRRピアpasswordが他ピア経由で迂回されるため)
- **回帰検査**: rrモードの config/grading/task.md は軸B時点と完全一致(挙動無回帰)。
  ※判明事項: **seed再現性は生成器バージョン内のみ**(軸A/Bの既定値・サンプリング変更で
  同一seedの故障選択は世代間で変わる)。検証済パックを固定したい場合は再生成しないこと
- **実機(9500)**: fullmesh baseline **一発100点**(36セッション+モード採点即動作)。
  急所ピア故障(password+リセット)= **64点**: 到達性全滅なのに RT12経路・セッション系
  チェック全緑=「ほぼ健康に見えて通信だけ死ぬ」fullmesh固有の高難度シグネチャを実証
  (反射迂回が存在しない構造主張の確認)
- 既知の未磨き: fullmesh では RT01↔境界セッション自体を直接見る採点チェックがない
  (症状は実機上で観測可能・採点は到達性系で捕捉)。次版で RT03セッションチェックの
  モード置換を検討
- 残: IGP入替軸(West⇄East アーキ交換・要新規実機デバッグ1式) / confed / depth2/4 / fix逆順

## 軸C第2弾実装完了: --igp-layout {ospf-eigrp, eigrp-ospf} (2026-07-06・実機1サイクル済)

**IGP入替アーキテクチャ(eigrp-ospf)**: West=EIGRP AS65100(RT10/11・単一境界RT01が
EIGRP⇄BGP再配送+redistribute-internal+タグ防御) / コア=OSPF area0(不変) /
East=**OSPFプロセス2**(RT07/09が ospf1+ospf2 の2プロセス境界・OSPF⇄BGP相互再配送)。

**設計判断(実機で立証済)**:
- **NH解決の自己完結化**: swap では 172.30 リンクが ospf2 アクティブ=ospf1 に
  passive広告できない(IFは1つのOSPFプロセスにしか属せない) → 再配送 route-map の
  **`set ip next-hop <自Lo0>`** で解決。West側(RT01)も同方式に統一
- ospf2 の router-id は 2.x.x.x 系に振る(同一ルータ内でRID重複不可)
- East LAN の Lo には ospf2 でも `ip ospf network point-to-point`(/32罠)
- swap 専用 L1(West EIGRP): as_mismatch/auth(key chain)/passive。
  L3 差替え: b2emetric→**subnets欠落**(OSPF再配送の古典罠)、nhpassive→**nhset欠落**
- 採点: 到達不変条件pairsからRT10/11除外(West LoはBGP経由のみ)・RT08タグ確認は
  RIB詳細(ospf 2 + Tag)・健全性はswap配分3+5+4+3(RT08 OSPF2 FULLは2.x RID regex)

**実機(9600)**: baseline **一発100点(新規デバッグゼロ!)** — NH自己完結/2プロセス/
subnets/p2p を教訓先回りで仕込んだ成果。swap固有故障3種の単独実効:
subnets=64 / nhset=66(base nhpassiveと同値=良い対称性) / weauth=58(新設RT01-EIGRP
チェック発火)。復旧100点→teardown。
**未実機2種**(w_eigrp_as/w_eigrp_passive)は検証済みパターンの変形のため
出題前1サイクル推奨扱い。v1組合せガード: eigrp-ospf は --ibgp rr かつ branchなし限定
(各組合せは baseline 実機検証後に解禁)。

## v2: 組合せ解禁 (2026-07-07・実機2サイクル済)

v1ガードを撤廃し、**fullmesh×eigrp-ospf** と **branch×eigrp-ospf** を解禁。
fullmesh×branch のみ構造的に不成立(brpassが他ピア経由で迂回)のため恒久ブロック。
rr×oe(既定)の出力は全変種でバイト一致(回帰ゼロ)を確認して実施。

- **監査で発見した潜在バグ2件を修正**:
  1. l4_send_community_missing が fullmesh で無効だった(RT12が境界と直結ピアのため
     RRs向けだけ剥がしても community が届く)→ fullmesh では全ピアから剥がす方式に
  2. l4_return_dlist の fix parents が eo で `router eigrp`(実体は `router ospf 2`
     配下)→ モード追随に。OSPF の distribute-list in は RIB 抑止として実効(実機72点)
- **eo用分岐故障 br_ospf2_area_mismatch 新設**: OSPF はプロセス番号が hello に
  乗らないためプロセス誤りでは隣接が切れない(監査時に机上検出)→ **area 不一致**なら
  hello 段で拒否=片系統が決定的に全滅。eigrp_as と同じ「丸ごと殺し」を eo で実現
- **fullmesh 採点盲点の解消**: RT03 セッションチェックを fullmesh では
  「RT01: iBGP セッション成立(RT07/RT09/RT12)」に置換(9500実機の宿題)
- **実機 GEN-CHAIN-9700 (fullmesh×eo, depth3)**: broken 53 → fix.json → **100 一発**。
  ホット注入で **w_eigrp_as=58 / meshsess=59(新チェック発火) / sendcomm(fm版)=96 /
  retdlist(eo版)=72** → 復帰100。**未実機だった w_eigrp_as/w_eigrp_passive を両方消化**
  (9700のseedがpassiveをE2E側で選択)
- **実機 GEN-CHAIN-9800 (rr×eo×branch, depth3)**: 段階fix **39→42(L1)→45(L2)→
  90(分岐RT07修復=疎通全緑・冗長-10)→100(RT09 area修正)**。分岐連鎖の教材構造が
  eo でも成立。br_ospf2_area の隣接切断は RT08 OSPF2 FULL チェック(-4)が捕捉
- 運用注意: **CML Personal は同時起動20ノード上限**(リース30個とは別の制約)。
  12台ラボ稼働中の並行余地は8台

## 真の再配送ループ検証 (GEN-LOOPPOC-1, 2026-07-07・実機PoC済)

4台ミニトポ(RT01=BGP側・RT02/03=二点境界・RT04=EIGRP内部)で「E2Bホワイトリスト+
タグdeny 撤去」を実機検証。**結論: この構造(iBGP AD200 コア)では恒久フォワーディング
ループは形成されない**。

- **Phase A(両境界の保護全撤去)**: 何も起きない。RT04 の West 経路サクセサが両境界
  (ECMP)のため **EIGRP スプリットホライズンが再広告自体を封じ**、AD 対決(170vs200)の
  入口が開かない
- **Phase B(片側の B2E 停止で非対称化)**: RT02 の RIB が **D EX 170 に反転**
  (還流外部経路が iBGP 200 を追い出す)。traceroute は RT02→RT04→RT03→RT01 の
  **大回り(本来1ホップ)**。RT01 には RT02 発の**偽 BGP 経路**(Origin incomplete)が出現。
  ただし迂回先が健全境界の BGP 経路に終端するため**ループにはならない**
  (両境界同時反転は定常状態で構造的に不可能=サクセサ側の境界は必ず BGP を保持)
- **Phase C(保護復元・B2E欠落は残置)**: RIB 乗っ取りは持続・偽経路は消滅
  = **タグ防御が防ぐのは BGP への還流だけ。RIB 乗っ取りは防げない**
- 真の恒久ループは AD 逆転がある IGP⇄IGP(RIP120 vs OSPF-ext110 等)に固有
  → 既存の gen_redist_ripospf 生成器がカバー済み(役割分担が明確化)
- PoC パックは problems/GEN-LOOPPOC-1 として保存(採点=loop_free 50+ping 50、
  netmodel が 4台でも動作することを確認済)

### 武器化の試行と最終判断: l4_b2e_oneside は不採用 (2026-07-08・実機3ラボで確定)

PoC の知見を「victim 境界の B2E 欠落→RIB 乗っ取り」故障＋「両境界が West 経路を
BGP で保持」チェックとして実装し、12台で実機検証した結果、**不採用**と確定。

- **eo で発見(GEN-CHAIN-2000)**: OSPF には EIGRP のスプリットホライズンに相当する
  再広告抑止が無く(LSA はフラッディング)、**健全構成でも必ず片側境界が O E2(110) に
  ロックイン**する(どちらが負けるかはレース)。eo の B2O 起点は常に実質片側=
  「両境界BGP保持」は構造的に達成不能
- **oe でも発見(GEN-CHAIN-3002)**: 本トポロジには**境界間直結 East リンク**があるため
  EIGRP でも各境界は相手の起点広告に直接晒される。片側を IFバウンスで復旧させると
  **相手側が固着する(後にバウンスした側が勝つ)いたちごっこ**で、両側同時バウンスでも
  非対称に収束。PoC(境界間リンク無し・RT04 の ECMP+スプリットホライズンが防御)で
  成立した「両側BGP保持」は**トポロジ依存の性質**であり本線には移植できない
- **固着は無害**: 片側 D EX 固着状態でも到達性・タグ・冗長の全標準チェックは 100点
  (実機確認済)。よって既存採点はこのままで正しい
- **★普遍教訓(作問全般)**:
  1. 二点相互再配送＋境界間直結リンクの構造では「境界の RIB が再配送元プロトコルを
     保持する」ことを採点不変条件にしてはならない(bistable ラチェット)
  2. RIB 乗っ取りは fix(設定復元)だけでは自然解消しない。復旧には固着解除
     (IF バウンス等)が要る — が、それが相手側を固着させ得る
  3. ミニトポ PoC の成立条件は本線トポロジと再照合すること(リンク1本で覆る)
- **副産物の恒久修正**: l2_activate_missing の fix が send-community を復元して
  いなかったバグを修正(day0 render は activate skip 時に send-community も落とす。
  rr では全経路が RR 経由のため West community が全域で消える。3002 実機で発見。
  fullmesh では RT12 直結のため無症状=9700 で見えなかった)
