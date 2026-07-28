# Lab ENARSI-OSPF-MADJ-01 : Leverage the Direct Link Between the ABRs

Difficulty: ★★★★☆ (4/5)

## Scenario

An enterprise network connects its West site (area 1) and East site (area 2)
through the backbone (area 0). The backbone consists of **slow long-haul
circuits** via RT03/RT04 (OSPF cost 100 on each segment).

Meanwhile, a **high-speed direct link** exists between the ABRs RT01 and RT02,
but this link belongs to the **NMS segment (area 100)** owned by the monitoring
team and is used for reachability to the monitoring probes
(172.31.100.1 / 172.31.100.2).

The user department has raised a complaint: "Communication between the West
site (RT05) and the East site (RT06) is slow." Your investigation shows that
RT05↔RT06 traffic does not use the high-speed direct link; instead it takes a
5-hop detour through the slow backbone.

## Topology

```
             area 1              area 0 (cost 100 ×3)             area 2
  RT05 ─────── RT01 ────── RT03 ────────── RT04 ────── RT02 ─────── RT06
 Lo0=5.5.5.5    │  10.1.13.0/30   10.1.34.0/30  10.1.24.0/30 │    Lo0=6.6.6.6
  10.1.15.0/30  │                                            │  10.1.26.0/30
                └──────────── 10.1.12.0/30 ──────────────────┘
                        area 100 (NMS; high-speed direct link)
```

- On each /30 link, the lower-numbered router takes .1
  (e.g. on RT01–RT02, RT01=.1 / RT02=.2)
- Lo0: RTxx = x.x.x.x/32 (RT05=5.5.5.5 in area 1 / RT06=6.6.6.6 in area 2)
- NMS probes: RT01 Lo100=172.31.100.1/32, RT02 Lo100=172.31.100.2/32 (area 100)
- OSPF process 1 is already running on all routers; all adjacencies are up and
  all routes are reachable

## Requirements

1. Traffic between RT05 (5.5.5.5) and RT06 (6.6.6.6) must traverse the direct
   RT01–RT02 link **in both directions** (it must not pass through RT03/RT04
   in the backbone).
2. If the direct link fails, traffic must automatically fail over to the
   RT03/RT04 path (the design must require no additional configuration at
   failure time).
3. Do not break the existing functions of the NMS segment (area 100):
   - Maintain the area 100 adjacency between RT01 and RT02
   - Maintain reachability to the monitoring probes 172.31.100.1 / 172.31.100.2

## Restrictions

- **The use of virtual-link is not allowed** (prohibited by corporate standard).
- **Do not change the area assignment of any existing interface or Loopback**
  (removing the direct link from area 100 or moving it to another area is not
  permitted under the agreement with the monitoring team).
- Cosmetic workarounds using static routes or PBR are not allowed.
- Adding physical links or changing IP addresses is not allowed.
- Do not change the existing OSPF cost values (100 in the backbone).

## Access

- CML console (SUZUKI / CCNP, enable CCNP)
- For SSH, use the mgmt IPs assigned at provision time
  (see `topologies/_generated/ENARSI-OSPF-MADJ-01/mgmt_map.yml`)

## Scoring

```
ansible-playbook playbooks/grade.yml -e problem=ENARSI-OSPF-MADJ-01 --vault-password-file <(printf 'CCNP\n')
```
