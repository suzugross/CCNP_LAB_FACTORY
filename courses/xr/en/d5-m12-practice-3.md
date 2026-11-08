# M12 — Practice 3: protecting the data plane

These are the tasks of lab **XRT-14**, shown here so that you can read them away from the lab.
Do them in the lab workspace: the **Tasks** tab there has a Check button, staged hints and,
once a task passes, a reference solution for each task. No command examples are given on purpose.

## M12 — Data-plane protection and QoS

### Task M12-4
<p class="tolab"><a href="/_learn?id=XRT-14&amp;step=m12t4">Open in the lab workspace</a> — Read: <a href="d4-m12-protect.html#s2-1">2.1 uRPF: checking the source against the routing table</a> · <a href="d4-m12-protect.html#s2-2">2.2 The infrastructure ACL</a> · <a href="d4-m12-protect.html#s3-1">3.1 uRPF</a> · <a href="d4-m12-protect.html#s3-2">3.2 The infrastructure ACL</a> · <a href="d4-m12-protect.html#s3-5">3.5 Checking it</a></p>


- CUST1 is attached to XR01 by a single link. Of the packets that XR01 receives from CUST1, drop those whose source is
  not an address that should arrive from CUST1.
- Of the packets that XR01 receives from INET, drop those whose source is an address with no route anywhere. A default
  route does not count as a route. Traffic of multihomed customers can come back over the Internet, so it does not
  matter which interface the route to the source points to.
- At XR01's entrance, drop the packets from INET to the provider's loopbacks (10.255.0.0/24) and core links
  (10.0.0.0/16). Keep the BGP session with INET and the traffic towards the customers. Count in hardware how many
  packets matched each condition.

### Task M12-5
<p class="tolab"><a href="/_learn?id=XRT-14&amp;step=m12t5">Open in the lab workspace</a> — Read: <a href="d4-m12-protect.html#s2-3">2.3 RTBH: dropping by destination</a> · <a href="d4-m12-protect.html#s2-4">2.4 RTBH: dropping by source</a> · <a href="d4-m12-protect.html#s3-3">3.3 The RTBH trigger</a> · <a href="d4-m12-protect.html#s3-4">3.4 The border router: set next-hop discard</a> · <a href="d4-m12-protect.html#s3-5">3.5 Checking it</a></p>


Your predecessor built an RTBH trigger on RR1. When a static route on RR1 is tagged 666, the route is handed to the PEs,
and the PEs drop the packets to that address. Customer CUST2's address 198.51.100.130 is under attack, and both the
victim, 198.51.100.130, and the attacker, 203.0.113.66, are registered on RR1. Yet the packets from the attacker still
reach CUST2.

- Drop the packets from the attacker (an address registered with tag 666 on RR1) at XR01's entrance. Keep dropping the
  packets to the address under attack at XR01 as well.
- The routes of the addresses registered on RR1 must not be advertised to the Internet.
- Keep using the trigger as it is: adding or removing an attacker or a victim must take only a change on RR1, and XR01
  must not list individual addresses.
- PE2 is not changed. PE2 keeps dropping the packets to the registered addresses through the discard address
  192.0.2.1, as before.
