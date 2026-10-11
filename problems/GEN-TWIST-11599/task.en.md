# Problem GEN-TWIST-11599 : OSPF Route Filtering (auto-generated, tree, 4 routers)

IP addressing is preconfigured on every inter-router link and on every Loopback.

## Requirements
1. Configure OSPF process 1 / area 0 on all routers, all links, and all Loopbacks, such that every router can reach the Loopbacks of all other routers.
2. However, **RT01** must **not hold** **RT02's Loopback (`21.21.21.21/32`)** in its own routing table.
   - All other routers must be able to reach `21.21.21.21/32`.
   - RT01 itself must also be able to reach all Loopbacks other than RT02's.

## Loopbacks
- RT01: 83.83.83.83/32
- RT02: 21.21.21.21/32
- RT03: 41.41.41.41/32
- RT04: 60.60.60.60/32

## Topology (Links)
- RT01(10.252.135.1) — RT02(10.252.135.2)  [10.252.135.0/30]
- RT01(10.106.190.1) — RT03(10.106.190.2)  [10.106.190.0/30]
- RT03(10.164.219.1) — RT04(10.164.219.2)  [10.164.219.0/30]

## Scoring
```
ansible-playbook playbooks/grade.yml -e problem=GEN-TWIST-11599 --vault-password-file <(printf 'CCNP\n')
```
