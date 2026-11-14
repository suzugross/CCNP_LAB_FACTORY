# J0 — Practice 3

These are the tasks of lab **JNT-01**, shown here so that you can read them away from the lab.
Do them in the lab workspace: the **Tasks** tab there has a Check button, staged hints and,
once a task passes, a reference solution for each task. No command examples are given on purpose.

## Topology

```
JUN01 et-0/0/0 ──── et-0/0/0 JUN02 et-0/0/1 ──── eth1 FRR1
         10.0.12.0/30                 10.0.23.0/30
```

| Device | Interface | Address |
|---|---|---|
| JUN01 | et-0/0/0.0 | 10.0.12.1/30 |
| JUN01 | lo0.0 | 192.168.0.1/32 |
| JUN02 | et-0/0/0.0 | 10.0.12.2/30 |
| JUN02 | et-0/0/1.0 | 10.0.23.1/30 |
| JUN02 | lo0.0 | 192.168.0.2/32 |
| FRR1 | eth1 | 10.0.23.2/30 |
| FRR1 | lo | 192.168.0.3/32 |
| FRR1 | lo (server network) | 198.51.100.1/24 |

FRR1 runs OSPF in area 0 on eth1 and advertises 192.168.0.3/32. It does not advertise the server network 198.51.100.0/24.

## J0 From IOS and IOS XR to Junos

These tasks follow the unit J0. They use what you already know from IOS (addresses, OSPF, static routes) and ask you to do it
the Junos way.

### Task J0-4  Reach the server network through the loopback of FRR1
<p class="tolab"><a href="/_learn?id=JNT-01&amp;step=j0t4">Open in the lab workspace</a> — Read: <a href="05-j0-routing-table.html#s2-3">2.3 Preference</a> · <a href="05-j0-routing-table.html#s2-4">2.4 Static routes: the next hop must be connected</a> · <a href="05-j0-routing-table.html#s2-5">2.5 The default policies: why OSPF does not advertise your static route</a> · <a href="05-j0-routing-table.html#s3-1">3.1 A backup static route and a recursive one</a></p>


The servers on 198.51.100.0/24 sit behind FRR1, which does not advertise that network in OSPF.

On JUN02, add a static route to 198.51.100.0/24. Its next hop is the loopback of FRR1 (192.168.0.3), not the link address,
so that the route does not have to be rewritten if the link to FRR1 is renumbered.
If FRR1 later starts to advertise this network into OSPF as an external route, JUN02 must use the OSPF route instead of the static route.

The loopback of JUN02 must reach 198.51.100.1. Do not change the OSPF configuration.
