# M6 — Practice

These are the tasks of lab **XRT-03**, shown here so that you can read them away from the lab.
Do them in the lab workspace: the **Tasks** tab there has a Check button, staged hints and,
once a task passes, a reference solution for each task. No command examples are given on purpose.

## Topology

| Link | XR01 | Peer | Addressing |
|---|---|---|---|
| ISP-A | GigabitEthernet0/0/0/0 | RT01 Ethernet0/0 | 10.0.11.0/24 (XR01 .1, RT01 .2) |
| ISP-B | GigabitEthernet0/0/0/1 | RT02 Ethernet0/0 | 10.0.12.0/24 (XR01 .1, RT02 .2) |
| CUSTOMER | GigabitEthernet0/0/0/2 | RT03 Ethernet0/0 | 10.0.13.0/24 (XR01 .1, RT03 .2) |
| CORE | GigabitEthernet0/0/0/3 | RT04 Ethernet0/0 | 10.0.14.0/24 (XR01 .1, RT04 .2) |

- XR01 is AS 65000. Its own prefix is **203.0.113.0/24** (a static route to Null0, announced with a `network`
  statement). Loopback0 1.1.1.1/32.
- RT01 is upstream provider ISP-A (AS 65101). RT02 is upstream provider ISP-B (AS 65102).
  Both send XR01 a set of Internet routes, and some routes that AS 65000 does not want.
- RT03 is a customer (AS 65201). It has been allocated **198.51.100.0/23** and may announce it as one prefix
  or as /24 prefixes, with or without prepending its own AS.
- RT04 is an internal router of AS 65000. XR01 and RT04 run OSPF process 1, area 0, over CORE and for their
  Loopback0 addresses (XR01 1.1.1.1/32, RT04 4.4.4.4/32). RT04 also has two internal LANs in OSPF,
  203.0.113.128/26 and 203.0.113.192/26. The provider and customer links are not in OSPF.
- The eBGP sessions to the three external peers are configured on XR01 and are Established.
  An iBGP session to RT04 is also configured on XR01; it is the subject of M6 and does not come up until then.
- AS 65000 publishes these communities for its customers:

  | Community | Meaning |
  |---|---|
  | `65000:1001` | Do not announce this route to ISP-A |
  | `65000:1002` | Do not announce this route to ISP-B |
  | `65000:101` | Set by AS 65000: this route was learnt from ISP-A |
  | `65000:102` | Set by AS 65000: this route was learnt from ISP-B |

## M6 — BGP

### Task M6-1
<p class="tolab"><a href="/_learn?id=XRT-03&amp;step=m6t1">Open in the lab workspace</a> — Read: <a href="60-m6-bgp.html#s2">2. iBGP between loopbacks</a></p>


The iBGP session between XR01 and RT04 does not come up. RT04 is configured to peer with XR01's Loopback0 from its own
Loopback0.

- Ensure that the session comes up between the two loopbacks.
- RT04 must install the provider and customer routes in its routing table.
- Do not add the provider or customer links to OSPF.

### Task M6-2
<p class="tolab"><a href="/_learn?id=XRT-03&amp;step=m6t2">Open in the lab workspace</a> — Read: <a href="60-m6-bgp.html#s3">3. Redistribution</a></p>


The customer must be able to reach AS 65000's internal LANs.

- Announce to the customer the internal LANs that XR01 learns by OSPF, that is, the prefixes inside
  203.0.113.0/24 that are longer than /24.
- Nothing else that XR01 learns by OSPF may enter BGP: no loopbacks and no link subnets.
- The providers must still receive only 203.0.113.0/24 from AS 65000's own address space.

### Task M6-3
<p class="tolab"><a href="/_learn?id=XRT-03&amp;step=m6t3">Open in the lab workspace</a> — Read: <a href="60-m6-bgp.html#s4">4. Prepending, and a trap with apply</a></p>


Traffic from the Internet to AS 65000 and to its customer must enter through ISP-A while ISP-A is available.

- Every route that XR01 announces to ISP-B must carry AS 65000 three more times than it does now.
- What XR01 announces to ISP-A must not change.
- ISP-B must still receive exactly the routes it received before: AS 65000's own prefix and the customer routes
  allowed by Task M5-4.

### Task M6-4
<p class="tolab"><a href="/_learn?id=XRT-03&amp;step=m6t4">Open in the lab workspace</a> — Read: <a href="60-m6-bgp.html#s5">5. Templates</a></p>


Prepare for more providers.

- Both providers must have a limit of **1000** prefixes received, with a warning when **80%** of the limit is reached.
- The settings the providers share, the community sending from Task M5-4 and this limit, must be defined once and
  inherited by each provider. Connecting a third provider later must need only its address, its AS number and the
  values for its policies.
