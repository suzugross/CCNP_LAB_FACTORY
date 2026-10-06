# 模範解答 : GEN-RDFIELD-29213 (ring=inject_ospf method=filter)

## 役割の種明かし(匿名化の解答)
- 起点 = RT04 / **震源(被害) = RT06** / 相互再配送境界 = RT05 / OSPF 中継 = RT07
- ノイズノード(ループ機構に無関係): RT02, RT01, RT03

## なぜ壊れるか
`192.168.31.0/24` は RT04 が BGP 起点広告し、RT06 が **iBGP(AD 200)** で学習する。
RT06 は BGP を **OSPF** へ再配送し、RT05 の EIGRP⇄OSPF 相互再配送で出自が一周、
戻ってきた **EIGRP 外部(D EX・AD 170)** が iBGP(200) に勝って RT06 が採用 → 定常転送ループ。

## 解
RC(RT06) で router eigrp 397 に distribute-list prefix in(戻り遮断・distance不使用)。投入後 `clear ip route *`。

## 確認
- RT06: `show ip route 192.168.31.0` が `Known via "bgp 65483"` に変わる。
- 任意ルータから `traceroute 192.168.31.1` が RT04 に一直線。

## 教育核心
既定 AD の並び(eBGP 20 / EIGRP内 90 / OSPF 110 / EIGRP外 170 / **iBGP 200**)と、
再配送リングで出自が一周して戻る構造。distance 解と フィルタ解(distribute-list in)は
表裏(前者=信用度を変える / 後者=戻りを学習段で捨てる)。
