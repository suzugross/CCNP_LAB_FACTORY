# PoC: distribute-list の意味論(BL-215)— IOL iol-xe 17.15・EIGRP AS 100

盤面 POC-DLIST = IOL 4 台。RT01(被験)←RT02(e0/0)・RT03(e0/1)、RT04 は RT02 の奥。経路は各ルータの
`ip route … Null0` ＋ `redistribute static`。採取= `sweep.py`、生ログ= `results-raw.md`。
battery: RT02= 10.50.0.0/22・/24・/26・0.16/28・1.0/24・2.0/24・2.128/25・3.0/24 ／ RT03= 10.50.0.0/24・/28・2.0/24・9.0/24 ／
RT04(RT02 経由)= 10.60.0.0/24・/28・1.0/24。基線 13 経路(10.50.0.0/24 と 2.0/24 は RT02・RT03 の等コスト)。

## 1. 結果(2026-09-21)

| ID | フィルタ(全体 `distribute-list … in`) | 残った経路 | 読み取れること |
|---|---|---|---|
| D1a | 標準 `permit 10.50.0.0` | 10.50.0.0 の /22・/24・/26・/28(4 本・カウンタ 5) | 標準 ACL は網アドレスだけ・長さは見ない |
| D1b | 拡張直接 `permit ip any host 10.50.0.0` | D1a と同じ | 直接指定の dst= 網アドレス・長さは見ない |
| D1c | 拡張直接 `permit ip host 10.50.0.0 any` | **なし** | src に網を書いても当たらない |
| D1d | 拡張直接 `permit ip host 10.0.13.3 any` | RT03 の 4 本だけ(等コストの /24 も RT03 側 1 本に) | src= 広告してきた隣接 |
| D1e | 拡張直接 `permit ip host 10.0.24.4 any`(RT04) | **なし** | 経路を作ったルータ(RT04)は src にならない |
| D1f | 拡張直接 `permit ip host 10.0.12.2 host 10.60.0.0` | RT04 の 10.60.0.0 /24 と /28 | 広告元 RT02 × 網。長さは区別されない |
| D1g | route-map 経由 `permit ip host 10.50.0.0 host 255.255.255.0` | 10.50.0.0/24 だけ(両隣接) | route-map 経由= src は網・dst はマスク |
| D1h | prefix-list `10.50.0.0/16 ge 24 le 24` | /24 の 5 本 | アドレスと長さを別々に指定 |
| D1i | 標準 非連続 `permit 10.50.0.0 0.0.2.255` | 10.50.0.x と 2.x の 7 本(長さまちまち) | ワイルドカードはビット一致・長さは見ない |
| D2a | 全体 prefix(/24 だけ)＋ IF(e0/1) ACL(10.50.0.0 のみ) | RT03 からは 10.50.0.0/24 だけ | **全体と IF 単位は両方効く(AND)** |
| D3a/b | 同じ IF に 2 つ目の in(ACL の後に prefix / route-map) | 2 つ目は入らない | **`%EIGRP: Access-list filter exists, de-config first`= 1 IF 1 フィルタ** |
| D4a | route-map 経由 `permit ip 10.50.0.0 0.0.255.255 255.255.255.0 0.0.0.255` | 10.50.x のうち /22 だけ落ちる(/24〜/28 残る) | **マスクのワイルドカード= マスク値の範囲(/24〜/32)** |
| D4b | route-map 経由 src 10.50/16・dst `host 255.255.255.0` | /24 の 5 本(D1h と同じ) | route-map＋拡張 ACL で prefix-list 相当 |
| D5 | 反映時間(clear なし) | 7〜11 秒で反映 | ログ `%DUAL-5-NBRCHANGE: … Neighbor … is resync: route configuration changed` |

## 2. 生成器への含意
- 第 2 部は **1 インターフェイス＝1 タスク**(同 IF に 2 つ目は入らない・方式を変えるときは `no` で外す手順も体験)。
- 全体の distribute-list は全隣接に効く(AND)→ 第 1 部(全体で実験)の後、最終状態では全体を外させる。
- 反映は clear 不要・10 秒前後。確かめ方= resync ログ・`show access-lists` のカウンタ(経路×隣接ごとに 1)・`show ip protocols`(`Ethernet0/1 filtered by 30 (per-user)`)。
- 測定の罠: 変更直後の 2 回連続一致で「安定」とみなすと変化前を掴む(初回 D1a/D1b で踏んだ)→ 変化を待ってから安定判定。
