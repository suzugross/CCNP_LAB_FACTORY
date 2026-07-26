# 模範解答 : ENCOR-DHCP-01 (DHCPv4 一気通貫)

> RT01(サーバ)・RT02(リレー+ACL)・CL1〜CL3(クライアント) を設定。
> 既設(変更禁止): RT01/RT02 の IF アドレス・静的経路。

## CL1/CL2/CL3 — クライアント (取得)

```
interface Ethernet0/0
 ip address dhcp
 no shutdown
```

CL1 のみ追加（固定割当を「01+MAC」の教科書形式で受けるため）:
```
interface Ethernet0/0
 ip dhcp client client-id Ethernet0/0    ! 識別子を IF の MAC に変更
```

## RT01 — DHCP サーバ

```
ip dhcp excluded-address 10.0.10.1 10.0.10.9
ip dhcp excluded-address 10.0.20.1 10.0.20.9
ip dhcp excluded-address 10.0.30.1 10.0.30.9
!
ip dhcp pool NET10
 network 10.0.10.0 255.255.255.0
 default-router 10.0.10.1
 dns-server 198.51.100.53
ip dhcp pool NET20
 network 10.0.20.0 255.255.255.0
 default-router 10.0.20.1
 dns-server 198.51.100.53
ip dhcp pool NET30
 network 10.0.30.0 255.255.255.0
 default-router 10.0.30.1
 dns-server 198.51.100.53
!
! 固定割当 (CL1 の MAC は show interfaces Ethernet0/0 の bia で調査。
!  例: aabb.cc02.0100 → client-identifier は 01+MAC を 2byte 区切り)
ip dhcp pool CL1-FIXED
 host 10.0.20.50 255.255.255.0
 client-identifier 01aa.bbcc.0201.00
```

## RT02 — リレー + DHCP-only ACL

```
interface Ethernet0/1
 ip helper-address 10.0.12.1
interface Ethernet0/2
 ip helper-address 10.0.12.1
!
ip access-list extended DHCP-ONLY
 permit udp any eq bootpc any eq bootps
 permit icmp any any
 deny ip any any          ! 明示 deny(遮断実績のカウンタ監査用・仕様指定)
!
interface Ethernet0/1
 ip access-group DHCP-ONLY in
interface Ethernet0/2
 ip access-group DHCP-ONLY in
```

## ★実機知見（2026-07-25 iol-xe 17.15・作問 PoC で確定）

1. **IOS クライアントの既定識別子は MAC ではない**: `cisco-<mac>-<IF名>` の ASCII 文字列
   （binding には `0063.6973.636f...` の hex で見える）。このため
   **`hardware-address <mac>` の手動バインディングは一致せず空振り**する
   （client-id が chaddr より優先）。解は2通り:
   - **本問の模範**: CL1 に `ip dhcp client client-id Ethernet0/0` → client-id が
     **`01`+MAC**（例 `01aa.bbcc.0201.00`）になり、サーバ側 `client-identifier` と一致。
   - 別解: binding 表示から**実際の識別子 hex をそのまま** `client-identifier` に貼る
     （クライアント無改造。採点は効果ベースなのでどちらでも満点）。
2. **同一識別子の動的リースが生存中は `client-identifier` 登録が拒否される**:
   `% A binding already exists in NET20 pool.` → 先に `clear ip dhcp binding *`。
3. **host プールはオプションを継承する**: CL1-FIXED に default-router を書かなくても
   同一サブネットの NET20 から継承され、CL1 に S* 0.0.0.0/0 が入る（実測）。
4. **ACL の DHCP 許可は `permit udp any eq bootpc any eq bootps` の1行で
   初回 DISCOVER（送信元 0.0.0.0）も更新 unicast も通る**。送信元をサブネットで
   絞ると初回だけ落ちる「時々効く」故障になる（TS 化候補・BL-067）。
5. **負の要件は telnet の出力文字列では採点不能**: クライアントに IP が無い(no route)
   場合も ACL deny の場合も IOS は同じ `% Destination unreachable; gateway or host down`
   を出す（フレッシュ 0点発射で偽陽性を実測）→ 仕様に**明示 `deny ip any any`** を含め、
   採点は telnet 発火(0点)→ **deny のヒットカウンタ**で判定（uRPF 問イディオムの踏襲）。
6. IP 無し IF は day0 の `no shutdown` が不発（既知の癖の IOL 版）→
   problem.yml の `bringup_data_ifs: true` で起動後に一括 no shut。
7. 採点運用: クライアントへの release/renew 連打は DORA と競合して偽 FAIL する
   → 発火は CL1 のみ・チェック列の先頭に置き、実 IP 判定は後段に離す。
