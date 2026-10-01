// stepper_test — ステッピングモーター 28BYJ-48 を 1 回転させて、逆に 1 回転で戻す
// 起動すると 1 回転 → 1 秒止まる → 逆に 1 回転。BOOT ボタンを押すと、もう一度やる。
//
// 配線: IO14 → ULN2003AN 1B (青)、IO27 → 2B (ピンク)、IO26 → 3B (黄)、IO25 → 4B (橙)
//       モーターの赤と ULN2003AN の COM は 5V、ULN2003AN の E は GND
// 回し方: 1 相励磁。青 → ピンク → 黄 → 橙 の順に、1 本ずつ電気を流す (1 度に 1 つのコイル)。
//         止まっている間はコイルを全部切る (電流を流しっぱなしにしない)。
// ボード: ESP32 Dev Module (Freenove ESP32 WROOM) / ESP32 Arduino core 3.x

const int COIL_PINS[4] = {14, 27, 26, 25};   // 青・ピンク・黄・橙 の順
const int BOOT_BUTTON = 0;

const int STEPS_PER_REV = 2048;      // 1 相励磁での 1 回転のステップ数 (秋月の仕様: 1-2 相で 0.0879°/ステップ)
int STEP_MS = 3;                     // 1 ステップの間隔 (ms)。震えるだけで回らないときは 4〜5 にする

int phase = 0;                       // いま電気を流しているコイル (0〜3)

void coilsOff() {
  for (int i = 0; i < 4; i++) digitalWrite(COIL_PINS[i], LOW);
}

// dir = +1 で 青→ピンク→黄→橙 の向き、-1 で逆向きに 1 ステップ
void stepOnce(int dir) {
  phase = (phase + (dir > 0 ? 1 : 3)) % 4;
  for (int i = 0; i < 4; i++) digitalWrite(COIL_PINS[i], (i == phase) ? HIGH : LOW);
}

void turn(int steps) {
  int dir = (steps > 0) ? 1 : -1;
  unsigned long t0 = millis();
  for (int i = 0; i < abs(steps); i++) {
    stepOnce(dir);
    delay(STEP_MS);
  }
  coilsOff();
  Serial.printf("%+d ステップ (%.0f°) を %lu ms で回りました\n", steps, steps * 360.0f / STEPS_PER_REV, millis() - t0);
}

void demo() {
  turn(STEPS_PER_REV);
  delay(1000);
  turn(-STEPS_PER_REV);
  Serial.println("BOOT を押すと、もう一度回します");
}

void setup() {
  Serial.begin(115200);
  for (int i = 0; i < 4; i++) pinMode(COIL_PINS[i], OUTPUT);
  coilsOff();
  pinMode(BOOT_BUTTON, INPUT_PULLUP);
  delay(500);
  demo();
}

void loop() {
  if (digitalRead(BOOT_BUTTON) == LOW) {
    delay(30);
    while (digitalRead(BOOT_BUTTON) == LOW) delay(10);   // 離すまで待つ
    demo();
  }
  delay(10);
}
