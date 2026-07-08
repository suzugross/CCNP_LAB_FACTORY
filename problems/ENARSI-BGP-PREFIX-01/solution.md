# 模範解答 : ENARSI-BGP-PREFIX-01

## RT01
```
ip prefix-list ALLOW-10 permit 10.10.0.0/16 ge 24
!
router bgp 65001
 neighbor 10.1.12.2 prefix-list ALLOW-10 in
!
end
clear ip bgp 10.1.12.2 soft in
```

## 確認
```
show ip prefix-list ALLOW-10
show ip bgp
show ip bgp 10.10.0.0/24
show ip bgp 192.168.0.0/24       ! "Network not in table"
```

### ポイント（落とし穴の解説）
- **`ge` の意味**: 「prefix length が指定値以上」の意味。`10.10.0.0/16 ge 24` は
  「network が 10.10.0.0/16 のサブネット範囲内、かつ prefix-length が 24 ~ 32 (上限デフォルト)」。
  つまり 10.10.0.0/24, 10.10.1.0/24, 10.10.0.0/28 等にマッチ。**10.10.0.0/16
  そのものはマッチしない** (16 < 24)。
- **`le` を併用するとレンジ指定**: `10.10.0.0/16 ge 24 le 24` なら /24 ジャストのみ。
  本問では `ge 24` のみで十分（広告されているのは /24 のみなので /28 等が来ない）。
- **prefix-list 末尾は暗黙 deny**: `permit 10.10.0.0/16 ge 24` 以外はすべて拒否される。
  これが 192.168.0.0/24 を弾く仕組み。**`permit` を省くと全 deny になるので注意**。
- **prefix-list vs `network` 文と混同しない**: `network` 文は「BGP に広告するプレフィックス」を
  指定。prefix-list は「受信／送信時の経路選別」のためのフィルタ。役割が違う。
- **適用は neighbor で**: グローバル ACL ではなく `neighbor X prefix-list NAME in/out`
  でピア単位に適用。
- **`clear ip bgp X soft in`**: 既存セッションに新ポリシーを反映するため。
  `clear ip bgp *` は乱暴（セッション断）なので避ける。

> 採点: prefix-list の `ge` 表記 / neighbor 適用 / 10.10.x.x/24 が残り、
> 192.168.0.0/24 が消えていることを判定。

## 変種 "bfd"（-e variant=bfd）の追加解答
RT02 側は BFD 対応済み。RT01 側にタイマと BGP 連動（fall-over bfd）を設定する。

```
! RT01
interface Ethernet0/0
 bfd interval 500 min_rx 500 multiplier 3
router bgp 65001
 neighbor 10.1.12.2 fall-over bfd
```

> 確認: `show bfd neighbors details`（State Up / Registered protocols: BGP）
