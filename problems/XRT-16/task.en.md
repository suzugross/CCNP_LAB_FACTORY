# XR Track 16 — Multicast

This lab is the practice part of unit **M14 Multicast** of the XR track. The unit has three pages:
*Delivering one stream to many: IGMP and PIM sparse mode* (tasks M14-1 and M14-2), *Two other trees: SSM and
bidirectional PIM* (tasks M14-3 and M14-4) and *Finding the RP, IPv6, and troubleshooting* (tasks M14-5 and M14-6). Read each page before its tasks, and work through the tasks here, in order.

## Ground rules

- You configure **PE1**, **PE2**, **P1** and **PE3** (IOS XRd) and **PE4** (IOS XE).
- **SRC1**, **RCV2** and **RCV3** are hosts: SRC1 stands in for the head-end that sends the channels, RCV2 and RCV3 for
  set-top boxes. To test your work you may add and remove group joins on their interface and change its IGMP version;
  change nothing else on them. A host answers pings sent to a group it has joined, so a ping from SRC1 to a group shows
  who received it.
- The tasks give no command examples. Each task states the behaviour that is required.
- The **Tasks** tab has a **Check** button for each task. It reads the live state of the routers and sends test
  traffic. Leave configuration mode before you press it. Each check joins the hosts to a group chosen at random within
  the range named in the task, sends from a host, counts the replies, and then removes its joins and returns the hosts'
  IGMP version to the default. A check takes one to two minutes.
- Hints open one level at a time (keyword → where to look → command). Opened hints are logged.
- Each task also has a **How to verify** button: an example of checking your work in order (is it in → send and count →
  look where it arrives → did anything else break). Open it whenever you like; it is not logged. Verify by hand before you
  press Check.
- **Start over** on the **Tasks** tab returns the routers and the hosts to the state they had right after the lab was
  built.
- The four XR routers run **IOS XRd** 26.1.1, the container form of IOS XR. PE4 runs IOS XE 17.15 (IOL), and so do the
  hosts.

## Topology

| Link | Ends | Addressing |
|---|---|---|
| CORE-12 | PE1 GigabitEthernet0/0/0/0 ─ PE2 GigabitEthernet0/0/0/0 | 10.0.12.0/24 (PE1 .1, PE2 .2) |
| CORE-1 | PE1 GigabitEthernet0/0/0/1 ─ P1 GigabitEthernet0/0/0/0 | 10.0.1.0/24 (PE1 .1, P1 .11) |
| CORE-2 | P1 GigabitEthernet0/0/0/1 ─ PE2 GigabitEthernet0/0/0/1 | 10.0.2.0/24 (P1 .11, PE2 .2) |
| CORE-3 | P1 GigabitEthernet0/0/0/2 ─ PE3 GigabitEthernet0/0/0/0 | 10.0.3.0/24 (P1 .11, PE3 .3) |
| CORE-4 | PE2 GigabitEthernet0/0/0/2 ─ PE4 Ethernet0/0 | 10.0.4.0/24 (PE2 .2, PE4 .4) |
| HEADEND | PE1 GigabitEthernet0/0/0/2 ─ SRC1 Ethernet0/0 | 192.168.1.0/24 (SRC1 .1, PE1 .254) |
| ACCESS-2 | PE2 GigabitEthernet0/0/0/3 ─ RCV2 Ethernet0/0 | 192.168.2.0/24 (RCV2 .1, PE2 .254) |
| ACCESS-3 | SW1 (an unmanaged switch): PE3 GigabitEthernet0/0/0/1, PE4 Ethernet0/1, RCV3 Ethernet0/0 | 192.168.3.0/24 (PE3 .252, PE4 .253, RCV3 .1) |

Every link also carries IPv6: the core links use 2001:db8:&lt;third octet&gt;::/64 (2001:db8:12::/64 for CORE-12) with
the same host numbers, and the access links use 2001:db8:100:&lt;third octet&gt;::/64 (SRC1 2001:db8:100:1::1, RCV2
2001:db8:100:2::1, RCV3 2001:db8:100:3::1; the routers use the IPv4 host number, such as 2001:db8:100:3::252). On
ACCESS-3 the link-local addresses are fixed: PE3 FE80::252, PE4 FE80::253.

