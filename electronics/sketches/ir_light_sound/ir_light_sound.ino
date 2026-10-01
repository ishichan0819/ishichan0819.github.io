// ir_light_sound — リモコンのボタンごとに、違う色と音を出す
// ボタンを押すと、基板のフルカラー LED (IO16) がボタンごとの色に光り、圧電スピーカーがボタンごとの音で鳴る。
// 押し続けている間 (リピートが届く間) は音が続く。キーの番号から色と音を決めるので、表を書かなくても動く。
//
// 配線: ir_receive に 圧電スピーカー (IO25 と GND の間、向きはない) を足す
// ボード: ESP32 Dev Module (Freenove ESP32 WROOM) / ESP32 Arduino core 3.1 以降 (rgbLedWrite を使う)

const int IR_PIN = 34;
const int PIEZO_PIN = 25;
const int RGB_LED = 16;              // Freenove のフルカラー LED
const uint8_t BRIGHT = 40;           // LED の明るさ (0〜255)
const unsigned long NOTE_MS = 150;   // 1 回押したときに鳴る長さ

// ド レ ミ ファ ソ ラ シ ド (Hz)
const uint32_t SCALE[8] = {523, 587, 659, 698, 784, 880, 988, 1047};

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

// 色相 (0〜359°) → R, G, B
void hueToRgb(int hue, uint8_t &r, uint8_t &g, uint8_t &b) {
  int sector = hue / 60, f = (hue % 60) * 255 / 60;
  int up = f, down = 255 - f;
  int rr[] = {255, down, 0, 0, up, 255}, gg[] = {up, 255, 255, down, 0, 0}, bb[] = {0, 0, up, 255, 255, down};
  r = rr[sector] * BRIGHT / 255;
  g = gg[sector] * BRIGHT / 255;
  b = bb[sector] * BRIGHT / 255;
}

unsigned long noteOffMs = 0;

void play(uint8_t key) {
  uint8_t r, g, b;
  hueToRgb((key * 47) % 360, r, g, b);           // キーの番号から色を決める (47 を掛けて散らす)
  rgbLedWrite(RGB_LED, r, g, b);
  uint32_t hz = SCALE[key % 8];
  ledcWriteTone(PIEZO_PIN, hz);
  noteOffMs = millis() + NOTE_MS;
  Serial.printf("キー 0x%02X → 色 (%d,%d,%d)  音 %lu Hz\n", key, r, g, b, (unsigned long)hz);
}

void setup() {
  Serial.begin(115200);
  pinMode(IR_PIN, INPUT);
  ledcAttach(PIEZO_PIN, 1000, 8);
  ledcWriteTone(PIEZO_PIN, 0);
  rgbLedWrite(RGB_LED, 0, 0, 0);
  attachInterrupt(digitalPinToInterrupt(IR_PIN), onIrChange, CHANGE);
  Serial.println("リモコンのボタンを押してください");
}

void loop() {
  if (irGotFrame) {
    irGotFrame = false;
    uint16_t maker;
    uint8_t key;
    if (irDecode(irFrame, maker, key)) play(key);
  }
  if (irGotRepeat) {                             // 押し続けている → 音を延ばす
    irGotRepeat = false;
    if (noteOffMs) noteOffMs = millis() + NOTE_MS;
  }
  if (noteOffMs && millis() > noteOffMs) {
    ledcWriteTone(PIEZO_PIN, 0);
    noteOffMs = 0;
  }
}
