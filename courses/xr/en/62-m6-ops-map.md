# M6 supplement — The parts of BGP operations and how they fit

This supplement is about the operational side of BGP: handing out a backup path in advance, protecting the sessions
with other ASes, and limiting what you accept. In the CCNP Service Provider blueprint (SPCOR) it covers 2.4.g,
additional paths, and 2.4.h, PIC, under 2.4, implementing BGP; and 1.5.b, BGP TTL security and protocol
authentication, and 1.5.c, BGP prefix suppression, under 1.5, control plane security.

M6 covered how BGP is put together on IOS XR: the address family hierarchy, iBGP between loopbacks and
next-hop-self, route policies, templates, and how to read paths. The prefix limit (`maximum-prefix`) appeared only in
a template example and in the table of commands. This supplement builds on that and looks at what happens when
something breaks, and when something unwanted arrives from outside.

No Cisco document defines the term in 1.5.c, so this supplement takes it to mean three things: the prefix limit,
dampening, and the suppression of more specific routes by aggregation (IOS XE's `bgp suppress-inactive` is in the
appendix). The supplement has three pages and an appendix.

| Page | Contents | Tasks |
|---|---|---|
| This page | One picture of the backup path arriving and of the moment PE2 fails, the three questions it answers, the words and the parts, where each part is configured | — |
| Handing out a backup path: ADD-PATH and PIC | Why a route reflector reflects only the best path; ADD-PATH and path IDs; PIC, which puts the backup path into CEF; the backup exit in a network without VPN labels | M6-5, M6-6 |
| Protecting the session: GTSM and TCP-AO | GTSM, which tells a neighbor by its TTL; MD5 authentication; key chains and TCP-AO; working with IOS XE | M6-7, M6-8 |
| Not taking too much: prefix limits, dampening and aggregation | maximum-prefix and what happens past the limit; dampening, its penalty and half-life; aggregation with summary-only and suppress-route | M6-9, M6-10 |
| Appendix | best-external and VPNs; PIC Core and PIC Edge; IOS XRd and IOS XRv 9000 compared; IOS XE's `bgp suppress-inactive`; defaults and commands side by side; where the official documents and the devices disagree | — |

The lab is XRT-17. A provider, AS 65000, carries packets from a customer, CE1 (AS 65001), to a destination T
(203.0.113.1) inside AS 65100. There are two exits to AS 65100: PE2, connected to X1, and PE3, connected to X2. PE1
runs IOS XRv 9000 26.1.1; PE2, PE3, P1 and RR1 run IOS XRd 26.1.1. CE1, X1, X2 and T run IOS XE 17.15 (IOL).

The five routers of AS 65000 run IS-IS (instance `CORE`, level 2), and LDP runs on the core links. P1 does not run
BGP. PE1, PE2 and PE3 are clients of RR1, a dedicated route reflector placed off the forwarding path. PE2 sets the
local preference of the routes it learns from X1 to 200, so PE2 is the primary exit and PE3 the backup exit.

:::topo
nodes:
  CE1: [0, 1]
  PE1: [1.4, 1]
  P1: [2.8, 1]
  RR1: [2.8, 2.35]
  PE2: [4.2, 0]
  PE3: [4.2, 2]
  X1: [5.75, 0]
  X2: [5.75, 2]
  T: {at: [7.05, 1], kind: host, label: "T 203.0.113.1"}
links:
  - [PE1, P1, "CORE-1\n10.0.1.0/24"]
  - [PE2, P1, "CORE-2\n10.0.2.0/24"]
  - [PE3, P1, "CORE-3\n10.0.3.0/24"]
  - [RR1, P1, "RR\n10.0.21.0/24"]
  - [PE1, CE1, "CUSTOMER\n172.16.1.0/24"]
  - [PE2, X1, "UPSTREAM-1\n172.16.2.0/24"]
  - [PE3, X2, "UPSTREAM-2\n172.16.3.0/24"]
  - [X1, T, "AS65100-1\n10.100.13.0/24"]
  - [X2, T, "AS65100-2\n10.100.23.0/24"]
  - [X1, X2, "AS65100-12\n10.100.12.0/24"]
