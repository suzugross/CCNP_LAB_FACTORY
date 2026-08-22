# IP SLA/track PoC 実測 (BL-134・2026-08-22)

盤面= `_POC-IPSLA`(4 IOL・ENCOR-IPSLA-02 の写し: RT01=顧客 / RT02=primary ISP /
RT03=backup ISP / RT04=Internet+ビーコン。戻り経路ポリシー= RT04→10.0.12.1 は
primary 限定・RT04→1.1.1.1 は backup 優先+AD200)。探針= probe.py、生ログ=
results-raw.md。gen_ipsla_ts の設計前提となる実測知見。

## 確定した挙動

### 基線(p0)

1. **タイミング**: golden(icmp-echo ビーコン・frequency 10)投入→track Up **11s**。
   奥障害(RT02-RT04 断)→track Down **7s**→backup 切替・疎通 100%。復旧→Up **7s**。
   採点の収束待ちは 30s も見れば十分(frequency 10 の場合)。
2. **書式**: `show track 1` は `Reachability is Up/Down`+`Latest operation return
   code:`。`show ip route track-table` は
   `ip route 0.0.0.0 0.0.0.0 10.0.12.2 track 1 state is [up]` の1行形。
   `show ip sla configuration` に timeout(既定5000)/frequency/threshold(既定5000)/
   Life/Status(Active|notInService) が全部出る(読解素材)。

### 編集ロック(p1)

3. **稼働中の SLA エントリは再入不可**:
   `Entry already running and cannot be modified` `(only can delete (no) and start
   over)` が返り、定義変更は `% Invalid input` になる。
4. **★unschedule すれば編集できる**(IOL では delete 必須ではない):
   `no ip sla schedule 1`→`frequency 20` 受理→再 schedule で稼働再開を確認。
   **fix 手順は「unschedule→編集→再 schedule」で成立**(no ip sla N から作り直しも可)。
5. **★unschedule の副作用**: Life が既定 **3600 に戻る**(notInService 表示)。
   再 schedule で `life forever` を言い直さないと1時間で止まる時限爆弾になる
   (故障種候補: life 有限で「翌日から backup 固着」)。

### 不稼働系の指紋(p2/p3/p8b)

6. **未 schedule**: track Down・return code **Unknown**・statistics は
   `Number of successes: Unknown` `Operation time to live: 0`。
   稼働失敗(Timeout)と**指紋が違う**のが診断の決め手。
7. **存在しない SLA 番号を track が参照**: 同じく Down/Unknown。決め手は
   `show track` の `IP SLA 2 reachability` と `show ip sla configuration` の
   Entry 番号の突き合わせ。
8. **★timeout>frequency は設定時素通り・schedule 時に拒否**:
   `%Scheduling a probe with timeout 20000 ms greater than frequency 5000 ms is
   not allowed.`(threshold>timeout も同型:
   `%Scheduling a probe with threshold 30000 ms greater than timeout 4000 ms is
   not allowed.`)。**day0 に焼くと schedule 行だけ落ちて「未 schedule と同じ指紋」
   の壊れ方になる**(running-config に schedule が残らない)。
9. **threshold は reachability に効かない**: threshold 4000(RTT 1〜30ms の遥か上)
   でも track Up のまま。「threshold を下げて切替を早める」は誤解(紙面向き知見)。

### オペレーション種別(p4/p4b/p5)

10. **★★path-echo は IOL で不発**: `path-echo <宛先> source-ip <IP>` は構文として
    受理されるが、**既定(`no ip source-route`)でも全機 `ip source-route` 有効化でも
    return code Timeout のまま上がらない**。同時点の通常 ping は 100%。
    per-hop 統計も出ない(details にも無し)。→ **ラボの故障種としては
    「path-echo 残骸=何をしても上がらない→icmp-echo への差し替えが唯一解」で出す**。
    「path-echo を活かす」要件世界は IOL では成立しないので作らない
    (実機ハードウェアでの挙動は未確認とだけ解説に書く)。
11. **udp-jitter は responder 必須**: 無し= return code **No connection**
    (Timeout と区別できる第3の指紋)・有り= responder 投入から **11s** で Up。
    jitter 書式(RTT Values/Latency one-way/Jitter Time/MOS)は results-raw.md
    p5 に全文。responder 側は `ip sla responder` 1行。
12. **IOL の `ip source-route` 既定は無効**(`show run all`= `no ip source-route`)。

### source 誤り(p7)

13. **backup 側 IF を source**: 戻り経路ポリシーで全滅(Timeout・track Down)=
    backup 固着形。
14. **★★Lo0 を source**: RT04 の 1.1.1.1 向け戻りが backup 優先のため
    **非対称往復で成功し track Up**。「監視は動いているが primary の健全性を
    見ていない」**不感形**が成立(奥障害時に…ではなく、戻り経路の監視が
    そもそも抜けている)。設計どおりの高価値故障種。

### route 系(p8/p9)

15. **AD 同値の floating 不成立**: backup を AD1 で並置すると RIB に 2 RDB
    (ECMP 混走)。疎通は 100% なので**ポリシー違反型**(採点は RIB/config で)。
16. **★★pin_missing(ビーコン /32 固定漏れ)= フェイルバック不能ラッチ**:
    平常時は track Up(プローブが default=primary を追って成功)の**潜在故障**。
    奥障害で Down・切替は機能。**復旧してもプローブは backup 側 default を追って
    ビーコンに届かず track Down のまま**(150s+ 観測)。fix(/32 投入)から **3.7s**
    で Up・primary 復帰。TS シナリオ=「障害復旧後も backup に張り付いたまま」。

