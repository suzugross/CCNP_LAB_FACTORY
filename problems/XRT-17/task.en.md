# XR Track 17 — BGP operations

This lab is the practice part of the XR track unit **M6 BGP, supplement (BGP operations)**. The unit pages are "Handing out a
backup path: ADD-PATH and PIC" (tasks M6-5 and M6-6), "Protecting the session: GTSM and TCP-AO" (tasks M6-7 and M6-8) and
"Not taking too much: prefix limits, dampening and aggregation" (tasks M6-9 and M6-10). Read each page, then work through the
tasks here in order.

## Ground rules

- You configure **PE1** (IOS XRv 9000), **PE2**, **PE3**, **P1** and **RR1** (IOS XRd), and **X1** and **X2** (IOS XE) for tasks
  M6-7 and M6-8.
- **CE1** is the customer router, **X1** and **X2** are the routers of AS 65100, and **T** is a destination inside AS 65100. Do not
  change anything that a task does not ask for.
- The tasks do not give example commands. Each task describes the behavior that is required.
- The **Tasks** tab has a **Check** button for each task. It reads the current state of the routers and, for some tasks, runs a
  test. Leave configuration mode before you press it. The tests are as follows, and each one puts things back when it ends.
  - M6-6: shuts down the interface of P1 toward PE2 (GigabitEthernet0/0/0/1) for about 40 seconds and measures the gap in packets
    sent from CE1 to T every 10 ms. One run takes about two minutes.
  - M6-9: adds three routes on CE1 for a moment, checks what PE1 does, removes them and re-establishes the session with CE1 on PE1.
  - M6-10: withdraws and restores 198.51.100.0/24 from X1 to PE2 three times in about 30 seconds, checks what PE2 does, and then
    clears the dampening state on PE2.
- Hints open one level at a time (keyword → where to look → command). Opened hints are recorded.
- Each task also has a **How to verify** button. It is an example of checking in this order: is it in → send and count → look where
  it arrives → did anything else break. You can open it at any time and it is not recorded. Try checking by hand before you press
  Check.
- **Start over** in the **Tasks** tab puts the routers back to the state right after the lab was built.
- PE1 runs **IOS XRv 9000** 26.1.1. PE2, PE3, P1 and RR1 run **IOS XRd** 26.1.1 (the container form of IOS XR). CE1, X1, X2 and T
  run IOS XE 17.15 (IOL).

## Topology

| Link | Ends | Addresses |
|---|---|---|
| CORE-1 | PE1 GigabitEthernet0/0/0/0 ─ P1 GigabitEthernet0/0/0/0 | 10.0.1.0/24 (PE1 .1, P1 .11) |
| CORE-2 | PE2 GigabitEthernet0/0/0/0 ─ P1 GigabitEthernet0/0/0/1 | 10.0.2.0/24 (PE2 .2, P1 .11) |
| CORE-3 | PE3 GigabitEthernet0/0/0/0 ─ P1 GigabitEthernet0/0/0/2 | 10.0.3.0/24 (PE3 .3, P1 .11) |
| RR | RR1 GigabitEthernet0/0/0/0 ─ P1 GigabitEthernet0/0/0/3 | 10.0.21.0/24 (RR1 .21, P1 .11) |
| CUSTOMER | PE1 GigabitEthernet0/0/0/1 ─ CE1 Ethernet0/0 | 172.16.1.0/24 (CE1 .1, PE1 .254) |
| UPSTREAM-1 | PE2 GigabitEthernet0/0/0/1 ─ X1 Ethernet0/0 | 172.16.2.0/24 (X1 .1, PE2 .254) |
| UPSTREAM-2 | PE3 GigabitEthernet0/0/0/1 ─ X2 Ethernet0/0 | 172.16.3.0/24 (X2 .1, PE3 .254) |
| AS65100-1 | X1 Ethernet0/1 ─ T Ethernet0/0 | 10.100.13.0/24 (X1 .1, T .3) |
| AS65100-2 | X2 Ethernet0/1 ─ T Ethernet0/1 | 10.100.23.0/24 (X2 .2, T .3) |
| AS65100-12 | X1 Ethernet0/2 ─ X2 Ethernet0/2 | 10.100.12.0/24 (X1 .1, X2 .2) |

