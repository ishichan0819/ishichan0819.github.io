// light_follower — CdS 2 個の明るさを比べて、光を追いかけて首を回す
// サーボの腕に CdS を 2 個、少し外向きに開いて付け、間に厚紙の仕切りを立てる。
// 明るい側の CdS に向かって少しずつ回り、2 個が同じくらい明るくなったら止まる。
// シリアルプロッタ (115200bps) で 2 個の明るさ・差・角度が見られる。
//
// 配線 (首振りガジェットに CdS をもう 1 組足す):
//   3V3 ─ CdS A ─┬─ IO34      3V3 ─ CdS B ─┬─ IO35
//               └─ 10kΩ ─ GND            └─ 10kΩ ─ GND
//   サーボ 橙 → IO25 / 赤 → 5V / 茶 → GND。5V と GND の間に 470µF (足の向きに注意)
// ボード: ESP32 Dev Module / ESP32 Arduino core 3.x

const int SERVO_PIN = 25;
const int CDS_A_PIN = 34;            // CdS A (c24–c25)
const int CDS_B_PIN = 35;            // CdS B (c27–c28)

// ★ 光から逃げるように回ったら -1 にする (CdS の左右とサーボの回る向きの組み合わせで決まる)
const int DIRECTION = 1;
// ★ 2 個に同じ光を当てても diff が 0 にならないときの補正。B の値にかける倍率
const float B_SCALE = 1.0f;

const float DEADBAND = 0.06f;        // 差がこれより小さければ動かない (ブルブル防止)
const float GAIN = 4.0f;             // 差 1.0 (片方だけ真っ暗) のとき、1 回で何度回すか
const float MAX_STEP = 3.0f;         // 1 回で回る角度の上限
const int TOO_DARK_MV = 60;          // 2 個とも暗すぎるときは動かない
const float MIN_ANGLE = 10;
const float MAX_ANGLE = 170;
const unsigned long LOOP_MS = 30;

const uint32_t SERVO_HZ = 50;
const uint8_t SERVO_BITS = 16;
const int SERVO_MIN_US = 500;
const int SERVO_MAX_US = 2400;

float angleNow = 90;

void servoWrite(float deg) {
  deg = constrain(deg, 0.0f, 180.0f);
  uint32_t us = SERVO_MIN_US + (uint32_t)((SERVO_MAX_US - SERVO_MIN_US) * deg / 180.0f);
  uint32_t duty = (uint32_t)((uint64_t)us * ((1UL << SERVO_BITS) - 1) / (1000000UL / SERVO_HZ));
  ledcWrite(SERVO_PIN, duty);
}

int readMilliVolts(int pin) {
  long sum = 0;
  for (int i = 0; i < 8; i++) sum += analogReadMilliVolts(pin);
  return (int)(sum / 8);
}

void setup() {
  Serial.begin(115200);
  ledcAttach(SERVO_PIN, SERVO_HZ, SERVO_BITS);
  servoWrite(angleNow);
  delay(500);
}

void loop() {
  int a = readMilliVolts(CDS_A_PIN);
  int b = (int)(readMilliVolts(CDS_B_PIN) * B_SCALE);

  // 差を「合計に対する割合」にする。部屋全体が明るくても暗くても、同じ動き方になる
  float diff = 0;
  if (a + b > TOO_DARK_MV) diff = (float)(a - b) / (float)(a + b);   // -1.0〜1.0

  if (fabsf(diff) > DEADBAND) {
    float step = constrain(diff * GAIN, -MAX_STEP, MAX_STEP);
    angleNow = constrain(angleNow + DIRECTION * step, MIN_ANGLE, MAX_ANGLE);
    servoWrite(angleNow);
  }

  // diff は ×100 して、角度と同じグラフで見やすくする
  Serial.printf("A:%d,B:%d,diff:%.0f,angle:%.1f\n", a, b, diff * 100, angleNow);
  delay(LOOP_MS);
}
