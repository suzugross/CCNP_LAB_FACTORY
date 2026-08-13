# 採点者専用 (GEN-BGPBEST-61307)

- mode: **ts** / fault: **lp_ebgp**
- AS: 自社=64900 ISP-A=64520 ISP-B=65402
- P=100.64.24.0/24(MED {'RT02': 60, 'RT03': 120, 'RT04': 10}) P2=198.51.100.0/24(タイ) own=172.29.40.0/24(戻り {'a1': 10, 'a2': 200, 'bk': 300})
- 紙面 shape=bgpbest と故障種名を共有(BL-115)。実測根拠= poc/bgpbest/README.md
- ★crid_missing の broken 時、P2 の nh チェックは oldest 依存で揺れる(監査 5 点は決定的に落ちる)
- fix は solution/fix.json(fix_generated.yml で投入)
