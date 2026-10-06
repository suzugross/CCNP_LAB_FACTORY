# 採点者専用 (GEN-BGPRING-12669)

- shape: **prefix_steer** / layout: four_as
- faults: ['prefix_steer:no_catchall']
- meta: {'A': 'RT01', 'B': 'RT03', 'P': 'RT02', 'S': 'RT04', 'variant': 'no_catchall', 'nets': ['172.16.193.0', '172.16.121.0', '172.16.229.0', '172.16.208.0'], 'special': '172.16.121.0'}
- AS: {'RT01': 64750, 'RT02': 65209, 'RT03': 64680, 'RT04': 65386}
- prefix: {'RT01': '172.16.193.0', 'RT02': '172.16.237.0', 'RT03': '172.16.143.0', 'RT04': '172.16.225.0'}
- 囮: [('unused_route_map', 'RT03')]

fix は solution/fix.json（fix_generated.yml で投入・exec の clear 込み）。
