# J1 — Practice 1

These are the tasks of lab **JNT-02**, shown here so that you can read them away from the lab.
Do them in the lab workspace: the **Tasks** tab there has a Check button, staged hints and,
once a task passes, a reference solution for each task.

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
<p class="tolab"><a href="/_learn?id=JNT-02&amp;step=j1t1">Open in the lab workspace</a> — Read: <a href="11-j1-policy-statement.html#s2-1">2.1 The shape of a policy-statement</a> · <a href="11-j1-policy-statement.html#s2-2">2.2 from: OR within a kind, AND across kinds</a> · <a href="11-j1-policy-statement.html#s2-3">2.3 then: three kinds of action</a> · <a href="11-j1-policy-statement.html#s2-6">2.6 Exporting into OSPF: the external type and metric</a> · <a href="11-j1-policy-statement.html#s3-1">3.1 One static route into OSPF, as type 1</a></p>


Make the two server networks behind JUN01 reachable from JUN02.

JUN01 must advertise 172.16.10.0/24 and 172.16.20.0/24 into OSPF, with a metric of 20 for 172.16.20.0/24.
It must not advertise the test network 172.16.99.0/24. Do not run OSPF on JUN01's server-side interface (et-0/0/1).

### Task J1-2  Hand the ISP's default route to the inside
<p class="tolab"><a href="/_learn?id=JNT-02&amp;step=j1t2">Open in the lab workspace</a> — Read: <a href="11-j1-policy-statement.html#s2-4">2.4 The order of evaluation: terms → the next policy → the default policy</a> · <a href="11-j1-policy-statement.html#s2-7">2.7 BGP routes into OSPF</a> · <a href="11-j1-policy-statement.html#s2-6">2.6 Exporting into OSPF: the external type and metric</a></p>


JUN01 must learn a default route through OSPF. The default route must exist only while JUN02 receives a default route from the ISP:
if the session with the ISP goes down, the default route on JUN01 must go away as well.

Do not put any other route received from the ISP into OSPF.
