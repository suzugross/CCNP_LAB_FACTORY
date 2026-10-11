# 模範解答 : GEN-RDFIELD-37274 (shape=twoborder kind=no_tag)

## 役割の種明かし
B1=RT04, B2=RT01, IA=RT06, IB=RT05, LA1=RT02, LB1=RT03, LB2=RT07(境界= RT04/RT01・OSPF内部代表= RT06・EIGRP内部代表= RT05)

## 故障と是正
双方向再配送はあるがタグ衛生(SET_TAG/BLOCK_TAG)が無く、OSPF発の経路が対向境界の EIGRP 外部(AD95<110)として戻り**次善経路化**。両境界にタグ付与+受信遮断を実装。是正は**両境界に対称**に行う(片側だけでは症状が残る)。
詳細の投入行は solution/fix.json のとおり。

## 教育核心
2点相互再配送では自ドメイン発の経路が対向境界から**外部経路として再注入**される。
EIGRP 外部 AD 95(<OSPF 110) の会社ポリシー下では次善経路化として顕在化(no_tag)。
対策の定石= **出自タグ+境界受信での自ドメイン発遮断**(SET_TAG/BLOCK_TAG)。
