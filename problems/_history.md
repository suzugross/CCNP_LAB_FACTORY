# 出題履歴 — いつ何を出題し何点だったか

出題フロー(`.claude/skills/quiz/SKILL.md`)が更新する台帳。**新しい行を表の一番上に追記**する。

- **状態**: `出題中` → `採点済` → `撤収済`。provision 時に `出題中` で1行追加し、以後は同じ行を更新。
- GEN 系は seed まで書く(例: `GEN-CHAIN-9812`)。variant があれば ID の後ろに `(bfd)` 等。
- 得点は最終得点。途中採点の経過はメモに(例: `81→100`)。
- 用途: 重複出題の回避・難易度調整・チャットまたぎでの「いま出題中の問題」の復元。

## 履歴

| 出題日 | 問題ID (variant/seed) | 難 | 状態 | 得点 | メモ |
|--------|----------------------|----|------|------|------|
| 2026-07-29 | GEN-RDFIELD-4471 (hard) | 5 | 撤収済 | 100 | ★--hardモード初出題(K=3・5台・EIGRP768/OSPF12/OSPF66・fault=wrong_id×2=両BRの参照ID誤り)を一発満点。config完備に見えて経路ゼロの型×2箇所・チケット範囲重複の解きほぐし込み。★wrong_id機構はこの回で実機フルサイクル検証完了(4故障型すべて実機済に)。※9418(3台missing×2)は較正不適合で引き直し・--hard実装(K=3固定+subtle保証) |
| 2026-07-29 | GEN-RDFIELD-6083 | 4 | 撤収済 | 100 | ★フィールド初出題(抽選=全EIGRP 3ドメインAS180/189/329・7台・fault=RT01のAS329→189方向missing)を一発満点。解=欠落方向のredistribute復旧(seed metric仕様値込み)・健全BR(RT05)は無変更の最小手。曖昧チケット(「全滅」申告)の裏取り→実範囲特定も自力 |
| 2026-07-29 | GEN-RDARENA-8351 | 5 | 撤収済 | 100 | アリーナ初出題(7台・inject_eigrp×filter)を一発満点。解=出自タグ方式(TAG01 set tag 200@BGP→EIGRP + TAG02 deny tag@OSPF distribute-list in)=4977と同型の1:1転用。★ユーザ指摘「全然違いなくない?」=正当(タイトル/チケット/ヒントがモチーフと診断手順をバラしている+単一モチーフ)→提示改修とPhase2(症状クラス抽選)へ |
| 2026-07-29 | GEN-REDISTLOOP-4977 (filter_ospf) | 5 | 撤収済 | 95→100 | distance禁止変種を出自タグ方式で完答: TAG01(set tag 110)をBGP→EIGRP再配送に付与+OSPFに`distribute-list route-map TAG02 in`(deny tag 110)=戻り経路のRIB搭載だけ拒否・RBのO E2は温存(LSAフラッディング非停止の理解が正確)。95の-5は試行残骸のdistance行(監査検知が機能)→除去で100。★弱点メモ「タグの位置づけ定着途上(7/19)」は完全克服と判定 |
| 2026-07-29 | GEN-FNFTS-8402 (faults2) | 4 | 撤収済 | 100 | FNF新seed TS一発満点(本日4連続)。fault=exporter_wrong_dest+apply_direction_output(エクスポート空振り×逆方向計測の2チケット)。解=destination是正+Et0/0をinput適用へ=最小手2点・模範解同型。※未出fault残り=apply_wrong_if/monitor_no_exporter/exporter_wrong_port/exporter_wrong_source/exporter_wrong_version/monitor_wrong_record |
| 2026-07-29 | GEN-DHCPTS-5741 (faults2) | 5 | 撤収済 | 100 | DHCP TS新seed一発満点(本日3連続)。fault=helper_missing(segB)+acl_no_dhcp_permit(両リモート)の2層交錯。解=Et0/2 helper復旧+ACLへseq5行挿入(permit udp any eq bootpc any eq bootps)=最小手。★BL-069の弱点(host 0.0.0.0限定形でrenew死)を自力回避=汎用形で初回からrenew実効PASS(学習ループ完結の実証) |
| 2026-07-29 | GEN-EGVRF-9153 (faults2) | 5 | 撤収済 | 100 | 新seed TS一発満点(EIGRP×VRF 3連覇)。fault=summary_wrong_if+auth_missing_a1(症状=site2に明細/site1不通の2チケット交錯)。解=summary-addressをaf-interface Et0/1へ移設+Et0/0へMD5認証投入=最小手2点・模範解同型。認証はmode md5+key-chainの2行構成も正確 |
| 2026-07-29 | DMVPN-POC-01 (再) | 5 | 撤収済 | 100 | 同値再演(ユーザ選択)を再び一発満点=完全定着。前回と同型(named mode・af-interfaceのno next-hop-self/no split-horizonはハブのみ・スポーク旧来3行NHRP・MTU/MSS先回り・IPsec自主実装tunnel key込み全台整合)。レビュー=hub map multicast dynamicの15.9暗黙デフォルト裏話を補足 |
| 2026-07-27 | ENARSI-VRFLITE-DNBIT-01 | 4 | 撤収済 | - | **en**(task.en.md新規作成・CML Notes英語差替の初適用)。未解答のままCMLサーバ停止のため中断→撤収。**再出題可**(問題パック・task.en.mdキャッシュ保持・ネタバレなし) |
| 2026-07-27 | ENARSI-OSPF-MADJ-01 | 4 | 撤収済 | 100 | **en**(英語出題初回・task.en.md新規作成・BL-071)。一発満点(全12チェックPASS)。P2P化+multi-area 0の2行×2台=模範解同型・broadcastサイレント罠を自力回避 |
| 2026-07-27 | ENARSI-BGP-AGGREGATE-01 | 3 | 撤収済 | 100 | BGP集約初出題を一発満点。as-set summary-onlyの1行最小解＋旧問に自主AF方式適用(規約定着)。レビューでAS_SETループ防止/atomic-aggregate/suppress-map3段構えを補足 |
| 2026-07-27 | GEN-EGVRF-4276 (faults2) | 5 | 撤収済 | 100 | VRF-aware EIGRP収容標準TS初出題を一発満点。fault=vrf_if_swap+missing_network_a2(3リンク全滅の初期状態)。★af-interface無言破棄のカスケード(VRF復旧後も隣接不成立→認証再投入)を初見で自力突破。運営反省=症状域重複時のチケット相互矛盾→生成器に注記追加 |
| 2026-07-27 | ENARSI-EIGRP-VRF-01 | 4 | 撤収済 | 100 | BL-070①初出題を一発満点(全11チェックPASS)。模範解答と構造同型・network文精密絞り・af-interface認証/集約の書き分け完璧。※IP剥がれ罠は完成報告時に開示済みだったため初見切り分けは未検証(再演か②TSで確認) |
| 2026-07-27 | ENCOR-FNF-01 (base) | 3 | 撤収済 | 100 | FNF構築問初出題を一発満点(全8チェックPASS)。仕様過不足ゼロの最小解。レビュー補足=export-protocol v9はデフォルトでconfig非表示/record編集ロックは既知(7842で経験済) |
| 2026-07-26 | ENARSI-DMVPN-IPSEC-01 (再) | 5 | 撤収済 | 100 | DMVPN+IPsec完全版の再出題→一発満点(定着確認OK)。Phase3をredirect+next-hop-self既定維持で正しく構成・MTU/MSS先回り・EIGRP named mode採用。※採点1回目はコンソール収集10分timeout→max_attempts=1で再実行(毎回の運用) |
| 2026-07-26 | DMVPN-POC-01 | 5 | 撤収済 | 100 | Phase2構築を一発満点。EIGRP named mode採用・af-interfaceでno next-hop-self/no split-horizon正実装(BGP-01の80点弱点が完全定着)。IPsec+tunnel key+MTU/MSSを仕様外で自主追加(全台整合・減点なし)。スポークNHRPは旧来3行構文 |
| 2026-07-26 | GEN-DMVPN-3194 | 4 | 撤収済 | 100 | DMVPN+IPsec TS(fault=p1_redirect_missing)。一発満点(5冠目)。解=hub Tunnel0にip nhrp redirect復旧の最小手1行・模範解同型。※初回採点は収束待ちで10分timeout→max_attempts=1で再実行 |
| 2026-07-26 | GEN-DHCPTS-8127 (faults2) | 5 | 撤収済 | 100 | DHCP TS初出題を一発満点。fault=helper_wrong_ip+excluded_swallows(両方segment B=片方直しても症状不変の2段重ね)。helper正常化+excluded .1-.9復元の最小手×2 |
| 2026-07-26 | ENCOR-DHCP-01 | 3 | 撤収済 | 80→100 | BL-066初出題。80=ACL未着手→自力完成。CL1固定割当は client-id 一行形(ip address dhcp client-id)で正攻法突破。★レビュー発見=ACLのDHCP permitがhost 0.0.0.0限定形でunicast renewがdeny落ち(採点盲点→BL-069)/CL1-FIXEDのdns typo 198.50/NET30 default-router行に余分な255.255.255.0 |
| 2026-07-26 | ENARSI-REDIST-POLICY-01 (s6127) | 4 | 撤収済 | 100 | BL-068初出題を一発満点。deny(tag)→deny(lab)→permit(個別色)→permit(包括色)の順序設計完璧・set metricのプレフィックス毎出し分けも模範同型。DENY01共用prefix-list・明示type-2は本人流 |
| 2026-07-25 | GEN-FNFTS-7842 (faults2) | 5 | 撤収済 | 100 | FNF監視標準TS初出題を一発満点。fault=record_missing_key(transport source-port)+monitor_not_applied。record編集ロック(要参照解除)を自力突破・キー追記順から編集パス採用と推定 |
| 2026-07-25 | ENCOR-IPSLA-01 | 4 | 撤収済 | 100 | 一発満点(全7チェックPASS)。仕様超えの丁寧解=SLA source-interface固定/timeout3000/frequency5/track delay down10 up5のダンピングまで実装。mgmt=.20/.31-.33 |
| 2026-07-23 | GEN-BGPCX-5926 (faults1+policy2) | 5 | 撤収済 | 76→100 | BGP複合TS(policy軸初)。3故障=prepend_wrong_side@be+weight_override@RR+missing_update_source@RT01。76時点で残ったのはweight_override(LPの上位で上書き)→自力是正。★チケット乖離を発見(シミュレータ「到達不能」予測vs実機到達可)→BL-061登録(update-source片側欠落の非対称成立仮説) |
| 2026-07-23 | GEN-BGPPATH-6152 (faults2+decoy1) | 5 | 撤収済 | 100 | BGP経路選択TS一発満点。fault=fwd_lp_wrong_nbr+ret_prepend_wrong_nbr。★ユーザ解は想定解(LP張り直し)と異なりAS_PATH操作で両方向制御の別解(効果採点で満点)。※私が修正内容をfault名から推測で誤断定→ユーザ訂正(レビューは実機の解を確認してから書く教訓) |
| 2026-07-23 | ENARSI-MPLS-L3VPN-03 (再) | 5 | 撤収済 | 100 | +採点後にsham-link端点の再配送遮断(両PE対称route-map)の設計問答→ユーザは片側では消えない事を実測して対称化(模範解答超えの完成形) | sham-link再演を一発満点(全15PASS・定着確認成功)。今回はcost100で主経路化(前回20・500未満なら可の理解が本物)。端点/32のBGP限定広告も再現 |
| 2026-07-23 | GEN-DMVPN-8817 (n4_multicast_map_tunnelip) | 4 | 撤収済 | 100 | DMVPN TS一発満点(4冠目)。multicast mapがトンネルIP指し→片方向hello周期フラップを範囲と層から特定。残骸行の掃除のみレビュー指摘 |
| 2026-07-22 | FGT-IPSEC-01 (伴走学習) | 3 | 撤収済 | 95→73→100 | マルチベンダIPsec完走。★ユーザ発案でPhase 0(管理IF自己設定)を正式課題化・S0一発PASS。踏んだ体験=DES罠(LENC)/GUI一括作成のPhase2デフォルトAESで-61/no policy configured(FW思想)/RBR側NO_PROPOSAL_CHOSEN誤診/staticルートtypo193→区間切り分けStep2で自力発見/phase1⇔2名前入れ替え→参照逆順削除・正名再作成の実務手順。機能は終始完動(G/E全PASS維持) |
| 2026-07-22 | FGT-FW-BASIC-01 (再×2:CLI伴走学習) | 2 | 撤収済 | 100 | ★2回目=FGT素人前提のCLI伴走学習モードで全Phase解説しながら再構築→100点。★前回2回とも指摘のID3 NAT不要を今回は NAT=off で正しく実装(学習効果=送信元保持を理解)。学んだ道具=show/get/grep -f(ブロック抽出)/session filter/debug flow。SNAT/DNAT/暗黙deny(policy0)を実機で目撃 |
| 2026-07-22 | ENCOR-PBR-01 | 3 | 採点済 | 100 | PBR基礎を一発満点。★02(通過=ip policy)直後の対比出題で ip local policy を正しく選択(自ルータ生成トラフィックの勘所を即座に把握)。Policy routing matches 29pktで実効確認 |
| 2026-07-22 | ENCOR-PBR-02 | 4 | 採点済 | 50→100 | PBR送信元別振り分け。1st50=IF適用/ACLは正だがroute-mapのset next-hop欠落→2nd100。名前付きACL PBR01+route-map PMAP・ip policy入口IF適用。Policy routing matches 85packetsで実効確認 |
| 2026-07-22 | ENARSI-IPSEC-IKEV2-01 | 4 | 撤収済 | 100 | sVTI×IKEv2構築を一発満点(全13PASS)。IKEv2 4点セット(proposal/policy/keyring peer別PSK/profile)・GCM=esp-gcm 256のみ(整合性内包)・DPD on-demand。P2P VTI×2なのでsplit-horizon不要(DMVPN単一mGREとの対比)を理解 |
| 2026-07-22 | ENARSI-IPSEC-VTI-01 | 3 | 撤収済 | 100 | sVTI×IKEv1構築を一発満点(全13チェックPASS)。仕様完全準拠(ISAKMP policy/transform-set/PFS/DPD/MTU/MSS)。tunnel mode ipsec ipv4・P2P型で/24保持。IPsec構築系デビュー戦 |
| 2026-07-21 | ENARSI-MPLS-L3VPN-05 | 4 | 撤収済 | 44→100 | フルメッシュ×H&S組み分け。1st44=折り返し半分(拠点発220受けのみ)→2nd100=上りCUST_B_UP export210×spoke import210で折返し完成。★ユーザはUP側peerにallowas-in設定で自AS重複の折返し経路を受理(置き場所=受信in方向で正解・04のas-overrideと送信/受信で対比)。RD補足=CUST_B_UPを65200:210(仕様65000:210)にしたが動作影響なし・慣習は管理AS |
| 2026-07-21 | GEN-DMVPN-6402 (r2_underlay_in_eigrp) | 4 | 撤収済 | 100 | DMVPN再帰ルーティングTS。★真因=restoreで入った広域network `10.0.0.0`(クラスフル)がunderlay/30まで巻き込む→mGRE再帰でフラップ。解=その1行を仕様どおり`network 10.255.106.0 0.0.0.255`(overlayのみ)に差替=最小手・一発満点。RECURDOWN非発出を状態フラップ観察で特定。※当初レビューで私が「Lo0広告が犯人」と誤読→ユーザ訂正(犯人は広域network文) |
| 2026-07-20 | FGT-FW-BASIC-01 | 2 | 撤収済 | 100 | FortiGate初出題を一発満点(全13チェックPASS)。仕様完全準拠。レビュー指摘=ポリシー3に不要なnat enable(LAN→DMZがSNATされDMZログから発信元が消える)・role未設定(採点外)。共用ラボFGT-LAB(stopのみ) |
| 2026-07-20 | ENARSI-MPLS-L3VPN-01 | 3 | 撤収済 | 100 | MPLS L3VPN一から構築を一発満点。全17チェックPASS(VRF/VPNv4/RT分離/顧客間分離/E2E)。ラベルスイッチング(Label17)・VPNv4セッションPfxRcd4も確認。重複172.16をRD/RTで正しく隔離 |
| 2026-07-20 | GEN-REDISTLOOP-3357 (ad_eigrp) | 5 | 撤収済 | 100 | 再配送リング定常ループ(逆回り変種・戻りD EX 170×iBGP 200)。解=distance bgp 20 80 20(効果完全・一発満点)。レビューで「勝ちたい相手だけに勝つ最小調整(165)」を補足 |
| 2026-07-20 | GEN-REDIST-8871 | 4 | 撤収済 | 100 | 相互再配送TS(fault=missing_e2o)。E→O再配送欠落を最小手(redistribute eigrp+metric20明示)で復旧・既設タグ機構は正しく温存・一発満点 |
| 2026-07-20 | DMVPN-PHASE3-01 | 5 | 撤収済 | 100 | Phase3構築一発満点。hub redirect＋next-hop-self温存の正しい作り分け(spoke shortcutはIOSv15.9暗黙既定で非表示)。MTU/MSS先回り・IPsec自主実装(不要だが整合・減点なし) |
| 2026-07-20 | GEN-SNMPTS-7605 | 5 | 撤収済 | 100 | SNMPv3×Zabbix監視TS。2故障(RT03 group ACLがポーラdeny/RT01 認証パス不一致=不可視の難5)を満点。RT03はACL参照撤去・RT01はuser再作成(鍵不可視→上書きの正攻法) |
| 2026-07-19 | ENARSI-MPLS-L3VPN-04 | 4 | 撤収済 | 100 | MPLS旗艦04一発満点。as-overrideをCUST_Bのみに精密適用・受信制御はホワイトリスト形(permit 172.16/16 le 24+暗黙deny)・顧客別にRM/PL分離の丁寧な実装 |
| 2026-07-19 | ENARSI-DMVPN-BGP-01 | 5 | 撤収済 | 80→100 | DMVPN Phase2構築+ハブ橋渡し。Phase3思い込み(next-hop-self残り)でスポーク間直接のみ未達→自己診断で是正。EIGRP named mode採用・MTU/MSS先回り設定・IPsecも自主実装(不要だが減点なし) |
| 2026-07-19 | GEN-REDISTMP-4515 (routemap) | 5 | 撤収済 | 80→100 | タグ基本形ドリル。効果は初回から完璧・80点の原因は set tag 側の prefix-list 絞り(監査違反=名指しアンチパターン)→指摘後**自力是正**(共用route-map 1枚のdeny/permit 2節に整理)。リセット1回 |
| 2026-07-18 | GEN-CHAIN-3661 (chain-depth3+decoy1) | 5 | 撤収済 | 100 | 12台連鎖TS。3段連鎖＋decoyを一発満点(4連続)。L3是正はIFモードospf+passive。採点後に再配送タグ講義→実機でRT07の陥落状態(clear起因のアンカー外れ)を発見→clear ip eigrp neighborsで復旧実験まで実施 |
| 2026-07-18 | GEN-OSPFX-7924 (vlink+redist static・faults2+decoy1) | 5 | 撤収済 | 100 | OSPF複合TS。distribute_list_in@RT06＋cost_suboptimal@RT03 を一発満点(本日3連続)。cost是正は明示100設定の別解(効果完全・最小形はno ip ospf cost) |
| 2026-07-18 | GEN-DMVPN-5177 (i3_keyring_perpeer) | 5 | 撤収済 | 100 | DMVPN Phase3+IKEv2 TS。keyring per-peer 絞りでスポーク間 IKE のみ不成立(ハブ経由疎通は正常)→peer ANY 復旧で一発満点。採点1回はコンソール収集10分timeout→max_attempts=1 で再実行(運用メモ) |
| 2026-07-18 | GEN-BGPRR-8442 (faults2+decoy1) | 5 | 撤収済 | 100 | RR伝播TS。2故障連鎖(missing_rr_client×transit_ospf_break)を一発満点。OSPF修正はhost-wildcard形の精密解。※seed6318は生成出力に故障名露出のため未出題破棄 |
| 2026-07-17 | ENARSI-DHCPV6-01 | 5 | 撤収済 | 73→88→100 | stateless/stateful/リレー。罠=O flag/statelessも relay要/no-autoconfig(A flag)/ipv6 nd autoconfig default-route/link-address プール選択 |
| 2026-07-17 | GEN-L2TS-8420 | 4 | 撤収済 | 100 | EtherChannel TS。3故障(member欠落/on↔active非互換/vlan不一致)全是正。一発満点 |
| 2026-07-16 | ENARSI-MPLS-L3VPN-03 | 5 | 撤収済 | 100 | バックドアintra vs コアinter→area0 sham-link(cost20)で主経路化。一発満点 |
| 2026-07-16 | ENCOR-IPSLA-02 | 5 | 撤収済 | 65→100 | 奥ビーコン監視IP SLA+track+固定/32+フローティングdefault。初回SLA source/ビーコン固定漏れ→是正で満点 |
| 2026-07-16 | ENCOR-VRF-NAT-01 | 6 | 撤収済 | 100 | VRF対応PAT(重複10.0.0.1を1グローバルIP共有・ポート分離)+vrf default global。一発満点 |
| 2026-07-16 | GEN-DMVPN-8305 | 3 | 撤収済 | 100 | DMVPN TS。fault=r1_split_horizon_on→ハブTunnel0のno ip split-horizon eigrpで解決。一発満点 |
| 2026-07-15 | GEN-BGPCX-7213 | 5 | 撤収済 | 100 | 4AS7台複合TS。3故障(send-community/default-originate/update-source)全是正。一発満点 |
| 2026-07-15 | ENCOR-OSPFV3-AREA-01 | 6 | 撤収済 | 100 | OSPFv3集約(area range/48)+Totally Stubby+手動RID。一発満点 |
| 2026-07-15 | ENCOR-VRF-LEAK-01 | 6 | 撤収済 | 100 | MP-BGP import/export RTでハブ&スポーク型共有サービス。一発満点 |
| 2026-07-15 | ENARSI-EIGRP-SIA-01 | 5 | 撤収済 | 100 | E0/1受信ACLがEIGRPユニキャスト遮断→access-group外して解決 |

## 記録開始前の既知出題(2026-07-14 以前・メモリからの復元)

| 時期 | 問題ID | 得点 | メモ |
|------|--------|------|------|
| 2026-07 | UM2-BUILD-01 | 96→100 | ユーザ解答。減点はトラック要件まわり |
| 2026-07 | ENARSI-DMVPN-IPSEC-01 | 100 | ユーザ解答(構築問) |
| 2026-07 | GEN-DMVPN(n2・難5) | 100 | ユーザ解答(TS)。seed 記録なし |
