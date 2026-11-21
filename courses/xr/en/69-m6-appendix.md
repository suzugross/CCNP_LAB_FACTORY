# M6 supplement — Appendix

This appendix collects what the main pages mention only briefly: best-external as a VPN feature, PIC Core and PIC
Edge, how IOS XRd and IOS XRv 9000 differ, and what happens to BGP routes that do not make it into the RIB. Then come
the defaults and commands of IOS XR and IOS XE side by side, and the points where the official documents and the
devices disagreed. best-external in a VPN, PIC Core and ADD-PATH on IOS XE were not tried in this supplement.

## 1. best-external: a feature for VPNs

`advertise best-external` makes a router advertise its best eBGP path (the best-external path) to its iBGP neighbors
and route reflectors when the best path it selected locally came from an iBGP neighbor. BGP computes the
best-external path only when the best path is an iBGP path.

PE3 on this board is in exactly that position. Its best path is the iBGP path through PE2 (local preference 200), and
the path learned from X2 becomes the best-external path. With the command on PE3, X2's path carries `best-external`
and is advertised to RR1 (an excerpt from PE3):

```console
RP/0/RP0/CPU0:PE3#show bgp 203.0.113.0/24
...
Paths: (2 available, best #1)
...
  65100
    10.255.0.2 (metric 20) from 10.255.0.21 (10.255.0.2)
      Origin IGP, metric 11, localpref 200, valid, internal, best, group-best
...
  Path #2: Received by speaker 0
  Advertised IPv4 Unicast paths to peers (in unique update groups):
    10.255.0.21
  65100
    172.16.3.1 from 172.16.3.1 (10.100.255.2)
      Origin IGP, metric 11, localpref 100, valid, external, best-external
```

RR1 now holds two paths, but it reflects only its best one, and PE1 still knows only the path through PE2.
best-external alone does not shorten the outage when PE2 fails. The backup exit advertises, and the news stops at the
route reflector.

The Cisco documents place `advertise best-external` under the VRF IPv4/IPv6, VPNv4/VPNv6, L2VPN and labelled-unicast
address families. Plain IPv4/IPv6 unicast is not in the list, and the Routing Command Reference for the ASR 9000 says
"Unlabelled best-external is not supported as it may create routing loop".

The ASR 9000 guide for 26.x adds that per-VRF label mode does not support best-external within the same address
family, as it may cause loops. Neither document describes the loop itself.

What happened on this board was this send-back. With the backup path delivered to the ingress and PIC on the ingress
PE1 only, cutting PE2 off from P1 stopped traffic for 3.01 seconds. With the ingress's BGP next-hop tracking delay
stretched to 10 seconds, it was 2.93 seconds: the ingress switched to the backup PE3 without waiting for BGP (with an
IOS XRv 9000 ingress; for an XRd ingress, see section 3).

The packets stopped at PE3. In a network without labels, PE3 looks each arriving packet up again by its IP address.
PE3's best path was still the iBGP path through PE2, so the packets were sent back toward PE2 and never arrived. PE3's
BGP selects a new best path only after its own next-hop tracking delay (3 seconds). For 3 seconds, the backup exit
dutifully sends everything back to the primary.

In a VPN, the ingress pushes the VPN label that the backup PE put on its route. With per-prefix or per-CE labels, the
backup PE sends the packet straight to the CE on the strength of that label, with no IP lookup (M9 appendix, section
1.1). With a per-VRF label it looks the packet up again in the VRF table, so the note above can be read as pointing at
the same shape as this send-back.

The documents and these virtual routers disagree. IOS XRd 26.1.1 and IOS XRv 9000 26.1.1 both accept
`advertise best-external` under plain IPv4 unicast at commit and, as the output above shows, it takes effect. A
setting the documents call unsupported goes through without a word.

This lab does not use it. Task M6-5 rules out best-external, and PE3 sends X2's path to RR1 as a backup with ADD-PATH
(`set path-selection backup 1 advertise`). ADD-PATH is documented as usable for IPv4 unicast.

