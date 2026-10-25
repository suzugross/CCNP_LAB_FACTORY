# M8 — Practice, Unified MPLS

These are the tasks of lab **XRT-08**, shown here so that you can read them away from the lab.
Do them in the lab workspace: the **Tasks** tab there has a Check button, staged hints and,
once a task passes, a reference solution for each task. No command examples are given on purpose.

## Ground rules

- You configure **XR01 only**. RT01 to RT05 are fixed; do not change them. You may log in to them to look.
- No command examples are given. Each task states the behaviour that is required. Use the CLI help (`?`),
  the `show` commands, and the Cisco IOS XR configuration guides and command references to find the commands.
- The **Tasks** tab has a **Check** button for each task. It reads the live state of the devices.
  Leave configuration mode before you press it. IS-IS and LDP need up to 30 seconds after a change. An iBGP session
  between RT02 and RT05 can take up to two minutes to come up once the two routers can reach each other.
- Hints open one level at a time (keyword → where to look → command). Opened hints are logged.
- XR01 runs **IOS XRd** 26.1.1, the container form of IOS XR, as in lab XRT-07. It switches labelled traffic like the
  other routers here.

## Topology

| Link | XR01 | Peer | Addressing | IS-IS metric |
|---|---|---|---|---|
| PRIMARY | GigabitEthernet0/0/0/0 | RT01 Ethernet0/0 | 10.0.1.0/24 (XR01 .1, RT01 .11) | 10 |
| BACKUP | GigabitEthernet0/0/0/1 | RT03 Ethernet0/0 | 10.0.3.0/24 (XR01 .1, RT03 .13) | 100 |
| CORE-A | — | RT01 Ethernet0/1 ─ RT02 Ethernet0/0 | 10.0.12.0/24 (RT01 .11, RT02 .12) | 10 |
| CORE-B | — | RT03 Ethernet0/1 ─ RT02 Ethernet0/1 | 10.0.23.0/24 (RT03 .13, RT02 .12) | 100 |
| ACCESS-1 | GigabitEthernet0/0/0/2 | RT04 Ethernet0/0 | 10.0.14.0/24 (XR01 .1, RT04 .14) | 10 |
| ACCESS-2 | — | RT04 Ethernet0/1 ─ RT05 Ethernet0/0 | 10.0.45.0/24 (RT04 .14, RT05 .15) | 10 |

| Router | Role | Platform | Loopback0 | Other networks |
|---|---|---|---|---|
| XR01 | provider edge, border between core and access | IOS XRd 26.1.1 | 10.255.0.1/32 | customer A 10.30.0.0/16 (Loopback100, in BGP only); management 10.255.255.1/32 (Loopback1) |
| RT01 | core | IOS XE 17.15 | 10.255.0.11/32 | — |
| RT02 | provider edge | IOS XE 17.15 | 10.255.0.12/32 | customer A 10.20.0.0/16 (Loopback100, in BGP only) |
| RT03 | core | IOS XE 17.15 | 10.255.0.13/32 | — |
| RT04 | access | IOS XE 17.15 | 10.255.0.14/32 | — |
| RT05 | provider edge in the access network | IOS XE 17.15 | 10.255.0.15/32 | customer A, new site 10.50.0.0/16 (Loopback100, in BGP only) |

- The core runs IS-IS instance `CORE` for IPv4 between XR01, RT01, RT02 and RT03: area 49.0001, Level 2 only, wide
  metrics, point-to-point circuits. LDP runs on every core link to the standard of lab XRT-07.
- The new access network runs IS-IS instance `ACCESS` for IPv4 between RT04 and RT05: area 49.0002, Level 2 only,
  wide metrics, point-to-point circuits, metric 10. LDP runs on its links, with the LDP identity taken from Loopback0.
- All routers are in AS 65000. RT01, RT03 and RT04 do not run BGP.
  - XR01 and RT02 run iBGP between their loopbacks, as in lab XRT-07.
  - RT02 and RT05 advertise their Loopback0 and customer A's networks to XR01 in BGP IPv4 labeled unicast.
  - RT02 and RT05 exchange customer A's routes with each other in a direct iBGP session between their loopbacks.
    They do not send their loopbacks in that session.

## M8 — Unified MPLS

### Task M8-6
<p class="tolab"><a href="/_learn?id=XRT-08&amp;step=m8t6">Open in the lab workspace</a> — Read: <a href="84-m8-appendix.html#s2">2. Three ways to build it</a> · <a href="82-m8-unified-mpls.html#s1-1">1.1 Why the IGP is split</a> · <a href="82-m8-unified-mpls.html#s2-1">2.1 Two IS-IS instances</a> · <a href="82-m8-unified-mpls.html#s2-2">2.2 The border's own loopback</a></p>


A new access network, RT04 and RT05, connects to XR01 over ACCESS-1. XR01 becomes the border between the core and
the access network.

- Make XR01 part of the access network: run IS-IS instance `ACCESS` on ACCESS-1 with the values of the access
  network, and run LDP on ACCESS-1.
- The core and the access network must not learn each other's routes. No route of the core may appear in the access
  network, except XR01's Loopback0, and no route of the access network may appear in the core.
- The operations team of the access network verifies the border with MPLS OAM: from RT05, an MPLS LSP ping to XR01's
  Loopback0 must succeed.

### Task M8-7
<p class="tolab"><a href="/_learn?id=XRT-08&amp;step=m8t7">Open in the lab workspace</a> — Read: <a href="84-m8-appendix.html#s5">5. What the border tells the PEs</a> · <a href="84-m8-appendix.html#s7">7. The border's two jobs</a> · <a href="82-m8-unified-mpls.html#s3-1">3.1 The address family</a> · <a href="82-m8-unified-mpls.html#s3-2">3.2 Next hop self on a route reflector</a> · <a href="82-m8-unified-mpls.html#s3-3">3.3 Allocating labels</a> · <a href="82-m8-unified-mpls.html#s3-4">3.4 Following the labels</a></p>


Under change CHG-1107, XR01 was to carry the loopbacks of the provider edges between the core and the access network
in BGP labeled unicast, as the route reflector for RT02 and RT05. The change has been applied, but the iBGP session
between RT02 and RT05 does not come up, and the new site of customer A cannot reach the site behind RT02.

- Make the iBGP session between RT02 and RT05 come up, and make the traffic between 10.50.0.0/16 and 10.20.0.0/16
  flow in both directions.
- RT02 and RT05 must reach each other's Loopback0 through XR01 over a label switched path: XR01 must advertise their
  loopbacks to each other with itself as the next hop.
- Do not redistribute routes between the two IS-IS instances, and do not run BGP on RT01, RT03 or RT04.

### Task M8-8
<p class="tolab"><a href="/_learn?id=XRT-08&amp;step=m8t8">Open in the lab workspace</a> — Read: <a href="82-m8-unified-mpls.html#s4-1">4.1 Customer routes between the provider edges</a> · <a href="82-m8-unified-mpls.html#s4-2">4.2 Labels for the loopbacks only</a> · <a href="82-m8-unified-mpls.html#s5-1">5.1 LSP ping for a BGP FEC</a></p>


The border must not carry customer routes: they belong to the provider edges.

- XR01 must assign BGP labels to the loopbacks of the provider edges (/32 routes in 10.255.0.0/24) only. No other
  route in XR01's BGP table may get a BGP label.
- XR01 must reflect only those loopbacks to RT02 and RT05. Customer A's routes are exchanged between RT02 and RT05
  directly.
- The traffic between customer A's sites behind RT02 and RT05, and between the sites behind XR01 and RT02, must keep
  flowing.
