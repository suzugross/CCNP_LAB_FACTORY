# EVPN-VXLAN-01 — 出題者向け運用メモ

EVPN-VXLAN ファブリックの**ガイド付き教育ラボ**（BL-055・伴走形式）。
SDA-LISP-01 の続編・「正統合流」編。PoC 記録は [poc/evpn-vxlan/README.md](../../poc/evpn-vxlan/README.md)。

## 運用（専用 ops）

```
python3 topologies/evpn_ops.py build      # import→リース確保(.20,.31-.37)→プリフライト→起動→到達待ち
python3 topologies/evpn_ops.py status     # ノード状態＋MGMT ping
python3 topologies/evpn_ops.py solve      # ★検証用: 模範解答(最終形)を SSH 一括投入
python3 topologies/evpn_ops.py grade      # 軽い最終疎通チェック(100点・grading.yml)
python3 topologies/evpn_ops.py stop       # 停止（状態保持）
python3 topologies/evpn_ops.py teardown   # 停止→wipe→削除→リース解放
```

- CML ラボ名は規約どおり不透明化: **CCNP-LAB-b7590c9b**（md5("EVPN-VXLAN-01")[:8]）。
- 静的 yaml（[evpn-lab.yaml](evpn-lab.yaml)）で MGMT **.20, .31-.37** 焼き込み。
  build 時に mgmt_alloc.py allocate の結果と突合し、**不一致なら中止**。
  ★**SDA-LISP-01（.37-.45 焼き込み）と .37 が重なる** — 両者は同時リース不可
  （RAM 的にも 29GB+40GB で同時稼働不可なので実害なし。先に teardown すること）。
- 8台（iol-xe×5 + nxosv9300×3）・**RAM 約40GB**・NX-OS ブート約4.5分（build 全体約6分）。
  ★稼働中は他の大型ラボを並行起動しないこと。

## 出題の流れ（伴走形式）

1. `build` → task.md 全文をチャットに貼る＋VSCode プレビュー案内
   （[[ccnp-task-presentation]] 規約）。
2. 受講者は CML コンソールで Phase 0〜4 を進める。**各 📋観察で一緒に出力を読み、
   🤔考察を対話する**のが本問の主体。答えは ANSWER_KEY.md 参照。
3. ★Phase 3 は**わざと失敗させる**設計: task.md の手順に
   `member vni 50000 associate-vrf` を意図的に**載せていない**。
   H1→H3 が 0% になったら、指紋（`show nve vni` に 50000 無し・
   BGP には Type-2 が居るのに VRF 経路表に降りない）を読むまで焦らず待つこと。
   是正コマンドは task.md の「処方箋」に載せてある（初学者向け救済）。
4. ★受講者が「LEAF1 にも VLAN200 を作れば良いのでは」と言い出したら止める
   （asymmetric フォールバックで通ってしまい L3VNI の学びが消える。
   task.md 末尾に「作らない」と明記済み — そこへ誘導）。
5. 全 Phase 完了後 `grade`（軽い答え合わせ・100点満点だが得点は主役にしない）。
6. 採点後レビューは通常どおり実施（[[ccnp-grading-review-style]]）。
   終章の3列対応表（pull/push・RR=胴元・border の対比）を必ず回収する。

## 検証履歴

- 2026-07-13 PoC（案A・leaf2台+border同居）: 全項目✅（poc/evpn-vxlan/README.md）。
  IOL RR interop・Symmetric IRB・Anycast GW・Type-5・ARP suppression(TCAMダンス) 実証。
- 2026-07-13 本問フルサイクル✅（2周）:
  1. build（8/8到達・約7分）→ **未解答 grade 0/100**（0点発射）→ 受講者フロー
     どおり段階投入 → **grade 100/100**。中間観察も実機一致:
     - 観察1: ピア Up・PfxRcd 0 ／ 観察2-2: H1→H2 初回1ドロップ(90%)
     - 観察2-3: SPINE の RR 視点で Type-2/3 が RD 別・Next-Hop 無変更
     - ★意図的失敗（associate-vrf 抜き）: H2→H3 通・H1→H3 0%・
       **MAC+IP Type-2 が LEAF2(送信側)ですら生成されない**（`show bgp l2vpn evpn
       172.16.200.13` が両 leaf で空・ARP はある）→ 是正後に label 10200 50000 +
       RT×2 + RMAC 付きで出現・/32 が segid 50000 で降りる
  2. wipe → 再build → **solve 一括投入 → grade 80/100** で★silent host 問題を実測
     （H3 が無発言だと LEAF2 が MAC+IP Type-2 を書かず P2/R2/A2 が落ちる）→
     grading に P2a(H2→H3 温め) を追加・task.md 考察3-3 で教材化 → **grade 100/100**。
  teardown・リース解放済み。build で再構築可。

## 実機で確認した作問知見（次回改訂時の参考）

- ★NX-OS は `nv overlay evpn` 前に BGP の `address-family l2vpn evpn` が
  **存在しない**（show コマンドすら Invalid）→ task.md Phase 1 に前倒し済み。
- ★`show ip route <addr> vrf <v>` の語順（`vrf` を先に書くと Invalid）。
- 設定投入直後は Type-2/3/5 の伝播に数十秒かかる（投入→即 ping で 0% になっても
  慌てない。伴走では「もう一度打ってみて」で拾える — 収束を見るのも教材のうち）。
