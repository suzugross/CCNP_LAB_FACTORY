# 採点者専用 (GEN-BGPRING-57104)

- shape: **path_select** / layout: four_as
- faults: ['path_select:prepend_missing']
- meta: {'A': 'RT04', 'B': 'RT02', 'P': 'RT01', 'S': 'RT03', 'fwd_mech': 'med'}
- AS: {'RT01': 64517, 'RT02': 64956, 'RT03': 65346, 'RT04': 64758}
- prefix: {'RT01': '172.16.49.0', 'RT02': '172.16.71.0', 'RT03': '172.16.7.0', 'RT04': '172.16.104.0'}
- 囮: [('unused_route_map', 'RT04')]

fix は solution/fix.json（fix_generated.yml で投入・exec の clear 込み）。
