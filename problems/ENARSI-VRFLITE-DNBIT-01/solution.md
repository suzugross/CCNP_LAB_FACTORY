# 解答 ENARSI-VRFLITE-DNBIT-01 — capability vrf-lite

## 診断
- RT03 で `show ip route vrf RED 172.20.20.0` → **`% Network not in table`**。
- しかし `show ip ospf 10 database external 172.20.20.0` → LSA は**在る**。しかも
  **`Options: (... Downward)`** ＝ **DNビット（down bit）が立っている**。
- 理由：RT02 が **BGP→OSPF を VRF 内で再配布**するとき、生成する外部LSAに **DNビット＋
  ドメインタグ**を立てる（MPLS-VPN のループ防止の仕組み）。**RT03 も VRF 内で OSPF を
  動かしている**ため、「DNビット付きLSA＝自分が出したVPN経路が戻ってきたかもしれない」と
  みなして**ルート計算から除外**する → RIB に載らない＝ブラックホール。
- これは MPLS を使っていない **VRF-Lite / マルチVRF CE** で典型的に起きる罠。

## 修正（RT03 のみ）
RT03 の VRF OSPF プロセスに **`capability vrf-lite`** を入れ、DNビット/ドメインタグ/
FA 計算のループ防止チェックを無効化する。
```
router ospf 10 vrf RED
 capability vrf-lite
```

## 確認
```
RT03# show ip route vrf RED 172.20.20.0     ! Known via "ospf" で載る (type extern 2)
RT03# ping vrf RED 172.20.20.20 source 172.30.30.30   ! 100%
```

## 落とし穴 / 注意
- **スタティックで逃げない**（要件違反）。正しくは capability vrf-lite で OSPF 経路として載せる。
- `capability vrf-lite` は「この OSPF は本物の MPLS-VPN PE ではなく VRF-Lite だ」と宣言して
  ループ防止を切るもの。**本物の MPLS-VPN PE では入れてはいけない**（BL-022 で見た通り、
  DNビットは PE では正しく機能させるべきループ防止＝そちらでは禁止）。同じ DNビットが、
  **VRF-Lite では過剰防護（要解除）／MPLS-VPN では必須防護（維持）**という表裏の関係。