frames:
  - {label: "AS 65001", nodes: [CE1]}
  - {label: "AS 65000", nodes: [PE1, P1, RR1, PE2, PE3]}
  - {label: "AS 65100", nodes: [X1, X2, T]}
:::

PE1 alone runs IOS XRv 9000 so that the PIC switch can be checked with traffic. An IOS XRd ingress shows the backup path
in CEF correctly, but on this virtual router it did not use that backup when a remote PE disappeared from the IGP; it
waited for BGP (see the appendix).

The operational features bring in many words at once: ADD-PATH, path ID, PIC, best-external, GTSM, TCP-AO, key chain,
dampening. On this board, though, only two things happen. The backup exit's path reaches PE1 at the entry and is
used at once when PE2 fails; and each of the three sessions with the outside is protected. This page follows both in
one picture (section 2.1), answers three questions (section 2.2), and only then lines up the words.

## 1. What it is good for

### 1.1 The problem: two exits, three sessions with the outside

Packets from CE1 to T normally go PE1 → P1 → PE2 → X1. The prefix 203.0.113.0/24 arrives from both X1 and X2, but PE2
sets the local preference of X1's route to 200, so every router in AS 65000 takes the path through PE2 as best.

PE3 also learns the route from X2, but PE3's own best path is the iBGP path through PE2 that RR1 sent it. BGP
advertises only its best path, so PE3 does not send X2's route to RR1. RR1, too, reflects only its one best path, so
PE1 knows only the path through PE2. There is a backup exit, and only PE3 knows the way to it.

When PE2 fails, PE1 can only wait for BGP to choose again. PE3 gives up on PE2's path, makes X2's route its best,
advertises it to RR1, RR1 reflects it to PE1, and only then does PE1 have a new path. Meanwhile, packets from CE1 to
T are dropped for about 3 seconds. Every step follows the specification; they just take their turns.

There are three eBGP sessions with other ASes: CE1 and PE1, X1 and PE2, X2 and PE3. A customer may misconfigure its
router and send a flood of routes; the route of X1's own customer (198.51.100.0/24) may keep disappearing and coming
back. A BGP session runs over TCP, so forged packets aimed at the session can arrive too. Nothing in the M6
configuration guards against any of this.

### 1.2 What this supplement adds

It adds three groups of features.

- **Handing out a backup path** (2.4.g, 2.4.h). With additional paths (ADD-PATH), PE3's route through X2 reaches RR1
  and PE1 as a second path, next to the best one. With PIC, PE1 keeps that path as a backup in its forwarding table
  and uses it the moment PE2 disappears. The gap when PE2 fails becomes shorter than one second.
- **Protecting the session** (1.5.b). GTSM (TTL security) uses the TTL of arriving packets to drop those sent from far
  away. TCP-AO (or MD5 authentication) checks each TCP segment with a key and drops segments made by anyone who does
  not know the key.
- **Not taking too much** (1.5.c). maximum-prefix (the prefix limit) sets how many routes one neighbor may send.
  Dampening leaves a route that keeps flapping unused for a while. Aggregation sums the customer's addresses up into
  one route and keeps the more specific routes inside.

Neither ADD-PATH nor PIC changes the best path. The path through PE2 stays best; the path through PE3 just waits on
the bench.

## 2. On the board

### 2.1 The picture: how the backup path arrives, and the moment PE2 fails

The circled numbers give the order in which the backup path for 203.0.113.0/24 reaches PE1 (① to ③), the order of
events when PE2 fails (④ to ⑥), and the three sessions with the outside and what protects them (⑦ to ⑨). The iBGP
sessions run between loopbacks, so the routes in ① and ② pass through P1, but P1 does not speak BGP; it only carries
them as packets.

:::topo
nodes:
  CE1: [0, 1]
  PE1: {at: [1.5, 1], label: "PE1 (ingress)"}
  P1: {at: [3.15, 1], label: "P1 (no BGP)"}
  RR1: {at: [3.15, 2.4], label: "RR1 (RR)"}
  PE2: {at: [4.65, 0], label: "PE2 (primary)"}
  PE3: {at: [4.65, 2], label: "PE3 (backup)"}
  X1: [6.25, 0]
  X2: [6.25, 2]
  T: {at: [7.45, 1], kind: host, label: "T"}
