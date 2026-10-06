# Lab GEN-BGPCX-7731 : BGP Complex Troubleshooting (Difficulty 5)

## Scenario

Faults and deviations from the design have occurred in a BGP network made up of four ASes.
**Restore the network to match the design specification below.**

## Trouble Ticket (representative symptom - one of several)

> **RT01 cannot reach `172.16.0.0/24`.** There is not necessarily just one cause.

## Design Specification (the restoration target - this state is authoritative)

- **AS65001 (4 core routers)**: OSPF area 0 is the underlay (Loopback0 + internal links).
  iBGP uses a **route reflector (RR = the central router; all others are clients)**, and **every session is a Loopback0 peering (update-source)**.
- **AS65100** is dual-homed to two border routers. **Primary = be (east border)**:
  for core -> AS65100 traffic, the backup (bw) applies **LP 50 (< 100)** inbound to demote its paths, making be the primary.
  The return path AS65100 -> core must also enter via be: the backup (bw) applies an outbound **AS-path prepend x3**.
- **AS65200** peers with **be (east border)** by **Loopback-to-Loopback eBGP (multihop)**.
  Static routes to each other's Loopback are in place.
  **Routes from AS65200 are tagged with the operational community `65001:400` at the core ingress (be)**,
  and the core iBGP **propagates the tag with send-community** (verifiable inside the core).
- **The four prefixes 172.31.0.0-3.0/24 of AS65300 are summarized into `172.31.0.0/22`
  with summary-only on bw (west border)**; all other routers must see **only the /22**
  (leaking any /24 violates the design; the aggregating router must keep the four component /24s in its BGP table).
  **bw also distributes a default route to the stub AS65300 (default-originate).**
- Border routers set **next-hop-self** toward iBGP.
- All routers use **MP-BGP syntax** (`no bgp default ipv4-unicast` + `address-family ipv4 unicast`
  with **activate required**).

## Router Inventory (mgmt addresses are assigned in order)
| Router | Role | AS | Loopback0 | mgmt (SSH) |
|--------|------|----|-----------|-----------|
| RT05 | hub | AS65001 | `10.0.91.91` | 10.1.10.11 |
| RT07 | bw | AS65001 | `10.0.52.52` | 10.1.10.12 |
| RT03 | be | AS65001 | `10.0.75.75` | 10.1.10.13 |
| RT01 | leaf | AS65001 | `10.0.90.90` | 10.1.10.14 |
| RT02 | cust | AS65100 | `10.0.43.43` | 10.1.10.15 |
| RT04 | mhop | AS65200 | `10.0.42.42` | 10.1.10.16 |
| RT06 | agg | AS65300 | `10.0.31.31` | 10.1.10.17 |

Roles: hub = core center / bw, be = border routers (west, east) / leaf = internal core router / cust = AS65100 /
mhop = AS65200 (multihop) / agg = AS65300 (aggregating router)

Destinations: cust=`172.16.0-2.0/24` / mhop=`198.51.100.0/24` / agg=`172.31.0.0/22` (aggregate) /
leaf=`192.0.2.0/24`

## Objectives / Isolation
- Every router learns the destinations above in `show ip route bgp` and has mutual reachability. Only the /22 is seen for the aggregate.
- The type, location, and number of faults are not disclosed. **Even when the symptom appears in BGP, the root cause
  may be in a lower layer (OSPF / static routes / ACL / transport).**
- Isolation commands: `show ip bgp summary` / `show ip bgp` / `show ip bgp neighbors <ip>` /
  `show ip route bgp` / `show ip ospf neighbor` / `show ip route <prefix>`.
- Hints on what to consider: what does **Established with PfxRcd 0** mean? What causes a route that is **in the BGP table but not in the RIB**?
  What is the difference between Idle and Active? RR reflection rules
  (client -> everyone / non-client -> clients only). **Best-path selection order (weight > LP >
  AS-path > MED ...)** - when the path is not the designed one, suspect the higher-order attributes first.
  **After changing a policy (route-map / filter / weight / community), run `clear ip bgp * soft`.**
  When a session **stays Idle and does not recover**, find out why (`show ip bgp neighbors` / the %BGP- and %TCP- log lines);
  some failure modes **require a clear even after the configuration is fixed**.
  Communities include **well-known ones (such as no-export)**, which change how far a tagged route is advertised.

## Access and Scoring
SSH `SUZUKI / CCNP`.
```
ansible-playbook playbooks/grade.yml -e problem=GEN-BGPCX-7731 --vault-password-file <(printf 'CCNP\n')
```
