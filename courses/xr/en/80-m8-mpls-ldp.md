# M8 — MPLS and LDP

A provider core moves customer traffic between its edges without knowing the customers' routes. It does that with
labels. This unit covers how IOS XR builds label switched paths with LDP: the neighbours and their sessions,
protecting the label exchange, keeping IS-IS and LDP in step, keeping a session through a link failure, and checking
a path with MPLS OAM. In the CCNP Service Provider blueprint this is section 3.1 (LDP synchronization, session
protection, neighbours and MPLS OAM) and 1.5.d (LDP authentication and label allocation filtering). Unified MPLS,
also in 3.1, comes in a follow-up unit.

The outputs on this page were captured on IOS XRd 26.1.1 with three IOS XE 17.15 routers on IOL (lab XRT-07). The
same steps on IOS XRv 9000 26.1.1 gave the same results. Times in seconds are measured in that lab, not guaranteed
values.

## 1. Labels in a provider core

### 1.1 A core without BGP

In the lab, customer A has networks behind two provider edge (PE) routers: 10.30.0.0/16 behind XR01 and
10.20.0.0/16 behind RT02. The two PEs exchange these routes in iBGP, with their loopbacks as next hops. The core
routers RT01 and RT03 run only IS-IS. They know every loopback and every link, but none of the customer routes.

That is the usual design of a provider core: the core routers do not carry the full table of customer routes, and
adding a customer touches only the edges. It has one consequence. If XR01 sends a customer packet as plain IP, RT01
has to look up 10.20.0.1, finds nothing, and drops the packet:

```console
RT01#show ip route 10.20.0.0
% Subnet not in table

RP/0/RP0/CPU0:XR01#ping 10.20.0.1 source Loopback100 count 5
.....
Success rate is 0 percent (0/5)
```

MPLS solves this with a label. XR01 looks up 10.20.0.0/16 in BGP and finds the next hop 10.255.0.12, RT02's
loopback. It puts a label in front of the packet, the label that RT01 has bound to 10.255.0.12/32. RT01 forwards on
the label alone and never reads the destination address. The set of packets that a label stands for is called a
**forwarding equivalence class** (FEC); with LDP, a FEC is a prefix of the routing table.

### 1.2 Label switching

Each router keeps a label forwarding table (LFIB). An entry says: for this incoming local label, send the packet out of
this interface with this outgoing label. The router that receives a labelled packet either **swaps** the label for the
next router's label or **pops** it. On IOS XR the table is `show mpls forwarding`; on IOS it is
`show mpls forwarding-table`:

```console
RP/0/RP0/CPU0:XR01#show mpls forwarding
Local  Outgoing    Prefix             Outgoing     Next Hop        Bytes
Label  Label       or ID              Interface                    Switched
------ ----------- ------------------ ------------ --------------- ------------
24000  Pop         10.255.0.11/32     Gi0/0/0/0    10.0.1.11       2340
24001  Pop         10.0.12.0/24       Gi0/0/0/0    10.0.1.11       0
24002  16          10.255.0.12/32     Gi0/0/0/0    10.0.1.11       0
24003  Unlabelled  10.255.0.13/32     Gi0/0/0/1    10.0.3.13       520
24004  17          10.0.23.0/24       Gi0/0/0/0    10.0.1.11       0

RT01#show mpls forwarding-table
Local      Outgoing   Prefix           Bytes Label   Outgoing   Next Hop
Label      Label      or Tunnel Id     Switched      interface
16         Pop Label  10.255.0.12/32   666           Et0/1      10.0.12.12
20         Pop Label  10.255.0.1/32    1487          Et0/0      10.0.1.1
```

XR01 sends customer A's packets for RT02 with label 16. RT01's entry for its local label 16 says `Pop Label`: RT02 is
the last router of the path and has asked its neighbours to remove the label one hop early. This is **penultimate hop
popping** (PHP). The egress router advertises the reserved label 3, **implicit null**, for its own prefixes, and the
router before it pops. RT02 then receives a plain IP packet and routes it with its own table, in which customer A's
network is directly connected.

