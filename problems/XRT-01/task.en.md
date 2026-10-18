# XR Track 01 — Finding Your Way / Managing Configuration

This lab is the practice half of two units of the XR track: **M0 Finding your way** and **M1 Managing configuration**.
Read the unit first, then work through its tasks here. One lab serves both units; do M0 before M1.

## Ground rules

- You configure **XR01 only**. RT01 and RT02 are fixed; do not change them. You may log in to them to look.
- No command examples are given. Each task states the behaviour that is required. Use the CLI help (`?`),
  the `show` commands, and the Cisco IOS XR configuration guides and command references to find the commands.
- The **Steps** tab has a **Check** button for each task. It reads the live state of the devices.
  Leave configuration mode before you press it.
- Hints open one level at a time (keyword → where to look → command). Opened hints are logged.
- Log in with the lab credentials. Management access (interface `MgmtEth0/RP0/CPU0/0`, VRF `MGMT`) must keep
  working throughout; the checks reach XR01 through it.

## Topology

| Link | XR01 | Peer | Addressing |
|---|---|---|---|
| LINK1 | GigabitEthernet0/0/0/0 | RT01 Ethernet0/0 | 10.0.12.0/24 (XR01 .1, RT01 .2), 2001:DB8:12::/64 (XR01 ::1, RT01 ::2) |
| LINK2 | GigabitEthernet0/0/0/2 | RT01 Ethernet0/1 | 10.0.21.0/24 (XR01 .1, RT01 .2) |
| CUST-A | GigabitEthernet0/0/0/1 | RT02 Ethernet0/0 | 10.0.13.0/24 (XR01 .1, RT02 .2) |
| LINK3 | GigabitEthernet0/0/0/3 | RT01 Ethernet0/2 | 10.0.31.0/24 (XR01 .1, RT01 .2) |

- XR01 Loopback0 1.1.1.1/32. RT01 Loopback0 2.2.2.2/32.
- RT01 runs OSPF process 1, area 0, on LINK1, LINK2, LINK3 and Loopback0. LINK3 uses MD5 authentication. It also holds 8.8.8.8/32, which is not in OSPF,
  and is ready to peer with XR01 by eBGP over LINK1 (RT01 AS 65002, expecting XR01 in AS 65001).
- RT02 is the CE of customer A. Its LAN is 172.16.2.0/24 (RT02 172.16.2.1). It has a default route to XR01.

## M0 — Finding your way

XR01 has been handed over half-configured. Parts of the configuration are present but wrong or incomplete.
Find out what is there before you change anything.

### Task M0-1

Ensure that XR01 and RT01 can reach each other over LINK1 with both IPv4 and IPv6.

### Task M0-2

Ensure that XR01 learns 2.2.2.2/32 from RT01 by OSPF over LINK1, and that RT01 learns 1.1.1.1/32 from XR01.
LINK1 must be an area 0 link. Leave LINK2 and LINK3 as they are for now; they are the subjects of Tasks M1-6 and M1-7.

### Task M0-3

Customer A must be isolated from the global routing table.
Ensure that the link to RT02 belongs to VRF `CUST-A`, that it keeps its address, and that XR01 can reach
the customer LAN 172.16.2.0/24 inside that VRF. The link's subnet must no longer appear in the global table.

### Task M0-4

Ensure that XR01 forwards traffic for unknown destinations to RT01 over LINK1, using a route you configure on XR01.
XR01 must be able to reach 8.8.8.8.

## M1 — Managing configuration

Use a label on every commit where the task names one. Labels are how the checks find your commits.
A label can be used only once. If you need to redo a labelled commit, add `-2`, `-3`, … to the label
(for example `M1-T3-2`); the checks use the newest of them.

### Task M1-1

**Label:** `M1-T1` (step 2)

1. Make a change that would cut you off if it stayed: administratively disable LINK1 on XR01. Apply it in such a way
   that XR01 restores the previous configuration by itself if you take no further action. Take no further action,
   and confirm that LINK1 has come back.
2. Add Loopback50 with the address 10.50.50.50/32. Apply it the same way, with the label `M1-T1`, and this time
   make the change permanent before XR01 restores the previous configuration.

### Task M1-2

**Labels:** `M1-T2A` (step 1), `M1-T2B` (step 2)

1. Add Loopback61 with the address 10.61.61.61/32 in a commit labelled `M1-T2A`.
2. Add Loopback62 with the address 10.62.62.62/32 in a separate commit labelled `M1-T2B`.
3. Undo exactly what `M1-T2A` did. Do not type the reverse configuration yourself, and do not undo `M1-T2B`.

### Task M1-3

**Label:** `M1-T3` (the commit that completes the task; the refused first attempt does not use up the label)

In a **single** commit labelled `M1-T3`, bring up the eBGP session with RT01 over LINK1 (XR01 is AS 65001,
router ID 1.1.1.1) and add Loopback70 with the address 10.70.70.70/32. XR01 must accept the prefixes RT01 sends,
through an inbound policy named `RP-IN` that accepts everything.

First attempt the commit **without** defining `RP-IN`. Before you fix it, answer for yourself:

- Why was the commit refused, and where does XR01 tell you?
- Did Loopback70 make it into the running configuration?
- Is the configuration you typed lost?

Then complete the task.

### Task M1-4

Open a second session to XR01 (for example, Telnet from RT01 to 10.0.12.1) so that you have two sessions at once.

1. In session A, enter configuration mode and stage a change without committing it. In session B, commit
   a different change. Then commit in session A and read what XR01 tells you.
2. In session A, enter configuration mode in such a way that nobody else can change the running configuration
   while you are in it. In session B, try to commit a change. Find out from session B who is holding the lock.

Press **Check** while session A still holds the lock. Afterwards leave configuration mode in both sessions
and discard anything left uncommitted.

### Task M1-5 (no check)

Enter configuration mode and stage only this: the host name `XR01-NEW`. Do **not** commit.

Find out exactly what would be removed from the running configuration if you replaced the entire configuration
with what you have staged. Answer for yourself: would the checks still be able to reach XR01 afterwards?
Then discard the staged change.

### Task M1-6

The NOC reports that the OSPF adjacency between XR01 and RT01 over LINK2 has been down since a series of changes
was made to XR01. Several changes were committed; only one of them is at fault.

Identify the change that broke the adjacency and undo that change only. The other changes must stay in place.
Do not change RT01.

### Task M1-7

Change `CHG2001` was made outside the change window and must be backed out completely: every part of XR01
that `CHG2001` touched must be exactly as it was before. The values that were in place before the change were not
recorded anywhere. Everything else committed on XR01 — before or after `CHG2001`, including your own work in
the earlier tasks — must stay. Do not change RT01.
