# Problem ENARSI-BGP-ROUTEMAP-01 : Inbound Control Combining a prefix-list and an as-path in a route-map

## Scenario
RT01 (AS65001) receives multiple prefixes from its neighbor RT02 (AS65002).
In addition to the routes of its own AS (AS65002), RT02 also relays routes from
RT03 (AS65003), which is one AS farther away. Under the new policy, implement the following
inbound control on RT01, **combined into a single route-map**:

1. **Routes in /24 units within `10.10.0.0/16`** (internal priority services) → accept them and
   raise **local-preference to 200**.
2. **Routes that passed through AS65003** (through an external AS) → reject them.
3. All other routes → accept them as they are (default local-pref 100).

## Topology
```
[Lo10  = 10.10.0.0/24]    [Lo172 = 172.16.0.0/24]
[Lo11  = 10.10.16.0/20]
[Lo20  = 10.20.0.0/24]
       │
RT01 ─ eBGP ─ RT02 ──── eBGP ──── RT03
AS65001       AS65002 (transit)    AS65003
```

In the initial state, four prefixes are visible in the BGP table of RT01: `10.10.0.0/24`,
`10.10.16.0/20`, `10.20.0.0/24`, and `172.16.0.0/24`.

## Objectives
- The RT01 ↔ RT02 eBGP session remains Established.
- BGP table of RT01:
  - `10.10.0.0/24` remains, and the **local-pref of the best path = 200**.
  - `10.10.16.0/20` remains, and its local-pref is the default (100).
  - `10.20.0.0/24` remains, and its local-pref is the default (100).
  - `172.16.0.0/24` **is gone**.

## Restrictions
- Make changes on **RT01 only**. RT02 / RT03 must not be changed.
- The inbound control must be combined in **a single route-map** with **multiple sequences**.
  A solution that uses only an individual prefix-list or only an individual filter-list is not allowed.
- Components to use inside it (at the candidate's discretion):
  - To match the priority-service prefixes, use a **prefix-list (`ge` notation)**.
  - To match AS65003, use an **as-path access-list**.
- Apply the route-map **inbound**.

## Access
- Use the CML console, or SSH to the management IP (SUZUKI / CCNP; refer to the assignment issued at provisioning for the management IPs)

## Scoring
```
scripts/lab.sh grade ENARSI-BGP-ROUTEMAP-01
```
