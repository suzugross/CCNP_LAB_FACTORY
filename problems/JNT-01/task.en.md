# JNT-01 — J0: From IOS and IOS XR to Junos

## Ground rules

- JUN01 and JUN02 start with nothing configured except their management access. You configure both.
- FRR1 is configured already. Do not change it. You may look at it from its console (`show` commands).
- Click a device in the **Topology** tab to open its console. You are logged in as `admin` on the Junos routers.
- Each task says what must be true, not which commands to use. The **Check** button looks at the state of the devices.
- Do the tasks in order. Later tasks rely on the earlier ones.

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

### Task J0-1  Address the two Junos routers

Give JUN01 and JUN02 the addresses in the table on their links and on lo0, and make them take effect.
Each router must answer a ping from its neighbour on every link.

### Task J0-2  Run OSPF across all three

Run OSPF in area 0 on JUN01 and JUN02, on the links between the three routers and on the loopbacks.
No adjacency may be formed on a loopback.
FRR1 must learn the loopbacks of JUN01 and JUN02 through OSPF, and the loopback of JUN01 must reach the loopback of FRR1 (192.168.0.3).

### Task J0-3  Try a risky change that takes itself back

A colleague asks you to raise the MTU of the JUN02 interface toward FRR1 to 9000 bytes, for jumbo frames. FRR1 cannot be changed today.

Put the change in so that JUN02 goes back to its previous configuration by itself unless you confirm the change within a few minutes
(choose the time). Watch what happens to OSPF between JUN02 and FRR1. If the change breaks it, do not confirm the change:
let JUN02 take it back by itself.

In the end, the adjacency between JUN02 and FRR1 is Full again and the MTU of that interface is not 9000.

### Task J0-4  Reach the server network through the loopback of FRR1

The servers on 198.51.100.0/24 sit behind FRR1, which does not advertise that network in OSPF.

On JUN02, add a static route to 198.51.100.0/24. Its next hop is the loopback of FRR1 (192.168.0.3), not the link address,
so that the route does not have to be rewritten if the link to FRR1 is renumbered.
If FRR1 later starts to advertise this network into OSPF as an external route, JUN02 must use the OSPF route instead of the static route.

The loopback of JUN02 must reach 198.51.100.1. Do not change the OSPF configuration.
