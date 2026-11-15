# J0 — Practice 1

These are the tasks of lab **JNT-01**, shown here so that you can read them away from the lab.
Do them in the lab workspace: the **Tasks** tab there has a Check button, staged hints and,
once a task passes, a reference solution for each task.

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
<p class="tolab"><a href="/_learn?id=JNT-01&amp;step=j0t1">Open in the lab workspace</a> — Read: <a href="01-j0-config-tree.html#s2-1">2.1 Where you stand in the tree</a> · <a href="01-j0-config-tree.html#s2-2">2.2 set, delete, and what the CLI refuses</a> · <a href="01-j0-config-tree.html#s2-5">2.5 Interfaces: the physical port, the logical unit, the family</a> · <a href="01-j0-config-tree.html#s3-2">3.2 From IOS to Junos</a></p>


Give JUN01 and JUN02 the addresses in the table on their links and on lo0, and make them take effect.
Each router must answer a ping from its neighbour on every link.

### Task J0-2  Run OSPF across all three
<p class="tolab"><a href="/_learn?id=JNT-01&amp;step=j0t2">Open in the lab workspace</a> — Read: <a href="01-j0-config-tree.html#s2-5">2.5 Interfaces: the physical port, the logical unit, the family</a> · <a href="01-j0-config-tree.html#s3-2">3.2 From IOS to Junos</a> · <a href="00-j0-map.html#s3">3. What it looks like</a></p>


Run OSPF in area 0 on JUN01 and JUN02, on the links between the three routers and on the loopbacks.
No adjacency may be formed on a loopback.
FRR1 must learn the loopbacks of JUN01 and JUN02 through OSPF, and the loopback of JUN01 must reach the loopback of FRR1 (192.168.0.3).