`Unlabelled` means that the router has a local label but no label from the next hop. It removes the label and sends
the packet as plain IP, which is fine when the next hop is the egress and a black hole when it is a core router
without the route. In the output above, the entry for RT03's loopback is `Unlabelled` because the session with RT03
was not up yet. IOS XR allocates labels from 24000 upward; IOS from 16.

## 2. LDP neighbours

### 2.1 Discovery and session

The Label Distribution Protocol (LDP, RFC 5036) binds a local label to each prefix and tells the neighbours about it.
Two LDP routers find each other with **link hellos**: UDP packets to port 646 of 224.0.0.2, sent every 5 seconds on
each LDP interface and held for 15 seconds. A hello carries two values:

| Value | What it is |
|---|---|
| LDP ID | the router ID and a label space, written `10.255.0.1:0` (0 = one label space for all interfaces) |
| Transport address | the address that the router uses for the TCP session, by default the router ID |

The two routers then open a TCP session to port 646 between their transport addresses. The router with the higher
transport address opens it (the active role). Over the session they exchange their addresses and their label
bindings. Each router keeps the bindings from all of its neighbours, not only from the one on the best path, so that
a new path can be used at once when the routing changes (liberal label retention). The session stays up as long as at
least one hello adjacency to the neighbour stays up.

The defaults on IOS XR are in `show mpls ldp parameters`: link hellos every 5 seconds held for 15, targeted hellos
every 10 seconds held for 90, and a session hold time of 180 seconds with a keepalive every 60.

### 2.2 LDP on IOS XR

IOS XR has no `mpls ip` on the interface. LDP is a process of its own, and the interfaces are listed under it:

```text
mpls ldp
 interface GigabitEthernet0/0/0/0
 interface GigabitEthernet0/0/0/1
```

IPv4 is enabled implicitly in the default VRF. A loopback cannot be an LDP interface, but its /32 still gets a label.
`show mpls interfaces` lists the interfaces where LDP runs:

```console
RP/0/RP0/CPU0:XR01#show mpls interfaces
Interface                  LDP      Tunnel   Static   Enabled
-------------------------- -------- -------- -------- --------
GigabitEthernet0/0/0/0     Yes      No       No       Yes
GigabitEthernet0/0/0/1     Yes      No       No       Yes
```

Instead of listing the interfaces, `mpls ldp auto-config` under `router isis CORE` → `address-family ipv4 unicast`
runs LDP on every IS-IS interface. `show mpls ldp interface brief` then shows the interfaces with a 1 in the
`IGP-Auto-Cfg` column and `N` under `Config`.

### 2.3 The LDP ID and the transport address

IOS XR chooses the LDP ID in this order: `router-id` under `mpls ldp`, then the router ID of the system. The router ID
of the system is in `show router-id`; release 26.1.1 has no global command to set it. In the lab it was Loopback0
(10.255.0.1), although Loopback1 has a higher address and Loopback100 a higher number. The configuration guide
recommends setting `router-id` under `mpls ldp`, so that a change elsewhere does not move the LDP ID.

The transport address follows the LDP ID unless it is set under `mpls ldp` → `address-family ipv4` with
`discovery transport-address`, globally or per interface. Whatever it is, every LDP neighbour needs a route to it.
When the neighbour has none, the hellos still come and go and nothing else happens. XR01's neighbour list stays empty,
and XR01 shows its own transport address only in `show mpls ldp parameters`. The neighbour says it plainly:

```console
RT01#show mpls ldp discovery detail
	Ethernet0/0 (ldp): xmit/recv
	    LDP Id: 10.255.0.1:0; no route to transport addr
	      Src IP addr: 10.0.1.1; Transport IP addr: 10.255.255.1

RP/0/RP0/CPU0:XR01#show mpls ldp parameters
  Router ID: 10.255.0.1
    Transport address:
      IPv4: 10.255.255.1
```

The LDP ID looks right; only the transport address points at a loopback that IS-IS does not carry. The usual rule is
one loopback for both, advertised in the IGP as a /32.

## 3. Protecting label distribution

### 3.1 Authentication

