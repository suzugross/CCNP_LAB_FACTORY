# poc/mpls-paper — BL-169 紙面 MPLS L3VPN ファミリの実測（IOL 17.15・2026-09-13）

設計= [problems/_drafts/PAPER-MPLS.design.md](../../problems/_drafts/PAPER-MPLS.design.md) §9。
生ログ= [results-raw.md](results-raw.md)（L3VPN-02: M1〜M9/M14）・[results-raw-04.md](results-raw-04.md)（L3VPN-04: M10/M11）。
駆動= `sweep.py`（02 を provision → 基線投入 → 採取 → 各実験は投入・待ち・採取・復旧）・`sweep04.py`（04 の PE-CE eBGP）。

## 実測表（2026-09-13 全項目採取済・M12 のみ保留）

| # | 項目 | 結果 | 紙面での使い方 |
|---|---|---|---|
| M1 | `show mpls forwarding-table` の書式 | ★確定: 列幅= Local 11／Outgoing 11／Prefix 17／Bytes 14／IF 11／Next Hop。`Pop Label`(対向が imp-null)・数値(swap)・`No Label`＋`[V]`(VRF 宛)。**17 文字以上のプレフィックスは `   \` で折り返し**、次行は 39 桁の空白＋Bytes＋`aggregate/<VRF>`。PE-CE 直結 /30 は aggregate 行 | `l_read`/`l_cause` の表(gen_paper_mpls.lfib_row・selftest で実測行と一致検査) |
| M2 | `show mpls ldp bindings/neighbor/discovery/interfaces` | ★確定: bindings= `lib entry: <pfx>, rev N`＋`local binding:  label: imp-null`／`remote binding: lsr: 2.2.2.2:0, label: 16`(自ループバックと直結 /30 は imp-null)。neighbor= `Peer LDP Ident`/`TCP connection: 2.2.2.2.57597 - 1.1.1.1.646`(646 は受け側)/`State: Oper`/`Addresses bound to peer`。discovery detail= `Transport IP addr`・`Reachable via 2.2.2.2/32`・`Password: not required` | `t_ldp` の事実(TCP 646・transport 到達性)・`l_read` |
| M3 | `traceroute vrf` のラベル表示 | ★確定: 1 ホップ目(P)= `[MPLS: Labels 17/20 Exp 0]`(トランスポート/VPN の 2 段)、2 ホップ目(出口 PE の CE 向け IP)= `[MPLS: Label 20 Exp 0]`(PHP 後は VPN ラベルのみ)、3 ホップ目 CE はラベル無し | `l_read`(php_trace/stack) |
| M4 | P の PE 向け IF で `no mpls ip`（LSP の穴） | ★確定: **IGP は正常**(`show ip route 3.3.3.3`= ospf intra)・VRF 経路も B で残る・**VPN の ping 0%**。指紋= P の LFIB で出口 PE のループバックが **`No Label`**(Pop Label→No Label)、P の `show mpls interfaces` からその IF が消える、出口 PE の `show mpls ldp neighbor` が空。入口 PE 側の LFIB/neighbor は不変 | `l_cause`(lsp_hole) |
| M5 | LDP router-id を未広告 Loopback に（transport address 不達） | ★確定: 自側 `show mpls ldp neighbor` が空、`discovery` は xmit/recv で相手の LDP Id は見える(発見は成立)。**対向の `discovery detail` に `LDP Id: 10.99.1.1:0; no route to transport addr`**。VPN の ping 0%。router-id を戻すと即復旧 | `l_cause`(transport_unreach)・`t_ldp` |
| M6 | VPNv4 表・`show ip route vrf`・`show vrf`・running-config 節 | ★確定: `show bgp vpnv4 unicast all` は `Route Distinguisher: 65000:100 (default for vrf CUST_A)` ごとに区切られ、同一プレフィックスが RD 違いで並ぶ。再配送経路は origin `?`。`show ip route vrf` は `Routing Table: CUST_A` 見出し＋B [200/11] via 3.3.3.3。`show vrf` は Name/Default RD/Protocols/Interfaces。`vpnv4 unicast rd 65000:100 172.16.2.0/24` の詳細に `Extended Community: RT:65000:100 …`・`mpls labels in/out nolabel/20` | `v_reach`/`v_cause`(将来 exhibit 拡張)・裏話 |
| M7 | RT import 取り違え（自動 RT フィルタの実挙動） | ★確定: 被疑 PE の VRF 表から対向経路が消え、**VPNv4 表にも当該 RD の対向経路は残らない**(PfxRcd 6→3= 自動 RT フィルタで受信時に捨てる)。対向 PE 側は不変。import を戻すと約 1 分で復帰 | `v_cause` の指紋・裏話(自動 RT フィルタ) |
| M8 | 同一 PE で 2 VRF に同じ RD | ★確定: **`% RD 65000:100 already in use by VRF CUST_A` で拒否**(構成は変わらず IF の IP も無事)。RD の一意性は同一ルータ内で強制、PE 間では不要 | `rt_model.vpnv4_entries` が ValueError・`v_peer` の錯乱肢 |
| M9a | vpnv4 ネイバーの send-community extended 欠落 | ★確定: セッションは Established のまま**対向の PfxRcd が 0**(RT の無い VPNv4 経路は受信側で捨てられ、VPNv4 表にも残らない)。running-config の vpnv4 節から行が消えるだけ。戻すと約 1 分で復帰 | `v_cause` の錯乱肢の反証(構成に行があるか) |
| M9b | vpnv4 ネイバーの activate 欠落 | ★確定: 自側の `show bgp vpnv4 unicast all summary` は**何も表示しない**、対向の要約では当該ネイバーが **Idle**(MsgRcvd 0)。戻すと send-community extended も再投入が要る(activate を外すと消える) | `v_cause` の錯乱肢の反証 |
| M10 | as-override 無し/有りの CE 側 AS_PATH と DENIED 指紋 | ★確定: **無し**= PE の `advertised-routes` に 2 経路が載るのに CE の `show ip bgp summary` は **PfxRcd 0**・CE の表に対向拠点が無い(CUST_A=サイト毎 AS は `65000 65102 i` で届く)。**as-override 後**= CE 受信 AS_PATH `65000 65000`・ping 100%。DENIED の debug 行は本日 soft out の構文誤りで再採取できず、先行 PoC の記録 `rcv UPDATE about 172.16.2.0/24 -- DENIED due to: AS-PATH contains our own AS;`(merged path 65000 65200)を流用 | `p_asoverride`(cause/fix/read) |
| M11 | allowas-in（CE 側）での受信 | ★確定: CE の `neighbor <PE> allowas-in` で受信・AS_PATH は `65000 65200`(自 AS が残る)・ping 100%。as-override を外した直後は再び 0 経路 | `w_pe_frozen` の正解・read 形の対比 |
| M12 | SoO（バックドア拠点） | 04 にバックドア無し → **P3 へ** | `p_soo` は保留 |
| M14 | `mpls ldp autoconfig`（OSPF 受理・EIGRP 不可） | ★確定: `router ospf 1` 配下で受理され OSPF の IF に LDP が有効化(`show mpls interfaces` に現れる)。classic `router eigrp` 配下は `% Invalid input` | `t_ldp` の事実 |

## 汎用知見（他の作問にも使える）

1. **LSP の穴は「IGP 正常・VRF 経路あり・VPN だけ断」**。指紋は P の LFIB の `No Label`(その IF で LDP 無効)。入口 PE 側からは何も壊れて見えない。
2. **LDP は発見(UDP hello)と確立(TCP 646)が別物**。transport address に経路が無いと `discovery` には相手が見えるのに `neighbor` は空で、対向側に `no route to transport addr` が出る。
3. **RT の無い VPNv4 経路・import に合わない VPNv4 経路は、受信 PE が VPNv4 表にも残さない**(自動 RT フィルタ)。`PfxRcd` の減少がそのまま指紋になる。
4. **同一ルータ内の RD 重複は構成時点で拒否される**。PE 間の一致は不要。
5. **vpnv4 の `activate` を外すと `send-community extended` も消える**(戻すときは 2 行)。対向の要約は Idle。
6. `mpls ldp autoconfig` は OSPF/IS-IS 配下のみ(classic EIGRP は構文が無い)。
7. ★類推(未実測): M5 の状態(PE1–P の LDP セッション無し)では PE1 の LFIB はコア宛がすべて `No Label` になるはず(M4 で P 側の該当行が No Label になったのと同じ機構)。紙面 `l_cause`(transport_unreach)はこの類推で PE1 の LFIB を描いている。次に 02 を上げたら `show mpls forwarding-table` を M5 の状態で採って確定させること。
