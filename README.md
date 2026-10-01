# ishichan0819.github.io

https://ishichan0819.github.io/

## ページ一覧

- [トップ](https://ishichan0819.github.io/) — 以下のページを選んで遷移するメニュー
- [New Relic: 障害スイッチ](https://ishichan0819.github.io/newrelic/) — 監視ツール検証用のプレイグラウンド
- [Computer 基礎: コンピュータの底](https://ishichan0819.github.io/computer-basics/) — 「キーを押すとどうやって電荷が動くのか」を体験する2つのページ
  - [指先から電荷まで](https://ishichan0819.github.io/computer-basics/yubisaki-kara-denka.html) — 5つの実験
  - [内部をのぞく](https://ishichan0819.github.io/computer-basics/naibu-wo-nozoku.html) — キーボードを打つと内部の回路を電気が走り、モニターに文字が出るアクティビティ
- [電子工作ノート](https://ishichan0819.github.io/electronics/) — ESP32 (DevKitC / Freenove) と秋月電子の部品で動くものを作る記録。開発環境、部品、首振りガジェット (CdS + サーボ)、障害物回避カー (HC-SR04 + DRV8835)、ワイヤレス操縦 (ESP-NOW + ジョイスティック)、針で指す温度計 (28BYJ-48 + ULN2003AN + サーミスター)、赤外線リモコン (NEC フォーマットを自前で解読)、光で文字を送る (LED + CdS) の回路図・ブレッドボード配線図・Arduino スケッチ
- [Visible Light: 光で文字を送る](https://ishichan0819.github.io/visible-light/) — LEDの点滅で文字を送って復号する、可視光通信(Li-Fi)のアクティビティ
- [CSK / DCSK: 色で文字を送る](https://ishichan0819.github.io/csk/) — RGB-LEDの色でビットを送るCSKと、LEDのON/OFF個数で色を作るDCSKを比べるアクティビティ
- [スマホ同士で光通信](https://ishichan0819.github.io/screen-camera/) — 1台の画面の色を切り替えて文字を送り、もう1台のカメラで読み取る画面→カメラ通信。色を必ず変える差動符号、パケットごとの色の見本による色較正、CRC つき。カメラの映像は端末の中だけで処理し、カメラなしで試すモードもある
- [QLED CSK: 4色で色を送る](https://ishichan0819.github.io/qled-csk/) — IEEE 802.15.7 の3色 CSK (TLED) と、青・シアン・黄・赤の4色 LED で信号点を四角形に置く QLED CSK (Singh ら, 2014) を、CIE 1931 色度図、信号空間の最小距離、シンボル誤り率 (SNR・反射による遅延の広がり・受信部品の損失・判定方法) で比べるアクティビティ
- [Indoor VLC: 部屋じゅうに光を届ける](https://ishichan0819.github.io/indoor-vlc/) — 天井のLED照明から部屋のあちこちへ光でデータを届ける室内可視光通信のシミュレータ。照度とSNRの地図、壁の反射による遅延の広がり、人の影とハンドオーバー
- [Optical OFDM: 狭い帯域で速く送る](https://ishichan0819.github.io/ofdm/) — 帯域が数MHzしかないLEDで速く送る光OFDMのアクティビティ。OOKのアイパターン、エルミート対称、DCO/ACO-OFDMのBER比較、ビット割り当て
- [FPGA DCSK: FPGA で色を送る](https://ishichan0819.github.io/fpga-dcsk/) — Zybo / Eclypse Z7 用に書いた DCSK 送信回路 (分周カウンタ・LFSR・LED 9個の色の表) の Verilog を、仮想ボードでクロック単位から実時間まで動かすアクティビティ。色の表を書き換えて Verilog を作り、受信側の帯域・距離・外光で誤り率がどう変わるかを確かめる
- [AWS 基盤パズル](https://ishichan0819.github.io/aws-platform/) — AWS 公式の実装ガイド・リファレンスアーキテクチャや企業の事例 (SeatGeek、Slack) で紹介されている構成を、枠に部品を置いて矢印でつないで組み立てる構成図の演習 (全16問)。解答例と元にした資料へのリンクつき
- [競プロ アルゴリズム図鑑](https://ishichan0819.github.io/algo/) — AtCoder 茶色から青色を目指す 12 のアルゴリズム。ステップ実行できる図と C++ / Python の実装
  - [競プロ 5分ドリル](https://ishichan0819.github.io/algo/drill.html) — 図鑑の12のアルゴリズムを、読む・穴埋め・並べる・組み立ての4段階で自分で書けるまで練習するスマホ向けドリル (Python / C++、復習つき、ホーム画面に追加してオフラインでも使える)
- [タルとハシゴ](https://ishichan0819.github.io/barrel/) — 斜めの足場とハシゴをのぼり、樽を飛び越えててっぺんを目指すレトロ風アクションゲーム
