# M14 — Practice 3: BSR and IPv6

These are the tasks of lab **XRT-16**, shown here so that you can read them away from the lab.
Do them in the lab workspace: the **Tasks** tab there has a Check button, staged hints and,
once a task passes, a reference solution for each task. No command examples are given on purpose.

## M14 — Multicast

### Task M14-5
<p class="tolab"><a href="/_learn?id=XRT-16&amp;step=m14t5">Open in the lab workspace</a> — Read: <a href="f4-m14-rp-ipv6-ts.html#s2-1">2.1 BSR: two elections</a> · <a href="f4-m14-rp-ipv6-ts.html#s2-3">2.3 Static and dynamic together</a> · <a href="f4-m14-rp-ipv6-ts.html#s3-1">3.1 BSR</a></p>


The provider no longer wants to configure the RP of the TV and ultra-HD channels by hand on every router.

- Use the bootstrap router (BSR) mechanism for 239.16.0.0/15. The candidate RPs are P1, PE3 and PE4, each with its
  Loopback0, and each announces 239.16.0.0/15 only. P1 must be the RP. If P1 stops announcing, PE3 must take over, and
  PE4 may become the RP only when both P1 and PE3 have stopped.
- The candidate BSRs are PE1 and P1, each with its Loopback0. PE1 must be the BSR, and P1 takes over only if PE1 stops.
- Every router must learn the RP of 239.16.0.0/15 through BSR. RCV2 and RCV3 must still receive the channels.

### Task M14-6
<p class="tolab"><a href="/_learn?id=XRT-16&amp;step=m14t6">Open in the lab workspace</a> — Read: <a href="f4-m14-rp-ipv6-ts.html#s2-4">2.4 IPv6: PIMv6 and MLD</a> · <a href="f4-m14-rp-ipv6-ts.html#s2-5">2.5 Troubleshooting: follow the tree from the receiver</a> · <a href="f4-m14-rp-ipv6-ts.html#s3-3">3.3 IPv6 multicast</a> · <a href="f4-m14-rp-ipv6-ts.html#s3-4">3.4 What faults look like</a></p>


Your predecessor started an IPv6 multicast trial: channels in FF0E::16:0/112 from SRC1 (2001:db8:100:1::1) to RCV2 and
RCV3, with P1 (2001:db8:255::11) as the RP. The RP accepts Register messages only from sources in the head-end LAN
(2001:db8:100:1::/64). Nothing has ever arrived.

- RCV2 and RCV3 must receive a channel in FF0E::16:0/112 from SRC1.
- Keep the restriction on the RP: only sources in the head-end LAN may register.
