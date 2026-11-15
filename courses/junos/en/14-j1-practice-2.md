# J1 — Practice 2

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

### Task J1-3  Accept fewer routes from the ISP
<p class="tolab"><a href="/_learn?id=JNT-02&amp;step=j1t3">Open in the lab workspace</a> — Read: <a href="13-j1-route-filter.html#s2-2">2.2 Match types</a> · <a href="13-j1-route-filter.html#s2-3">2.3 Several route filters in one term: the longest match decides</a> · <a href="11-j1-policy-statement.html#s2-4">2.4 The order of evaluation: terms → the next policy → the default policy</a> · <a href="10-j1-map.html#s2-1">2.1 The two places where policies act, and the default policies</a> · <a href="13-j1-route-filter.html#s3-1">3.1 Accept only the ISP's own network and the default route</a></p>


Of the routes that it receives from the ISP, JUN02 must accept only these:

- the default route;
- routes with a length from /8 to /24 that do not fall within any of these ranges: 10.0.0.0/8, 172.16.0.0/12 and 192.168.0.0/16
  (private addresses), 100.64.0.0/10 (shared address space) and 198.18.0.0/15 (benchmarking).

The routes that are not accepted must not be in use in JUN02's routing table.
