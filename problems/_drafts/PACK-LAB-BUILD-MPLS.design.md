# PACK ラボ枠の拡張: ENARSI 構築問(DMVPN 等)の合流 ＋ MPLS-VPN の合流(BL-158)

2026-09-07 ユーザ要望「ENARSI 範囲は構築問(DMVPN など)も含める(比率は TS 多め)。
MPLS-VPN もラボ問の範疇に入れる」。同日検討・ユーザ判断待ち。

## 0. 現状(gen_pack.py 2026-09-07 時点)

- ラボ枠 = 固定ジャンル `--lab 2`(既定 7 ジャンル: hvrf/dhcp/dmvpn/ipsla/rtctl/v6addr/v6build
  をシャッフルし台数予算に入る順に 2 つ) ＋ 追加枠 `--lab-extra 1`(通常プールから **TS 限定**・
  余り台数 ≤ budget−reserve)。
- 構築問が入る経路は固定ジャンルの rtctl / v6build だけ(固定ジャンルは `_is_ts` を通らない)。
  静的な構築問(DMVPN-POC-01 等)は追加枠の `ts_only` で落ち、固定ジャンルは生成器接頭辞しか
  解決できない(`resolve_genre` は `cat["generator"]` のみ参照)。→ **DMVPN 構築 4 本・IPsec 構築 3 本・
  MPLS 構築 6 本は構造的にパックへ出ない**。
- MPLS TS(`gen_mpls_ts.py`・GEN-MPLSTS/GEN-MPLSEB・12 台 IOL)は追加枠の候補にはなるが、
  固定 2 問(9〜16 台)の後の残り台数(最大 8)に 12 台は入らない → **一度も出ていない**(履歴確認)。
- 現在の構築比: 7 ジャンル中 2 が構築。2 抽選で「構築 ≥1」≈52%・「構築 2 本」≈5%。

### 現物の棚卸(パックに載せうるもの)

| 系 | ID | 種別 | 台数 | 像/採点 | 備考 |
|---|---|---|---|---|---|
| DMVPN | DMVPN-POC-01 / DMVPN-PHASE3-01 / ENARSI-DMVPN-BGP-01 / ENARSI-DMVPN-IPSEC-01 | 構築(静的) | 4/4/5/4 | IOSv・console | 全て既出(各 100・再演含む)。seed 無し |
| IPsec | ENARSI-IPSEC-VTI-01 / -IKEV2-01 / ENARSI-GREIPSEC-MAP-01 | 構築(静的) | 3/4/4 | IOSv・console | 全て既出 100 |
| VPN 設計 | GEN-S2SVPN(+--day2) | 構築(生成) | 8/12 | IOSv・専用 ops | **lab.sh 非対応**(s2svpn_ops.py)→ 現行 provision_lab では扱えない |
| DMVPN | GEN-DMVPN | TS(生成) | 4〜6 | IOSv・console | 既定ジャンル(現行のまま) |
| MPLS | GEN-MPLSTS / GEN-MPLSEB(`--pece ebgp`) | TS(生成) | 12(+MGMTSW) | IOL・SSH | 故障 1〜3・decoy |
| MPLS | ENARSI-MPLS-L3VPN-01〜06 | 構築(静的) | 7/7/7/7/12/9 | IOL・SSH | 全て既出 100(03・05 は再演あり)。01 は「一から構築」で所要が長い |

## 1. 提案(推奨)

### A. LAB_GENRES に「静的問題ローテーション」を許す

`prefixes` に加えて `ids: [...]`(静的 ID 列)を持てるようにし、`resolve_genre` が
`cat["normal"]` からも引けるようにする。静的 ID は seed が無いので **repeat_days(90日)で
ローテーション**し、全て直近なら最も古いものへフォールバック(「候補ゼロ」で欠落させない)。

新ジャンル案:

| genre | 種別 | 中身 | 台数 |
|---|---|---|---|
| `vpnbuild` | 構築 | DMVPN 4 本 + IPsec 3 本の静的ローテーション(DMVPN 優先・IPsec は DMVPN が全て直近のとき) | 3〜5 |
| `mpls` | TS | GEN-MPLSTS(`--pece` を ospf/ebgp で抽選・`--faults` 1〜2) | 12 |
| `mplsbuild` | 構築 | ENARSI-MPLS-L3VPN-01〜06 の静的ローテーション(05 は 12 台で重い→除外か低確率) | 7〜9 |

### B. 「構築枠は最大 1・確率で付く」= TS 多めの比率を規則で担保

現行の「7 ジャンル素シャッフル」に構築ジャンルを足すと構築 2 本のパックが増える。
代わりに 2 段抽選にする:

1. 構築スロット: 確率 `--build-rate`(既定 0.4)で 1 つだけ構築ジャンル(rtctl/v6build/vpnbuild/mplsbuild)
   から抽選。外れれば構築 0。
2. 残りは TS ジャンル(hvrf/dhcp/dmvpn/ipsla/v6addr/mpls)から埋める。追加枠は従来どおり TS 限定。

→ 1 パック(2〜3 本)あたり構築 ≤1、期待比 TS:構築 ≈ 2.6:1〜3:1。`--build-rate 0` で従来動作。

### C. MPLS の台数問題 = 「大型スロット」

12 台(+MGMTSW)は CML Personal 20 ノード上限の 6 割。`mpls`/`mplsbuild`(05)が引かれた日は
- 相方を **小型 TS(ipsla 4 / dhcp 5 / rtctl 5 / dmvpn 4)に限定**し、追加枠は自動で 0。
- 稼働中ノードがある(他ラボ生存)と入らないので、夜間ビルド前の teardown を前提にする
  (現状 20/20 稼働で dry-run 全滅、と同じ落ち方)。
- 出現頻度は `mpls` を週 1 程度に抑える(`family_days` を 5〜7 に個別設定)。

### D. 見送り(今回はやらない)

- GEN-S2SVPN のパック合流: lab.sh 非対応で provision/grade 経路の別立てが要る。
  BL-063/064 の専用 ops を lab.sh 互換にする改修が先。
- DMVPN **構築の生成器化**(要件書駆動で Phase2/3×IGP×IKEv1/2×profile を seed 抽選): 静的 4 本は
  全て既出 100 のため、ローテーションの学習効果は「定着確認」止まり。継続的に出すなら生成器が要る。
  → 別 BL(候補)。今回は静的ローテーションで開始し、様子見。

## 2. 実装規模(着手時)

- gen_pack.py: LAB_GENRES 拡張(ids/kind/nodes/family_days)・resolve_genre の静的解決・
  select_genre_labs の 2 段抽選・大型スロット時の相方制限と extra 抑止・`--build-rate`。
  約 120〜150 行。dry-run で seed 20 本回して比率と台数を確認。
- 静的問題の provision は lab.sh の既存経路(履歴で全て lab.sh 実績あり)。IOSv+console 採点も既存。
- 実機 E2E: `vpnbuild`(DMVPN-POC-01)と `mpls`(GEN-MPLSTS 新 seed)を各 1 パックで通す。
- 所要時間目安: パック index の「ラボ 60 分」を種別で分ける(構築 DMVPN 60・MPLS 構築 90・MPLS TS 75)。

## 3. 実機 E2E 結果(2026-09-07 PACK-20260907-D・seed 158)

- `--lab-genres vpnbuild,mpls --build-rate 1` → VPN 構築 = ENARSI-GREIPSEC-MAP-01(静的・IOSv・console)
  ・MPLS TS = GEN-MPLSTS-55847(pece=ospf)。provision→bringup(3 試行/2 試行)→基線 0/100・71/100 で正常。
- ★CML 実ノード= 6(4 IOSv+MGMTSW+EXTC)+14(12 IOL+MGMTSW+EXTC)= **20/20 ちょうど**。
  相方に 5 台ルータは載らない → `BIG_PARTNER_MAX` を 5→4 に是正。
- 所要= 選定〜完了 18 分(GREIPSEC 11 分・MPLS 7 分)。
