# XR Track 07 — MPLS and LDP

This lab is the practice part of unit **M8 MPLS and LDP** of the XR track. Read the unit page
*M8 — MPLS and LDP* first, then work through the tasks here, in order. Each task builds on the previous one.

## Ground rules

- You configure **XR01 only**. RT01, RT02 and RT03 are fixed; do not change them. You may log in to them to look.
- No command examples are given. Each task states the behaviour that is required. Use the CLI help (`?`),
  the `show` commands, and the Cisco IOS XR configuration guides and command references to find the commands.
- The **Tasks** tab has a **Check** button for each task. It reads the live state of the devices.
  Leave configuration mode before you press it. LDP needs up to 15 seconds to notice a lost neighbour on a link,
  and IS-IS up to 30 seconds.
- Two Checks cause a fault for a moment and then undo it: the Check of M8-3 disables LDP on one interface of RT01,
  and the Check of M8-4 discards the packets on one link. Each takes one to two minutes. Do not change the
  configuration while it runs.
- Hints open one level at a time (keyword → where to look → command). Opened hints are logged.
- XR01 runs **IOS XRd** 26.1.1, the container form of IOS XR, as in the labs of M4 to M6. It switches labelled
  traffic like the other routers here.

## Topology

| Link | XR01 | Peer | Addressing | IS-IS metric |
|---|---|---|---|---|
| PRIMARY | GigabitEthernet0/0/0/0 | RT01 Ethernet0/0 | 10.0.1.0/24 (XR01 .1, RT01 .11) | 10 |
| BACKUP | GigabitEthernet0/0/0/1 | RT03 Ethernet0/0 | 10.0.3.0/24 (XR01 .1, RT03 .13) | 100 |
| CORE-A | — | RT01 Ethernet0/1 ─ RT02 Ethernet0/0 | 10.0.12.0/24 (RT01 .11, RT02 .12) | 10 |
| CORE-B | — | RT03 Ethernet0/1 ─ RT02 Ethernet0/1 | 10.0.23.0/24 (RT03 .13, RT02 .12) | 100 |

| Router | Role | Platform | Loopback0 | Other networks |
|---|---|---|---|---|
| XR01 | provider edge | IOS XRd 26.1.1 | 10.255.0.1/32 | customer A 10.30.0.0/16 (Loopback100, in BGP only); management 10.255.255.1/32 (Loopback1) |
| RT01 | core | IOS XE 17.15 | 10.255.0.11/32 | — |
| RT02 | provider edge | IOS XE 17.15 | 10.255.0.12/32 | customer A 10.20.0.0/16 (Loopback100, in BGP only) |
| RT03 | core | IOS XE 17.15 | 10.255.0.13/32 | — |

- The four routers run IS-IS instance `CORE` for IPv4: area 49.0001, Level 2 only, wide metrics, point-to-point
  circuits, with the metrics in the table in both directions.
- XR01 and RT02 run iBGP in AS 65000 between their loopbacks and carry customer A's networks. The core routers RT01
  and RT03 do not run BGP.
- RT01, RT02 and RT03 follow the standard of the core: LDP on every core link, the LDP identity taken from
  Loopback0, and IS-IS synchronized with LDP. RT01 accepts targeted LDP hellos. RT03 requires authentication on all
  of its LDP sessions and does not accept targeted hellos.

## M8 — MPLS and LDP

### Task M8-1

XR01 has replaced PE-OLD, an IOS router, as the provider edge for customer A. Since the replacement, customer A's
networks behind XR01 and behind RT02 cannot reach each other. Last week the LDP settings of PE-OLD were copied to
XR01 under change CHG-1021, but the change was never finished.

- Make the traffic between 10.30.0.0/16 and 10.20.0.0/16 flow across the core in both directions. Do not run BGP on
  the core routers and do not advertise customer A's networks in IS-IS.
- Run LDP on both core links of XR01, PRIMARY and BACKUP.
- Like every router of the core, XR01 must identify itself in LDP with its Loopback0 address alone. Loopback1 is
  reserved for the management systems and must not be advertised in IS-IS.
- RT03 has its own rules for LDP sessions. The session with RT03 is the subject of Task M8-2.

### Task M8-2

The security standard of the core sets two rules for LDP.

- Every LDP session with RT03 must be authenticated with TCP MD5, key `CoreLdp-2026`. Bring up the session between
  XR01 and RT03. RT01 does not use authentication for LDP.
- XR01 must assign local labels to host routes (/32) only. No other prefix in XR01's routing table may get a local
  label.

### Task M8-3

Last month, an LDP failure on a core link that kept IS-IS up sent customer traffic into a core router, which dropped
it.

- While IS-IS is up on a core link of XR01 but LDP is not ready on it, XR01 must not use that link for traffic. This
  applies to both core links.
- When LDP becomes ready on such a link again, XR01 must wait 10 seconds before it uses the link again.
- The Check disables LDP on RT01's side of PRIMARY for about a minute, sends customer traffic from XR01, and then
  restores RT01.

### Task M8-4

Planned work on the transport network under PRIMARY will cut the link several times, each time for up to a few
minutes.

- When PRIMARY fails, XR01 must keep its LDP session with RT01 and the labels learned from RT01, so that they are
  ready as soon as PRIMARY returns. Keep them for no longer than 10 minutes after a failure.
- RT03 does not accept this protection from its neighbours. XR01 must not attempt it toward RT03.
- The Check discards all packets on PRIMARY for about 45 seconds, while both ports stay up, and then restores the
  link.

### Task M8-5

The operations team at RT02 verifies label switched paths with MPLS OAM, and the quality team wants the traffic class
that the core marks in the label (the MPLS EXP bits) to reach XR01.

- From RT02, an MPLS LSP ping and an MPLS LSP traceroute to XR01's Loopback0 must succeed, with XR01 answering. XR01's
  own operators must be able to run the same tests toward RT02's Loopback0.
- Packets for XR01's own prefixes must arrive at XR01 still carrying a label, so that XR01 can read the traffic class
  set in the core. The router before XR01 must not remove the label.