### tcp-connect(p6c)

17. **tcp-connect(control disable)は実在ポートで成立**: RT04 vty(telnet)宛
    port 23= return code OK・RTT 1ms・track Up。**誰も listen しないポート
    (8080)= return code `Socket connect error`**(RST 到達=L3 は健全、の証拠に
    なる**第4の指紋**)。★tcp-connect の既定 timeout は 60000ms なので
    `timeout 5000` 等を明示しないと frequency と衝突して schedule 拒否(知見8)。
18. (副産物)p6/p6b の失敗より: **宛先への経路が無い場合の return code は
    Timeout**(Socket connect error にはならない)。

## return code 指紋の一覧表(診断の決め手・全て実測)

| return code | 意味(この盤面での原因) |
|---|---|
| OK | 成功 |
| Timeout | 応答が返らない(経路断・戻り経路なし・source 誤り・path-echo 残骸・**宛先へ経路なし**) |
| Unknown | **稼働していない**(未 schedule / schedule 拒否 / track の参照先 SLA が不存在) |
| No connection | udp-jitter の responder 不在(制御ハンドシェイク不成立) |
| Socket connect error | tcp-connect が RST を受けた(L3 は届いている・ポート違い) |

## E2E 自己検品 (gen_ipsla_ts・2026-08-22・e2e.sh)

全13故障種で provision→broken採点→fix_generated→採点→teardown のフルサイクル。
不感系4種は fix 後に verify_ipsla_generated.yml(奥障害注入→切替→復帰)も実行。

| 故障種 | broken | fix後 | 破壊実証 |
|---|---|---|---|
| sla_not_scheduled | 55 | 100 | - |
| sla_wrong_source | 55 | 100 | - |
| sla_wrong_source_lo | 90 | 100 | PASS |
| sla_wrong_target | 90 | 100 | PASS |
| op_pathecho | 50 | 100 | - |
| op_udp_jitter | 50 | 100 | - |
| op_tcp_connect | 50 | 100 | - |
| track_wrong_sla | 75 | 100 | - |
| pin_missing | 55 | 100 | PASS |
| pin_wrong_nh | 55 | 100 | - |
| route_track_missing | 80 | 100 | PASS |
| ad_not_floating | 75 | 100 | - |
| acl_probe_block | 65 | 100 | - |
| ★複合 `--faults 2`(wrong_source_lo×route_track_missing) | 70 | 100 | PASS |

- ★**pin_missing は day0 でラッチが即時成立する**(ブート順でプローブが先に失敗→
  track Down→default が backup へ→固定なしのプローブは backup を追って恒久失敗)。
  盤面は最初から backup 固着で観測される=チケット「復旧後も戻らない」と整合し、
  broken 55(状態チェックも落ちる)になる。
- 不感系(wrong_source_lo/wrong_target)は broken 90= 落ちるのは監視標準との
  config 差分のみ、が想定どおりの形。
- track_wrong_sla の fix は `track T ip sla S reachability` の**直接再定義で成立**
  (no 形不要・実機確認)。

## p10 症状文監査(2026-08-22・出題初日のユーザ指摘を受けた事後実測)

PACK-20260822-D Q1 で sla_wrong_target のチケット(フラップ)が実挙動と矛盾すると
ユーザが発見 → 机上予測で書いた2種の症状文を実測で是正した。

19. **sla_wrong_source_lo(source=Lo0)の真の症状= 誤フェイルオーバ**:
    ①primary 奥障害は**普通に検知する**(Down まで 10.2s。「切替されず Up のまま」
    という当初の症状文は誤り)。②★**backup 奥障害で誤って Down(10.2s)**→
    健全な primary から死んだ backup へ切替→ **ping 0% 全断**(プローブ応答が
    RT04 の Lo0 宛戻り=backup 優先に依存しているため)。対照= golden source は
    同状況で track Up を維持。
20. **sla_wrong_target(データ宛監視)は機能症状が出ない**: プローブ送信元
    (primary IF アドレス)への戻りが primary 限定のため、default 追従でも backup
    経由で成功できず、**フラップは構造的に不成立**。奥障害の検知・復帰も golden と
    外形が同じ → チケットは「構成監査からの不適合指摘」形に変更。
21. (盤面特性・チケット使用禁止)backup 側奥障害では **golden でもデータが全断**
    する= RT04 の Lo0 宛戻りが backup 優先で、IOL リンクダウン非伝播により
    AD200 フォールバックが発動しないため(p10 対照で track Up・ping 0% を実測)。
22. ★恒久教訓: **症状文(チケット)も実測対象**。E2E の「fix で満点」だけでは
    症状文の正しさは保証されない。

## 生成器設計への反映(design.md への差分)

- 故障種に追加: `sla_life_finite`(知見5)・`sla_schedule_rejected`(知見8)・
  `sla_wrong_source_lo`(知見14・★p10 で誤フェイルオーバ形と確定)。
- `op_pathecho_blocked` は「差し替え唯一解」形に確定(知見10)。要件世界Bは廃止。
- 収束待ち: frequency 10 なら遷移 7〜11s。採点は 30s 待ちで安全。
- 破壊実証の破壊点= RT02 e0/2 shutdown(奥)。track Down 0.4〜7s で速い。
