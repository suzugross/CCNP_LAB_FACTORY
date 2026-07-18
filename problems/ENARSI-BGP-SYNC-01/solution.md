# 模範解答 : ENARSI-BGP-SYNC-01

## 故障は2段構え（片方だけ直すと次の症状が現れる）

### 故障1: レガシー `synchronization` の残骸（RT02/RT04）
2004 年から使い回された BGP 設定に **`synchronization`** が残っている。
BGP 同期ルール=「**iBGP で学習した経路は、同じ経路を IGP でも学習していない限り、
使わない・広告しない**」。顧客網は OSPF に存在しないので、境界ルータでは

```
RT02# show ip bgp 203.0.113.0
  Paths: (1 available, no best path)      ← ベストパス無し
  Not advertised to any peer              ← eBGP へも広告されない
    ... valid, internal, not synchronized ← ★診断の決定打
```

となり、**RIB 不搭載(% Network not in table)＋eBGP 非広告=AS 間全断**。
セッションが全部 Established・テーブルに経路が「見えている」のに使われない、が指紋。

### 故障2: コア RT03 が BGP を喋らない（非BGP中継ブラックホール）
`no synchronization` で経路は流れ出すが、**RT03 は顧客網の経路を知らない**。
RT01→RT05 のパケットは RT02 までは届き、RT03 で**サイレントドロップ**する
（traceroute が 10.0.12.2 の次で沈黙）。これこそが **synchronization が黙って
防いでいた事故**である（「IGP が知らない宛先をトランジットに流すな」）。

## 解

### 手順1: 境界 2 台から synchronization を除去（★clear 必須）
```
RT02(config)# router bgp 65000
RT02(config-router)# no synchronization
RT04 も同様
```
**★`no synchronization` だけでは既存経路のベストパス再計算は走らない**（実機確認済み。
「no best path」のまま張り付く）。**`clear ip bgp *`**（RT02/RT04）で再評価させて
初めて best になり RIB へ載る。

### 手順2: RT03 を iBGP に参加させる（真の修正・full-mesh 化）
```
RT03(config)# router bgp 65000
RT03(config-router)# bgp router-id 3.3.3.3
RT03(config-router)# neighbor 2.2.2.2 remote-as 65000
RT03(config-router)# neighbor 2.2.2.2 update-source Loopback0
RT03(config-router)# neighbor 4.4.4.4 remote-as 65000
RT03(config-router)# neighbor 4.4.4.4 update-source Loopback0

RT02/RT04(config-router)# neighbor 3.3.3.3 remote-as 65000
RT02/RT04(config-router)# neighbor 3.3.3.3 update-source Loopback0
RT02/RT04(config-router)# neighbor 3.3.3.3 next-hop-self
```
iBGP は水平分割（iBGP 学習経路を iBGP へ再広告しない）のため、**経路を運ぶ全ルータが
iBGP に参加（full-mesh）**する必要がある。next-hop-self が無いと RT03 は外部ネクストホップ
(10.0.12.1/10.0.45.5) を解決できず経路が無効になる点にも注意。

## 確認
- RT02/RT04: `show ip bgp <顧客網>` が `best` になり `not synchronized` が消える。
- RT03: `show ip route bgp` に `B 198.51.100.0/24` と `B 203.0.113.0/24`。
- RT01: `traceroute 203.0.113.1 source Lo1` が 10.0.12.2→10.0.23.3→10.0.34.4→10.0.45.5 と完走。
- 双方向 ping 100%。

## 別解（効果ベース採点なので可）
- **ルートリフレクタ**: RT02(または RT04)を RR にし、RT03(＋対向境界)をクライアント化。
  full-mesh のセッション数を減らす現代の標準解。RT03 が経路を持てば良い。
- **不可**: 静的経路/デフォルトによる回避、`redistribute bgp → OSPF`（監査ポリシー違反。
  かつて同期ルールとセットで使われた歴史的手法だが、フルルートを IGP に注入する設計は現代では禁じ手）。

## 教育核心（なぜ synchronization は存在し、なぜ消えたか）
- 同期ルールは「**BGP を喋らない中継ルータがいる AS で、ブラックホールを未然に防ぐ**」ための
  古い安全装置。当時の運用は「iBGP full-mesh が組めないなら BGP→IGP 再配布で同期させる」だった。
- 現代は **iBGP full-mesh / ルートリフレクタ / コンフェデレーション**で「経路を運ぶ全ルータが
  BGP を知っている」設計にするのが正、さらに発展形が **MPLS の BGP-free core**（コアは
  ラベルスイッチングだけで顧客経路を知らなくてよい＝L3VPN シリーズで実機済みの世界）。
  そのため synchronization は既定 OFF(12.2(8)T〜)を経て役目を終えた。
- ★実機知見: 本イメージ(iol-xe 17.15)は `synchronization` を**受理し判定ロジックも完全動作**する。
  ただし **`no synchronization` は既存経路の再評価を誘発しない**ため `clear ip bgp *` が必須。
