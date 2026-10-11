# Problem GEN-RDFIELD-37274 : Route Reachability Trouble Ticket (Difficulty 5)

## Scenario
The corporate network connects the **OSPF 19 domain and the EIGRP AS 485 domain** in a redundant design
through mutual redistribution on **two border routers (RT04, RT01)**. There are signs that work was performed
around the border routers last night, and the ticket below has been arriving since this morning.
Investigate and correct the network so that it **fully complies with the corporate routing standard (below)**.

## Topology: Link List (directly connected at L2; addresses are .1/.2 of each /30)

```
  RT06 ── RT04   (OSPF 19 area 0 / 10.184.87.0/30)
  RT06 ── RT01   (OSPF 19 area 0 / 10.163.209.0/30)
  RT04 ── RT01   (EIGRP AS 485 / 10.229.239.0/30)
  RT04 ── RT05   (EIGRP AS 485 / 10.199.245.0/30)
  RT01 ── RT05   (EIGRP AS 485 / 10.97.190.0/30)
  RT06 ── RT02   (OSPF 19 area 0 / 10.11.118.0/30)
  RT05 ── RT03   (EIGRP AS 485 / 10.158.225.0/30)
  RT03 ── RT07   (EIGRP AS 485 / 10.106.68.0/30)
```

## Routers / Protocols / Loopbacks

| Router | Protocols | Loopback |
|--------|----------------|----------|
| RT01 | OSPF 19 / EIGRP AS 485 | `59.59.59.59/32` |
| RT02 | OSPF 19 | `21.21.21.21/32` |
| RT03 | EIGRP AS 485 | `63.63.63.63/32` |
| RT04 | OSPF 19 / EIGRP AS 485 | `30.30.30.30/32` |
| RT05 | EIGRP AS 485 | `25.25.25.25/32` |
| RT06 | OSPF 19 | `22.22.22.22/32` |
| RT07 | EIGRP AS 485 | `36.36.36.36/32` |

## Trouble Ticket (as reported; verifying it is your job)
> 1. The monitoring team reports that "**routes take a detour on some segments** (hops through the other domain are seen even though the destination is in the same domain)" (the affected scope has not been verified yet).

## Corporate Routing Standard (excerpt)
1. The two border routers perform **mutual redistribution** between OSPF and EIGRP, and **the Loopbacks of all routers must be mutually reachable**.
2. **Injection into EIGRP requires the seed metric `100000 100 255 1 1500`**.
3. **Protection against re-injection with two-point mutual redistribution**: **tag `903` must be attached** to routes
   of OSPF origin, and routes originated by the local domain (tag `903`) must be **blocked on EIGRP reception (in)** at the border routers.
4. **The EIGRP AD is fixed at internal 90 / external 95 (must not be changed; company policy)**.
5. Routes must be the **shortest** (a remaining suboptimal route caused by redistribution, or a remaining loop, is non-compliant).

## Restrictions
- Only the two border routers (RT04, RT01) may be reconfigured. All other routers must not be changed (show, ping, and traceroute are allowed).
- Workarounds using static routes, default routes, AD changes, or changes to the domain structure are not allowed.

## Notes
* If the routes do not change after a configuration change, recalculate them with `clear ip route *`.

## Access / Scoring
SSH `SUZUKI / CCNP` (mgmt addresses in order of assignment, from 10.1.10.11).
```
ansible-playbook playbooks/grade.yml -e problem=GEN-RDFIELD-37274 --vault-password-file <(printf 'CCNP\n')
```
Scoring is **effect-based (reachability, shortest path, absence of loops) plus a comparison against the corporate routing standard**.
