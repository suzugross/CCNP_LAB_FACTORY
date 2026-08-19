# 採点者専用 (GEN-BGPRING-25856)

- shape: **path_select** / layout: four_as
- faults: ['path_select:prepend_missing']
- meta: {'A': 'RT02', 'B': 'RT04', 'P': 'RT01', 'S': 'RT03', 'fwd_mech': 'med'}
- AS: {'RT01': 65409, 'RT02': 64620, 'RT03': 64802, 'RT04': 64828}
- prefix: {'RT01': '172.16.134.0', 'RT02': '172.16.100.0', 'RT03': '172.16.41.0', 'RT04': '172.16.210.0'}
- 囮: [('unused_prefix_list', 'RT03')]

fix は solution/fix.json（fix_generated.yml で投入・exec の clear 込み）。
