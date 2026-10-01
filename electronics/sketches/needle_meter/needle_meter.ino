// needle_meter — ステッピングモーターの針で温度を指す
// 目盛りの左端 = T_LOW ℃、右端 = T_HIGH ℃ (半円 = 180°)。0.5 秒ごとに温度を測って針を動かす。
//
// 針の 0 合わせ (起動したとき):
//   起動してから 3 秒のあいだ、BOOT を押している間だけ針が左へ回る。左端の目盛りで離す。
//   3 秒なにもしなければ「いまの位置が左端」として始まる。
// 片付けるとき: BOOT を 2 秒長押しすると、針が左端に戻って止まる。次に起動したときは 0 合わせが要らない。
//
// 配線は stepper_test と thermistor_test を合わせたもの。
// ボード: ESP32 Dev Module (Freenove ESP32 WROOM) / ESP32 Arduino core 3.x

const int COIL_PINS[4] = {14, 27, 26, 25};   // ULN2003AN 1B〜4B (青・ピンク・黄・橙)
const int THERM_PIN = 34;
const int BOOT_BUTTON = 0;

// ---- 目盛り ----
const float T_LOW = 10;              // 左端の温度 (℃)
const float T_HIGH = 40;             // 右端の温度 (℃)
const int SWEEP_STEPS = 1024;        // 左端から右端まで = 180° (1 回転 2048 ステップの半分)
bool REVERSE = false;                // ★ 温度が上がると針が左へ回るなら true にする

// ---- 動かし方 ----
const int STEP_MS = 3;
const int JOG_STEP_MS = 6;           // 0 合わせのときはゆっくり
const int DEADBAND = 3;              // これより小さいずれ (約 0.1℃) では動かない
const unsigned long MEASURE_MS = 500;
const unsigned long ZERO_WAIT_MS = 3000;
const unsigned long PARK_PRESS_MS = 2000;
const float SMOOTH = 0.3f;           // 温度のなめらかさ (0〜1。小さいほどゆっくり追う)

// ---- 温度 (thermistor_test と同じ) ----
float VCC_MV = 3300;                 // ★ テスターで測った 3V3 の値にすると正確
const float R_FIXED = 10000, R25 = 10000, B_CONST = 3960;

int readMilliVolts() {
  long sum = 0;
  for (int i = 0; i < 16; i++) sum += analogReadMilliVolts(THERM_PIN);
  return (int)(sum / 16);
}

float readCelsius() {
  int mv = readMilliVolts();
  if (mv <= 0 || mv >= VCC_MV) return NAN;
  float r = R_FIXED * (VCC_MV - mv) / mv;
  return 1.0f / (1.0f / (25.0f + 273.15f) + logf(r / R25) / B_CONST) - 273.15f;
}

// ---- モーター (stepper_test と同じ) ----
int phase = 0;
int position = 0;                    // いまの針の位置 (左端 = 0)

void coilsOff() {
  for (int i = 0; i < 4; i++) digitalWrite(COIL_PINS[i], LOW);
}

void stepOnce(int dir) {             // dir = +1 で右へ (温度が上がる向き)
  int d = REVERSE ? -dir : dir;
  phase = (phase + (d > 0 ? 1 : 3)) % 4;
  for (int i = 0; i < 4; i++) digitalWrite(COIL_PINS[i], (i == phase) ? HIGH : LOW);
  position += dir;
}

bool bootDown() { return digitalRead(BOOT_BUTTON) == LOW; }

// 起動直後の 0 合わせ
void zeroNeedle() {
  Serial.println("針の 0 合わせ: BOOT を押している間、針が左へ回ります。左端の目盛りで離してください");
  unsigned long quietSince = millis();
  while (millis() - quietSince < ZERO_WAIT_MS) {
    if (bootDown()) {
      stepOnce(-1);
      delay(JOG_STEP_MS);
      quietSince = millis();
    } else {
      coilsOff();
      delay(10);
    }
  }
  coilsOff();
  position = 0;
  Serial.println("ここを左端 (0) にして、温度計を始めます");
}

// 左端に戻して止まる (片付け用)
void park() {
  Serial.println("左端に戻します");
  while (position > 0) { stepOnce(-1); delay(STEP_MS); }
  coilsOff();
  Serial.println("止まりました。電源を切ってかまいません (EN ボタンで再起動)");
  while (true) delay(1000);
}

float tempSmooth = NAN;
int target = 0;
bool moving = false;
unsigned long lastMeasureMs = 0, lastStepMs = 0, lastPrintMs = 0, pressSince = 0;

void setup() {
  Serial.begin(115200);
  for (int i = 0; i < 4; i++) pinMode(COIL_PINS[i], OUTPUT);
  coilsOff();
  pinMode(BOOT_BUTTON, INPUT_PULLUP);
  delay(500);
  zeroNeedle();
}

void loop() {
  // BOOT の長押しで片付け
  if (bootDown()) {
    if (pressSince == 0) pressSince = millis();
    if (millis() - pressSince >= PARK_PRESS_MS) park();
  } else {
    pressSince = 0;
  }

  // 温度 → 針の目標位置
  if (millis() - lastMeasureMs >= MEASURE_MS) {
    lastMeasureMs = millis();
    float c = readCelsius();
    if (!isnan(c)) {
      tempSmooth = isnan(tempSmooth) ? c : tempSmooth + (c - tempSmooth) * SMOOTH;
      float ratio = (tempSmooth - T_LOW) / (T_HIGH - T_LOW);
      target = (int)(constrain(ratio, 0.0f, 1.0f) * SWEEP_STEPS);
    }
  }

  // 目標へ 1 ステップずつ。DEADBAND より離れたら動き出し、ぴったり着いたら止まってコイルを切る
  int diff = target - position;
  if (!moving && abs(diff) > DEADBAND) moving = true;
  if (moving && diff == 0) {
    moving = false;
    coilsOff();
  }
  if (moving && millis() - lastStepMs >= (unsigned long)STEP_MS) {
    lastStepMs = millis();
    stepOnce(diff > 0 ? 1 : -1);
  }

  if (millis() - lastPrintMs >= 1000) {
    lastPrintMs = millis();
    Serial.printf("%.1f ℃  針 %4d / %d ステップ\n", tempSmooth, position, SWEEP_STEPS);
  }
}
