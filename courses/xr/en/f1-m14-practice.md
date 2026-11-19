# M14 — Practice 1: PIM sparse mode

These are the tasks of lab **XRT-16**, shown here so that you can read them away from the lab.
Do them in the lab workspace: the **Tasks** tab there has a Check button, staged hints and,
once a task passes, a reference solution for each task. No command examples are given on purpose.

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
<p class="tolab"><a href="/_learn?id=XRT-16&amp;step=m14t1">Open in the lab workspace</a> — Read: <a href="f0-m14-igmp-pim-sm.html#s2-2">2.2 IGMP: the receiver tells its router</a> · <a href="f0-m14-igmp-pim-sm.html#s2-4">2.4 PIM sparse mode: the shared tree through the RP</a> · <a href="f0-m14-igmp-pim-sm.html#s2-5">2.5 Register: how the RP learns the source</a> · <a href="f0-m14-igmp-pim-sm.html#s3-1">3.1 Turning multicast on: multicast-routing, router pim, router igmp</a> · <a href="f0-m14-igmp-pim-sm.html#s3-2">3.2 A static RP</a> · <a href="f0-m14-igmp-pim-sm.html#s3-5">3.5 Reading the state</a></p>


The provider will carry its TV channels from the head-end SRC1 to the set-top boxes with IPv4 multicast in PIM sparse
mode.

- Enable IPv4 multicast routing on PE1, PE2, P1 and PE3 on all their interfaces, and on PE4 on both of its links.
- Use P1's Loopback0 (10.255.0.11) as a static RP for 239.0.0.0/8 only, on every router. Groups outside 239.0.0.0/8
  must have no RP.
- RCV2 and RCV3 must receive a channel in 239.16.0.0/16 from SRC1.

### Task M14-2
<p class="tolab"><a href="/_learn?id=XRT-16&amp;step=m14t2">Open in the lab workspace</a> — Read: <a href="f0-m14-igmp-pim-sm.html#s2-6">2.6 Switching to the shortest-path tree</a> · <a href="f0-m14-igmp-pim-sm.html#s3-4">3.4 Staying on the shared tree</a> · <a href="f0-m14-igmp-pim-sm.html#s3-5">3.5 Reading the state</a></p>


The channels in 239.17.0.0/16 are ultra-HD feeds. They must stay on the shared tree through the RP, and must not take
the direct link between PE1 and PE2.

- No router may switch a group in 239.17.0.0/16 to the shortest-path tree.
- Groups in 239.16.0.0/16 must still switch to the shortest-path tree as usual.
- RCV2 and RCV3 must still receive both kinds of channel.
