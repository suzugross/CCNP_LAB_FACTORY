# BGPBEST-LAB — ラボ問 GEN-BGPBEST(BGP ベストパス両刀・BL-115)

2026-08-13 起案・ユーザ承認済み。紙面 shape=bgpbest(BL-112)の実機側。
AAA の両刀(紙面 shape=aaa ⇔ GEN-AAAGRP)と同じ型= **故障種名を紙面と共有**する。

## 1. 前提(なぜ「すぐ」作れるか)

PoC は BL-112 で完了済み(POC-BGPBEST・IOL 6台・poc/bgpbest/README.md B1〜B17)。
盤面・基線 config・全故障の実機挙動・復旧手順(clear 要否まで)が実測済みなので、
残る作業は生成器の皮(day0 化・故障注入・採点・チケット文)と実機フルサイクルのみ。

## 2. トポロジ(PoC と同一・6× IOL・SSH 採点)

```
      RT02(ISP-A #1) --- RT05(境界)      RT01=視点(自社AS)
     /                    |              RT02/RT03= 同一 ISP-A(2リンク+境界経由)
  RT01 --- RT03(ISP-A #2)-RT06(境界)     RT04= ISP-B
     \                                   RT05/RT06= iBGP(Loピア+NHS)+OSPF
      RT04(ISP-B)                        宛先 P= ISP 側が起源広告
```

- RT01: e0/0→RT02 / e0/1→RT03 / e0/2→RT04 / e0/3=mgmt / **e1/0→RT05 / e1/1→RT06**
  (★mgmt_slot=3 の規約を守るため、PoC の e0/3・e1/0 結線から**ずらす**)
- OSPF コスト: RT01→RT05=10 / RT01→RT06=100(igp 判定の土台)
- eBGP 区間は OSPF に載せない(nh_no_self の土台)
- 自社広告 own_prefix(戻り方向の採点対象)= RT01 の Lo に付与し network 広告

## 3. TS モード(既定)— 故障6種(紙面と同名)

健全基線= 要件書(task.md に常設)を満たす完成ポリシー:
R1) P への転送は ISP-A 主用(LP 200 in・AS 全体) R2) 戻りは link-a1(MED 10/200 out)
R3) MED は全事業者横並びで尊重(acm) R4) 選択は決定的(crid) R5) 境界経由の経路が有効(NHS)

| fault | 壊し方 | 症状(実測根拠) | fix |
|---|---|---|---|
| weight_remote | R1 の LP を消し、代わりに RT05 に weight | RT01 は ISP-B のまま(伝播しない) | weight 撤去+LP 復元(+soft in) |
| lp_ebgp | R2 の MED out を「set local-preference out」に差替 | 戻りが動かない(B16=無警告無効) | route-map を set metric へ(+soft out) |
| nh_no_self | RT05 の NHS 撤去 | detail のみ (inaccessible)(B15) | NHS 再投入 |
| acm_missing | acm 撤去 | 異AS の MED 合意が不発(P4) | acm 投入(clear 不要・実測15s) |
| crid_missing | crid 撤去 | 全段タイが oldest 依存(B13b) | crid 投入(clear 不要・11s) |
| prepend_wrong_link | R2 の適用先を逆リンクに | 戻りが逆(ring の wrong_nbr 型) | 適用先付替え(+soft out) |

チケットは中立(症状の運用語)。fix.json= 上表(検証で使用)。

## 4. build モード(--mode build)

day0 からポリシー(LP/MED/acm/crid/NHS)を抜き、要件書だけ渡す。
採点は TS と同一(=要件書駆動の共通 grading)。監査 not_regex で解法を強制:
- 経路単位の weight 禁止(R1 は LP で)・LP は route-map 経由(bare `neighbor weight` 不可)
- R2 は MED で表現(prepend 禁止)

## 5. 採点(SSH・全6台)

- RT01: `show ip bgp <P>` best が期待 next-hop(contains/not_contains)
- **戻り方向**: RT02/RT03 の `show ip bgp <own_prefix>` best が link-a1 側
  (対向を自分で持っているので戻り採点が実機で成立する)
- 監査: `bgp always-compare-med`/`bgp bestpath compare-routerid` の存在・
  `neighbor .* weight` の不在・route-map の指紋
- 回帰: 全セッション Established・P への ping
- ★fix 反映の作法(実測): acm/crid は clear 不要(自動再計算)。route-map/LP/weight は
  `clear ip bgp * soft` を要件文に許可として明記(裏採点は最終状態のみ見る)

## 6. 検証計画

各故障= provision(broken) → grade(<100) → fix.json 適用 → grade(100) → teardown。
build= provision(blank) → grade(低) → 模範解答 → grade(100)。
CML 20 ノード上限に注意(並行 pack ラボ 8 台稼働時でも 6 台は収まる)。

## 7. ★実装記録(2026-08-13)

- 成果物= `topologies/gen_bgpbest_ts.py`(TS 6故障+build・GEN-BGPBEST-<seed>)。
  採点は §5 のとおり+★best 判定は `show ip bgp <pfx> bestpath`(PoC B1 で実在確認済の
  サブコマンド= best ブロックだけ出す)。DOTALL の横断 regex(`nh .*?, best`)は
  別ブロックの best を拾い偽合格になるため**使わない**。受信 MED の判定は
  「from 行→ Origin 行」の行ペア regex で縛る。
- ★実機検証で検出した設計欠陥 2 件(いずれも修正済み):
  1. **「境界経由の候補」チェックは P では構造的に不成立**(初回 90001)。
     境界の P ベストは MED 合意により「RT01 経由」= iBGP 学習となり、
     **スプリットホライズンで RT01 へ広告し返さない**。境界自身の eBGP が勝つ
     タイ prefix **P2 に付け替え**(nh_no_self の inaccessible 指紋も P2 に出る)。
  2. **fix.json の 1 エントリに同一文字列を 2 回入れると ios_config が畳む**
     (90005)。lp_ebgp の fix で `no set local-preference` が 2 枚の route-map に
     必要 → 1 エントリにまとめると 2 枚目が残り fix 後 95 点(監査が正しく検出)。
     **route-map ごとに parents を分けた 2 エントリへ**。
- 実機フルサイクル結果(broken→fix→100):
  nh_no_self 90→100 / acm_missing 60→100 / crid_missing 95→100(監査-5 は決定的・
  P2 nh チェックは oldest 依存で揺れる=仕様として solution/README に明記) /
  weight_remote 85→100 / lp_ebgp 70→100(fix 修正後) / med_swapped 75→100 /
  **build 20→100**(模範解答= solution/fix.json の全ポリシー投入)。
- 検証 seed(90001〜90010)は掃除済み。出題時は新 seed。

## 8. 参照

- 台帳= BL-115(本件)・BL-112(紙面側・完了)
- 実測= poc/bgpbest/README.md(B1〜B17)・poc/bgp-ring/README.md(P4)
- 型= gen_bgp_ring_ts.py(パック形式)・gen_aaa_build.py(両刀の先例)
