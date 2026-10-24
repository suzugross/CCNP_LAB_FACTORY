# XR Track 06 — High availability

This lab is the practice part of unit **M7 High availability** of the XR track. Read the unit page
*M7 — High availability* first, then work through the tasks here, in order. Each task builds on the previous one.

## Ground rules

- You configure **XR01 only**. RT01 and RT02 are fixed; do not change them. You may log in to them to look.
- No command examples are given. Each task states the behaviour that is required. Use the CLI help (`?`),
  the `show` commands, and the Cisco IOS XR configuration guides and command references to find the commands.
- The **Tasks** tab has a **Check** button for each task. It reads the live state of the devices.
  Leave configuration mode before you press it. IS-IS needs a few seconds to flood a change and recompute routes;
  a broken adjacency takes up to 30 seconds to time out.
- Some Checks cause a fault for a moment and then undo it: the Check of M7-2 shuts a port on RT01, the Check of M7-4
  discards the packets on one link, and the Check of M7-5 restarts processes on XR01. Such a Check takes one to two
  minutes. Do not change the configuration while it runs.
- Hints open one level at a time (keyword → where to look → command). Opened hints are logged.
- XR01 runs **IOS XRv 9000** 26.1.1, the virtual form of the IOS XR routers. It forwards traffic like a hardware
  router and runs BFD, which IOS XRd, used in the earlier labs, does not.

## Topology

| Link | XR01 | Peer | Addressing |
|---|---|---|---|
| BUNDLE | Bundle-Ether1 = GigabitEthernet0/0/0/0 and GigabitEthernet0/0/0/1 | RT01 Port-channel1 = GigabitEthernet1 and GigabitEthernet2 | 10.0.1.0/24 (XR01 .1, RT01 .11) |
| PRIMARY | GigabitEthernet0/0/0/2 | RT02 Ethernet0/0, through the switch SW01 | 10.0.2.0/24 (XR01 .1, RT02 .12) |
| BACKUP | — | RT01 GigabitEthernet3 ─ RT02 Ethernet0/2 | 10.0.12.0/24 (RT01 .11, RT02 .12) |

| Router | Platform | Loopback0 | Other networks |
|---|---|---|---|
| XR01 | IOS XRv 9000 26.1.1 | 10.255.0.1/32 | platform 10.30.0.0/16 (Loopback10, in BGP only) |
| RT01 | Catalyst 8000V, IOS XE 17.15 | 10.255.0.11/32 | users 10.10.0.0/16 |
| RT02 | IOS XE 17.15 | 10.255.0.12/32 | services 10.20.0.0/16 |

- The three routers run IS-IS instance `CORE` for IPv4: area 49.0001, Level 2 only, wide metrics, point-to-point
  circuits. BACKUP has a metric of 1000 in both directions; all other links have the default metric.
- XR01 and RT02 run iBGP in AS 65000 between their loopbacks. XR01 advertises 10.30.0.0/16 and RT02 advertises
  10.20.0.0/16.
- RT01 runs LACP in active mode on both members of Port-channel1.
- RT02 has BFD on Ethernet0/0 (100 ms, multiplier 3) and has enabled it for IS-IS there. RT02 has BGP graceful
  restart enabled.

## M7 — High availability

### Task M7-1

The BUNDLE link was built last week under change CHG-0917. XR01 shows Bundle-Ether1 as up, but XR01 and RT01 cannot
exchange traffic across it, and IS-IS has no adjacency on it. RT01 is configured correctly.

- Make Bundle-Ether1 carry traffic between XR01 and RT01, with LACP running on both members and both members in use.
- Bring up the IS-IS adjacency with RT01 on Bundle-Ether1.
- IP packets of 1500 bytes must cross the bundle in both directions without fragmentation.

### Task M7-2

The operations team has set two rules for the bundle.

- Bundle-Ether1 must not carry traffic on one member alone. With fewer than two members in use, the traffic must take
  the backup path.
- A member that stops working must leave the bundle within five seconds, also when its port stays up. The Check shuts
  RT01 GigabitEthernet2 for a few seconds, which XR01 does not see as a link failure, and then restores it.

### Task M7-3

Now that the bundle works, users report that the traffic between RT01's users and RT02's services still runs over the
backup link and not through XR01. XR01 had maintenance two weeks ago, under change CHG-0903.

- Make the traffic between RT01 and RT02 take the path through XR01 again.
- Keep one protection from that maintenance: whenever XR01 starts up, the other routers must not send transit traffic
  through XR01 until its BGP has converged.

### Task M7-4

The PRIMARY link runs through a switch. When the far side fails, XR01's port stays up, and the traffic is lost until
IS-IS notices that RT02 is gone.

- When the primary path fails while the ports at both ends stay up, the traffic between RT01 and RT02 must move to the
  backup path within one second. RT02 is already prepared for this.
- The Check discards all packets on the link between SW01 and RT02 for a while and counts the pings from RT01 to RT02's
  services network that are lost.

### Task M7-5

XR01 is to receive a software patch that restarts its routing processes. The service owners have set these conditions.

- When the IS-IS process of XR01 restarts, no IS-IS adjacency may go down as RT01 and RT02 see it.
- When the BGP process of XR01 restarts, RT02 must keep the routes that it has learned from XR01.
- The Check restarts each of the two processes on XR01 once.
