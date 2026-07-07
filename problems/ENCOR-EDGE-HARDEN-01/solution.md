# 模範解答 : ENCOR-EDGE-HARDEN-01（エッジ装置ハードニング）

設定はすべて **RT01**。RT02 は変更しない。隣接(RT02)向け IF = **IOL: Ethernet0/0 / IOSv: GigabitEthernet0/0**（`-e image_family=iosv` で起動した場合は Gi 名で読み替え）。

## 1. AAA（管理プレーン）
```
aaa new-model
aaa authentication login default local
```
- ★**必ず `aaa authentication login default local` も同時に**。`aaa new-model` だけだと VTY の
  `login local` が無効化され、認証方式が未定義になって **SSH がロックアウト**する。
- ローカルユーザ(SUZUKI, privilege 15)は既設。enable も enable secret で継続。

## 2. CoPP（制御プレーン保護）
```
ip access-list extended COPP-ICMP
 permit icmp any any
ip access-list extended COPP-TELNET
 permit tcp any any eq 23
!
class-map match-all CM-ICMP
 match access-group name COPP-ICMP
class-map match-all CM-TELNET
 match access-group name COPP-TELNET
!
policy-map PM-COPP
 class CM-TELNET
  police 8000 conform-action drop exceed-action drop
 class CM-ICMP
  police 8000 conform-action transmit exceed-action drop
!
control-plane
 service-policy input PM-COPP
```
- Telnet は適合・超過とも drop で全廃棄。ICMP は police でレート制限（適合 transmit / 超過 drop）。
- `class-default` は触らない（OSPF/SSH 等の正常制御を巻き込まない）。

## 3. インフラ ACL（自装置保護）
```
ip access-list extended INFRA-ACL
 deny tcp any host 1.1.1.1 eq 22
 deny tcp any host 1.1.1.1 eq 23
 permit ip any any
!
interface Ethernet0/0
 ip access-group INFRA-ACL in
```
- 隣接セグメントから自装置(Lo0)宛の SSH/Telnet を遮断、他は許可。
- **末尾 `permit ip any any` を忘れない**（暗黙 deny だと OSPF hello が落ちて隣接断）。
- 管理 SSH は別の管理 VRF 経由なので、この ACL の影響を受けない。

## 4. 認証 NTP（サービス）
```
ntp authentication-key 1 md5 CCNP-NTP
ntp authenticate
ntp trusted-key 1
ntp server 10.0.12.2 key 1
```
- RT02(マスター)と同じ key 1 / `CCNP-NTP`。`ntp authenticate` + `trusted-key` で認証を強制。
- 同期確認（時間がかかる）: `show ntp associations` / `show ntp status`。

## 確認
```
show running-config | include aaa
show policy-map control-plane
show ip access-lists ; show ip interface Ethernet0/0
show ip ospf neighbor        ! RT02 が FULL のまま（ACLが制御を壊していない）
show running-config | include ntp
```

> 採点: AAA有効 / CoPP(ICMP police・Telnet drop) / インフラACL(deny ACE + inbound適用) /
> OSPF隣接維持 / NTPサーバ鍵付き + NTP認証、の8観点で判定。名前は任意。