From IOS XR 7.8.1 there is also a feature that sends the best path and the best-external path without ADD-PATH when
the PEs of a VPN use different RDs. It is on by default and cannot be turned off ("BGP Advertisement without
Additional Paths" in the BGP configuration guide for the NCS 5500, 25.x). With different RDs, the two are different
VPNv4 routes (M9), so a route reflector does not reduce them to one.

## 2. PIC Core and PIC Edge

PIC (Prefix Independent Convergence) takes its name from a switchover time that does not depend on the number of
routes. The forwarding table of IOS XR is hierarchical: a BGP route points to a shared entry for its next hop, and that
entry points to the IGP path. The release notes for IOS XR 5.1.1 on the ASR 9000 say that the FIB is updated
independently of the prefixes, for core and edge failures alike, with or without MPLS.

PIC Core covers a failure inside the core that changes the IGP path to a BGP next hop. The next hop is still
reachable, so only the one shared IGP entry changes, and every BGP route that points to it moves to the new path at
once. No backup BGP path is needed.

"BGP PIC for RIB and FIB" in the ASR 9000 guide (26.x) has "Recursive PIC activation at third level and beyond, on
failure trigger at the first (IGP) level": a failure at the first (IGP) level triggers PIC at the third level of
recursion and beyond.

The current IOS XR configuration guides, however, do not define "PIC Core" as a feature of its own, and they do not say
whether it is on by default. The name appears separately in places such as the BGP-LU section of the Cisco 8000 BGP
guide (7.2.x), which lists PIC core as supported and PIC edge as not. This page says nothing about a default for PIC
Core on IOS XR either.

PIC Edge covers the loss of the BGP next hop itself: the egress PE fails, or the line between the egress PE and the
neighboring AS is cut. No change of IGP path reaches it, so a second BGP path with another next hop must be computed
in advance and placed in the forwarding table. On IOS XR, that is `set path-selection backup 1 install`.

The ASR 9000 guides (24.x, 26.x) give its purpose as "install a backup path into the forwarding table and provide
prefix independent convergence (PIC) in case of a PE-CE link failure". At most one backup path goes into the RIB and
CEF (TAC tech note 217097).

On IOS XE, PIC Core is on by default; `cef table output-chain build favor memory-utilization` turns it off, and
`cef table output-chain build favor convergence-speed` turns it back on. PIC Edge is `bgp additional-paths install`,
and it works only while PIC Core is on (the BGP guide for IOS XE 17.1 on the ASR 900). This was not tried on IOL.

On this board, each PE has one line to P1. Task M6-6 cuts a core link (P1–PE2), but there is no other way to PE2, so
from PE1 the next hop PE2 itself disappears. What works is PIC Edge. With no second path in the core, changing paths
inside the core is not an option that ever comes up.

## 3. How IOS XRd and IOS XRv 9000 differ

Of the XR routers in this lab, only PE1 runs IOS XRv 9000; PE2, PE3, P1 and RR1 run IOS XRd. The BGP configuration
commands were the same on both: every `?` list for the BGP commands (ADD-PATH, PIC, GTSM, authentication, limits,
dampening, aggregation) matched, and so did the defaults with nothing configured (section 5.1). What differed was how
a failure is noticed, and how long the PIC switchover takes.

Stopping a link in CML does not bring the XRd interface down. IS-IS keeps the adjacency until its 30-second hold time,
and a link stopped for 15 seconds and started again never drops the adjacency at all (IOS XRv 9000 interfaces do not
go down on a CML link stop either; M10, section 3). On top of that, XRd creates no IS-IS BFD session:
`show bfd session` is empty, and the BFD column of the adjacency table stays at `Init`. BFD works on XRv 9000 (M7).

That is why the Check of task M6-6 does not stop a link but shuts down P1's interface toward PE2. When the interface
goes down, P1's IS-IS drops the adjacency at once, so what is measured is how fast the IGP spreads the news that PE2 is
gone, and how each PE reacts.

How long the PIC switchover took depended on the platform of the ingress PE. The comparison board had two ingress PEs
(one on XRd, and one on XRv 9000 like the lab's PE1), and PE2 was cut off from P1 with the same configuration. The XRv
9000 ingress lost 0.18 and 0.15 seconds, the XRd ingress 2.96, 3.02 and 3.01 seconds. With the backup handed out by
ADD-PATH (the lab's form), it was 0.18 seconds on XRv 9000 and 3.01 seconds on XRd.

On the XRd ingress too, `show bgp`, `show route … detail` and `show cef … detail` showed the backup path in the same
form as on XRv 9000. The outage stayed at about 3 seconds even with the ingress's BGP next-hop tracking delay set to
10 seconds, so the ingress was not waiting for BGP either. What sets the 3 seconds on an XRd ingress was not isolated.

XRd routers did switch to a backup elsewhere. The backup exit PE3 (XRd) switched to its directly connected eBGP
backup, and the 0.18 seconds of the XRv 9000 ingress depend on it.

In the displays, the two platforms differed in the `LW-LDI` line of `show cef … detail`. Excerpts from the lab's PE1
(XRv 9000) and PE3 (XRd), with their backups installed:

```console
RP/0/RP0/CPU0:PE1#show cef 203.0.113.0/24 detail
...
  LW-LDI[type=3, refc=1, ptr=0xf92ee58, sh-ldi=0xf86ad50]
...
   via 10.255.0.2/32, 3 dependencies, recursive [flags 0x6000]
...
   via 10.255.0.3/32, 2 dependencies, recursive, backup [flags 0x6100]
```

```console
RP/0/RP0/CPU0:PE3#show cef 203.0.113.0/24 detail
...
  LW-LDI[type=0, refc=0, ptr=0x0, sh-ldi=0x0]
...
   via 10.255.0.2/32, 2 dependencies, recursive [flags 0x6000]
...
   via 172.16.3.1/32, 2 dependencies, recursive, bgp-ext, backup [flags 0x6120]
```

XRv 9000 shows `type=3` and pointers; XRd shows `type=0` and zeros. On XRd the line was the same on every route
looked at (the XRd ingress of the comparison board, and PE2 and PE3 with their backups). The display splits the same
way as the switchover times, but this line was not shown to be the cause: PE3 switched to its directly connected backup
with `type=0`. Both displays carry the backup; what differs is how long the traffic takes to come back.

The lab makes only the ingress PE1, where the PIC switchover is measured on the traffic, an IOS XRv 9000, and runs the
other XR routers on XRd.

## 4. Routes that do not make it into the RIB, and bgp suppress-inactive

A BGP best path can lose in the RIB to another route with a lower administrative distance. With a static route for
10.199.9.0/24 on PE2 (to Null0, distance 1), the BGP path learned from X1 (eBGP, 20) does not make it into the RIB.

IOS XR advertises the route anyway. In the BGP table it stays `*>`: the legend lists `r RIB-failure`, but no `r`
appears. PE2 advertises the route to RR1, where it became the best path as well (an excerpt from PE2):

```console
RP/0/RP0/CPU0:PE2#show route 10.199.9.0/24

Routing entry for 10.199.9.0/24
  Known via "static", distance 1, metric 0 (connected)
...
    directly connected, via Null0
...
RP/0/RP0/CPU0:PE2#show bgp
...
Status codes: s suppressed, d damped, h history, * valid, > best
              i - internal, r RIB-failure, S stale, N Nexthop-discard
Origin codes: i - IGP, e - EGP, ? - incomplete
   Network            Next Hop            Metric LocPrf Weight Path
* i10.199.9.0/24      10.255.0.3                    100      0 65100 i
*>                    172.16.2.1               0    200      0 65100 i
...
RP/0/RP0/CPU0:PE2#show bgp neighbor 10.255.0.21 advertised-routes
Network            Next Hop        From            AS Path
10.199.9.0/24      10.255.0.2      172.16.2.1      65100i
203.0.113.0/24     10.255.0.2      172.16.2.1      65100i
```

The IOS XR documents do not say whether routes that fail to enter the RIB are advertised. There is no command matching
`bgp suppress-inactive` either: neither `bgp ?` under `router bgp` nor `bgp ?` under the address family offers one. A
flag in the legend is not a promise that it will appear in the table.

IOS XE shows it differently. With the same setup on X2 (a static route for 10.199.9.0/24 to Null0), the path learned
from X1 over iBGP carries `RIB-failure(17)`, `show ip bgp rib-failure` gives the reason as `Higher admin distance`,
and the list of advertised routes shows `r>i`. It is advertised all the same.

```console
X2#show ip bgp rib-failure
  Network            Next Hop                      RIB-failure   RIB-NH Matches
10.199.9.0/24      10.100.255.1        Higher admin distance              n/a
X2#show ip bgp neighbors 172.16.3.254 advertised-routes
...
     Network          Next Hop            Metric LocPrf Weight Path
 r>i  10.199.9.0/24    10.100.255.1             0    100      0 i
 *>   203.0.113.0      10.100.23.3             11         32768 i
```

TAC tech note 213286 says that IOS still advertises routes in RIB-failure, and the IOS XE 17.x guide says that
`bgp suppress-inactive` under the address family makes BGP stop advertising such inactive routes to any BGP neighbor.
The TAC note adds that only the RIB-failure routes whose BGP next hop differs from the next hop of the same entry in
the RIB are suppressed.

On X2 with IOL 17.15, after `bgp suppress-inactive`, 10.199.9.0/24 was still advertised, both after
`clear ip bgp 172.16.3.254 soft out` and after the session was reset with `clear ip bgp 172.16.3.254`.

```console
X2#show running-config | section router bgp
router bgp 65100
...
 address-family ipv4
  bgp suppress-inactive
...
X2#show ip bgp rib-failure
  Network            Next Hop                      RIB-failure   RIB-NH Matches
10.199.9.0/24      10.100.255.1        Higher admin distance              Yes
X2#clear ip bgp 172.16.3.254
X2#show ip bgp neighbors 172.16.3.254 advertised-routes
...
     Network          Next Hop            Metric LocPrf Weight Path
 r>i  10.199.9.0/24    10.100.255.1             0    100      0 i
 *>   203.0.113.0      10.100.23.3             11         32768 i
```

Once the command was in, the `RIB-NH Matches` column changed from `n/a` to `Yes`. Read by its name, the router treated
the next hop as matching the RIB entry (Null0), which would put the route outside the TAC note's case. Why it shows `Yes`
was not checked. This is recorded as a disagreement between the documents and the device (section 6.1) and is not used
to decide whether a task is right.

The phrase "BGP prefix suppression" in SPCOR 1.5.c does not appear in the Cisco documents. This supplement treats it as
the three features of the page "Not taking too much" (prefix limits, dampening and aggregation), and mentions
`bgp suppress-inactive` here only as an IOS XE feature with a similar name.

## 5. Defaults and commands side by side (IOS XR and IOS XE)

The values and forms below are what was checked on IOS XRd 26.1.1 for IOS XR (the defaults and `?` lists are the same
on IOS XRv 9000 26.1.1) and on IOL 17.15 for IOS XE, together with what the documents state. A "—" in the IOS XE column means it was not
checked in this supplement and is not in the documents consulted.

### 5.1 Defaults

| Item | IOS XR | IOS XE | Where it is stated |
|---|---|---|---|
| ADD-PATH capability | Not negotiated (`Additional-paths operation: None`) | — | Routing Command Reference for the ASR 9000; devices |
| Paths advertised per route with ADD-PATH | Up to 32 (33 to 96 with `additional-paths advertise-limit`) | — | NCS 5500 BGP guide (25.x); devices (`default 32` in `?`) |
| Installing a backup path (PIC Edge) | Done by `install` in the selection policy | Done by `bgp additional-paths install` | ASR 9000 guides (24.x, 26.x); IOS XE 17.1 guide for the ASR 900 |
| PIC Core | No definition and no default in the documents (section 2) | On | IOS XE 17.1 guide for the ASR 900 |
| Next-hop tracking delay (other than VPNv4/VPNv6) | Critical 3000 ms, non-critical 10000 ms | — | ASR 9000 and Cisco 8000 command references; devices (`show bgp nexthops`) |
| Next-hop tracking delay (VPNv4/VPNv6) | Critical 50 ms (since 7.10.1; 0 ms before), non-critical 10000 ms | — | ASR 9000 command reference |
| fast-external-fallover | On: directly connected eBGP neighbors show `Fast fallover is enabled`, iBGP neighbors `Fast fallover is not enabled` | — | ASR 9000 command reference; devices |
| GTSM | Off | — | ASR 9000 command reference |
| Prefix limit | No limit line (`Maximum prefixes allowed`) in the display of a neighbor without one; the documents disagree (section 6.2) | — | Devices |
| Prefix limit warning | At 75 % of the limit | — | ASR 9000 and Cisco 8000 command references |
| When the limit is exceeded | Sends a Cease and tears the session down; `Idle (PfxCt)` until `clear bgp` or the `restart` time | — | The same; devices |
| Dampening | Off. Half-life 15 minutes, reuse 750, suppress 2000, maximum suppress time four times the half-life (60 minutes) | — | ASR 9000 command reference; devices (`half life 00:15:00, suppress value 2000, reuse value 750`, `Maximum suppress time 01:00:00`) |
| Dampening penalty | 1000 per flap, cumulative; a neighbor reset adds none | — | ASR 9000 guide (26.x), "Route Dampening" |
| ATOMIC_AGGREGATE on an aggregate | Set unless `as-set` is given | — | ASR 9000 command reference; devices (`aggregated, atomic-aggregate`) |
| A BGP route that does not make it into the RIB | Advertised; stays `*>` in the table | Advertised (`r>i`); the documents say `bgp suppress-inactive` stops it | Devices; TAC 213286, IOS XE 17.x guide |

### 5.2 Configuration

In the IOS XR column, "address family" means `router bgp` → `address-family ipv4 unicast`, "neighbor" means `router bgp` →
`neighbor <address>`, and "neighbor address family" means the `address-family ipv4 unicast` under it. `route-policy`, `key chain`
and `tcp ao`, where no place is given, are global configuration. In the IOS XE column, everything except the
`key chain` and `cef` rows goes under `router bgp`.

| To do | IOS XR | IOS XE |
|---|---|---|
| Capability to send and receive additional paths | `additional-paths send` and `additional-paths receive` in the address family (all iBGP neighbors; per neighbor with `capability additional-paths …`). The capability is negotiated in the OPEN, so it takes effect only after the session is reset (RFC 7911) | — |
| Which paths to advertise or install | `set path-selection backup 1 advertise` (advertise), `… install` (into the forwarding table), `… advertise install` (both) in a `route-policy`, attached with `additional-paths selection route-policy <name>` in the address family | — |
| Backup path into the forwarding table (PIC Edge) | The `install` above | `bgp additional-paths install` (while PIC Core is on) |
| Turn PIC Core off and on | (Not described in the documents) | `cef table output-chain build favor memory-utilization`, `cef table output-chain build favor convergence-speed` |
| best-external | `advertise best-external` in the address family (in the documents: VRF, VPNv4/VPNv6, labelled unicast and others) | — |
| Next-hop tracking delay | `nexthop trigger-delay {critical \| non-critical} <ms>` in the address family | — |
| Turn fast-external-fallover off | `bgp fast-external-fallover disable` under `router bgp` | — |
| GTSM | `ttl-security` on the neighbor (no hop count; accepts TTL 255 only, and sends 255) | `neighbor <address> ttl-security hops <1-254>` (accepts 255 − hops and above) |
| GTSM and `ebgp-multihop` | Both can be configured (the documents say `ttl-security` wins) | Not together (`Remove ttl-security before configuring ebgp-multihop`) |
| MD5 authentication | `password {clear \| encrypted} <string>` on the neighbor | `neighbor <address> password <string>` |
| Key chain authentication | `keychain <name>` on the neighbor (a method other than RFC 2385 MD5; does not connect to an IOS XE `password`) | — |
| TCP-AO key | `key chain <name>` → `key <ID>` → `key-string clear <key>`, `cryptographic-algorithm AES-128-CMAC-96`, `send-lifetime`, `accept-lifetime` | `key chain <name> tcp` → `key <ID>` → `key-string <key>` (32 or 64 hexadecimal digits), `cryptographic-algorithm aes-128-cmac`, `send-id`, `recv-id` |
| TCP-AO SendID and ReceiveID | `tcp ao` → `keychain <name>` → `key <ID> SendID <n> ReceiveID <n>` | `send-id` and `recv-id` under the key above |
| TCP-AO on the neighbor | `ao <name> include-tcp-options enable` on the neighbor | `neighbor <address> ao <name> include-tcp-options` |
| Two methods on one neighbor | Refused at commit (`Password and Keychain/AO based authentication together`) | One or the other (MD5 or TCP-AO) |
| Prefix limit | `maximum-prefix <limit> [<threshold %>] [discard-extra-paths] [warning-only] [restart <minutes>]` in the neighbor address family | `neighbor <address> maximum-prefix <limit> [<threshold>] [restart <minutes>] [warning-only]` (IOS XE 17.x guide "Configuring a Basic BGP Network"; not tried on a device) |
| Dampening | `bgp dampening [<half-life> [<reuse> <suppress> <max-suppress-time>]]` in the address family, or `bgp dampening route-policy <name>` (`set dampening` in the policy) | — |
| Aggregation | `aggregate-address <prefix/length> [as-set] [summary-only] [route-policy <name>]` in the address family | `aggregate-address <address> <mask> [as-set] [summary-only] [suppress-map <name>]` (same guide; not tried on a device) |
| Suppress only some of the more specific routes | `suppress-route` in the aggregate's `route-policy` | `suppress-map` |
| Still send suppressed routes to some neighbors | `unsuppress-route` in the neighbor's outbound `route-policy` | `unsuppress-map` |
| Do not advertise routes that are not in the RIB | (No equivalent) | `bgp suppress-inactive` under the address family |

The IOS XE `suppress-map` and `unsuppress-map` come from the section "Suppressing and Unsuppressing the Advertisement
of Aggregated Routes Using BGP" of the IOS XE 17.x guide and were not tried in this supplement. IOS XR has neither
command.

### 5.3 Show and clear

| To do | IOS XR | IOS XE |
|---|---|---|
| See the next-hop tracking delay | `show bgp nexthops` | — |
| See the backup path | `show bgp <prefix>` (`backup, add-path`), `show route <prefix> detail` (`BGP backup path`), `show cef <prefix> detail` (`backup`) | — |
| See the ADD-PATH negotiation | `show bgp neighbor <address>` (`Additional-paths operation: …`) | — |
| See GTSM | `show bgp neighbor <address>` (`TTL security is configured`) | `show ip bgp neighbors <address>` (`Mininum incoming TTL 254, Outgoing TTL 255`) |
| See the authentication | `show tcp authentication keychain <name>` (TCP-AO) | `show ip bgp neighbors <address>` (`md5` or `TCP AO` in `Option Flags`) |
| See the prefix limit | `show bgp neighbor <address>` (`Maximum prefixes allowed …`, `Threshold for warning message …`) | — |
| A neighbor over its prefix limit | `show bgp summary` (`Idle (PfxCt)`) | — |
| See dampening | `show bgp dampened-paths`, `show bgp flap-statistics`, `show bgp <prefix>` (`Dampinfo`) | — |
| Routes suppressed by an aggregate | `show bgp` (`s` at the start of the line), `show bgp <prefix>` (`Advertisements of this net are suppressed by an aggregate.`) | — |
| Routes not in the RIB | (No flag appears) | `show ip bgp rib-failure` |
| Reset the session | `clear bgp <address>` | `clear ip bgp <address>` |
| Send the updates again only | `clear bgp ipv4 unicast <address> soft` (`clear bgp ipv4 unicast <address>` needs `soft` or `long-lived-stale` after it and cannot reset the session by itself) | `clear ip bgp <address> soft out` |
| Clear dampening | `clear bgp ipv4 unicast dampening [<prefix>]` | — |

## 6. Where the documents and the devices disagreed

Where a document and a device disagree, the pages of this supplement describe what the device did and name the
document. "Device" means IOS XRd 26.1.1 and IOS XRv 9000 26.1.1 for IOS XR, and IOL 17.15 for IOS XE.

### 6.1 Where the devices behaved differently from the documents

- **best-external on plain IPv4 unicast.** The Routing Command Reference for the ASR 9000 says that unlabelled
  best-external is not supported (it may create a loop), and plain IPv4 unicast is not among its modes. Both virtual
  routers accept it at commit, and it takes effect (section 1). Task M6-5 rules out best-external, and the backup path
  is handed out with ADD-PATH.
- **GTSM on one side only.** The same Command Reference says that with the command on one side only, the session
  progresses as far as OpenSent or OpenConfirm and goes down when the hold time expires. With `ttl-security` on PE2
  (IOS XR) only, not even the TCP connection came up, and X1 stayed `Idle` (`… due to Active open failed`). X1 was
  sending with TTL 1 (capture), and PE2 accepts TTL 255 only. Task M6-7 asks for the state with both sides
  configured and the session up.
- **The TTL that IOS XE GTSM sends.** The IOS XE 17.x guide says that `ttl-security hops` secures the incoming
  direction only and has no effect on outgoing packets. RFC 5082 (section 3) says the TTL of sent packets MUST be 255.
  X1 shows `Outgoing TTL 255`, and in the capture X1's TTL went from 1 before the command to 255 after it. This
  supplement follows the RFC and the device, and the Check of task M6-7 reads this display as well.
- **`bgp suppress-inactive` on IOS XE.** The IOS XE guide and TAC 213286 say that it stops the advertisement of
  routes that are not in the RIB. IOL 17.15 kept advertising after a soft out and after a session reset (section 4).
- **PIC on IOS XRd.** This is less a disagreement with the documents than behaviour they do not cover. An XRd ingress
  PE showed the backup path, yet lost about 3 seconds when PE2 disappeared (section 3). A lab that shows the PIC
  switchover on the traffic uses an IOS XRv 9000 ingress.

### 6.2 Where the documents disagree with each other

- **The default prefix limit.** The Routing Command Reference for the ASR 9000 lists per-address-family defaults
  (1048576 for IPv4 unicast and so on) and, in the history of the same entry, says that 7.3.1 removed the default and
  the value must be configured. "BGP Default Limits" in the NCS 5500 BGP guide (25.x) gives 512K (IPv4 unicast), 128K
  (IPv6 unicast) and 512K (VPNv4 unicast).
- **The sample outputs for the prefix limit.** The ASR 9000 guide (26.x) shows `Maximum prefixes allowed 1048576`,
  the Command Reference shows `maximum limit 524288`, and the Cisco 8000 BGP Command Reference lists no defaults. The
  26.1.1 devices show no limit line for a neighbor without `maximum-prefix`. This supplement always configures the
  limit and does not rely on a default.
- **Key chain algorithms for BGP.** The Routing Command Reference (`keychain`) says that BGP supports only HMAC-MD5 and
  HMAC-SHA1-12; the System Security Command Reference also lists AES-128-CMAC-96 and HMAC-SHA1-96. On the devices, a
  BGP session with TCP-AO using an AES-128-CMAC-96 key chain came up (task M6-8).
- **Keywords missing from the syntax lines.** The Routing Command Reference's syntax for `set path-selection` has no
  `multipath`, which the NCS 5500 guide and TAC 217097 use. Its syntax for `maximum-prefix` has no
  `discard-extra-paths`, which the Cisco 8000 Command Reference and the ASR 9000 guide have. The devices' `?` lists
  both.
- **TCP-AO spellings.** The IOS XR documents have `accept-ao-mismatch-connection` (System Security Command Reference
  and a guide example), `accept-ao-mismatch-connections` (a guide syntax template) and "accept-non-ao-connections" (a
  guide's text). This was not tried on the devices.
- **The form of a `tcp ao` key.** There are two: `key 1 SendID 5 ReceiveID 5` (Command Reference) and
  `key-id <id> send_id … receive_id …` (a guide syntax template). On the devices, the form
  `key <ID> SendID <n> ReceiveID <n>` was accepted.
- **How a TCP-AO key is written.** The IOS XE guide requires 32 or 64 hexadecimal digits, while the IOS XR guide's
  example uses a string like `keys1`. Task M6-8 uses the same 32-digit hexadecimal key on both sides.
- **`password inheritance-disable`.** The ASR 9000 and Cisco 8000 command references have only `password-disable`.
  The devices' `password ?` lists `inheritance-disable`, and the neighbor's `?` shows `password-disable` as
  "(Deprecated from 7.4.1) Replaced by password inheritance-disable".

None of these points is used to decide whether a paper question is right. The lab tasks are built in a form that
avoids the disputed features (ADD-PATH instead of best-external, a configured limit instead of a default), and the
Checks look at what the devices did (sessions up, routes received, the length of an outage, the devices' displays).

:::note
Sources: RFC 7911 (sections 4 and 5), RFC 5082 (sections 2 and 3), RFC 5925 and RFC 2385. Cisco: the Routing Command
Reference for the ASR 9000 (2026-09-08); the BGP Command Reference for the Cisco 8000 (2026-09-11); the BGP
Configuration Guide for the NCS 5500 (IOS XR 25.1.x–25.4.x); the Routing Configuration Guide for the ASR 9000 ("Implementing
BGP" for IOS XR 24.1.x–24.4.x and 26.1.x–26.3.x, "Implementing Routing Policy" for 24.x); "Keychain Management
Commands" in the System Security Command Reference for the ASR 9000; the BGP Configuration Guide for the Cisco 8000
(IOS XR 7.2.x); the release notes for IOS XR 5.1.1 on the ASR 9000; TAC tech notes 217097 "Configure and Verify BGP
Path Selection in IOS-XR" and 213286 "Understand BGP RIB-Failure and BGP Suppress-Inactive Command"; the IP Routing
Configuration Guide for IOS XE 17.x ("Configuring BGP Neighbor Session Options", "BGP Support for TCP Authentication
Option", "Configuring a Basic BGP Network"); the BGP Configuration Guide for IOS XE 17.1 on the ASR 900 ("BGP PIC Edge
for IP and MPLS-VPN"). The SPCOR (350-501) blueprint. All checked in November 2026. Measured on 2026-11-21: on lab
XRT-17 (PE1 on IOS XRv 9000 26.1.1; PE2, PE3, P1 and RR1 on IOS XRd 26.1.1; CE1, X1, X2 and T on IOL 17.15), the
`LW-LDI` lines of section 3 and the TCP-AO key and `tcp ao` key of section 6.2; on the same board with PE1 on IOS XRd
26.1.1 and a second ingress PE (IOS XRv 9000 26.1.1) with its own customer added, the best-external and outage times
of section 1, the link stop, switchover times and XRd `LW-LDI` line of section 3, section 4, the values, displays and
`?` lists checked on the devices in section 5, and the GTSM and `bgp suppress-inactive` behaviour of section 6.1.
Outages were counted with IP SLA udp-jitter from a CE to T (203.0.113.1), every 10 ms, one way, and the failure was a
shutdown of P1's interface toward PE2.
:::
