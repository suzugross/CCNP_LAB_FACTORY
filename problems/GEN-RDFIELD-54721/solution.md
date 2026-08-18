# 模範解答 : GEN-RDFIELD-54721

## 役割の種明かし
BR1=RT02, BR2=RT03, D0I1=RT04, D2I1=RT01(ドメイン: EIGRP AS 222 / EIGRP AS 471 / EIGRP AS 659)

## 故障と是正
### RT02 / router eigrp 222 (filter)
route-map RM-SVC が RT01 の Lo(27.27.27.27/32) を deny(収容標準はフィルタ禁止)。`no redistribute ...` → `redistribute eigrp 471 metric 100000 100 255 1 1500` で貼り替え、route-map/prefix-list も撤去。

投入後 `clear ip route *`(対象 BR)。

## 教育核心
再配送の故障は「無い」「参照が違う」「seed が無い」「絞りすぎ」の4型がほとんど。
config の**見た目の完備**と**実効**(show ip route / show ip protocols の
Redistributing 節)を突き合わせるのが切り分けの型。