links:
  - [CE1, PE1, "⑦ prefix\nlimit"]
  - [PE1, P1, "③ gets both\n⑤ uses backup"]
  - [P1, PE2, "④ fails"]
  - [P1, PE3, "① sends the backup\n⑤ new path"]
  - [P1, RR1, "② reflects both"]
  - [PE2, X1, "⑧ GTSM\ndampening\naggregation"]
  - [PE3, X2, "⑥ new path\n⑨ TCP-AO,\naggregation"]
  - [X1, T, ""]
  - [X2, T, "⑥"]
  - [X1, X2, ""]
:::

How the backup path arrives:

- ① PE3 sends 203.0.113.0/24, learned from X2, to RR1 as a backup path. It is configured to send additional paths,
  and the route policy that picks the paths to send says to advertise one backup path besides the best. The path
  carries a path ID, so the receiver treats it as a second path for the same prefix.
- ② RR1 is configured to receive and to send additional paths. It reflects both paths, the best from PE2 and the
  backup from PE3, each with its path ID, to PE1.
- ③ PE1 is configured to receive additional paths, takes both, and installs the backup in the RIB and CEF next to the
  best (PIC). The best path is still the one through PE2.

The moment PE2 fails:

- ④ The link between PE2 and P1 goes down. IS-IS removes PE2's loopback, 10.255.0.2/32, from the routing table.
- ⑤ As soon as PE1's CEF can no longer resolve the best path's next hop (10.255.0.2), it switches to the installed
  backup (next hop 10.255.0.3). It does not wait for BGP to choose again.
- ⑥ The packets reach PE3 as plain IP packets without a VPN label, and PE3 looks up 203.0.113.0/24 in its own table.
  PE3's best path is still the iBGP path through PE2, so PE3, too, needs its own eBGP path through X2 installed as a
  backup. If it is, PE3 switches at the same moment, and the packets reach T through X2. Preparing only the entry is
  not enough: if the exit's table is out of date, the packets are dropped there.

The three sessions with the outside:

- ⑦ CE1–PE1: PE1 limits the number of routes it accepts from CE1 (maximum-prefix). Past the limit, PE1 tears the
  session down.
- ⑧ PE2–X1: PE2 and X1 use GTSM, which sets the lowest TTL they accept. Both send with TTL 255, so a directly
  connected neighbor's packets arrive with 255, and packets from further away arrive with less. PE2 dampens the routes
  it learns from X1, and advertises the customer's addresses (192.168.0.0/22) to X1 as one aggregate.
- ⑨ PE3–X2: PE3 and X2 use TCP-AO: each TCP segment carries a MAC computed from a key, and the receiver checks it.
  PE3, too, advertises the customer's addresses to X2 as one aggregate.

### 2.2 Three questions

Each number in the picture answers one of three questions. The answers name the parts that the next pages configure.

**Who tells whom about the second path?** PE3 tells RR1, and RR1 tells PE1. ADD-PATH gives each path a path ID, so
that more than one path for a prefix can be sent. The capability has a direction: paths flow only where the sender
has announced send and the receiver has announced receive. PE3 only sends, PE1 only receives, and RR1 does both. A
route policy on the sending side decides what to send (page "Handing out a backup path").

**When PE2 disappears, who switches first?** The forwarding table (CEF). If a backup is installed, CEF uses it as
soon as IS-IS removes PE2's loopback. BGP is slower: even after it learns that the next hop is gone, it waits for the
next-hop tracking delay before choosing again. For IPv4 unicast the critical delay is 3 seconds by default (an
excerpt):

```console
RP/0/RP0/CPU0:PE1#show bgp nexthops
...
Gateway Address Family: IPv4 Unicast
...
Critical Trigger Delay: 3000msec
Non-critical Trigger Delay: 10000msec
```

