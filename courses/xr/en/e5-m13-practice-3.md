# M13 — Practice 3: flows and SNMP

These are the tasks of lab **XRT-15**, shown here so that you can read them away from the lab.
Do them in the lab workspace: the **Tasks** tab there has a Check button, staged hints and,
once a task passes, a reference solution for each task. No command examples are given on purpose.

## M13 — Automation and assurance

### Task M13-5
<p class="tolab"><a href="/_learn?id=XRT-15&amp;step=m13t5">Open in the lab workspace</a> — Read: <a href="e4-m13-flow-snmp.html#s2-1">2.1 A flow and the flow cache</a> · <a href="e4-m13-flow-snmp.html#s2-2">2.2 Timeouts: when a record leaves the cache</a> · <a href="e4-m13-flow-snmp.html#s2-3">2.3 Export: NetFlow v9 and IPFIX templates</a> · <a href="e4-m13-flow-snmp.html#s3-1">3.1 Flexible NetFlow on IOS XE</a> · <a href="e4-m13-flow-snmp.html#s3-4">3.4 Checking it</a></p>


The NMS collects flow records with IPFIX.

- On PE2, record the IPv4 traffic that enters from customer A (GigabitEthernet2). Each flow record holds the source and
  destination addresses, the protocol, the source and destination ports and the input interface, with the packet and
  byte counts.
- Export the records to the flow collector on SRV01 with IPFIX, from Loopback0.
- Report a long flow at least every 60 seconds.

### Task M13-6
<p class="tolab"><a href="/_learn?id=XRT-15&amp;step=m13t6">Open in the lab workspace</a> — Read: <a href="e4-m13-flow-snmp.html#s2-6">2.6 SNMPv2c: a community and an access list</a> · <a href="e4-m13-flow-snmp.html#s2-7">2.7 SNMPv3: users, groups, views and the engine ID</a> · <a href="e4-m13-flow-snmp.html#s2-8">2.8 Traps and informs</a> · <a href="e4-m13-flow-snmp.html#s3-3">3.3 SNMP on IOS XR</a> · <a href="e4-m13-flow-snmp.html#s3-4">3.4 Checking it</a></p>


Your predecessor configured SNMP on XR01 for the NMS. Two things do not work.

- The NMS reads XR01 with SNMPv2c, community `NMS-RO`, read-only, and only SRV01 may use that community. Today SRV01 gets
  no answer.
- XR01 must send a trap to the trap receiver on SRV01 both when a link goes down and when it comes back up, with
  SNMPv3 (user `nms-trap`, authentication and encryption). Today nothing reaches the trap receiver.
- Keep the community, the user and their passwords. Do not change SRV01.