LDP sessions can be protected with the TCP MD5 signature option: each TCP segment carries a digest computed with a
shared key. On IOS XR the key is set per neighbour, by its LDP ID, under `mpls ldp`:
`neighbor 10.255.0.13:0 password clear <key>`. The running configuration keeps it only in encrypted form, under a
`neighbor` block. `neighbor password <key>` without an LDP ID sets a default for every neighbour, and
`neighbor <id>:0 password disable` exempts one.

On IOS the key is `mpls ldp neighbor <address> password <key>`, and `mpls ldp password required` refuses every session
without one. Without `for <acl>`, that rule applies to all neighbours, including those that nobody gave a key.

The two sides report a mismatch in different words:

| Situation | Message |
|---|---|
| the neighbour signs, XR01 has no key for it | XR01: `%IP-TCP-3-NOAUTH : Authentication info not programmed for the packet received from 10.255.0.13` |
| XR01 signs, the neighbour has no key | XR01: `%IP-TCP-3-BADAUTH : Invalid MD5 digest from 10.255.0.11` |
| IOS requires a key, the neighbour sends none | IOS: `%TCP-6-BADAUTH: No MD5 digest from 10.255.255.1(57070) to 10.255.0.13(646)` |
| IOS requires a key and has none for a peer | IOS: `%LDP-4-PWD: MD5 protection is required for peer 10.255.0.12:0, no password configured` |

An IOS router that gets a new key keeps an existing session until the session is reset. IOS XR resets the session at
the commit.

:::try
See what a default password does to a neighbour that has none. Do it after Task M8-2.

1. On XR01, under `mpls ldp`, add `neighbor password clear CoreLdp-2026` (no LDP ID) and commit.
2. Run `show mpls ldp neighbor brief` and `show logging last 10`, and on XR01 ping 10.20.0.1 from Loopback100.
3. Remove the line again with `no neighbor password`, commit, and check that the session with RT01 returns within a
   minute.

What the lab measured: at the commit the session with RT01 went down, and XR01 logged
`%IP-TCP-3-BADAUTH : Invalid MD5 digest from 10.255.0.11` every 10 to 14 seconds. The session with RT03 stayed up,
because its own key overrides the default. Customer A's traffic stopped until the line was removed.
:::

### 3.2 Which prefixes get labels

By default LDP binds a local label to every prefix in the routing table that BGP did not install: the loopbacks, the
link networks and connected networks such as customer A's 10.30.0.0/16 on XR01. It advertises all of them to every
neighbour. Only the PE loopbacks are next hops of BGP routes, so most of those labels are never used.

IOS XR has three places to limit that, all under `mpls ldp` → `address-family ipv4` → `label`:

| Command | Limits |
|---|---|
| `local allocate for {host-routes \| <acl>}` | the prefixes that get a local label at all |
| `local advertise to <ldp-id> for <acl>` (and `interface`) | which local labels are sent to which neighbour |
| `remote accept from <ldp-id> for <acl>` | which labels from a neighbour are kept |

The ACLs are IPv4 access lists that match the prefixes. When both outbound and inbound filtering would do, the
configuration guide recommends outbound filtering. With `allocate for host-routes`, XR01 keeps labels for the /32s
only:

```console
RP/0/RP0/CPU0:XR01#show mpls ldp bindings brief
Prefix              Local      Advertised  Remote Bindings
                    Label        (peers)       (peers)
------------------  ---------  ----------  ---------------
10.0.1.0/24         -                   0                2
10.0.12.0/24        -                   0                2
10.30.0.1/32        ImpNull             2                0
10.255.0.1/32       ImpNull             2                2
10.255.0.12/32      24002               2                2
10.255.255.1/32     ImpNull             2                0
```

The remote bindings for the link networks stay: they come from RT01 and RT03, which still allocate labels for them.
The local labels that XR01 no longer advertises leave its forwarding table a few minutes later. On IOS the same
limit is `allocate global host-routes` under `mpls ldp label`.

## 4. LDP and IS-IS synchronization

### 4.1 The black hole

IS-IS and LDP run separately. When LDP fails on a link but IS-IS stays up, IS-IS still chooses the link, and the
router sends its traffic over it without a label. Whether that hurts depends on who receives the packet. When the next
router is the egress, it routes the plain packet itself. When it is a core router without BGP, the packet is dropped.

