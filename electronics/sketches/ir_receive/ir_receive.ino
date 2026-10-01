// ir_receive — 赤外線リモコンのボタンのコードを読む
// リモコン (秋月 107245, NEC フォーマット) のボタンを押すと、シリアルモニタ (115200bps) に
//   メーカー 0x10EF  キー 0x??
// のように出る。押し続けると「リピート」が 108ms ごとに出る。基板の青い LED (IO2) も光る。
// ライブラリは使わず、受信モジュールの出力が変わった時刻の差から 0 と 1 を読み分ける。
//
// 配線: 受信モジュール OSRB38C9AA (レンズを手前に向けて左から OUT・GND・VCC)
//   OUT → IO34、GND → GND、VCC → 3V3
// ボード: ESP32 Dev Module (Freenove ESP32 WROOM) / ESP32 Arduino core 3.x

const int IR_PIN = 34;
const int BLUE_LED = 2;              // Freenove の青い LED。DevKitC には無い (光らないだけ)

// ---- NEC の解読 (ir_light_sound・ir_car と同じ) ----
// 受信モジュールは光を受けている間 LOW になる。LOW の長さ (マーク) と HIGH の長さ (スペース) で読む:
//   リーダー: マーク 9ms + スペース 4.5ms     リピート: マーク 9ms + スペース 2.25ms
//   0: マーク 0.56ms + スペース 0.56ms        1: マーク 0.56ms + スペース 1.69ms
//   32 ビット = メーカー 16 ビット + キー 8 ビット + キーの反転 8 ビット (下位ビットから)
volatile uint32_t irLastUs = 0;
volatile uint8_t irState = 0;        // 0: 待ち  1: リーダーのマークの後  2: ビットを読んでいる
volatile bool irMarkOk = false;
volatile uint32_t irBits = 0;
volatile uint8_t irCount = 0;
volatile uint32_t irFrame = 0;       // 読めた 32 ビット
volatile bool irGotFrame = false;
volatile bool irGotRepeat = false;

static inline bool near(uint32_t t, uint32_t target, uint32_t tol) {
  return t + tol >= target && t <= target + tol;
}

// 出力が変わるたびに呼ぶ。high = 変わった後のレベル、dt = 前に変わってからの時間 (µs)
void irEdge(bool high, uint32_t dt) {
  if (high) {                                    // マークが終わった
    if (near(dt, 9000, 1500)) irState = 1;       // リーダー (またはリピート) の始まり
    else if (irState == 2 && near(dt, 560, 300)) irMarkOk = true;
    else irState = 0;
  } else {                                       // スペースが終わった
    if (irState == 1) {
      if (near(dt, 4500, 800)) { irState = 2; irBits = 0; irCount = 0; irMarkOk = false; }
      else if (near(dt, 2250, 500)) { irGotRepeat = true; irState = 0; }
      else irState = 0;
    } else if (irState == 2 && irMarkOk) {
      irMarkOk = false;
      if (near(dt, 1690, 400)) irBits |= (1UL << irCount);
      else if (!near(dt, 560, 300)) { irState = 0; return; }
      irCount = irCount + 1;
      if (irCount == 32) { irFrame = irBits; irGotFrame = true; irState = 0; }
    }
  }
}

void onIrChange() {                  // 割り込みで呼ばれる (出力が変わるたび)
  uint32_t now = micros();
  irEdge(digitalRead(IR_PIN) == HIGH, now - irLastUs);
  irLastUs = now;
}

// 読めたフレームの中身。キーとその反転が合わなければ false
bool irDecode(uint32_t frame, uint16_t &maker, uint8_t &key) {
  maker = (uint16_t)(((frame & 0xFF) << 8) | ((frame >> 8) & 0xFF));   // 送られた順に 0x10EF のように並べる
  key = (frame >> 16) & 0xFF;
  uint8_t inv = (frame >> 24) & 0xFF;
  return (uint8_t)(key ^ inv) == 0xFF;
}
// ---- ここまで ----

unsigned long ledOffMs = 0;

void setup() {
  Serial.begin(115200);
  pinMode(IR_PIN, INPUT);
  pinMode(BLUE_LED, OUTPUT);
  attachInterrupt(digitalPinToInterrupt(IR_PIN), onIrChange, CHANGE);
  Serial.println("リモコンを受信モジュールに向けて、ボタンを押してください");
}

void loop() {
  if (irGotFrame) {
    irGotFrame = false;
    uint16_t maker;
    uint8_t key;
    if (irDecode(irFrame, maker, key)) {
      Serial.printf("メーカー 0x%04X  キー 0x%02X\n", maker, key);
    } else {
      Serial.printf("読み違い (0x%08lX)\n", (unsigned long)irFrame);
    }
    digitalWrite(BLUE_LED, HIGH);
    ledOffMs = millis() + 100;
  }
  if (irGotRepeat) {
    irGotRepeat = false;
    Serial.println("  (リピート)");
    digitalWrite(BLUE_LED, HIGH);
    ledOffMs = millis() + 100;
  }
  if (ledOffMs && millis() > ledOffMs) {
    digitalWrite(BLUE_LED, LOW);
    ledOffMs = 0;
  }
}
