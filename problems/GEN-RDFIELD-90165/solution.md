# 模範解答 : GEN-RDFIELD-90165 (shape=twoborder kind=missing_seed_metric)

## 役割の種明かし
B1=RT05, B2=RT01, IA=RT04, IB=RT02, LB1=RT03(境界= RT05/RT01・OSPF内部代表= RT04・EIGRP内部代表= RT02)

## 故障と是正
o2e に seed metric が無く∞メトリックで不広告(config は存在)。metric 付きで再投入。是正は**両境界に対称**に行う(片側だけでは症状が残る)。
詳細の投入行は solution/fix.json のとおり。

## 教育核心
2点相互再配送では自ドメイン発の経路が対向境界から**外部経路として再注入**される。
EIGRP 外部 AD 95(<OSPF 110) の会社ポリシー下では次善経路化として顕在化(no_tag)。
対策の定石= **出自タグ+境界受信での自ドメイン発遮断**(SET_TAG/BLOCK_TAG)。
