// servo_test — サーボ (SG90) が配線どおり動くかの確認
// 20° → 160° → 20° をゆっくり往復する。シリアルに角度とパルス幅を出す。
//
// 配線: サーボ 橙(信号) → IO25 / 赤 → 5V / 茶 → GND
// ボード: ESP32 Dev Module / ESP32 Arduino core 3.x (ledcAttach を使う)

const int SERVO_PIN = 25;

// サーボは「20ms ごとのパルス」の幅で角度が決まる。0.5ms で 0°、2.4ms で 180° とする。
const uint32_t SERVO_HZ = 50;        // 周期 20ms
const uint8_t  SERVO_BITS = 16;      // PWM の分解能 (0〜65535)
const int SERVO_MIN_US = 500;        // 0° のパルス幅 [µs]
const int SERVO_MAX_US = 2400;       // 180° のパルス幅 [µs]

// 端 (0° と 180°) はギアが突き当たって唸ることがあるので、少し内側で使う
const int ANGLE_LOW = 20;
const int ANGLE_HIGH = 160;

int servoPulseUs(float deg) {
  deg = constrain(deg, 0.0f, 180.0f);
  return SERVO_MIN_US + (int)((SERVO_MAX_US - SERVO_MIN_US) * deg / 180.0f);
}

void servoWrite(float deg) {
  uint32_t us = servoPulseUs(deg);
  // デューティ = パルス幅 / 周期。16bit なので 65535 が 100%
  uint32_t duty = (uint32_t)((uint64_t)us * ((1UL << SERVO_BITS) - 1) / (1000000UL / SERVO_HZ));
  ledcWrite(SERVO_PIN, duty);
}

void setup() {
  Serial.begin(115200);
  if (!ledcAttach(SERVO_PIN, SERVO_HZ, SERVO_BITS)) {
    Serial.println("ledcAttach に失敗しました (ボードパッケージが 3.x か確認)");
  }
  servoWrite(90);
  delay(1000);
}

void loop() {
  for (int a = ANGLE_LOW; a <= ANGLE_HIGH; a++) {
    servoWrite(a);
    if (a % 20 == 0) Serial.printf("angle %3d°  pulse %4d us\n", a, servoPulseUs(a));
    delay(15);
  }
  for (int a = ANGLE_HIGH; a >= ANGLE_LOW; a--) {
    servoWrite(a);
    delay(15);
  }
}
