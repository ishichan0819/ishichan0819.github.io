// thermistor_test — サーミスターで温度を測る
// シリアルプロッタ (115200bps) に温度 (℃) を出す。サーミスターを指でつまむと上がる。
//
// 配線:
//   3V3 ─ サーミスター ─┬─ IO34
//                      └─ 10kΩ ─ GND     (温かい → サーミスターの抵抗が下がる → IO34 の電圧が上がる)
// サーミスター (秋月 117250): 25℃ で 10kΩ、B 定数 3960
// ボード: ESP32 Dev Module (Freenove ESP32 WROOM) / ESP32 Arduino core 3.x

const int THERM_PIN = 34;            // ADC1

// ★ テスターで 3V3 と GND の間を測った値 (mV) にすると、温度が正確になる
float VCC_MV = 3300;

const float R_FIXED = 10000;         // 下側の抵抗 (Ω)
const float R25 = 10000;             // サーミスターの 25℃ での抵抗 (Ω)
const float B_CONST = 3960;          // B 定数

int readMilliVolts() {
  long sum = 0;
  for (int i = 0; i < 16; i++) sum += analogReadMilliVolts(THERM_PIN);
  return (int)(sum / 16);
}

// 電圧 → サーミスターの抵抗 → 温度 (B 定数の式)
float toCelsius(int mv) {
  if (mv <= 0 || mv >= VCC_MV) return NAN;                 // 線が外れている
  float r = R_FIXED * (VCC_MV - mv) / mv;                  // 分圧の式を逆に解く
  float invT = 1.0f / (25.0f + 273.15f) + logf(r / R25) / B_CONST;   // 1/T = 1/T25 + ln(R/R25)/B
  return 1.0f / invT - 273.15f;
}

void setup() {
  Serial.begin(115200);
}

void loop() {
  int mv = readMilliVolts();
  float c = toCelsius(mv);
  // プロッタで同じ目盛りに収まるよう、電圧は 1/100 にして出す
  Serial.printf("temp:%.2f,mV/100:%.1f\n", c, mv / 100.0f);
  delay(200);
}
