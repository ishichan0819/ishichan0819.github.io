// motor_test — 左右のモーターが配線どおりの向きに回るかの確認
// BOOT ボタンを押すと 1 回だけ、次の順に動く (車体を持ち上げて、タイヤを浮かせて試す):
//   左タイヤだけ前進 → 右タイヤだけ前進 → 両方前進 → 両方後退 → その場で右回転
// 「前進」のはずが後ろに回ったら、下の LEFT_REVERSED / RIGHT_REVERSED を true/false 反転させる。
//
// 配線 (DRV8835 は MODE を VCC につないで PHASE/ENABLE モード):
//   IO33 → AIN1(APHASE)  IO25 → AIN2(AENBL)   … 左モーター (AOUT1/AOUT2)
//   IO26 → BIN1(BPHASE)  IO27 → BIN2(BENBL)   … 右モーター (BOUT1/BOUT2)
// ボード: ESP32 Dev Module / ESP32 Arduino core 3.x

const int L_PHASE = 33;
const int L_ENABLE = 25;
const int R_PHASE = 26;
const int R_ENABLE = 27;
const int BOOT_BUTTON = 0;

// 左右のモーターは鏡写しに付くので、片方は逆に回すと「両方前進」になる
bool LEFT_REVERSED = false;
bool RIGHT_REVERSED = true;

const uint32_t PWM_HZ = 20000;       // 20kHz。人の耳に聞こえない高さ
const uint8_t  PWM_BITS = 8;         // 0〜255
const int MAX_DUTY = 200;            // 単3×4本 (約6V) に対して平均 約4.7V までに抑える

// speed: -255〜255。正で前進、負で後退、0 でブレーキ
void setMotor(int phasePin, int enablePin, bool reversed, int speed) {
  bool backward = (speed < 0);
  int duty = min(abs(speed), MAX_DUTY);
  digitalWrite(phasePin, (backward != reversed) ? HIGH : LOW);
  ledcWrite(enablePin, duty);
}

void drive(int left, int right) {
  setMotor(L_PHASE, L_ENABLE, LEFT_REVERSED, left);
  setMotor(R_PHASE, R_ENABLE, RIGHT_REVERSED, right);
}

void step(const char* label, int left, int right, int ms) {
  Serial.printf("%-22s L=%4d R=%4d\n", label, left, right);
  drive(left, right);
  delay(ms);
  drive(0, 0);
  delay(500);
}

void setup() {
  Serial.begin(115200);
  pinMode(L_PHASE, OUTPUT);
  pinMode(R_PHASE, OUTPUT);
  pinMode(BOOT_BUTTON, INPUT_PULLUP);
  ledcAttach(L_ENABLE, PWM_HZ, PWM_BITS);
  ledcAttach(R_ENABLE, PWM_HZ, PWM_BITS);
  drive(0, 0);
  Serial.println("タイヤを浮かせて、BOOT ボタンを押すとテスト開始");
}

void loop() {
  if (digitalRead(BOOT_BUTTON) == LOW) {
    delay(300);                                     // 押した指が離れるのを待つ
    step("左だけ前進",            160,    0, 1000);
    step("右だけ前進",              0,  160, 1000);
    step("両方前進",              160,  160, 1000);
    step("両方後退",             -160, -160, 1000);
    step("その場で右回転",        160, -160,  800);
    Serial.println("おわり。もう一度 BOOT で再実行");
  }
  delay(20);
}
