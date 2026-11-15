# J2 — Practice 3

These are the tasks of lab **JNT-03**, shown here so that you can read them away from the lab.
Do them in the lab workspace: the **Tasks** tab there has a Check button, staged hints and,
once a task passes, a reference solution for each task.

## Topology

```
SRV1 eth1 ──── et-0/0/1 JUN01 et-0/0/0 ──── et-0/0/0 JUN02 et-0/0/1 ──── eth1 FRR1(ISP) eth2 ──── eth1 NET1
       172.16.10.0/24                10.0.12.0/30                10.0.23.0/30                 192.0.2.0/30
```

| Device | Interface | Address |
|---|---|---|
| SRV1 | eth1 | 172.16.10.10/24 (default route via 172.16.10.1) |
| SRV1 | lo (the server network) | 172.16.20.1/24 |
| JUN01 | et-0/0/1.0 | 172.16.10.1/24 |
| JUN01 | et-0/0/0.0 | 10.0.12.1/30 |
| JUN01 | lo0.0 | 192.168.0.1/32 |
| JUN02 | et-0/0/0.0 | 10.0.12.2/30 |
| JUN02 | et-0/0/1.0 | 10.0.23.1/30 |
| JUN02 | lo0.0 | 192.168.0.2/32 |
| FRR1 | eth1 | 10.0.23.2/30 |
| FRR1 | eth2 | 192.0.2.1/30 |
| FRR1 | lo | 203.0.113.1/32 |
| NET1 | eth1 | 192.0.2.2/30 (default route via 192.0.2.1) |
| NET1 | lo | 198.51.100.10/32, 203.0.113.10/32, 10.200.0.1/32, 192.168.50.1/32 |

- JUN01 and JUN02 are in AS 65000. They run OSPF in area 0 between them, and JUN02 has an eBGP session with FRR1 (the ISP, AS 64500).
  As set up in J1, JUN02 advertises only 172.16.0.0/16 to the ISP and hands the default route from the ISP to JUN01 through OSPF.
- NET1 is a host on the Internet, beyond the ISP. Its loopback addresses serve as different sources: 198.51.100.10 is an ordinary host,
  203.0.113.10 is a host in the ISP's operations network, and 10.200.0.1 and 192.168.50.1 are sources that pretend to be private addresses.

## J2 Firewall filters

These tasks follow unit J2. Control the traffic that passes through JUN02, and the traffic that JUN02 itself receives,
with Junos firewall filters.

### Task J2-4  Drop packets with spoofed sources at the entrance
<p class="tolab"><a href="/_learn?id=JNT-03&amp;step=j2t4">Open in the lab workspace</a> — Read: <a href="25-j2-lists-logging.html#s2-1">2.1 Filter lists</a> · <a href="25-j2-lists-logging.html#s2-2">2.2 Lists of addresses, and except</a> · <a href="25-j2-lists-logging.html#s2-3">2.3 Counter names in a list</a></p>


Of the packets that JUN02 receives from the ISP, JUN02 must drop those whose source address is in one of the following ranges,
and count them with the counter `BOGON`.

- 10.0.0.0/8, 172.16.0.0/12 and 192.168.0.0/16 (private addresses), 100.64.0.0/10 (shared address space), 127.0.0.0/8 (loopback)

Packets from the addresses of the link to the ISP (10.0.23.0/30) must not be dropped. Make this decision in a filter separate from
the one of J2-1, and have it evaluated before the filter of J2-1. The requirements of J2-1 to J2-3 must still hold.

### Task J2-5  Record the dropped traffic
<p class="tolab"><a href="/_learn?id=JNT-03&amp;step=j2t5">Open in the lab workspace</a> — Read: <a href="25-j2-lists-logging.html#s2-4">2.4 log and syslog</a> · <a href="25-j2-lists-logging.html#s2-3">2.3 Counter names in a list</a></p>


Make the packets that the filter of J2-1 drops visible in JUN02's `show firewall log`. Also record the same packets in the syslog
file `fw-drops`.
