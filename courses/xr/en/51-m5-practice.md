# M5 — Practice

These are the tasks of lab **XRT-03**, shown here so that you can read them away from the lab.
Do them in the lab workspace: the **Tasks** tab there has a Check button, staged hints and,
once a task passes, a reference solution for each task. No command examples are given on purpose.

## Ground rules

- You configure **XR01 only**. RT01, RT02, RT03 and RT04 are fixed; do not change them. You may log in to them to look.
- No command examples are given. Each task states the behaviour that is required. Use the CLI help (`?`),
  the `show` commands, and the Cisco IOS XR configuration guides and command references to find the commands.
- The **Steps** tab has a **Check** button for each task. It reads the live state of the devices.
  Leave configuration mode before you press it. BGP needs a few seconds to pass a change on to the peers.
- Hints open one level at a time (keyword → where to look → command). Opened hints are logged.
- XR01 runs **IOS XRd**, the container form of IOS XR. For this unit it behaves as IOS XRv 9000 does.
  It forwards ping through itself, but not traceroute or TCP sessions; check your work with `show` commands.

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

## M5 — Routing Policy Language

### Task M5-1
<p class="tolab"><a href="/_learn?id=XRT-03&amp;step=m5t1">Open in the lab workspace</a> — Read: <a href="50-m5-rpl.html#s1">1. Why a policy is required</a> · <a href="50-m5-rpl.html#s3">3. How a policy decides</a></p>


XR01 has Established sessions with both providers, but it receives no routes from either of them, and neither
receives anything from XR01. A colleague started on ISP-B with a policy meant to drop private address space only.

- XR01 must accept every route from both providers except private address space (10.0.0.0/8, 172.16.0.0/12 and
  192.168.0.0/16, at any prefix length). The colleague's intent is correct; apply it to both providers.
- XR01 must announce 203.0.113.0/24 to both providers, and nothing else.

### Task M5-2
<p class="tolab"><a href="/_learn?id=XRT-03&amp;step=m5t2">Open in the lab workspace</a> — Read: <a href="50-m5-rpl.html#s2">2. Sets</a></p>


Tighten what XR01 accepts from the providers. In addition to private address space, XR01 must not accept
a default route or any prefix longer than /24 from either provider. Everything else stays accepted.

### Task M5-3
<p class="tolab"><a href="/_learn?id=XRT-03&amp;step=m5t3">Open in the lab workspace</a> — Read: <a href="50-m5-rpl.html#s4">4. Parameters and apply</a></p>


ISP-A is the primary provider and ISP-B the backup.

- Routes learnt from ISP-A must have local preference 200, and routes learnt from ISP-B local preference 100.
- Every route learnt from a provider must carry the community that tells where it was learnt (see the table above),
  in addition to any communities it arrived with.
- Write this as **one** policy definition that is used for both providers. Connecting a third provider later must not
  require a new policy definition.
- The filtering from M5-1 and M5-2 must stay in effect, without being written twice.

### Task M5-4
<p class="tolab"><a href="/_learn?id=XRT-03&amp;step=m5t4">Open in the lab workspace</a> — Read: <a href="50-m5-rpl.html#s2">2. Sets</a> · <a href="50-m5-rpl.html#s3">3. How a policy decides</a></p>


Connect the customer.

- From RT03, accept only prefixes inside 198.51.100.0/23, no longer than /24, that originate in the customer's AS.
  Prepending by the customer is allowed.
- Announce the customer's routes to both providers, together with 203.0.113.0/24. Honour `65000:1001` and
  `65000:1002`.
- The providers must not receive any community in the range `65000:*`. Communities the customer sets in its own
  range (`65201:*`) must reach the providers.
- Announce to the customer every route XR01 has, with the communities from Task M5-3.
