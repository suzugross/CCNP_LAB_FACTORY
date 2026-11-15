# J1 — Practice 3

These are the tasks of lab **JNT-02**, shown here so that you can read them away from the lab.
Do them in the lab workspace: the **Tasks** tab there has a Check button, staged hints and,
once a task passes, a reference solution for each task.

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

### Task J1-4  Advertise only the summary to the ISP
<p class="tolab"><a href="/_learn?id=JNT-02&amp;step=j1t4">Open in the lab workspace</a> — Read: <a href="15-j1-bgp.html#s2-6">2.6 Sending an aggregate route</a> · <a href="15-j1-bgp.html#s2-5">2.5 Changing attributes: local preference, community, AS path, MED</a> · <a href="15-j1-bgp.html#s2-2">2.2 BGP's default policies</a> · <a href="11-j1-policy-statement.html#s2-5">2.5 The order of terms, and insert</a> · <a href="15-j1-bgp.html#s3-1">3.1 Sending the inside networks to the ISP as /24s, with a MED</a></p>


JUN02 must advertise only 172.16.0.0/16, which covers the server networks, to the ISP. It must not advertise the /24 routes, the links
or the loopbacks. As seen from the ISP, the AS path of this route must be `65000 65000 65000` (your own AS added twice).

The server network on SRV1 (172.16.20.1) must reach the ISP's loopback (203.0.113.1).

### Task J1-5  Mark a single route from the ISP
<p class="tolab"><a href="/_learn?id=JNT-02&amp;step=j1t5">Open in the lab workspace</a> — Read: <a href="15-j1-bgp.html#s2-5">2.5 Changing attributes: local preference, community, AS path, MED</a> · <a href="11-j1-policy-statement.html#s2-4">2.4 The order of evaluation: terms → the next policy → the default policy</a> · <a href="15-j1-bgp.html#s2-4">2.4 The levels to write policy at: global, group, neighbor</a> · <a href="15-j1-bgp.html#s3-2">3.2 Marking received routes: inserting a term into a policy</a></p>


On JUN02, only the route 203.0.113.0/24 from the ISP must carry community `65000:100` and a local preference of 200.
Do not change the attributes of the other routes (local preference stays at 100, and they carry no community).

The routes that J1-3 accepts must stay the same.