In the lab, XR01 is the ingress and RT01 a core router. With LDP down on PRIMARY and IS-IS up, XR01's entry for RT02
turned `Unlabelled` and customer A's traffic stopped:

```console
RP/0/RP0/CPU0:XR01#show mpls forwarding prefix 10.255.0.12/32
Local  Outgoing    Prefix             Outgoing     Next Hop        Bytes
Label  Label       or ID              Interface                    Switched
------ ----------- ------------------ ------------ --------------- ------------
24002  Unlabelled  10.255.0.12/32     Gi0/0/0/0    10.0.1.11       107

RP/0/RP0/CPU0:XR01#ping 10.20.0.1 source Loopback100 count 5
.....
Success rate is 0 percent (0/5)
```

The reverse direction kept working: RT01 received RT02's packets with a label and sent them to XR01 as plain IP, and
XR01 is the egress.

:::try
Make LDP fail on PRIMARY while IS-IS stays up. Do it once before Task M8-3 and once after.

1. On XR01, under `mpls ldp`, remove `interface GigabitEthernet0/0/0/0` and commit. IS-IS keeps running on the link.
2. Run `show mpls forwarding prefix 10.255.0.12/32`, `show isis database verbose XR01.00-00 | include Metric` and
   `ping 10.20.0.1 source Loopback100 count 5`.
3. Put `interface GigabitEthernet0/0/0/0` back under `mpls ldp` and commit.

What the lab measured: before Task M8-3, the entry stayed on Gi0/0/0/0 as `Unlabelled`, the metric toward RT01 stayed
10, and the ping lost every packet. After Task M8-3, XR01 advertised the link to RT01 with metric 16777214 at once, the
route moved to BACKUP, and the ping lost three packets while the routes moved, then went through.
:::

### 4.2 Synchronization on IOS XR

With LDP-IGP synchronization (RFC 5443), IS-IS advertises a link with the largest usable metric until LDP is ready on
it. For wide metrics that is 16777214 (0xFFFFFE). The value 0xFFFFFF is reserved and would remove the link from the
topology, so the link stays usable as a last resort. On IOS XR it is enabled in IS-IS, per interface and address
family:

```text
router isis CORE
 interface GigabitEthernet0/0/0/0
  address-family ipv4 unicast
   mpls ldp sync
```

LDP counts a link as ready when it has a hello adjacency on the link, the session with that neighbour is up, and the
labels have been exchanged. `show mpls ldp igp sync` shows the state of each link, and `show isis interface` shows
`MPLS LDP Sync (L1/L2)` and `LDPv4 Sync Status`:

```console
RP/0/RP0/CPU0:XR01#show mpls ldp igp sync
GigabitEthernet0/0/0/0:
  VRF: 'default' (0x60000000)
  Sync delay: 10 sec
  Sync status: Not ready (No hello adjacency)
GigabitEthernet0/0/0/1:
  VRF: 'default' (0x60000000)
  Sync delay: 10 sec
  Sync status: Ready
    Peers:
      10.255.0.13:0

RP/0/RP0/CPU0:XR01#show isis database verbose XR01.00-00
  Metric: 16777214   IS-Extended RT01.00
  Metric: 100        IS-Extended RT03.00
```

`igp sync delay on-session-up <5-300>` under `mpls ldp` holds the link at the high metric for that many seconds once
LDP is ready on it again; while it runs, the state reads `Deferred (8 sec remaining)`. In the lab it ran after a new
session and also when the link hellos returned to a session that session protection had kept (section 5.2). Release
26.1.1 has a second form, `on-proc-restart`, for the start of the LDP process, and no plain `igp sync delay <seconds>`.

Each router decides only for its own direction of the link. XR01's synchronization keeps XR01's traffic off the link;
RT01's keeps RT01's. On IOS, `mpls ldp sync` under `router isis` enables it on every interface that runs LDP. In the
lab, while XR01 had no LDP at all, RT01 already advertised its link to XR01 with 16777214.

## 5. Session protection

### 5.1 Targeted hellos keep the session

An LDP session ends when its last hello adjacency ends. When PRIMARY fails, the link hellos from RT01 stop, the
adjacency times out after 15 seconds, the session goes down, and XR01 forgets RT01's labels. When the link returns,
the session has to be built again and the labels exchanged before the link can carry labelled traffic.

