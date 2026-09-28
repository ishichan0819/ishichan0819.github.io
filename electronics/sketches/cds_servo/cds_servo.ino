// cds_servo — 明るさでサーボの角度を変える
// 明るいほど 160° 側、暗いほど 20° 側に首を振る。
// シリアルプロッタ (115200bps) で「電圧」と「角度」をグラフで見られる。
//
// 配線:
//   3V3 ─ CdS ─┬─ IO34
//              └─ 10kΩ ─ GND        (明るい → CdS の抵抗が下がる → IO34 の電圧が上がる)
//   サーボ 橙 → IO25 / 赤 → 5V / 茶 → GND
// ボード: ESP32 Dev Module / ESP32 Arduino core 3.x

const int SERVO_PIN = 25;
const int CDS_PIN = 34;              // ADC1。Wi-Fi を使っても読める側の ADC

const uint32_t SERVO_HZ = 50;
const uint8_t  SERVO_BITS = 16;
const int SERVO_MIN_US = 500;
const int SERVO_MAX_US = 2400;
const int ANGLE_LOW = 20;
const int ANGLE_HIGH = 160;

// ★ 部屋に合わせて調整する。シリアルに出る mV を見て、
//    手で CdS を覆ったときの値を DARK_MV、ライトを当てたときの値を BRIGHT_MV にする。
int DARK_MV = 100;
int BRIGHT_MV = 1600;

const float SMOOTH = 0.15f;          // 0〜1。小さいほどゆっくり追いかける (ブルブル防止)

float angleNow = 90;

void servoWrite(float deg) {
  deg = constrain(deg, 0.0f, 180.0f);
  uint32_t us = SERVO_MIN_US + (uint32_t)((SERVO_MAX_US - SERVO_MIN_US) * deg / 180.0f);
  uint32_t duty = (uint32_t)((uint64_t)us * ((1UL << SERVO_BITS) - 1) / (1000000UL / SERVO_HZ));
  ledcWrite(SERVO_PIN, duty);
}

// 8 回読んで平均する。ADC のばらつきを減らす
int readCdsMilliVolts() {
  long sum = 0;
  for (int i = 0; i < 8; i++) sum += analogReadMilliVolts(CDS_PIN);
  return (int)(sum / 8);
}

void setup() {
  Serial.begin(115200);
  ledcAttach(SERVO_PIN, SERVO_HZ, SERVO_BITS);
  servoWrite(angleNow);
}

void loop() {
  int mv = readCdsMilliVolts();

  // mV を 0.0〜1.0 の「明るさ」に直してから角度にする
  float level = (float)(mv - DARK_MV) / (float)(BRIGHT_MV - DARK_MV);
  level = constrain(level, 0.0f, 1.0f);
  float target = ANGLE_LOW + (ANGLE_HIGH - ANGLE_LOW) * level;

  // いきなり目標に飛ばず、差の 15% ずつ近づく (指数移動平均)
  angleNow += (target - angleNow) * SMOOTH;
  servoWrite(angleNow);

  // シリアルプロッタ用: "名前:値" をカンマ区切りで 1 行に
  Serial.printf("mV:%d,angle:%.1f\n", mv, angleNow);
  delay(30);
}
