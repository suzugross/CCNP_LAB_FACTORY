# M6 — Practice 3: GTSM and TCP-AO

These are the tasks of lab **XRT-17**, shown here so that you can read them away from the lab.
Do them in the lab workspace: the **Tasks** tab there has a Check button, staged hints and,
once a task passes, a reference solution for each task. No command examples are given on purpose.

## M6 — BGP (supplement)

### Task M6-7
<p class="tolab"><a href="/_learn?id=XRT-17&amp;step=m6t7">Open in the lab workspace</a> — Read: <a href="65-m6-protect-session.html#s2-1">2.1 Checking the neighbor with the TTL: GTSM</a> · <a href="65-m6-protect-session.html#s3-1">3.1 The GTSM configuration</a> · <a href="65-m6-protect-session.html#s3-4">3.4 Reading the output, and pitfalls</a></p>


AS 65100 has agreed to use GTSM (Generalized TTL Security Mechanism) on the eBGP session between PE2 and X1.

- Configure GTSM for this session on both PE2 and X1 so that it accepts only packets from the directly connected peer, one hop away.
- The session must be established, and PE2 must continue to learn routes from X1.

### Task M6-8
<p class="tolab"><a href="/_learn?id=XRT-17&amp;step=m6t8">Open in the lab workspace</a> — Read: <a href="65-m6-protect-session.html#s2-2">2.2 Signing the TCP segments: MD5 and TCP-AO</a> · <a href="65-m6-protect-session.html#s2-3">2.3 The TCP-AO keys: key chain, KeyID, SendID and ReceiveID</a> · <a href="65-m6-protect-session.html#s3-3">3.3 The TCP-AO configuration</a> · <a href="65-m6-protect-session.html#s3-4">3.4 Reading the output, and pitfalls</a></p>


Protect the eBGP session between PE3 and X2 with the TCP Authentication Option (TCP-AO). The values have been agreed with AS 65100.

| Item | Value |
|---|---|
| Key chain name | AS65100-AO |
| Key ID | 7 |
| Cryptographic algorithm | AES-128-CMAC-96 (aes-128-cmac on IOS XE) |
| Key string | 5A3C9E107B2D4F6681A0C3E5F7092B4D |
| SendID and ReceiveID on PE3 | 37 and 73 (X2 uses SendID 73 and ReceiveID 37) |
| TCP options | Included in the MAC calculation |
| Key lifetime | Infinite |

- Configure both PE3 and X2. The session must be established with TCP-AO.
