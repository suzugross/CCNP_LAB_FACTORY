# Lab GEN-DOJO-PREFIX-45311 : ip prefix-list Dojo (10 Drills · Difficulty 3)

## About This Lab (Kata Practice)

The upstream router **RT02 (AS65099)** advertises a large number of routes (a test battery) by eBGP.
On **RT01 (AS65001)**, for each of the 10 small tasks below,
**define one ip prefix-list with the specified name**. That is the entire lab.

- The prefix lists only need to be **defined** (applying them to a neighbor is not required).
- Scoring is based not on how a list is written (sequence numbers, equivalent expressions) but on
  semantic equivalence — "**what it permits and what it denies**" (10 points per task; no partial credit).
- The lab can be regenerated repeatedly with a different seed. Repeat it until it becomes second nature.

```
  RT01 (TARGET, AS65001)  Lo0=1.1.1.1
    | E0/0  10.1.12.1
    | E0/0  10.1.12.2
  RT02 (FEEDER, AS65099)  Lo0=2.2.2.2  ← battery advertiser (do not modify)
```

## How to Self-Check (Practice Swings)

- The entire advertised battery: `show ip bgp`
- Verify the effect of your list **on the spot**: `show ip bgp prefix-list PL-x`
  (read-only. It displays the BGP table as matched by the list and does not affect the session.
  `clear ip bgp` is not required.)
- Verify the definitions: `show ip prefix-list`

## Tasks (the list names must match exactly)

### Task 1 — list name `PL-1`

> Permit only the route `192.168.100.0/24` **itself**. Do not permit any longer (more specific) route under it, or any other route.

### Task 2 — list name `PL-2`

> Of the routes that fall within `172.20.0.0/16`, permit all routes with a prefix length of **/22 or longer** (up to /32). Do not permit anything else.

### Task 3 — list name `PL-3`

> Permit only the route `172.20.0.0/16` **itself**. Do not permit any longer (more specific) route under it, or any other route.

### Task 4 — list name `PL-4`

> Of the routes that fall within `192.168.100.0/22`, permit all routes with a prefix length of **/25 or longer** (up to /32). Do not permit anything else.

### Task 5 — list name `PL-5`

> Of the routes that fall within `172.20.0.0/16`, permit all routes with a prefix length of **/20 or shorter** (including the aggregate route of the range itself, if it exists). Do not permit anything else.

### Task 6 — list name `PL-6`

> **Deny all host routes (/32)**, and permit all other routes (including the default route).

### Task 7 — list name `PL-7`

> This list is **predefined** (two lines: `seq 10 permit 10.0.0.0/8` and `seq 30 permit 172.20.64.0/20`). **Add** a line at `seq 20`, **between** the two existing lines, that permits the route `172.20.84.0/24` itself (exact match). Deleting or modifying the existing lines, recreating the list, and resequencing it are not allowed.

### Task 8 — list name `PL-8`

> Permit all routes that fall within `192.168.100.0/22` and are **exactly /24**, and only those (the aggregate route of the range itself and routes longer than /24 are not permitted).

### Task 9 — list name `PL-9`

> Of the routes that fall within `10.0.0.0/8`, permit all routes with a prefix length **from /24 through /26**. Do not permit lengths outside this band (including the aggregate route of the range itself).

### Task 10 — list name `PL-10`

> Permit all routes that fall within `172.20.0.0/16` with a prefix length of **/22 or shorter** (including the aggregate route of the range itself). However, **deny `172.20.32.0/19` as an exception**.

## Restrictions

1. **Do not change the configuration of RT02 (FEEDER)** (verifying its state with show commands is allowed).
2. **Do not change the BGP, interface, or routing configuration** of RT01
   (the work consists only of defining ip prefix-lists).
3. For a task with a predefined list, **deleting, modifying, or resequencing the existing lines is not allowed**.
4. The list names must be exactly as specified in the tasks (`PL-1` through `PL-10`), including case.

## Access and Scoring

SSH `SUZUKI / CCNP` (the mgmt addresses are assigned in order, starting from 10.1.10.11). The CML console can also be used.
```
ansible-playbook playbooks/grade.yml -e problem=GEN-DOJO-PREFIX-45311 --vault-password-file <(printf 'CCNP\n')
```
