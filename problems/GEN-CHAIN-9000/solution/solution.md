# GEN-CHAIN-9000 解答（採点者用）

連鎖: L1:l1_ospf_auth → L2:l2_password_mismatch → L3:l3_b2e_metric_missing

## L1: l1_ospf_auth
RT11 側 West アクセスIF のみ OSPF MD5 認証が有効(RT01側は無し)

## L2: l2_password_mismatch
RT01 の急所ピア(RT03/RT04)にだけ MD5 パスワード(相手側は無し→セッション不成立)

## L3: l3_b2e_metric_missing
両境界の EIGRP に default-metric が無い(BGP→EIGRP 再配送が経路を注入しない=戻り不在)

## おとり（無害・修正不要）
- RT05: dc_legacy_acl（未適用/無影響の残骸。削除しなくても減点なし）
- RT02: dc_quarantine_pl（未適用/無影響の残骸。削除しなくても減点なし）

修復は solution/fix.json（fix_generated.yml で投入可）。
下位レイヤから直すのが素直だが、順序は自由（採点は結果主義）。
