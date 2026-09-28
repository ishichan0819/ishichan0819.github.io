// distance_test — 超音波センサー (HC-SR04) で距離を測って表示する
// 手や箱を近づけ遠ざけして、cm が素直に変わるかを確かめる。
// シリアルプロッタ (115200bps) でグラフでも見られる。
//
// 配線 (秋月の HC-SR04 は 3〜5.5V で動く版。3.3V で動かすと Echo も 3.3V で返るので、そのまま ESP32 に入れられる):
//   HC-SR04 VCC → 3V3 / GND → GND / Trig → IO32 / Echo → IO35
//   ※ 5V で動かすと Echo も 5V になる。その場合は ESP32 に直接つながないこと
// ボード: ESP32 Dev Module / ESP32 Arduino core 3.x

const int TRIG_PIN = 32;
const int ECHO_PIN = 35;             // 入力専用ピン。Echo の受け口にちょうどいい

// 音速 343 m/s → 1cm を往復するのに 58.3µs かかる
const float US_PER_CM = 58.3f;
const unsigned long ECHO_TIMEOUT_US = 30000;   // 30ms ≒ 5m。これ以上は「何もない」とみなす
const unsigned long INTERVAL_MS = 200;         // データシート: 測定の間隔は 200ms 以上

// 距離 [cm] を返す。反射が返ってこなければ -1
float measureCm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);      // 10µs 以上のパルスで 1 回測定
  delayMicroseconds(12);
  digitalWrite(TRIG_PIN, LOW);
  unsigned long us = pulseIn(ECHO_PIN, HIGH, ECHO_TIMEOUT_US);
  if (us == 0) return -1;
  return us / US_PER_CM;
}

void setup() {
  Serial.begin(115200);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  digitalWrite(TRIG_PIN, LOW);
}

void loop() {
  float cm = measureCm();
  if (cm < 0) {
    Serial.println("cm:-1");         // 何も返ってこない (遠すぎる / 斜めの面 / 配線ミス)
  } else {
    Serial.printf("cm:%.1f\n", cm);
  }
  delay(INTERVAL_MS);
}
