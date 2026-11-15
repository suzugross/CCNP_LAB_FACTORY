# JNT-03 — J2: Firewall filters

## Ground rules

- JUN01 and JUN02 are where J1 left them: addresses, OSPF, static routes, the BGP session with the ISP, and the routing policies of J1.
  No firewall filter is configured. Traffic flows from the server network of SRV1 all the way past the ISP.
- FRR1 (the ISP), SRV1 (a server) and NET1 (a host on the Internet) are configured already. Do not change them. You can look at them
  from their consoles (`show` commands), and you can send traffic from SRV1 and NET1 (`ping`, `probe`).
- On the **Topology** tab, click a device to open its console. On the Junos routers you are logged in as `admin`.
  SRV1 and NET1 open in a shell (bash).
- `probe <destination> <port> [-s <source>]` is a small tool on SRV1 and NET1. It tries a TCP connection and says in one word what came back:
  `open` (the connection was accepted), `refused` (the packet reached the device, but nothing listens on that port),
  `timeout` (nothing came back) or `unreachable` (an ICMP unreachable message came back).
- SRV1 serves the web on TCP ports 80 and 443. NET1 serves the web on TCP port 8080.
- Each task states what must be true. The **Check** button looks at the devices and sends real traffic from SRV1 and NET1.
- Do the tasks in order. Later tasks build on the results of earlier ones. After you solve a later task, the requirements of the
  earlier tasks must still hold.

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

### Task J2-1  Narrow the entrance from the ISP

Of the traffic that JUN02 receives on its ISP-facing interface (et-0/0/1), JUN02 must let only the following through.

- BGP with the ISP (10.0.23.2)
- ICMP
- Web traffic (TCP ports 80 and 443) to the server network 172.16.20.0/24
- SSH to the server network 172.16.20.0/24, but only from the ISP's operations network 203.0.113.0/24

Any other traffic must be dropped without sending anything back to the source. Count the dropped packets with the counter `ISP-DENY`.

### Task J2-2  Let the replies to connections from the inside through

TCP connections that the inside starts toward hosts beyond the ISP must get their replies back (for example, from the server network
of SRV1 to the web server of NET1). TCP connections that hosts beyond the ISP start toward the inside must stay blocked,
except for what J2-1 allows.

### Task J2-3  Protect the RE of JUN02

Limit the traffic that JUN02 itself (its RE) receives to the following. Treat traffic from every interface the same way.

- BGP. The peers must be exactly the neighbors in JUN02's BGP configuration, and this filter must not need rewriting when a neighbor
  is added or changed
- OSPF
- ICMP
- SSH, only from the server network 172.16.0.0/16
- Replies to TCP connections that JUN02 itself starts

Drop any other traffic, and count it with the counter `RE-DENY`.

### Task J2-4  Drop packets with spoofed sources at the entrance

Of the packets that JUN02 receives from the ISP, JUN02 must drop those whose source address is in one of the following ranges,
and count them with the counter `BOGON`.

- 10.0.0.0/8, 172.16.0.0/12 and 192.168.0.0/16 (private addresses), 100.64.0.0/10 (shared address space), 127.0.0.0/8 (loopback)

Packets from the addresses of the link to the ISP (10.0.23.0/30) must not be dropped. Make this decision in a filter separate from
the one of J2-1, and have it evaluated before the filter of J2-1. The requirements of J2-1 to J2-3 must still hold.

### Task J2-5  Record the dropped traffic

Make the packets that the filter of J2-1 drops visible in JUN02's `show firewall log`. Also record the same packets in the syslog
file `fw-drops`.