**Session protection** adds a second adjacency to the same neighbour: **targeted hellos**, sent as unicast UDP to
the neighbour's LDP ID, which the routing can deliver over any path. While PRIMARY is down, the targeted adjacency
keeps the session, and the labels stay. On IOS XR it is one line under `mpls ldp`:

```text
mpls ldp
 session protection [for <acl>] [duration <seconds>]
```

The ACL selects neighbours by LDP ID. Without `duration`, release 26.1.1 keeps a session for 86400 seconds (24 hours)
after its link adjacency ends. The command reference gives the same default; the configuration guide says the
protection is unlimited. The neighbour has to answer the targeted hellos: IOS does that with
`mpls ldp discovery targeted-hello accept`, and IOS XR with `discovery targeted-hello accept` under
`mpls ldp` → `address-family ipv4`. A neighbour that runs session protection itself answers anyway (RFC 5036, 3.5.2).

`show mpls ldp neighbor <id> detail` shows the state:

| State | Meaning |
|---|---|
| `Incomplete` | targeted hellos are sent, but the neighbour does not answer |
| `Ready` | the targeted adjacency and at least one link adjacency are up |
| `Protecting` | only the targeted adjacency is up; a holdup timer runs |

```console
RP/0/RP0/CPU0:XR01#show mpls ldp neighbor 10.255.0.11:0 detail
  LDP Discovery Sources:
    IPv4: (2)
      GigabitEthernet0/0/0/0
      Targeted Hello (10.255.0.1 -> 10.255.0.11, active)
  Session Protection:
    Enabled, state: Ready
    ACL: 'LDP-SP', Duration: 600 sec
```

Toward RT03, which does not accept targeted hellos, the state stays `Incomplete`, and `show mpls ldp discovery` shows
the targeted hellos as `xmit` only.

### 5.2 Protection and synchronization together

Session protection keeps the session, not the link. While PRIMARY is down, there is no hello adjacency on it, so
synchronization keeps it at the high metric, and the traffic uses BACKUP. In the lab, the link hellos timed out and
the traffic moved to BACKUP within 12 seconds of a silent failure, while the IS-IS adjacency on PRIMARY stayed up for
about ten seconds more. Synchronization moves the traffic as soon as LDP loses the link, whether the session survives
or not.

When PRIMARY returns, the session is still there with all of RT01's labels. The link hellos resume, the 10-second
delay runs (`Sync status: Deferred (8 sec remaining)`), and in the lab the traffic was back on PRIMARY 12 seconds
after the link. Without protection, the session had ended during the failure, a new one had to be built first, and
the traffic came back after about 20 seconds. The difference grows with the number of labels to exchange.

:::try
Cut PRIMARY without its ports going down, and watch the session to RT01. Do it after Task M8-4.

1. In CML, select the link between XR01 GigabitEthernet0/0/0/0 and RT01 Ethernet0/0. On its **Settings** tab, set
   **Loss** to 100, tick **Enable** and press **Apply**.
2. On XR01, run `show mpls ldp neighbor 10.255.0.11:0 detail` and `show mpls ldp bindings 10.255.0.12/32` every few
   seconds for a minute. Note when the state changes and whether RT01's label is still there.
3. Press **Reset** on the same tab. Run `show mpls ldp neighbor 10.255.0.11:0` and compare the `Up time` with the one
   before the failure.

What the lab measured: within 12 seconds the state turned to `Protecting`, with a `Holdup timer remaining` counting
down from the duration, and the binding from 10.255.0.11:0 stayed. The route to RT02 moved to BACKUP while the IS-IS
adjacency with RT01 was still up. After the reset, the `Up time` simply went on, and the route returned to PRIMARY
after the 10-second delay. Without protection the session ended during the failure and was new after the reset.
:::

## 6. MPLS OAM

### 6.1 LSP ping and traceroute

An ordinary ping can succeed while the label switched path is broken, because a packet without a label may still find
its way. MPLS OAM (RFC 8029) tests the path itself. An **MPLS echo request** is a UDP packet to port 3503, addressed
to 127.0.0.1 so that no router forwards it as IP. It carries the FEC under test and is sent with the label of that FEC.
The egress answers with an echo reply, by default as a plain UDP packet. An LSP traceroute sends the request with
increasing TTLs, and each router reports what it would do with the label.

