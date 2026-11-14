# [PoC] containerlab learning mode — Junos × FRR

> A test bed for the lab workspace on containerlab (not a graded problem).

## Topology

```
JUN01 et-0/0/0 ──── eth1 FRR1
       10.0.14.0/30
```

| Device | Interface | Address |
|---|---|---|
| JUN01 | et-0/0/0.0 | 10.0.14.1/30 |
| JUN01 | lo0.0 | 192.168.0.1/32 |
| FRR1 | eth1 | 10.0.14.2/30 |
| FRR1 | lo | 192.168.0.4/32 |

FRR1 is already configured. Do not change it.

## M0 Getting around

JUN01 starts with no configuration other than its management access. Click a device in the Topology tab to open its console.

### Task M0-1  Address the link and the loopback

Give JUN01 the addresses in the table on et-0/0/0.0 and lo0.0, and make them take effect.

### Task M0-2  Exchange routes with FRR1

Run OSPF in area 0 between JUN01 and FRR1. JUN01 advertises its loopback without forming adjacencies on it.
From the loopback of JUN01, the loopback of FRR1 (192.168.0.4) must answer a ping.
