# Lab ENARSI-EIGRP-VRF-01 : Multitenant Aggregation with VRF-Lite and EIGRP Named Mode

## Scenario
The shared aggregation router **RT02** in the data center must now host two tenants.

- **Tenant A**: two sites (RT01 = site1 / RT04 = site2). EIGRP **AS 100**.
- **Tenant B**: one site (RT03 = site1). EIGRP **AS 200**.

As a leftover from before the consolidation, both tenants **reuse the same overlapping
172.16.0.0/16 addressing plan** (Tenant A site1 and Tenant B site1 both use
172.16.10.0/24 and 172.16.11.0/24).
Configure VRF-Lite on RT02 to provide fully isolated routing for each tenant.

## Topology
```
RT01 (A-site1)  ──10.10.1.0/30──┐
  Lo1 172.16.10.1/24            │e0/0
  Lo2 172.16.11.1/24            │
                              RT02 (shared aggregation router; candidate scope)
RT04 (A-site2)  ──10.10.2.0/30──┤e0/1
  Lo1 172.16.20.1/24            │
                                │e0/2
RT03 (B-site1)  ──10.20.1.0/30──┘
  Lo1 172.16.10.1/24  ← overlaps with Tenant A
  Lo2 172.16.11.1/24  ← overlaps with Tenant A
  Lo3 172.16.30.1/24
```

## Existing Configuration (do not modify)
- The three CE routers (RT01/RT03/RT04) are **preconfigured and must not be changed**.
  - Tenant A CEs run EIGRP AS100 (classic mode) with **MD5 authentication**
    (key chain `KC-A` / key 1 / key-string `Suzu2026A`) already configured on the
    interfaces facing RT02.
  - The Tenant B CE runs EIGRP AS200 (classic mode) with no authentication.
- Link addresses are already configured on the RT02 interfaces.
  **Preserve the current addressing plan.**

## Requirements (configure on RT02 only)

1. **VRF**: Create one VRF per tenant and assign the corresponding interfaces.
   - `TENANT-A` (rd **65000:100**) … `Ethernet0/0` (facing RT01), `Ethernet0/1` (facing RT04)
   - `TENANT-B` (rd **65000:200**) … `Ethernet0/2` (facing RT03)
2. **EIGRP**: Per corporate standard, host both tenant address families under a
   **single named-mode virtual instance `SUZUNET`**.
   - Tenant A = **AS 100** / Tenant B = **AS 200**
   - Adjacencies must be established with every CE (**including authentication** for Tenant A).
3. **Route summarization**: Toward Tenant A site2 (RT04), advertise the two site1 /24s
   **as a single summary (`172.16.10.0/23`)**. The specific /24s must not be visible at site2.
4. **Isolation**: Routes must not leak between tenants. The overlapping prefixes of both
   tenants must coexist on RT02, each within its own VRF.

## Verification Guidelines
- From RT04, a ping to 172.16.10.1 sourced from 172.16.20.1 succeeds.
- From RT02, a ping to Tenant B's 172.16.30.1 succeeds.
- In each VRF routing table on RT02, 172.16.10.0/24 is installed via a different neighbor.

## Restrictions
- Configuration changes are allowed on **RT02 only**. You may log in to the CEs for
  verification (show commands) only.
- Do not use static routes or redistribution (use only native EIGRP features).

## Scoring
```
ansible-playbook playbooks/grade.yml -e problem=ENARSI-EIGRP-VRF-01 --vault-password-file <(printf 'CCNP\n')
```
