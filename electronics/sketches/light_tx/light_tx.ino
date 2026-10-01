// light_tx — 基板のフルカラー LED の点滅で文字を送る (送る側。配線なし)
// シリアルモニタ (115200bps) に文字を打って Enter を押すと、その 1 行を光で送る。
// 何も打たなければ、MESSAGE を送り終わるたびに 5 秒休んで、また送る。
// シリアルモニタの改行の設定は「改行なし」以外にする (Enter で行の終わりが届くように)。
//
// 1 文字の送り方 (OOK、1 = 点灯 / 0 = 消灯):
//   スタートビット 1 (点灯) → データ 8 ビット (下位ビットから) → ストップビット 0 (消灯) を STOP_BITS 個
//   送っていない間は消灯。1 行の頭に 0x01 (受け取る側は表示しない) を付け、終わりに改行を付ける。
// TEST_MODE = true にすると、"0123456789" を休みなく送り続ける (受け取る側で誤りを数える実験用)。
// ボード: ESP32 Dev Module (Freenove ESP32 WROOM) / ESP32 Arduino core 3.1 以降 (rgbLedWrite を使う)

const int RGB_LED = 16;
const uint8_t ON_LEVEL = 255;        // 白でいちばん明るく

// ★ 受け取る側 (light_rx) と同じ値にする
int BIT_MS = 100;                    // 1 ビットの長さ。100ms = 10 ビット/秒 (1 文字 11 ビットで 約 1 文字/秒)
bool TEST_MODE = false;

const int STOP_BITS = 2;             // 消灯で区切る長さ。CdS が暗さに戻るのを待つため 2 ビットにしている
const char *MESSAGE = "HELLO ESP32";
const unsigned long REPEAT_MS = 5000;

unsigned long bitClock = 0;          // 次のビットの終わりの時刻 (ずれがたまらないよう、足していく)

void sendBit(bool one) {
  uint8_t v = one ? ON_LEVEL : 0;
  rgbLedWrite(RGB_LED, v, v, v);
  bitClock += BIT_MS;
  while ((long)(millis() - bitClock) < 0) { }      // ビットの終わりまで待つ
}

void sendByte(uint8_t b) {
  sendBit(true);                                    // スタート
  for (int i = 0; i < 8; i++) sendBit((b >> i) & 1);
  for (int i = 0; i < STOP_BITS; i++) sendBit(false);
}

void sendLine(const char *s) {
  bitClock = millis();
  sendByte(0x01);                                   // 頭の印 (受け取る側の明るさ合わせ用)
  for (const char *p = s; *p; p++) sendByte((uint8_t)*p);
  sendByte('\n');
  Serial.printf("送りました: %s\n", s);
}

void setup() {
  Serial.begin(115200);
  rgbLedWrite(RGB_LED, 0, 0, 0);
  Serial.printf("1 ビット %d ms で送ります。送りたい文字を打って Enter\n", BIT_MS);
}

String typed;
unsigned long lastSendMs = 0;

void loop() {
  if (TEST_MODE) {
    sendLine("0123456789");
    return;
  }
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (typed.length() > 0) { sendLine(typed.c_str()); typed = ""; lastSendMs = millis(); }
    } else {
      typed += c;
    }
  }
  if (millis() - lastSendMs >= REPEAT_MS) {
    sendLine(MESSAGE);
    lastSendMs = millis();
  }
}
