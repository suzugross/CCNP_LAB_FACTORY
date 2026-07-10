# 模範解答 : ENARSI-DMVPN-IPSEC-01 (DMVPN Phase 3 + IKEv2 tunnel protection)

> 学習核心 = ENARSI-IPSEC-IKEV2-01 で確立した IKEv2 オブジェクト連鎖
> **proposal → policy → keyring → ikev2 profile → ipsec profile → tunnel protection**
> を mGRE(DMVPN) に載せ替えること。sVTI との差分は 2 点だけ —
> **① keyring を wildcard にする**（spoke-spoke の対向 NBMA は事前不定）
> **② ESP を transport mode にする**（GRE 済みトンネルに tunnel mode は無駄）。

## 暗号ブロック（★全 3 拠点共通・そのまま投入）

```
crypto ikev2 proposal PROP-NGE
 encryption aes-gcm-256
 prf sha384
 group 19
!
crypto ikev2 policy POL-NGE
 proposal PROP-NGE
!
crypto ikev2 keyring KR-DMVPN
 peer ANY
  address 0.0.0.0 0.0.0.0
  pre-shared-key Ss2026#Dmvpn
!
crypto ikev2 profile IKEV2-DMVPN
 match identity remote address 0.0.0.0
 authentication remote pre-share
 authentication local pre-share
 keyring local KR-DMVPN
 dpd 30 5 on-demand
!
crypto ipsec transform-set TS-GCM esp-gcm 256
 mode transport
!
crypto ipsec profile IPSEC-DMVPN
 set transform-set TS-GCM
 set pfs group19
 set ikev2-profile IKEV2-DMVPN
```

## RT01 (Hub / NHS)

```
interface Tunnel0
 ip address 10.255.0.1 255.255.255.0
 no ip redirects
 ip mtu 1400
 ip tcp adjust-mss 1360
 ip nhrp authentication DMVPNKEY
 ip nhrp map multicast dynamic
 ip nhrp network-id 1
 ip nhrp redirect
 no ip split-horizon eigrp 100
 tunnel source GigabitEthernet0/0
 tunnel mode gre multipoint
 tunnel key 100
 tunnel protection ipsec profile IPSEC-DMVPN
!
router eigrp 100
 network 1.1.1.1 0.0.0.0
 network 10.255.0.0 0.0.0.255
```

## RT02 (Spoke1)　※RT03 は tunnel IP `.3` / network 文 `3.3.3.3` に読み替え

```
interface Tunnel0
 ip address 10.255.0.2 255.255.255.0
 no ip redirects
 ip mtu 1400
 ip tcp adjust-mss 1360
 ip nhrp authentication DMVPNKEY
 ip nhrp network-id 1
 ip nhrp nhs 10.255.0.1 nbma 10.0.14.1 multicast
 ip nhrp shortcut
 tunnel source GigabitEthernet0/0
 tunnel mode gre multipoint
 tunnel key 100
 tunnel protection ipsec profile IPSEC-DMVPN
!
router eigrp 100
 network 2.2.2.2 0.0.0.0
 network 10.255.0.0 0.0.0.255
```

> スポークの NHS は現代構文 `ip nhrp nhs <tunnel IP> nbma <NBMA> multicast` 1 行で
> 従来の `ip nhrp map` + `map multicast` + `nhs` の 3 行と等価（IOSv 15.9 実機確認済）。
> 従来 3 行構文でも正解。

## 検証コマンド

```
show dmvpn                          ! Hub: 2 spokes UP(D) / Spoke: NHS UP(S)＋ping後に D
show crypto ikev2 sa                ! READY ＋ Encr: AES-GCM, keysize: 256 / PRF: SHA384 / DH Grp:19
show crypto ipsec sa                ! in use settings ={Transport, } / #pkts encaps 加算
show ip route eigrp                 ! 対向スポーク /32 の next-hop が 10.255.0.1 のまま (Phase3)
ping 3.3.3.3 source Lo0             ! スポーク間: 直結誘発 → show dmvpn に動的エントリ
show ip nhrp shortcut               ! ping 後: 対向 /32 が rib nho で載る
traceroute 3.3.3.3 source Lo0       ! 直結成立後は 1 ホップ
```

## 解説（採点後レビュー用）

- **★最大の罠 = keyring のスコープ**。sVTI 問の流儀でピア毎に
  `address 10.0.14.1` と絞ると、**hub-spoke は完全正常なのに spoke 間直行だけが
  沈黙**する（スポーク間トラフィックは通り続ける＝永久ハブ折返しなので気付きにくい）。
  `show dmvpn` に `IKE`/`IX`/`DX`(No Socket) が残り、スポーク間 IKEv2 SA が無いのが
  シグネチャ。Phase 3 の動的直結は「相手 NBMA が事前に分からない」ので
  **wildcard keyring (`address 0.0.0.0 0.0.0.0`) + `match identity remote address 0.0.0.0`**
  が必須。
- **transport mode の意味**: GRE で既に外側 IP が付くため tunnel mode の外側 IP 20B は
  純粋な無駄（OCG も transport を推奨）。なお **両端で mode が食い違っても不通には
  ならず Tunnel mode に合意して上がる**（実機確認済）— 「動くから OK」ではなく
  `show crypto ipsec sa` の `in use settings ={Transport, }` で仕様適合を確認する癖を。
- **tunnel protection は 3 拠点全部に**。片側だけ欠けると hub が平文 GRE を破棄し
  NHRP 登録自体が失敗（`show dmvpn` が空/`NHRP` 固着 → 「NHRP の問題に見えて crypto」
  という切り分け練習の定番）。単一 Tunnel0 なので `shared` キーワードは不要
  （同一 source を複数トンネルで共有する時だけ）。
- **`set ikev2-profile` を忘れない**: 忘れると ISAKMP(IKEv1) にフォールバックし
  smart default が無いため単に上がらない（IKEV2-01 と共通の罠）。
- **NHRP network-id はローカル有意**で、hub/spoke で不一致でも動作する（実機確認済）。
  「揃える運用」が普通だが、不一致を疑って時間を溶かさないこと。認証キー
  (`ip nhrp authentication`) の不一致は逆に**完全サイレント**で登録拒否される
  （debug nhrp error にも出ない）。
- **MTU/MSS**: GRE(4+key4)+IPsec で実効 payload が縮む。`ip mtu 1400` +
  `ip tcp adjust-mss 1360` は DMVPN/GRE 系の定石。IOSv 実測では ip mtu 未設定でも
  外側 GRE が断片化して ping は通る（DF は外側に複製されない）が、断片化は
  性能劣化・実務では PMTUD ブラックホールの温床 — 明示設定が正解。
- **Phase 3 の観察**: 経路は常にハブ向き（`show ip route` の next-hop は 10.255.0.1、
  shortcut 成立後は `%`=NHO 印付き）で、データプレーンだけが直行に切り替わる。
  Phase 2（`no ip next-hop-self eigrp` で経路の next-hop 自体を対向スポークにする）
  との対比が試験の頻出ポイント。
