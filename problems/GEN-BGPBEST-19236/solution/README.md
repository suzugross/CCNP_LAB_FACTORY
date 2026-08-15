# 採点者専用 (GEN-BGPBEST-19236)

- mode: **ts** / fault: **weight_remote**
- AS: 自社=64900 ISP-A=64520 ISP-B=65520
- P=203.0.113.0/24(MED {'RT02': 50, 'RT03': 140, 'RT04': 20}) P2=192.0.2.0/24(タイ) own=172.29.40.0/24(戻り {'a1': 10, 'a2': 200, 'bk': 300})
- 紙面 shape=bgpbest と故障種名を共有(BL-115)。実測根拠= poc/bgpbest/README.md
- ★crid_missing の broken 時、P2 の nh チェックは oldest 依存で揺れる(監査 5 点は決定的に落ちる)
- fix は solution/fix.json(fix_generated.yml で投入)
