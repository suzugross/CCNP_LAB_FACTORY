# 採点者専用 (GEN-BGPRING-23453)

- shape: **stale** / layout: four_as
- faults: ['stale:weight', 'stale:allowas_in']
- meta: {'A': 'RT03', 'B': 'RT01', 'P': 'RT02', 'S': 'RT04', 'harmful': 'weight', 'harmless': 'allowas_in', 'audit_node': 'RT04'}
- AS: {'RT01': 65030, 'RT02': 64667, 'RT03': 64945, 'RT04': 65184}
- prefix: {'RT01': '172.16.71.0', 'RT02': '172.16.102.0', 'RT03': '172.16.194.0', 'RT04': '172.16.60.0'}
- 囮: [('unused_route_map', 'RT02')]

fix は solution/fix.json（fix_generated.yml で投入・exec の clear 込み）。
