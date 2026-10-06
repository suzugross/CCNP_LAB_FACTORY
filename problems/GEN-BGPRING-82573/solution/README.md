# 採点者専用 (GEN-BGPRING-82573)

- shape: **stale** / layout: four_as
- faults: ['stale:lp_rm', 'stale:allowas_in']
- meta: {'A': 'RT02', 'B': 'RT04', 'P': 'RT03', 'S': 'RT01', 'harmful': 'lp_rm', 'harmless': 'allowas_in', 'audit_node': 'RT04'}
- AS: {'RT01': 65405, 'RT02': 65202, 'RT03': 65454, 'RT04': 64857}
- prefix: {'RT01': '172.16.240.0', 'RT02': '172.16.37.0', 'RT03': '172.16.9.0', 'RT04': '172.16.210.0'}
- 囮: [('unused_prefix_list', 'RT03')]

fix は solution/fix.json（fix_generated.yml で投入・exec の clear 込み）。
