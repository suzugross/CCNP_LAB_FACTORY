# SDA-LISP-01 — 出題者向け運用メモ

SD-Access 中核技術（LISP/VXLAN）の**ガイド付き教育ラボ**（BL-054・伴走形式）。
試験ドリルではなくエンリッチメント教材。PoC 記録は [poc/sda-lisp/README.md](../../poc/sda-lisp/README.md)。

## 運用（専用 ops）

```
python3 topologies/sda_ops.py build      # import→リース登録(.37-.45)→プリフライト→起動→到達待ち
python3 topologies/sda_ops.py status     # ノード状態＋MGMT ping
python3 topologies/sda_ops.py solve      # ★検証用: 模範解答を SSH 一括投入
python3 topologies/sda_ops.py grade      # 軽い最終疎通チェック(100点・grading.yml)
python3 topologies/sda_ops.py stop       # 停止（状態保持）
python3 topologies/sda_ops.py teardown   # 停止→wipe→削除→リース解放
```

- CML ラボ名は規約どおり不透明化: **CCNP-LAB-95bb4c6b**（md5("SDA-LISP-01")[:8]）。
- ラボは静的 yaml（[sda-lab.yaml](sda-lab.yaml)）で MGMT .37-.45 焼き込み。
  build 時に mgmt_alloc.py allocate の結果と突合し、**不一致なら中止**する
  （プール状況が変わった場合は yaml の MGMT を再焼成すること）。
- 9台（iol-xe×7 + nxosv9300×2）・RAM 約29GB・NX-OS ブート約4.5分。
  20ノード上限に対し unmanaged_switch/ext-conn は数えない（PoC で確認済み）。

## 出題の流れ（伴走形式）

1. `build` → task.md 全文をチャットに貼る＋VSCode プレビュー案内
   （[[ccnp-task-presentation]] 規約）。
2. 受講者は CML コンソールで Phase 0〜8 を進める。**各 📋観察で一緒に出力を読み、
   🤔考察を対話する**のが本問の主体。答えは ANSWER_KEY.md の「考察の答え」参照。
3. ★Phase 4 は**わざと失敗させる**設計（proxy-itr/etr のみ→戻り0%）。
   受講者が指紋（`ITR local RLOC: NOT FOUND` / `Could not find EID table`）を
   読むところまで焦らず待つこと。構文罠（`ipv4 map-cache` は Invalid）は
   task.md に注意書きがあるので、ハマったらそこへ誘導。
4. 全 Phase 完了後 `grade`（軽い答え合わせ・100点満点だが得点は主役にしない）。
5. 採点後レビューは通常どおり実施（[[ccnp-grading-review-style]]）。
   終章の対比表（LISP=pull / EVPN=push、Border=PxTR 等）を必ず回収する。

## 検証履歴

- 2026-07-13 PoC: LISP/VXLAN とも実機で全項目✅（poc/sda-lisp/README.md）。
- 2026-07-13 本問フルサイクル✅: build（9/9到達・約6分）→ **未解答 grade 0/100**（0点発射）
  → 模範解答を受講者フローどおり段階投入 → **grade 100/100** → teardown・リース解放。
  段階投入時に task.md の中間観察も実機一致を確認:
  - 観察1: MSMR のみ設定時 `show lisp site` = `never / no / --`
  - 観察2-1: XTR1 投入直後に SITE-A のみ `yes#` に変化（SITE-B は `no` のまま）
  - 観察2-2: XTR2 投入後 `established: 2`
  - 観察7: NVE 作成前の BGP EVPN = ピア Up・**PfxRcd 0**（Type-2/3 とも 0）
  - 観察8-1: NVE 投入後 peers `Up/CP`・VNI 10100 `Up/CP`
  （Phase 3/4 の初回ドロップ・PxTR 故障指紋は PoC で実機確認済み → poc/sda-lisp/README.md）
