# 採点者専用 (GEN-BGPRING-75212)

- shape: **prefix_steer** / layout: four_as
- faults: ['prefix_steer:deny_catchall']
- meta: {'A': 'RT04', 'B': 'RT02', 'P': 'RT03', 'S': 'RT01', 'variant': 'deny_catchall', 'nets': ['172.16.5.0', '172.16.67.0', '172.16.151.0', '172.16.51.0'], 'special': '172.16.5.0'}
- AS: {'RT01': 65502, 'RT02': 64713, 'RT03': 64633, 'RT04': 65082}
- prefix: {'RT01': '172.16.70.0', 'RT02': '172.16.77.0', 'RT03': '172.16.97.0', 'RT04': '172.16.5.0'}
- 囮: [('legacy_comment', 'RT02')]

fix は solution/fix.json（fix_generated.yml で投入・exec の clear 込み）。
