# Lab ENARSI-VRFLITE-DNBIT-01 : Unreachable Remote Site over VRF-Lite (Difficulty 4)

## Scenario
An enterprise extends its internal isolated segment **RED** across the WAN using
VRF-Lite (multi-VRF). Routes are carried as follows.

```
 [Site A server network]                                [Site B server network]
  172.20.20.0/24                                            172.30.30.0/24
      │                                                          │
     RT01 ──(RED / eBGP)── RT02 ──(RED / OSPF area0)── RT03 ─────┘
   (RED border; origin)  (RED transit; redistributes    (Site B access; VRF RED OSPF)
                          received eBGP into OSPF)
```

- **RT01** advertises the Site A network 172.20.20.0/24 to RT02 via **eBGP**.
- **RT02** receives it and **redistributes it into OSPF in VRF RED** toward the
  RED domain. In the other direction, it returns the Site B network
  172.30.30.0/24 to RT01 via OSPF→eBGP.
- **RT03** hosts Site B (172.30.30.0/24) and maintains an OSPF adjacency with
  RT02 in VRF RED.

## Reported Problem (NOC ticket)

> **Site B cannot reach the Site A servers (172.20.20.0/24) at all.**
> However:
> - The **OSPF adjacency between RT03 and RT02 is FULL** and healthy.
> - The Site B network is reachable from other sites (i.e. RT03's
>   advertisements are working).
> - On RT02, the Site A network 172.20.20.0/24 **is properly visible**.
>
> **Remediate on RT03 so that Site B can reach Site A.**

## Requirements (target state)

1. **172.20.20.0/24 must be installed in RT03's VRF RED routing table.**
2. **RT03 must have reachability to Site A**
   (`ping vrf RED 172.20.20.20 source 172.30.30.30` succeeds).
3. Do not break the parts that already work, such as the Site B advertisements
   and the OSPF adjacency with RT02.

## Diagnostic Hint
- The OSPF adjacency is FULL, RT02 has the route, and yet it does not reach RT03.
  → On RT03, check whether 172.20.20.0/24 is in a state where it **"exists in
    the OSPF database but is absent from the routing table"**
    (compare `show ip ospf 10 database external ...` with
    `show ip route vrf RED ...`). When a route is in the database but not
    installed in the RIB, there is a reason.

## Restrictions
- **You may operate on RT03 only.** Changes to RT01 / RT02 are prohibited.
- **Do not use static routes** (172.20.20.0/24 must be installed as an OSPF route).
- Do not touch the management VRF `MGMT` or Ethernet0/3.

## Scoring
```
ansible-playbook playbooks/grade.yml -e problem=ENARSI-VRFLITE-DNBIT-01 \
  --vault-password-file <(printf 'CCNP\n')
```
