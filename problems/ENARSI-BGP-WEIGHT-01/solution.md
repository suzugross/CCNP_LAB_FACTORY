# 模範解答 : ENARSI-BGP-WEIGHT-01

## RT01
```
router bgp 65001
 bgp router-id 1.1.1.1
 neighbor 10.1.12.2 remote-as 65002
 neighbor 10.1.12.2 weight 200
 neighbor 10.1.13.2 remote-as 65003
!
```

## 確認
```
show ip bgp summary
show ip bgp 10.100.0.0/24
show ip route 10.100.0.0
```

`show ip bgp 10.100.0.0/24` の **Best path** 行に `weight 200` と表示され、
nexthop が `10.1.12.2` になっていれば成功。

### ポイント（落とし穴の解説）
- **weight はローカル属性**: 受信側のルータでのみ意味を持ち、BGP の update には
  含まれない。AS 内の他のルータには伝播しない。今回 RT01 単体での経路選択なので weight が向く。
- **best-path アルゴリズム順**: weight は **第1段階** で評価される最強の属性。
  weight 200 vs weight 0 (デフォルト) なら weight が大きい方が無条件で勝つ。
- **weight の設定方法は3通り**:
  1. `neighbor X weight 200` — 隣接単位のショートカット
  2. `route-map IN-WEIGHT permit 10 / set weight 200` を `neighbor X route-map IN-WEIGHT in` で適用
  3. （受信側全体に `bgp default ...` という形では設定できない；通常 1 か 2）
  本問は 1 でも 2 でも採点 PASS。
- **local-pref との違い**: local-pref は AS 内で iBGP 経由で伝播する。AS 内に他ルータが
  あって全員に同じ選好を共有させたいなら local-pref。1 台でローカルに完結させたいなら weight。

> 採点: RT01 から両 eBGP ネイバーが Established、`neighbor 10.1.12.2 weight 200` が
> 設定済み、10.100.0.0/24 のベストパス nexthop=10.1.12.2 になっていることを判定。
