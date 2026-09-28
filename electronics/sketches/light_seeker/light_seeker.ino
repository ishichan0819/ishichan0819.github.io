// light_seeker — 首を振って「いちばん明るい方向」を探し、そっちを向く
// サーボの腕に CdS を貼り付けて使う。
//   1. 20° → 160° を 5° ずつ動きながら、各角度で明るさを測る (スキャン)
//   2. いちばん明るかった角度を向いて、3 秒じっとする
//   3. くり返し
// シリアルモニタ (115200bps) に、スキャン結果が棒グラフで出る。
//
// 配線は cds_servo と同じ。CdS だけ、オス-メスのジャンパー線で延長してサーボの腕に貼る。
// ボード: ESP32 Dev Module / ESP32 Arduino core 3.x

const int SERVO_PIN = 25;
const int CDS_PIN = 34;

const uint32_t SERVO_HZ = 50;
const uint8_t  SERVO_BITS = 16;
const int SERVO_MIN_US = 500;
const int SERVO_MAX_US = 2400;

const int SCAN_FROM = 20;
const int SCAN_TO = 160;
const int SCAN_STEP = 5;
const int SETTLE_MS = 60;            // サーボが止まり、CdS が反応しきるまで待つ時間 (CdS の応答は 20〜30ms)
const unsigned long HOLD_MS = 3000;  // 見つけた方向を向いている時間

const int N_STEPS = (SCAN_TO - SCAN_FROM) / SCAN_STEP + 1;
int scanMv[N_STEPS];

void servoWrite(float deg) {
  deg = constrain(deg, 0.0f, 180.0f);
  uint32_t us = SERVO_MIN_US + (uint32_t)((SERVO_MAX_US - SERVO_MIN_US) * deg / 180.0f);
  uint32_t duty = (uint32_t)((uint64_t)us * ((1UL << SERVO_BITS) - 1) / (1000000UL / SERVO_HZ));
  ledcWrite(SERVO_PIN, duty);
}

int readCdsMilliVolts() {
  long sum = 0;
  for (int i = 0; i < 8; i++) sum += analogReadMilliVolts(CDS_PIN);
  return (int)(sum / 8);
}

// ゆっくり動かす (急に動かすと CdS のケーブルが引っかかる・電源が揺れる)
void moveSlowly(int from, int to) {
  int step = (to > from) ? 1 : -1;
  for (int a = from; a != to; a += step) {
    servoWrite(a);
    delay(8);
  }
  servoWrite(to);
}

// 1 回スキャンして、いちばん明るかった角度を返す
int scan() {
  int bestAngle = SCAN_FROM;
  int bestMv = -1;
  int minMv = 100000;

  moveSlowly(90, SCAN_FROM);
  delay(300);
  for (int i = 0; i < N_STEPS; i++) {
    int a = SCAN_FROM + i * SCAN_STEP;
    servoWrite(a);
    delay(SETTLE_MS);
    scanMv[i] = readCdsMilliVolts();
    if (scanMv[i] > bestMv) { bestMv = scanMv[i]; bestAngle = a; }
    if (scanMv[i] < minMv) minMv = scanMv[i];
  }

  // 結果を棒グラフで表示 (いちばん暗い値を 0、いちばん明るい値を 40 文字として)
  Serial.println("--- scan ---");
  for (int i = 0; i < N_STEPS; i++) {
    int a = SCAN_FROM + i * SCAN_STEP;
    int bars = (bestMv > minMv) ? (scanMv[i] - minMv) * 40 / (bestMv - minMv) : 0;
    Serial.printf("%3d° %5d mV |", a, scanMv[i]);
    for (int b = 0; b < bars; b++) Serial.print('#');
    Serial.println(a == bestAngle ? "  <- ここ" : "");
  }

  // 明るさの差がほとんどない (= どこも同じ明るさ) ときは正面を向く
  if (bestMv - minMv < 30) {
    Serial.println("明るさの差が小さいので正面 (90°) を向きます");
    bestAngle = 90;
  }
  moveSlowly(SCAN_TO, bestAngle);
  return bestAngle;
}

void setup() {
  Serial.begin(115200);
  ledcAttach(SERVO_PIN, SERVO_HZ, SERVO_BITS);
  servoWrite(90);
  delay(1000);
}

void loop() {
  int best = scan();
  Serial.printf("いちばん明るい方向: %d°\n\n", best);
  delay(HOLD_MS);
  moveSlowly(best, 90);
}