Without a backup in CEF, PE1 keeps dropping packets for T until BGP has chosen again (those 3 seconds, plus the
advertisement from PE3 through RR1). With a backup on PE1 alone, the same wait happens on PE3 at ⑥, and the gap stays
at about 3 seconds. With a backup on PE3 as well, it drops to about 0.2 seconds (page "Handing out a backup path").

**What does each protection of the outside sessions stop?** The five protections look at different things and stop
different things.

| Protection | What it looks at | What it stops |
|---|---|---|
| GTSM | The TTL of arriving packets | Packets sent from far away (they arrive with a TTL below the minimum) |
| TCP-AO, MD5 authentication | A MAC or digest on each segment, computed from a key | Segments made by anyone who does not know the key (forged resets, for example) |
| maximum-prefix | The number of routes accepted from one neighbor | Routes beyond the set number; by default the whole session is torn down |
| Dampening | Each route's flaps (the penalty) | Routes that keep flapping: left unused, and not advertised, for a while |
| Aggregation (summary-only) | The routes inside the aggregate's range | The advertisement of the more specific routes |

The first two protect the session; the last three protect the routes. GTSM and TCP-AO are configured on both ends: with
GTSM on one end only, or with TCP-AO key IDs that do not match, the session does not come up. The last three work inside the router they are configured on (pages
"Protecting the session" and "Not taking too much").

## 3. Words and parts

These are the words that appear in the picture and the questions. The left column is how the next pages say it.

| Word | What it is |
|---|---|
| Additional paths (ADD-PATH) | A BGP extension that sends a neighbor more than the best path for a prefix (RFC 7911). The capability is exchanged in the OPEN message, per address family, with send and receive as separate directions |
| Path ID | The identifier given to each path sent with ADD-PATH. It lets the receiver tell apart different paths for the same prefix (`Received Path ID`, `Local Path ID`) |
| Backup path | The best of the paths left after removing all paths that share the best path's next hop. IOS XR computes it with `set path-selection backup 1` in a route policy |
| best-external | When a router's best path is an iBGP path, it advertises the best of its eBGP paths to its iBGP neighbors. Cisco documents it for the VPN, VRF and labelled-unicast address families, and says that without labels it may create a routing loop. Not used in this supplement (see the appendix) |
| PIC | Installing a backup path next to the best one in the forwarding table, and switching to it, whatever the number of prefixes, as soon as the best path's next hop becomes unusable. PIC Edge covers the failure of an exit PE or link, PIC Core a change of path inside the core; this supplement configures PIC Edge (the difference is in the appendix) |
| Next-hop tracking | BGP watching the IGP route to each next hop and running path selection again when it changes, after a delay (the trigger delay). The IOS XR default for IPv4 unicast is 3 seconds (critical) and 10 seconds (non-critical) |
| GTSM (TTL security) | Both ends send with TTL 255, and the receiver drops packets whose TTL is below a minimum (RFC 5082). It relies on the TTL dropping by 1 at each router |
| MD5 authentication | Adding to each TCP segment an MD5 digest computed from a shared password (RFC 2385). On IOS XR, `password` under the neighbor; on IOS XE, `neighbor … password` |
| TCP-AO | The TCP authentication option that replaces MD5 authentication (RFC 5925). It computes a MAC with a key and an algorithm from a key chain (such as AES-128-CMAC-96), and keys can be changed |
| Key chain | A list of keys. Each key has an ID, a key string, an algorithm and lifetimes |
| KeyID, SendID, ReceiveID | The KeyID is the key number a TCP-AO segment carries. The sender puts its SendID there, and the receiver looks it up as its own ReceiveID. Your SendID must match the neighbor's ReceiveID |
| maximum-prefix (the prefix limit) | The most routes accepted from one neighbor, and the threshold for a warning (75% by default). Past the limit, by default, the router sends a Cease notification and tears the session down |
| Route flap dampening | Adding a penalty to a route each time it flaps, and suppressing it (not using it, not advertising it) once the penalty passes a threshold (RFC 2439) |
| Penalty, half-life | The value that grows by 1000 with each flap, and the time it takes to fall by half (15 minutes by default) |
| suppress, reuse, max suppress time | The penalty at which suppression starts (2000 by default), the penalty at which it ends (750 by default), and the longest a route can stay suppressed (four times the half-life by default, 60 minutes) |
| Aggregation (`aggregate-address`) | While a route inside a range is in the BGP table, creating one route for the whole range and advertising it |
| summary-only, suppress-route | summary-only stops the advertisement of all the more specific routes. suppress-route, in the aggregate's route policy, stops only the routes it selects (it does the job of IOS's suppress-map) |
| atomic-aggregate | An attribute saying that aggregation lost information (such as AS paths) from the more specific routes. It is set on an aggregate without `as-set` |

