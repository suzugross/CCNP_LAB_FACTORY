# 模範解答 : GEN-RDFIELD-6083

## 役割の種明かし
BR1=RT05, BR2=RT01, D0I1=RT02, D0I2=RT04, D1I1=RT07, D2I1=RT03, D2I2=RT06(ドメイン: EIGRP AS 180 / EIGRP AS 189 / EIGRP AS 329)

## 故障と是正
### RT01 / router eigrp 189 (missing)
注入方向が丸ごと欠落。`redistribute eigrp 329 metric 100000 100 255 1 1500` を投入。

投入後 `clear ip route *`(対象 BR)。

## 教育核心
再配送の故障は「無い」「参照が違う」「seed が無い」「絞りすぎ」の4型がほとんど。
config の**見た目の完備**と**実効**(show ip route / show ip protocols の
Redistributing 節)を突き合わせるのが切り分けの型。
