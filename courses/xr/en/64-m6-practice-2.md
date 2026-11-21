# M6 — Practice 2: ADD-PATH and PIC

These are the tasks of lab **XRT-17**, shown here so that you can read them away from the lab.
Do them in the lab workspace: the **Tasks** tab there has a Check button, staged hints and,
once a task passes, a reference solution for each task. No command examples are given on purpose.

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
<p class="tolab"><a href="/_learn?id=XRT-17&amp;step=m6t5">Open in the lab workspace</a> — Read: <a href="63-m6-add-path-pic.html#s2-1">2.1 A route reflector reflects only its best path</a> · <a href="63-m6-add-path-pic.html#s2-2">2.2 ADD-PATH: path identifiers and capability negotiation</a> · <a href="63-m6-add-path-pic.html#s2-3">2.3 What to send and what to install: advertise and install in the selection policy</a> · <a href="63-m6-add-path-pic.html#s3-1">3.1 The ADD-PATH configuration</a> · <a href="63-m6-add-path-pic.html#s3-3">3.3 Reading the output</a></p>


The provider uses PE2 as the primary exit to AS 65100 and PE3 as the backup. Today the best path on PE3 is the iBGP path through PE2,
so PE3 does not advertise the path it learns from X2. As a result, RR1 and PE1 know only the path through PE2.

- For 203.0.113.0/24, PE1 and RR1 must learn the path through PE3 (X2) as a backup path, in addition to the best path through PE2.
- PE3 must send this path to RR1 with BGP additional paths (ADD-PATH). Do not use best-external.
- The path through PE2 must remain the best path on every router.

### Task M6-6
<p class="tolab"><a href="/_learn?id=XRT-17&amp;step=m6t6">Open in the lab workspace</a> — Read: <a href="63-m6-add-path-pic.html#s2-4">2.4 PIC: the backup already in the forwarding table</a> · <a href="63-m6-add-path-pic.html#s2-5">2.5 The trap in an unlabelled network: the backup exit sends packets back</a> · <a href="63-m6-add-path-pic.html#s3-2">3.2 The PIC configuration</a> · <a href="63-m6-add-path-pic.html#s3-3">3.3 Reading the output</a> · <a href="63-m6-add-path-pic.html#s3-4">3.4 Pitfalls</a></p>


Shorten the time for which traffic from CE1 to T stops when PE2 fails.

- When the link between PE2 and P1 goes down, traffic from CE1 to T (203.0.113.1) must stop for less than one second.
- PE1 must install the backup path in its forwarding table in advance.
