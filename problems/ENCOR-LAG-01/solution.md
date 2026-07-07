# 模範解答 : ENCOR-LAG-01

両スイッチで同じ構成。「動的にネゴシエーション」= **LACP**（`mode active`/`passive`）または
**PAgP**（`desirable`/`auto`）。ここでは LACP（両端 active）の例。

## SW01 / SW02（共通）
```
interface range Ethernet0/0 - 1
 channel-group 1 mode active
```
（`interface range` が使えない場合は Ethernet0/0 と Ethernet0/1 に個別投入）

## 確認
```
show etherchannel summary
  → 1   Po1(SU)   LACP   Et0/0(P)   Et0/1(P)
  （SU = Layer2 + in use、P = bundled、Protocol = LACP）
```

### ポイント（落とし穴の解説）
- メンバに `channel-group <n> mode active` を入れると Port-channel<n> が自動生成され、
  両メンバが LACP で折衝して束(P=bundled)になる。
- **動的ネゴシエーション**は LACP（標準, active/passive）か PAgP（Cisco独自, desirable/auto）。
  - LACP: 少なくとも片側 active（active-active / active-passive で確立）。passive-passive は確立しない。
  - PAgP: 少なくとも片側 desirable。
  - `mode on`（静的）は本問では不可（折衝しないため Protocol が "-" になり要件を満たさない）。
- 両端でモードや設定（速度/デュプレックス/スイッチポート設定）が食い違うと束に入れず、
  フラグが P 以外（I=独立 / s=suspended 等）になる。

> 採点は最終状態（Port-channel が LACP か PAgP で up、Et0/0 と Et0/1 が両方 bundled）で判定する。
> LACP/PAgP のどちらでも、mode の組み合わせは問わない。
