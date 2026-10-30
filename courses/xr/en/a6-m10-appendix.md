# M10 — Appendix: flexible algorithm, SRv6, SID conflicts

This appendix covers the parts of blueprint section 3.3 that the lab tasks do not use: the flexible algorithm (3.3.f),
SRv6 (3.3.g), and the disagreement between routers when two of them share a SID. The flexible algorithm has a try-it box
that you can do in lab XRT-10.

## 1. The flexible algorithm

### 1.1 What it is good for

The IGP computes one shortest path per destination, on one metric. The network has a single "map". Sometimes, though,
you want a path with low delay, or a path that avoids a given link, next to the ordinary one.

An SR policy (page "SR policies and the PCE") can do that, but the head end computes a path per destination and stacks
several labels. The **flexible algorithm** (Flex-Algo, RFC 9350) gives every router another map. Say you define
"algorithm 128 = the map without PRIMARY": every router that takes part then computes shortest paths on that map too,
next to the ordinary one.

Each router hands out a separate number (prefix SID) per map. On RT02 in the lab, the number on the ordinary map is 12
(label 16012), and the number on the algorithm-128 map is 112 (label 16112). 16112 means "go to RT02 along the shortest
path on the algorithm-128 map". The head end picks the map just by putting on one label. The routers on the way have
that map too, and forward along it.

### 1.2 How it works and how to configure it

An algorithm is a number from 128 to 255, each with its own definition: which metric to use (the IGP metric, a delay,
a TE metric) and which links to leave out (affinities, SRLGs). One router advertises the definition; the others take
part and follow it. A router that does not take part is left out of that algorithm's map (RFC 9350).

On IOS XR, the definition is `router isis` → `flex-algo 128` → `metric-type`, `affinity`, `advertise-definition`; the SID
is `prefix-sid algorithm 128 index <n>` under the loopback. A definition on delay needs delay values on the links
(`performance-measurement`), and a link without one is left out. In the PoC, `metric-type delay` with no delay advertised
gave no path at all.

The IOS routers of the lab take part in algorithm 128 with prefix-SID indexes 111 to 113, and advertise no definition.
XR02 does not take part. Only MPLS-to-MPLS entries are installed for a flexible algorithm, so IP traffic reaches one
through an SR policy (for example an on-demand policy with `sid-algorithm 128`).

:::try
Define algorithm 128 so that it avoids PRIMARY. Do it after Task M10-5.

1. On XR01, under `router isis CORE`: `affinity-map RED bit-position 0`; `flex-algo 128` with `advertise-definition` and
   `affinity exclude-any RED`; under `interface GigabitEthernet0/0/0/0`, `affinity flex-algo RED`; under
   `interface Loopback0` → `address-family ipv4 unicast`, `prefix-sid algorithm 128 index 101`. Commit.
2. On XR01, run `show isis flex-algo 128`, `show isis segment-routing label table`, `show mpls forwarding labels 16012`
   and `show mpls forwarding labels 16112`. On RT01, run `show isis topology flex-algo 128`.
3. Remove what you added and commit.

What the lab measured: XR01 advertised the definition (`Exclude Any Affinity Bit Positions: 0`) and built labels 16101
to 16113 for algorithm 128. Label 16012 (algorithm 0) left through GigabitEthernet0/0/0/0 towards RT01, and label 16112
(algorithm 128) through GigabitEthernet0/0/0/1 towards RT03. RT01 still reached XR01 over PRIMARY in algorithm 128
(`show isis topology flex-algo 128`): the affinity is an attribute of the direction that XR01 advertises, not of the
link as a whole. XR02 appeared as `**`, outside the algorithm.
:::

## 2. SRv6

### 2.1 What it is good for

SRv6 writes the path with IPv6 addresses instead of MPLS labels. SR then works in a network that runs IPv6 only, with
no MPLS. Because a SID is an IPv6 address, a router that knows nothing of SRv6 still passes the packet on with ordinary
IPv6 routing. A VPN can be expressed as one of the SID functions too (End.DT4), so an L3VPN needs neither LDP nor MPLS.

### 2.2 How it works and how to configure it

An SRv6 SID is a **locator**, a prefix that the IGP advertises and that leads to the router, followed by a **function**
that says what the router does with the packet (End: go on to the next SID; End.X: leave through this adjacency;
End.DT4: look up an IPv4 VRF). The list of SIDs travels in a segment routing header. With **micro-SIDs** (uSID, format
f3216 by default on IOS XR), several 16-bit SIDs are packed into one destination address.

On IOS XR, the locator is `segment-routing` → `srv6` → `locators` → `locator <name>` with
`micro-segment behavior unode psp-usd` and a prefix, and IS-IS advertises it with `address-family ipv6 unicast` →
`segment-routing srv6` → `locator <name>`. The IOS XE guide supports SRv6 from 17.12.1a on ASR 1000 and Catalyst 8000
platforms only. IOL shows the commands, but it is not in that list, and the lab's core runs IPv4 only. SRv6 stays on
this page.

## 3. Two routers, one SID

A prefix SID is global, so two routers must never advertise the same index for different prefixes. When they do, every
router has to pick one of them for that label. RFC 8660 gives a default rule: the lowest administrative distance first,
then the smallest prefix value. The rule is a SHOULD, though: an implementation may use another one, and RFC 8660 then
requires the operator to run routers with the same rule in one IGP area.

In the PoC of this unit, RT03 advertised index 12 for its own loopback, the index of RT02. XR01 followed the default
rule: it kept 16012 for 10.255.0.12, the smaller prefix, left 10.255.0.13 without a label, and logged
`Label Conflict: Prefix-SID label 16012 for algo SPF is used by 10.255.0.12/32 and 10.255.0.13/32`. RT01, an IOS router,
chose the other way: it mapped 16012 to 10.255.0.13.

XR01 sent customer A's traffic to RT01 with 16012 for RT02, RT01 forwarded it towards RT03, and the VPN stopped. Taken
one at a time, every router made a sensible choice. But the routers chose differently from each other, so across the
network as a whole the path did not join up.

:::note
Sources: the Segment Routing Configuration Guide for the ASR 9000, IOS XR 26.1.x–26.3.x (2026: flexible algorithm,
performance measurement, SRv6 micro-SIDs) and its command reference (2025); the IOS XE Segment Routing Configuration
Guide (2026: flexible algorithm, SRv6); RFC 8660 and 9350. All checked October 2026. Cisco Live sessions BRKSPG-3624
(EMEA 2025) and BRKSP-2551 (EMEA 2026) were used only for background on the unit as a whole. The IOS routers in
algorithm 128, the definition on delay, and the SID conflict between IOS XR and IOS come from measurement in lab XRT-10
and its PoC.
:::
