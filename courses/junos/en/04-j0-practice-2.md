# J0 — Practice 2

These are the tasks of lab **JNT-01**, shown here so that you can read them away from the lab.
Do them in the lab workspace: the **Tasks** tab there has a Check button, staged hints and,
once a task passes, a reference solution for each task.

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

### Task J0-3  Try a risky change that takes itself back
<p class="tolab"><a href="/_learn?id=JNT-01&amp;step=j0t3">Open in the lab workspace</a> — Read: <a href="03-j0-commit.html#s2-3">2.3 A commit on probation</a> · <a href="03-j0-commit.html#s2-2">2.2 The 50 saved configurations</a> · <a href="03-j0-commit.html#s3-1">3.1 A risky change, the Junos way</a></p>


A colleague asks you to raise the MTU of the JUN02 interface toward FRR1 to 9000 bytes, for jumbo frames. FRR1 cannot be changed today.

Put the change in so that JUN02 goes back to its previous configuration by itself unless you confirm the change within a few minutes
(choose the time). Watch what happens to OSPF between JUN02 and FRR1. If the change breaks it, do not confirm the change:
let JUN02 take it back by itself.

In the end, the adjacency between JUN02 and FRR1 is Full again and the MTU of that interface is not 9000.
