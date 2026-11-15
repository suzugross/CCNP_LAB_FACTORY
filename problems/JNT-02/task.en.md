# JNT-02 — J1: Routing policy

## Ground rules

- JUN01 and JUN02 already have everything from unit J0 (addresses, OSPF, static routes) and the BGP session between JUN02 and FRR1.
  No routing policy is configured.
- FRR1 (the ISP) and SRV1 (a server) are configured already. Do not change them. You may look at them from their consoles (`show` commands).
- Click a device in the **Topology** tab to open its console. You are logged in as `admin` on the Junos routers.
- Each task says what must be true. The **Check** button looks at the state of the devices.
- Do the tasks in order. Later tasks rely on the earlier ones. After you solve a later task, the requirements of the earlier tasks must still be met.

## Topology

```
SRV1 eth1 ──── et-0/0/1 JUN01 et-0/0/0 ──── et-0/0/0 JUN02 et-0/0/1 ──── eth1 FRR1 (ISP)
       172.16.10.0/24                10.0.12.0/30                10.0.23.0/30
```

| Device | Interface | Address |
|---|---|---|
| SRV1 | eth1 | 172.16.10.10/24 (default route via 172.16.10.1) |
| SRV1 | lo (server network) | 172.16.20.1/24 |
| JUN01 | et-0/0/1.0 | 172.16.10.1/24 |
| JUN01 | et-0/0/0.0 | 10.0.12.1/30 |
| JUN01 | lo0.0 | 192.168.0.1/32 |
| JUN02 | et-0/0/0.0 | 10.0.12.2/30 |
| JUN02 | et-0/0/1.0 | 10.0.23.1/30 |
| JUN02 | lo0.0 | 192.168.0.2/32 |
| FRR1 | eth1 | 10.0.23.2/30 |
| FRR1 | lo | 203.0.113.1/32 |

- JUN01 and JUN02 are in AS 65000. They run OSPF area 0 on the link between them and on their loopbacks.
- JUN01 has two static routes. 172.16.20.0/24 is the server network behind SRV1 (172.16.10.10). 172.16.99.0/24 is a test network;
  its route points to discard.
- JUN02 has an eBGP session with FRR1 (the ISP, AS 64500). In place of the Internet table, the ISP sends a default route and a few other routes.

## J1 Routing policy

These tasks follow unit J1. Control which routes go in and out with Junos routing policy.

### Task J1-1  Advertise the server networks into OSPF

Make the two server networks behind JUN01 reachable from JUN02.

JUN01 must advertise 172.16.10.0/24 and 172.16.20.0/24 into OSPF, with a metric of 20 for 172.16.20.0/24.
It must not advertise the test network 172.16.99.0/24. Do not run OSPF on JUN01's server-side interface (et-0/0/1).

### Task J1-2  Hand the ISP's default route to the inside

JUN01 must learn a default route through OSPF. The default route must exist only while JUN02 receives a default route from the ISP:
if the session with the ISP goes down, the default route on JUN01 must go away as well.

Do not put any other route received from the ISP into OSPF.

### Task J1-3  Accept fewer routes from the ISP

Of the routes that it receives from the ISP, JUN02 must accept only these:

- the default route;
- routes with a length from /8 to /24 that do not fall within any of these ranges: 10.0.0.0/8, 172.16.0.0/12 and 192.168.0.0/16
  (private addresses), 100.64.0.0/10 (shared address space) and 198.18.0.0/15 (benchmarking).

The routes that are not accepted must not be in use in JUN02's routing table.

### Task J1-4  Advertise only the summary to the ISP

JUN02 must advertise only 172.16.0.0/16, which covers the server networks, to the ISP. It must not advertise the /24 routes, the links
or the loopbacks. As seen from the ISP, the AS path of this route must be `65000 65000 65000` (your own AS added twice).

The server network on SRV1 (172.16.20.1) must reach the ISP's loopback (203.0.113.1).

### Task J1-5  Mark a single route from the ISP

On JUN02, only the route 203.0.113.0/24 from the ISP must carry community `65000:100` and a local preference of 200.
Do not change the attributes of the other routes (local preference stays at 100, and they carry no community).

The routes that J1-3 accepts must stay the same.
