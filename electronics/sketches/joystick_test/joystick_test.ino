// joystick_test — Grove ジョイスティックの値を見る
// シリアルプロッタ (115200bps) に、X と Y を -100〜100 (%) で出す。押し込みも表示する。
// 起動するときはスティックに触らない (そのときの位置を「真ん中」として覚える)。
// 起動したら一度スティックをぐるっと大きく回す (端の位置を覚える)。
//
// 配線 (Grove → ピンヘッダーの変換ケーブル経由):
//   黄 (X) → IO34   白 (Y) → IO35   赤 (VCC) → 3V3   黒 (GND) → GND
//   ※ VCC は必ず 3V3。5V にすると押し込んだときに X が 5V になり、ESP32 の入力を壊す
// ボード: ESP32 Dev Module / ESP32 Arduino core 3.x

const int JOY_X_PIN = 34;            // ADC1。Wi-Fi (ESP-NOW) を使っても読める側
const int JOY_Y_PIN = 35;

// ★ 倒した向きと符号が逆なら true にする (右に倒して +、前に倒して + になるように)
bool INVERT_X = false;
bool INVERT_Y = false;

const int PRESS_RAW = 3900;          // 押し込むと X が 3.3V いっぱい (4095 付近) になる
const int DEAD = 8;                  // 真ん中の遊び (%)。手を離しても 0 にならないなら上げる
const int START_RANGE = 600;         // 端の位置を覚えるまでの仮の幅 (生の値)

struct Axis {
  int pin;
  bool invert;
  int center, lo, hi;
};
Axis ax = {JOY_X_PIN, false, 0, 0, 0};
Axis ay = {JOY_Y_PIN, false, 0, 0, 0};

int readRaw(int pin) {               // 4 回読んで平均。0〜4095
  long sum = 0;
  for (int i = 0; i < 4; i++) sum += analogRead(pin);
  return (int)(sum / 4);
}

void calibrate(Axis &a) {
  long sum = 0;
  for (int i = 0; i < 32; i++) { sum += analogRead(a.pin); delay(2); }
  a.center = (int)(sum / 32);
  a.lo = a.center - START_RANGE;
  a.hi = a.center + START_RANGE;
}

// 生の値を -100〜100 に。倒しきった位置を覚えながら、真ん中から左右別々に割る
int toPercent(Axis &a, int raw) {
  if (raw > a.hi) a.hi = min(raw, PRESS_RAW - 300);   // 押し込み途中の値で幅を広げすぎない
  if (raw < a.lo) a.lo = raw;
  float v = (raw >= a.center) ? (float)(raw - a.center) / max(1, a.hi - a.center)
                              : -(float)(a.center - raw) / max(1, a.center - a.lo);
  int p = (int)(v * 100);
  if (abs(p) <= DEAD) return 0;
  p = (p > 0 ? p - DEAD : p + DEAD) * 100 / (100 - DEAD);   // 遊びの外側を 0〜100 に広げ直す
  p = constrain(p, -100, 100);
  return a.invert ? -p : p;
}

void setup() {
  Serial.begin(115200);
  analogReadResolution(12);
  ax.invert = INVERT_X;
  ay.invert = INVERT_Y;
  delay(300);
  calibrate(ax);
  calibrate(ay);
  Serial.printf("真ん中: X=%d  Y=%d (生の値)\n", ax.center, ay.center);
}

void loop() {
  int rx = readRaw(JOY_X_PIN);
  int ry = readRaw(JOY_Y_PIN);
  bool pressed = (rx >= PRESS_RAW);
  int x = pressed ? 0 : toPercent(ax, rx);   // 押している間の X は使えないので 0 にする
  int y = toPercent(ay, ry);

  // シリアルプロッタ用 (名前:値)。rawX / rawY は生の値を 1/40 にして同じグラフに収める
  Serial.printf("x:%d,y:%d,press:%d,rawX:%d,rawY:%d\n", x, y, pressed ? 100 : 0, rx / 40, ry / 40);
  delay(50);
}