## 4. Easy to mix up

- **Capabilities are exchanged only when a session comes up.** ADD-PATH send and receive are announced in the OPEN
  message, so adding the configuration does nothing to a session that is already up. To bring it up again, use
  `clear bgp <neighbor>`. `clear bgp ipv4 unicast <neighbor>` wants `soft` or `long-lived-stale` after it; on its own it
  answers `% Incomplete command.`
- **Send and receive are directions, per router.** Paths flow only where the sender has announced send and the
  receiver has announced receive. On this board PE3 sends, RR1 does both, and PE1 receives. Send only announces the
  capability; which paths to send is decided by the route policy under `additional-paths selection`.
- **Advertise and install.** After `set path-selection backup 1`, `advertise` sends the backup to neighbors, and
  `install` puts it into the router's own RIB and CEF. RR1 is off the forwarding path, so it only advertises; PE1 only
  installs; PE3 does both.
- **ADD-PATH and PIC sit on different planes.** ADD-PATH is a control-plane feature: it changes how many paths BGP
  sends a neighbor. PIC is a forwarding-plane feature: it changes what CEF holds in advance. PIC needs a path in the
  table to use as a backup, and on this board it is ADD-PATH that brings that path to PE1.
- **GTSM is written differently on each OS.** IOS XR's `ttl-security` takes no hop count and accepts TTL 255 only.
  IOS XE's `neighbor … ttl-security hops <n>` accepts 255−n and above (254 and above with `hops 1`). Both send with TTL
  255. The IOS XE documentation says the command has no effect on outgoing packets, but IOS XE 17.15 sends with 255.
- **On IOS XR, `keychain` under a neighbor is not MD5 authentication.** The IOS XR form of RFC 2385 MD5 authentication
  is `password` under the neighbor, and it works with IOS XE's `neighbor … password`. `keychain` under the neighbor is a
  different method and does not work with IOS XE's `password`. TCP-AO is `ao` under the neighbor. A neighbor can use
  only one of the three.
- **By default, maximum-prefix leaves the session down.** A session torn down for passing the limit stays down until
  `clear bgp <neighbor>`, unless `restart` is configured. `warning-only` only logs; `discard-extra-paths` keeps the
  session and drops the routes beyond the limit. The limit holds, and every route from that session is gone.
- **Dampening does not count peer resets.** The penalty grows with the flaps of a route; when routes disappear because
  the session with the neighbor was reset, no penalty is added. A suppressed route comes back when its penalty falls
  below the reuse value, when the max suppress time has passed, or with
  `clear bgp ipv4 unicast dampening`.
- **summary-only stops the more specific routes too.** `aggregate-address` alone advertises both the aggregate and the
  more specific routes. With `summary-only`, the more specific routes are advertised to no neighbor (`s` at the start of
  the line in `show bgp`). To stop only some of them, use `suppress-route` in the aggregate's route policy.

## 5. Where each part is configured

The configuration examples are on the pages that follow; this table only says which router, and where. The IOS XR
rows are under `router bgp 65000`, and the IOS XE rows under `router bgp 65100` (the key chains and IOS XR's
`tcp ao` are global).

