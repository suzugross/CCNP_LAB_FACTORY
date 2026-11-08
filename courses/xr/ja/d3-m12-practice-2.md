# M12 — 実践(2) ポリシングと出口の PE

ラボ **XRT-14** の課題です。ラボから離れた場所でも読めるように、ここに載せています。
取り組むのはラボのワークスペースです。**Tasks** タブに、課題ごとの確認ボタン、段階式のヒント、
通過後に開く模範解があります。コマンド例は意図して示していません。

## M12 — データプレーンの保護と QoS

### 課題 M12-2
<p class="tolab"><a href="/_learn?id=XRT-14&amp;step=m12t2">ワークスペースで開く</a> — 読み物: <a href="d2-m12-police-shape.html#s2-1">2.1 トークン バケツ: 1 速度 2 色</a> · <a href="d2-m12-police-shape.html#s2-2">2.2 2 速度 3 色</a> · <a href="d2-m12-police-shape.html#s3-1">3.1 ポリサ</a> · <a href="d2-m12-police-shape.html#s3-5">3.5 確かめ方</a> · <a href="d0-m12-marking.html#s3-5">3.5 落とし穴</a></p>


顧客 A の契約では、業務の通信(AF21)は、契約速度が 256 kbps、最大が 512 kbps です。

- XR01 がサイト 1 から受け取る業務の通信のうち、契約速度に収まる分はそのまま運び、契約速度を超えて最大に収まる分は
  AF22 にして運び、最大を超える分は捨ててください。
- 音声の通信は、この制限の影響を受けてはなりません。課題 M12-1 の動作は保ってください。

### 課題 M12-3
<p class="tolab"><a href="/_learn?id=XRT-14&amp;step=m12t3">ワークスペースで開く</a> — 読み物: <a href="d0-m12-marking.html#s2-5">2.5 3 つのモデル: 顧客の印とプロバイダーの印</a> · <a href="d0-m12-marking.html#s2-6">2.6 PHP と explicit null: コアで付け替えた印はどこへ行くか</a> · <a href="d0-m12-marking.html#s3-3">3.3 出口の PE: EXP を受け継ぐ</a> · <a href="d2-m12-police-shape.html#s2-4">2.4 キューと優先: LLQ</a> · <a href="d2-m12-police-shape.html#s2-5">2.5 階層の QoS</a> · <a href="d2-m12-police-shape.html#s3-2">3.2 整形と優先(階層)</a></p>


コアの P1 は、混雑への備えとして、PE2 から受け取った業務の通信(EXP 3)を EXP 1 に格下げしています(据え付け)。
顧客 A は、サイト 1 で、コアでの扱いを DSCP で知りたいと考えています。

- XR01 がサイト 1 へ送る通信の DSCP を、コアから届いた EXP に合わせてください。EXP 5 は EF、3 は AF21、1 は AF11、0 は
  DSCP 0 です。
- サイト 1 への出口は、契約の 2 Mbps に整形してください。音声(EXP 5 で届いたもの)は優先して送り、その上限は 512 kbps と
  します。
- P1 と PE2 は変更しないでください。
