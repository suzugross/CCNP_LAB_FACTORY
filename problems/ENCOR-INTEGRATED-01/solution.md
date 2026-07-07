# 模範解答 : ENCOR-INTEGRATED-01（実運用エッジ: ISPデフォルト注入 + PAT + エッジACL）

> 値は `params/<variant>.yml` 由来。以下は **base**（`as_internal=65001`, RT02 outside=`10.0.24.1`,
> 外部ホスト=RT04 Lo `4.4.4.4`, RT03 Lo=`3.3.3.3`）。v2/seed では AS・IP・Loopback が変わるので
> 各自の `task.md`（`_generated/ENCOR-INTEGRATED-01/task.md`）の値に読み替えること。
> 採点は値ではなく **効果**（O*E2 デフォルト学習 / 実ping成功 / NAT変換エントリ / ACL適用・deny ACE）で判定する。

すべて **RT02** で構成する。インタフェースは iol マッピングで Eth0/0=RT01側, Eth0/1=RT03側, Eth0/2=RT04側(outside)。

## タスク1: ISP デフォルトを OSPF へ注入
```
router ospf 1
 default-information originate
```
- RT02 は ISP(RT04) から `0.0.0.0/0` を eBGP で受信済み（`B* 0.0.0.0/0`）。
- `default-information originate` で、その既定経路を OSPF に `O*E2 0.0.0.0/0` として注入 → RT01/RT03 へ波及。

## タスク2: PAT(オーバーロード)
```
ip access-list standard NAT-LOCAL
 permit any
!
ip nat inside source list NAT-LOCAL interface Ethernet0/2 overload
!
interface Ethernet0/0
 ip nat inside
interface Ethernet0/1
 ip nat inside
interface Ethernet0/2
 ip nat outside
```
- inside = 社内側 2 IF（Eth0/0=RT01, Eth0/1=RT03）, outside = ISP側（Eth0/2）。
- `overload` で社内送信元を **outside IF の公開アドレス(`10.0.24.1`)** に PAT。
- これで RT03 が Lo0(`3.3.3.3`) 発で `4.4.4.4` へ到達でき、**戻りも RT02 outside 宛に返って un-NAT される**（=NATが戻り経路問題を解決）。

## タスク3: エッジ ACL（outside に inbound）
```
ip access-list extended INTERNET-IN
 deny tcp any any eq telnet
 permit ip any any
!
interface Ethernet0/2
 ip access-group INTERNET-IN in
```
- ISP側(outside)の **inbound** に適用 ＝ 外部から入る Telnet を境界で遮断する正しい位置・方向。
- `permit ip any any` で eBGP(179)・ping の戻り(echo-reply)・社内発の戻り通信を許可（これが無いと暗黙denyで eBGP/疎通が落ちる）。

## 確認
```
! RT01 / RT03
show ip route ospf            → O*E2 0.0.0.0/0
! RT03
ping 4.4.4.4 source Loopback0 → Success
! RT02
show ip nat translations      → icmp 10.0.24.1 ... 3.3.3.3 ...（inside-global ← inside-local）
show ip nat statistics        → Inside/Outside interfaces
show ip interface Ethernet0/2 → Inbound access list is INTERNET-IN
show ip bgp summary           → RT04 と Established 維持
show ip ospf neighbor         → 既設の OSPF 隣接 FULL 維持
```

## ポイント（実運用エッジの要点）
- **デフォルトの配り方**: ISP からの 1 本のデフォルトを IGP に注入すれば社内全体が外向き経路を得る。
- **NAT が戻りを解決**: 内部はプライベートのまま、境界 PAT で公開アドレスに変換 → 外部は内部経路を知らなくてよい。
  （再配送で内部を広告する必要が無い＝セキュリティ的にも自然）。
- **ACL は位置と方向が命**: outside の inbound でこそ「外部からの流入」を制御できる。末尾 permit で既存通信を壊さない。