| Device | Role | Platform | Loopback0 |
|---|---|---|---|
| PE1 | Provider edge (customer side) | IOS XRv 9000 26.1.1 | 10.255.0.1/32 |
| PE2 | Provider edge (primary exit to AS 65100) | IOS XRd 26.1.1 | 10.255.0.2/32 |
| PE3 | Provider edge (backup exit to AS 65100) | IOS XRd 26.1.1 | 10.255.0.3/32 |
| P1 | Provider core | IOS XRd 26.1.1 | 10.255.0.11/32 |
| RR1 | Route reflector | IOS XRd 26.1.1 | 10.255.0.21/32 |
| CE1 | Customer (AS 65001). Loopback1 192.168.1.1/24, Loopback2 192.168.2.1/24 | IOS XE 17.15 | — |
| X1, X2 | Border routers of AS 65100. X1's Loopback9 198.51.100.1/24 is a customer of X1 | IOS XE 17.15 | 10.100.255.1/32, 10.100.255.2/32 |
| T | Destination inside AS 65100 (Loopback1 203.0.113.1/24) | IOS XE 17.15 | 10.100.255.3/32 |

- The five routers of AS 65000 run the IS-IS instance `CORE` (level 2). LDP also runs on the core links (CORE-1 to CORE-3). P1 does
  not run BGP.
- PE1, PE2 and PE3 are clients of RR1 and peer with iBGP between their Loopback0 interfaces (each PE sets next-hop-self). PE1 and
  CE1, PE2 and X1, and PE3 and X2 use eBGP. The eBGP route policies pass every route. PE2 sets the local preference of the routes
  learned from X1 to 200.
- X1 and X2 run OSPF and iBGP inside AS 65100 and advertise 203.0.113.0/24. The default route of T prefers X2.

## M6 — BGP (supplement)

### Task M6-5

The provider uses PE2 as the primary exit to AS 65100 and PE3 as the backup. Today the best path on PE3 is the iBGP path through PE2,
so PE3 does not advertise the path it learns from X2. As a result, RR1 and PE1 know only the path through PE2.

- For 203.0.113.0/24, PE1 and RR1 must learn the path through PE3 (X2) as a backup path, in addition to the best path through PE2.
- PE3 must send this path to RR1 with BGP additional paths (ADD-PATH). Do not use best-external.
- The path through PE2 must remain the best path on every router.

### Task M6-6

Shorten the time for which traffic from CE1 to T stops when PE2 fails.

- When the link between PE2 and P1 goes down, traffic from CE1 to T (203.0.113.1) must stop for less than one second.
- PE1 must install the backup path in its forwarding table in advance.

### Task M6-7

AS 65100 has agreed to use GTSM (Generalized TTL Security Mechanism) on the eBGP session between PE2 and X1.

- Configure GTSM for this session on both PE2 and X1 so that it accepts only packets from the directly connected peer, one hop away.
- The session must be established, and PE2 must continue to learn routes from X1.

### Task M6-8

Protect the eBGP session between PE3 and X2 with the TCP Authentication Option (TCP-AO). The values have been agreed with AS 65100.

| Item | Value |
|---|---|
| Key chain name | AS65100-AO |
| Key ID | 7 |
| Cryptographic algorithm | AES-128-CMAC-96 (aes-128-cmac on IOS XE) |
| Key string | 5A3C9E107B2D4F6681A0C3E5F7092B4D |
| SendID and ReceiveID on PE3 | 37 and 73 (X2 uses SendID 73 and ReceiveID 37) |
| TCP options | Included in the MAC calculation |
| Key lifetime | Infinite |

- Configure both PE3 and X2. The session must be established with TCP-AO.

### Task M6-9

Prevent a configuration mistake at the customer from flooding PE1 with routes.

- PE1 must accept at most four IPv4 unicast routes from CE1, and log a warning when the number reaches three.
- When the number exceeds four, PE1 must tear down the session with CE1 and re-establish it automatically after two minutes.

### Task M6-10

- PE2 must use route flap dampening for the routes learned from X1. Use a half-life of 10 minutes and the default values for the
  others.
- PE2 and PE3 must advertise the customer addresses 192.168.0.0/22 to X1 and X2 as one route, and must not advertise the individual
  routes inside it to X1 and X2.