| Part | Router | Where |
|---|---|---|
| Sending additional paths | PE3 | A `route-policy` (`set path-selection backup 1 …`), and `additional-paths send` and `additional-paths selection route-policy <name>` under `address-family ipv4 unicast` |
| Receiving and sending additional paths | RR1 | A `route-policy` (as above), and `additional-paths receive`, `additional-paths send` and `additional-paths selection route-policy <name>` under `address-family ipv4 unicast` |
| Receiving additional paths | PE1 | `additional-paths receive` under `address-family ipv4 unicast` |
| Installing the backup (PIC) | PE1, PE3 | A `route-policy` that includes `install`, attached with `additional-paths selection route-policy <name>` under `address-family ipv4 unicast` |
| GTSM | PE2 | `ttl-security` under `neighbor 172.16.2.1` |
| GTSM | X1 | `neighbor 172.16.2.254 ttl-security hops <n>` |
| TCP-AO | PE3 | Global `key chain <name>` → `key <ID>` (key string, algorithm, lifetimes); global `tcp ao` → `keychain <name>` → `key <ID> SendID <n> ReceiveID <n>`; `ao <name> include-tcp-options …` under `neighbor 172.16.3.1` |
| TCP-AO | X2 | Global `key chain <name> tcp` → `key <ID>` (`send-id`, `recv-id`, key string, algorithm); `neighbor 172.16.3.254 ao <name> …` |
| MD5 authentication (not used on this board) | — | On IOS XR, `password` under the neighbor; on IOS XE, `neighbor … password` |
| maximum-prefix | PE1 | `maximum-prefix <maximum> <threshold %> …` under `neighbor 172.16.1.1` → `address-family ipv4 unicast` |
| Dampening | PE2 | `bgp dampening …` under `address-family ipv4 unicast` |
| Aggregation | PE2, PE3 | `aggregate-address <prefix> …` under `address-family ipv4 unicast` |

On IOS XR, each BGP part goes into one of three levels inside `router bgp`. What protects the session sits directly
under the neighbor, the number of routes under the neighbor's address family, and ADD-PATH, PIC, dampening and
aggregation under the process's address family. That is the same rule as in M6: session settings directly under the
neighbor, route settings under an address family. The exceptions are the key chains and `tcp ao`, which are global,
and that is about all.

<p class="tolab"><a href="/_learn?id=XRT-17">Open lab XRT-17 in the workspace</a> — <a href="64-m6-practice-2.html">Tasks M6-5 and M6-6</a></p>

:::note
`show bgp nexthops` was taken on PE1 (IOS XRd 26.1.1) of a PoC board: the XRT-17 board plus PE4 (IOS XRv 9000 26.1.1)
and CE4. PE4 showed the same values. The gaps when PE2 fails were measured on the same PoC board by shutting down
P1's interface toward PE2 and timing the one-way traffic from a CE to T with IP SLA (every 10 ms): 2.5 to 3.3 seconds
with no protection, 3.0 to 3.5 seconds with PIC at the entry only, and 0.15 to 0.18 seconds with PIC on PE3 as well.
The last figure is for an IOS XRv 9000 entry; with an IOS XRd entry the gap stayed at about 3 seconds while CEF
showed the backup correctly. That `ttl-security hops 1` on IOS XE 17.15 (IOL) sends with TTL 255 was checked with a
packet capture. Where each part is configured was checked on XRT-17 (PE1 on IOS XRv 9000 26.1.1, the other XR routers
on IOS XRd 26.1.1) with the task values. Sources: RFC 7911 (ADD-PATH), RFC 5082 (GTSM), RFC 2385 (MD5), RFC 5925
(TCP-AO), RFC 2439 (dampening); the Routing Configuration Guide for Cisco ASR 9000 Series Routers (IOS XR 24.x and
26.x), "Implementing BGP" and "Implementing Routing Policy"; the Routing Command Reference for Cisco ASR 9000 Series
Routers; the BGP Configuration Guide for Cisco NCS 5500 (IOS XR 25.x); the System Security Command Reference for
Cisco ASR 9000, "Keychain Management Commands"; the IP Routing Configuration Guide (IOS XE 17.x), "Configuring BGP
Neighbor Session Options" and "BGP Support for TCP Authentication Option". All checked in November 2026.
:::
