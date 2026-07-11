# ENARSI-OSPF-MADJ-01 模範解答

## 解法の核心

- OSPF の経路計算では、ABR は**バックボーン (area 0) 経由で受信した Type-3 LSA
  しかエリア間経路の計算に使わない**（RFC 3509 のループ防止ルール）。
  そのため RT01/RT02 が area 100 側で互いの Type-3 を受け取っていても無視され、
  エリア間トラフィック (area1↔area2) は低速な area 0 チェーンへ迂回する。
- 制約（virtual-link 禁止・エリア割当変更禁止・スタティック禁止）の下で
  これを解決できるのは **マルチエリア隣接 (RFC 5185)** のみ:
  直結リンクを area 100 に残したまま、同じ物理リンク上に **area 0 の
  論理隣接 (OSPF_MA0)** を追加する。

## 設定（RT01 / RT02 の両方）

```
! 1) マルチエリア隣接は P2P インタフェース限定。
!    直結リンク(Ethernet0/0)はイーサネットなので network type を P2P 化する。
!    ★IOL/IOS-XE 17.15 では broadcast のまま multi-area を入れても
!      エラーが出ない（MA0 が DOWN のまま = サイレント故障）ことに注意。
interface Ethernet0/0
 ip ospf network point-to-point
 ip ospf multi-area 0
```

これだけで完了（両端に投入）。cost は物理 IF 継承（=10）なので、
area 0 チェーン（300）より小さく直結が最短になる。
`ip ospf multi-area 0 cost <n>` で MA0 のみ独立したコストも設定可能。

## 動作確認

```
RT01# show ip ospf neighbor
  → 2.2.2.2 が 2 行: Ethernet0/0 (area100) と OSPF_MA0 (area0) の両方 FULL
RT01# show ip ospf interface brief
  → MA0  1  0  Unnumbered Et0/0  10  P2P  1/1
RT01# show ip route 6.6.6.6
  → metric 21, via 10.1.12.2 (直結)。修正前は metric 311, via 10.1.13.2
RT05# traceroute 6.6.6.6 source Loopback0
  → 10.1.15.1 → 10.1.12.2 → 6.6.6.6 の 3 ホップ
```

フェイルオーバ（到達目標2）は MADJ の性質で自動成立:
直結リンクが落ちると MA0 も落ち、SPF が area 0 チェーンを再選択する。

## よくある誤答と部分点（実機検証済 2026-07-09）

| 誤答 | 症状 | 実測点 |
|------|------|--------|
| 何もしない（初期状態） | 遠回りのまま | 20 |
| broadcast のまま `ip ospf multi-area 0` のみ | **MA0 が DOWN のまま**（エラーなし=サイレント故障）。`show ip ospf interface brief` の `MA0 ... DOWN 0/0` が唯一の手掛かり | 20 |
| 直結リンクを area 0 に移す | 最適化はされるが area100 の隣接消滅＝制約違反（MADJ シグネチャ4チェック=40点分が弾く） | 60 |
| virtual-link (area100 経由) | 制約違反。virtual-link チェックで減点＋MADJ シグネチャ不成立 | 〜60（未実測） |

## 採点後レビュー観点（出題者用）

- P2P 化を先に入れてから multi-area を入れたか（順序はどちらでも動くが、
  network type 変更で area100 隣接が一瞬落ちることを理解しているか）。
- `ip ospf multi-area` の cost オプションの存在（発展: MA0 だけ別コストにできる）。
- virtual-link との対比: virtual-link は「area0 が分断/未接続の救済」、
  MADJ は「リンクを複数エリアで共有して最適化」。用途が違うことを説明できるか。
