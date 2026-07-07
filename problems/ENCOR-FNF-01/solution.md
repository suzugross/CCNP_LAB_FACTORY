# 模範解答 : ENCOR-FNF-01 (Flexible NetFlow 基本構成)

> RT02 にのみ設定。OSPF/到達性は既設。
> ★本問は**パラメータ化済**(`params/<variant>.yml`)。下記は variant=base の値。
> 名前・コレクタ・キー/コレクト項目・サンプラー有無は variant で変わる
> （例: `-e variant=v2` で別アドレス＋L4ポートキー＋collect long＋サンプラー有）。
> 構成手順そのものは同じ。サンプラー有の variant では `sampler <名> / mode ...` を作り、
> IF 適用を `ip flow monitor <名> sampler <サンプラー名> input` にする。

## RT02 — Flexible NetFlow の 3 要素 + IF 適用
```
! 1) フローレコード: 何をキー(match)にし、何を収集(collect)するか
flow record FNF-REC
 match ipv4 source address
 match ipv4 destination address
 match ipv4 protocol
 match transport source-port
 match transport destination-port
 collect counter bytes
 collect counter packets
!
! 2) フローエクスポータ: どこへ(コレクタ)どう(UDP)送るか
flow exporter FNF-EXP
 destination 198.51.100.100
 source Loopback0
 transport udp 2055
!
! 3) フローモニタ: レコード + エクスポータ(キャッシュは既定でよい)
flow monitor FNF-MON
 exporter FNF-EXP
 record FNF-REC
!
! 4) インタフェースへ適用(RT01 向け IF の ingress)
interface Ethernet0/0
 ip flow monitor FNF-MON input
!
```

## 確認
```
show flow record FNF-REC
show flow exporter FNF-EXP
show flow monitor FNF-MON
show flow interface Ethernet0/0
! トラフィックを流してから:
ping 3.3.3.3 source 1.1.1.1 repeat 10        ! RT01 で実行(または下のように RT02 経由)
show flow monitor FNF-MON cache              ! 送信元1.1.1.1 / 宛先3.3.3.3 のフローが見える
show flow monitor FNF-MON statistics
```

### ポイント（基本の要点）
- **FNF は 3 要素の組み立て**:
  - **flow record** = フローの定義。`match` がキー（同じ match 値＝同一フロー）、
    `collect` が集計項目（バイト/パケット等）。最低でも 送信元/宛先 IP を match する。
  - **flow exporter** = エクスポート先（コレクタの IP・UDP ポート・送信元 IF）。
  - **flow monitor** = record と exporter を束ね、キャッシュを保持する実体。
  - 仕上げに **インタフェースへ `ip flow monitor <名> input|output`** で適用して初めて計測が始まる。
- **方向 (input/output)**: 本問は RT01 から入ってくる通過トラフィックを見たいので
  RT01 向け IF (`Ethernet0/0`) の **input** に適用する。output や別 IF だと
  目的のフロー（1.1.1.1→3.3.3.3）がそのキャッシュに乗らない。
- **動作確認はキャッシュで**: 実コレクタが無くても、`show flow monitor FNF-MON cache` で
  採取されたフロー（送信元/宛先/カウンタ）を直接確認できる。トラフィックを流して
  初めてエントリができる点に注意（流す前のキャッシュは空）。
- **エクスポータ宛先は実在不要**: `198.51.100.100` は届かなくてもキャッシュ計測には影響しない
  （export パケットが送られるだけ）。本問の動作確認はキャッシュで行う。

> 採点: record/exporter/monitor の構成、`Ethernet0/0` ingress への適用、RT01→RT03 の
> 能動 ping 疎通、そして RT02 の cache に該当フロー（1.1.1.1 / 3.3.3.3）が採取されることで判定。
