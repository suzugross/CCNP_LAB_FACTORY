# M9 — Practice 3: shared services and the Internet

These are the tasks of lab **XRT-09**, shown here so that you can read them away from the lab.
Do them in the lab workspace: the **Tasks** tab there has a Check button, staged hints and,
once a task passes, a reference solution for each task. No command examples are given on purpose.

## M9 — L3VPN

### Task M9-3
<p class="tolab"><a href="/_learn?id=XRT-09&amp;step=m9t3">Open in the lab workspace</a> — Read: <a href="94-m9-shared-internet.html#s2-1">2.1 Route targets decide who is connected to whom</a> · <a href="94-m9-shared-internet.html#s2-2">2.2 Importing is not passed on</a> · <a href="94-m9-shared-internet.html#s2-3">2.3 A tag on one route only</a> · <a href="94-m9-shared-internet.html#s2-4">2.4 Several VRFs on one PE</a> · <a href="94-m9-shared-internet.html#s3-1">3.1 Shared services</a></p>


The provider offers shared services from SVC, behind XR01. The servers are on 10.99.1.0/24; 10.99.2.0/24 is internal
to the provider.

- Connect SVC to XR01 in the VRF SVC of the table. XR01 reaches SVC's networks by static routes.
- Every site of customers A and B must reach 10.99.1.0/24, and SVC must reach every site of both customers. No
  customer site may learn 10.99.2.0/24. Customers A and B must still not reach each other.
- The provider's convention for the routes of SVC: every route carries route target 65000:999, and 10.99.1.0/24 carries
  65000:900 in addition. No other route of SVC may carry 65000:900.

### Task M9-4
<p class="tolab"><a href="/_learn?id=XRT-09&amp;step=m9t4">Open in the lab workspace</a> — Read: <a href="94-m9-shared-internet.html#s2-5">2.5 Between a VRF and the global table</a> · <a href="94-m9-shared-internet.html#s2-6">2.6 Following a packet</a> · <a href="94-m9-shared-internet.html#s3-2">3.2 Internet access</a> · <a href="96-m9-appendix.html#s1-2">1.2 In the lab</a></p>


Customer A buys Internet access for its public segments, 198.51.100.0/25 at site 1 and 198.51.100.128/25 at site 2.
INET (AS 64500) is connected to XR01 in the global routing table and advertises a default route and 203.0.113.0/24.

- Run eBGP between XR01 and INET, in the global routing table.
- Both sites of customer A must learn a default route, and their public segments must reach 203.0.113.0/24 in both
  directions.
- INET must learn customer A's two public segments, and no other route from AS 65000.
- Customer B must not learn a default route.