| Device | Role | Platform | Loopback0 |
|---|---|---|---|
| PE1 | Provider edge, head-end side | IOS XRd 26.1.1 | 10.255.0.1/32, 2001:db8:255::1/128 |
| PE2 | Provider edge | IOS XRd 26.1.1 | 10.255.0.2/32, 2001:db8:255::2/128 |
| P1 | Provider core | IOS XRd 26.1.1 | 10.255.0.11/32, 2001:db8:255::11/128 |
| PE3 | Provider edge on the shared access | IOS XRd 26.1.1 | 10.255.0.3/32, 2001:db8:255::3/128 |
| PE4 | Provider edge on the shared access | IOS XE 17.15 | 10.255.0.4/32, 2001:db8:255::4/128 |
| SRC1 | Head-end (host) | IOS XE 17.15 | — |
| RCV2, RCV3 | Set-top boxes (hosts) | IOS XE 17.15 | — |

- All five routers run the IS-IS instance `CORE` (level 2) for IPv4 and IPv6. The access links and the loopbacks are
  passive, so ACCESS-3 never carries traffic between PE3 and PE4.
- The hosts use a default route to their router; RCV3's is PE4 (192.168.3.253, 2001:db8:100:3::253).
- IPv4 multicast is not configured anywhere. Your predecessor configured an IPv6 multicast trial (Task M14-6).

## M14 — Multicast

### Task M14-1

The provider will carry its TV channels from the head-end SRC1 to the set-top boxes with IPv4 multicast in PIM sparse
mode.

- Enable IPv4 multicast routing on PE1, PE2, P1 and PE3 on all their interfaces, and on PE4 on both of its links.
- Use P1's Loopback0 (10.255.0.11) as a static RP for 239.0.0.0/8 only, on every router. Groups outside 239.0.0.0/8
  must have no RP.
- RCV2 and RCV3 must receive a channel in 239.16.0.0/16 from SRC1.

### Task M14-2

The channels in 239.17.0.0/16 are ultra-HD feeds. They must stay on the shared tree through the RP, and must not take
the direct link between PE1 and PE2.

- No router may switch a group in 239.17.0.0/16 to the shortest-path tree.
- Groups in 239.16.0.0/16 must still switch to the shortest-path tree as usual.
- RCV2 and RCV3 must still receive both kinds of channel.

### Task M14-3

A second service uses source-specific multicast: the set-top box names both the channel and its source.

- Treat 232.0.0.0/8 and 239.232.0.0/16 as SSM ranges on every router (PE1, PE2, P1, PE3 and PE4).
- A receiver that names SRC1 as the source must receive a channel in either range. A receiver that joins a group in
  these ranges without naming a source must receive nothing.
- Use IGMP version 3 on every router interface that faces hosts.

### Task M14-4

A conferencing service lets every site send to all the others.

- Use bidirectional PIM for 239.48.0.0/16, with PE3's Loopback0 (10.255.0.3) as the RP, on every router.
- Any host may send to a group in 239.48.0.0/16, and every host that joined it must receive it.
- No router may keep per-source state for these groups.

### Task M14-5

The provider no longer wants to configure the RP of the TV and ultra-HD channels by hand on every router.

- Use the bootstrap router (BSR) mechanism for 239.16.0.0/15. The candidate RPs are P1, PE3 and PE4, each with its
  Loopback0, and each announces 239.16.0.0/15 only. P1 must be the RP. If P1 stops announcing, PE3 must take over, and
  PE4 may become the RP only when both P1 and PE3 have stopped.
- The candidate BSRs are PE1 and P1, each with its Loopback0. PE1 must be the BSR, and P1 takes over only if PE1 stops.
- Every router must learn the RP of 239.16.0.0/15 through BSR. RCV2 and RCV3 must still receive the channels.

### Task M14-6

Your predecessor started an IPv6 multicast trial: channels in FF0E::16:0/112 from SRC1 (2001:db8:100:1::1) to RCV2 and
RCV3, with P1 (2001:db8:255::11) as the RP. The RP accepts Register messages only from sources in the head-end LAN
(2001:db8:100:1::/64). Nothing has ever arrived.

- RCV2 and RCV3 must receive a channel in FF0E::16:0/112 from SRC1.
- Keep the restriction on the RP: only sources in the head-end LAN may register.