IOS XR runs MPLS OAM only after the global command `mpls oam`, both for the tests that it starts and for the requests
that it answers. Without it, the tests stop at once:

```console
RP/0/RP0/CPU0:XR01#ping mpls ipv4 10.255.0.12/32 repeat 3
% MPLS Embedded Management Subsystem is not running.
To enable, use 'mpls oam' global config command.
```

and a traceroute from RT02 ends at the router before XR01. IOS answers without any configuration:

```console
RT02#traceroute mpls ipv4 10.255.0.1/32 timeout 1 ttl 4
  0 10.0.12.12 MRU 1500 [Labels: 20 Exp: 0]
L 1 10.0.12.11 MRU 1500 [Labels: implicit-null Exp: 0] 1 ms
. 2 *
. 3 *
. 4 *
```

| Code | Meaning (RFC 8029 return code) |
|---|---|
| `!` | the replying router is the egress for the FEC (3) |
| `L` | the packet is label switched, out of a labelled interface (8) |
| `B` | label switched, but sent out without a label |
| `.` | no reply before the timeout |
| `Q` | the request could not be sent |
| `N` | no label entry for the FEC (11) |

When there is more than one equal-cost path, `traceroute mpls multipath ipv4 <prefix>` on IOS XR finds and tests each
of them by varying the 127/8 destination address.

### 6.2 Explicit null and the last hop

With PHP the egress receives plain IP, and the traffic class that the core marked in the label (the EXP bits) is lost
one hop early. A router that needs that marking advertises the reserved label 0, **explicit null**, for its own
prefixes instead. The router before it then swaps to label 0 instead of popping, and the egress removes the label
itself. On IOS XR the setting is `explicit-null` under `mpls ldp` → `address-family ipv4` → `label` → `local` →
`advertise`; on IOS it is `mpls ldp explicit-null`.

```console
RT01#show mpls forwarding-table 10.255.0.1
Local      Outgoing   Prefix           Bytes Label   Outgoing   Next Hop
Label      Label      or Tunnel Id     Switched      interface
20         explicit-n 10.255.0.1/32    0             Et0/0      10.0.1.1

RT02#traceroute mpls ipv4 10.255.0.1/32 timeout 1 ttl 4
  0 10.0.12.12 MRU 1500 [Labels: 20 Exp: 0]
L 1 10.0.12.11 MRU 1500 [Labels: explicit-null Exp: 0] 1 ms
! 2 10.0.1.1 3 ms
```

In the lab, RT01 took 20 to 30 seconds after XR01's commit to switch from `Pop Label` to `explicit-n`.

:::try
Compare an ordinary traceroute through the core before and after Task M8-5.

1. On RT02, run `traceroute 10.30.0.1 source Loopback100 timeout 1 probe 1 ttl 1 4`.
2. After Task M8-5, wait half a minute and run it again.

What the lab measured: before, the first hop was `*` and the second was XR01 (10.0.1.1). After, the first hop was
`10.0.12.11 [MPLS: Label 20 Exp 0]`. A core router that drops a labelled packet for its TTL can send its
time-exceeded message on along the path, and the egress routes it back. With PHP, RT01's next step for label 20 was
to pop it, and no answer came back; with label 0 to swap, RT01's answer reached RT02 through XR01. RT01 itself has no
route to customer A.
:::

### 6.3 Labels and MTU

Each label adds 4 bytes. The core links in the lab have an MTU of 1500 bytes for IP on IOS and 1514 bytes, including
the Ethernet header, on IOS XR, which leaves 1500 bytes for the labelled packet. A 1500-byte IP packet with one label
is 1504 bytes and does not fit:

```console
RP/0/RP0/CPU0:XR01#ping 10.20.0.1 source Loopback100 size 1500 df-bit count 3
...
Success rate is 0 percent (0/3)

RP/0/RP0/CPU0:XR01#ping mpls ipv4 10.255.0.12/32 sweep 1490 1510 4 repeat 1
Sending 1, [1490..1510]-byte MPLS Echos to 10.255.0.12/32,
!!!QQQ
```

