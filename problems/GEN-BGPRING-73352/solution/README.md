# 採点者専用 (GEN-BGPRING-73352)

- shape: **path_select** / layout: four_as
- faults: ['path_select:prepend_wrong_nbr']
- meta: {'A': 'RT01', 'B': 'RT03', 'P': 'RT02', 'S': 'RT04', 'fwd_mech': 'med'}
- AS: {'RT01': 65157, 'RT02': 65291, 'RT03': 65287, 'RT04': 64951}
- prefix: {'RT01': '172.16.26.0', 'RT02': '172.16.101.0', 'RT03': '172.16.16.0', 'RT04': '172.16.67.0'}
- 囮: [('legacy_comment', 'RT02')]

fix は solution/fix.json（fix_generated.yml で投入・exec の clear 込み）。