A real core raises the MTU of every core link, at both ends, to leave room for the labels. A Layer 3 VPN adds a second
label (unit M9), and other services add more.

:::try
Find the largest packet that crosses the core with a label.

1. On XR01, ping 10.20.0.1 from Loopback100 with the DF bit set, once with `size 1500` and once with `size 1496`.
2. Run `ping mpls ipv4 10.255.0.12/32 sweep 1490 1510 4 repeat 1` and read where the `!` turn into `Q`.
3. Ping RT02's Loopback0 from XR01's Loopback0 with `size 1500 df-bit`.

What the lab measured: 1500 bytes failed in both directions and 1496 passed. The sweep sent 1490 to 1498 and could not
send 1502 and more. The loopback-to-loopback ping of 1500 bytes failed as well, because XR01 puts a label on its own
traffic to an LDP prefix too.
:::

## 7. Command names

| On IOS | On IOS XR |
|---|---|
| `mpls ip` on the interface | `interface <name>` under `mpls ldp` (or `mpls ldp auto-config` in IS-IS) |
| `mpls ldp router-id Loopback0 force` | `router-id <address>` under `mpls ldp` |
| `mpls ldp discovery transport-address` on the interface | `discovery transport-address` under `mpls ldp` → `address-family ipv4` (or the interface) |
| `mpls ldp neighbor <address> password <key>` | `neighbor <ldp-id>:0 password clear <key>` under `mpls ldp` |
| `mpls ldp password required` | (no counterpart; a key per neighbour or a default key) |
| `allocate global host-routes` under `mpls ldp label` | `allocate for host-routes` under `label` → `local` |
| `mpls ldp sync` under `router isis` | `mpls ldp sync` under the interface's address family in `router isis` |
| `mpls ldp session protection [for <acl>] [duration …]` | `session protection [for <acl>] [duration …]` under `mpls ldp` |
| `mpls ldp discovery targeted-hello accept` | `discovery targeted-hello accept` under `mpls ldp` → `address-family ipv4` |
| `mpls ldp explicit-null` | `explicit-null` under `label` → `local` → `advertise` |
| (on by default) | `mpls oam` |
| `show mpls forwarding-table`, `show mpls ldp bindings` | `show mpls forwarding`, `show mpls ldp bindings` |
| `show mpls ldp discovery detail` | `show mpls ldp discovery`, `show mpls ldp parameters` |

## Practice

Go to lab **XRT-07** and do the M8 tasks. The lab uses IOS XRd, which takes about four minutes to build.

<p class="tolab"><a href="/_learn?id=XRT-07">Open lab XRT-07 in the workspace</a> — <a href="81-m8-practice.html">The tasks</a></p>

:::note
Sources: the IOS XR *MPLS* configuration guide (ASR 9000, releases 26.1.x to 26.3.x) and command reference,
"Implementing MPLS Label Distribution Protocol" (enabling LDP and the implicit IPv4 address family, the order for the
router ID, the transport address, the neighbour password and the default password, label allocation, advertisement
and acceptance control, explicit null, session protection and its states, IGP synchronization and the delay) and
"Implementing MPLS OAM"; the IOS XR *Routing* configuration guide and command reference, "Implementing IS-IS" (MPLS
LDP IS-IS synchronization, the metric 16777214, `mpls ldp auto-config`); the IOS XE 17.x MPLS configuration guides,
"MPLS LDP Session Protection" and "MPLS LDP MD5 Global Configuration", checked October 2026; RFC 5036 (LDP, the active
role, targeted hellos), RFC 5443 (LDP-IGP synchronization), RFC 8029 (LSP ping and traceroute, return codes). The
following come from measurement in lab XRT-07: the LDP ID taken from Loopback0, the transport address that is not
routed and its messages, the MD5 messages on both sides and the reset at the commit, the labels after
`allocate for host-routes`, the black hole without synchronization, the state `Not ready (No hello adjacency)` during
session protection, the default duration of 86400 seconds, `mpls oam` for both sending and answering, the traceroute
with explicit null, and the MTU with one label.
:::
