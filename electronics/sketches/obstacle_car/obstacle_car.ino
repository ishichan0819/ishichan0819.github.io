// obstacle_car — 障害物をよけて走り回る車
// BOOT ボタンで スタート / ストップ。
//   前に何もない      → 前進 (近づくほど減速)
//   STOP_CM より近い → 少し下がり、左右交互にその場で回る
//   前が空いたら      → また前進
// 状態の変化はシリアルモニタ (115200bps) に出る。
//
// 配線は motor_test と distance_test を合わせたもの。
// ボード: ESP32 Dev Module / ESP32 Arduino core 3.x

// ---- ピン ----
const int L_PHASE = 33;              // DRV8835 AIN1 (APHASE) 左の向き
const int L_ENABLE = 25;             // DRV8835 AIN2 (AENBL)  左の速さ
const int R_PHASE = 26;              // DRV8835 BIN1 (BPHASE) 右の向き
const int R_ENABLE = 27;             // DRV8835 BIN2 (BENBL)  右の速さ
const int TRIG_PIN = 32;
const int ECHO_PIN = 35;
const int BOOT_BUTTON = 0;

// ---- motor_test で決めた向き ----
bool LEFT_REVERSED = false;
bool RIGHT_REVERSED = true;

// ---- 走り方 (ここをいじって性格を変える) ----
const int SPEED_FORWARD = 150;       // 前進の速さ (0〜255)
const int SPEED_SLOW = 100;          // 障害物に近いときの速さ
const int SPEED_BACK = 130;
const int SPEED_TURN = 140;
const float SLOW_CM = 50;            // これより近いと減速
const float STOP_CM = 25;            // これより近いと回避
const float CLEAR_CM = 40;           // 回っていて、これより遠くなったら前進に戻る
const unsigned long BACK_MS = 400;
const unsigned long TURN_MS = 400;   // 1 回の回転時間。この間に距離が 2 回測れる
const unsigned long MAX_TURN_MS = 3000;  // 回っても空かないときは反対向きを試す

const uint32_t PWM_HZ = 20000;       // 20kHz。人の耳に聞こえない高さ
const uint8_t  PWM_BITS = 8;         // 0〜255
const int MAX_DUTY = 200;            // 単3×4本 (約6V) に対して平均 約4.7V までに抑える
const float US_PER_CM = 58.3f;
const unsigned long ECHO_TIMEOUT_US = 25000;
const unsigned long MEASURE_MS = 200;    // HC-SR04 のデータシート: 測定の間隔は 200ms 以上
const float FAR_CM = 400;            // 反射なし = 前は空いている、として扱う距離

// ---- 状態 ----
// Arduino IDE は関数のプロトタイプを最初の関数の直前に自動で差し込むので、
// 関数の引数に使う型 (State) はそれより上で宣言しておく
enum State { STOPPED, FORWARD, BACKING, TURNING };
const char* STATE_NAME[] = {"STOPPED", "FORWARD", "BACKING", "TURNING"};

// ---- モーター ----
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

// ---- 距離 ----
float measureCmOnce() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(12);
  digitalWrite(TRIG_PIN, LOW);
  unsigned long us = pulseIn(ECHO_PIN, HIGH, ECHO_TIMEOUT_US);
  return (us == 0) ? FAR_CM : us / US_PER_CM;
}

float distanceCm = FAR_CM;
unsigned long lastMeasureMs = 0;

// 200ms ごとに 1 回だけ測る。測ったら true
bool updateDistance() {
  if (millis() - lastMeasureMs < MEASURE_MS) return false;
  lastMeasureMs = millis();
  distanceCm = measureCmOnce();
  return true;
}

// ---- 状態機械 ----
State state = STOPPED;
unsigned long stateSinceMs = 0;
unsigned long turnStartMs = 0;
int turnDir = 1;                     // 1: 右回り, -1: 左回り

void enter(State next) {
  state = next;
  stateSinceMs = millis();
  Serial.printf("[%7lu ms] %-8s dist=%.0f cm\n", millis(), STATE_NAME[next], distanceCm);
}

bool bootPressed() {                 // 押した瞬間だけ true
  static bool last = false;
  bool now = (digitalRead(BOOT_BUTTON) == LOW);
  bool edge = now && !last;
  last = now;
  return edge;
}

void setup() {
  Serial.begin(115200);
  pinMode(L_PHASE, OUTPUT);
  pinMode(R_PHASE, OUTPUT);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(BOOT_BUTTON, INPUT_PULLUP);
  ledcAttach(L_ENABLE, PWM_HZ, PWM_BITS);
  ledcAttach(R_ENABLE, PWM_HZ, PWM_BITS);
  drive(0, 0);
  Serial.println("床に置いて BOOT ボタンでスタート / もう一度押すとストップ");
}

void loop() {
  updateDistance();

  if (bootPressed()) {
    if (state == STOPPED) enter(FORWARD);
    else { drive(0, 0); enter(STOPPED); }
  }

  unsigned long inState = millis() - stateSinceMs;

  switch (state) {
    case STOPPED:
      drive(0, 0);
      break;

    case FORWARD:
      if (distanceCm < STOP_CM) {
        drive(-SPEED_BACK, -SPEED_BACK);
        enter(BACKING);
      } else if (distanceCm < SLOW_CM) {
        drive(SPEED_SLOW, SPEED_SLOW);
      } else {
        drive(SPEED_FORWARD, SPEED_FORWARD);
      }
      break;

    case BACKING:
      if (inState >= BACK_MS) {
        turnDir = -turnDir;          // 前回と逆に回る (同じ角でハマり続けないように)
        turnStartMs = millis();
        drive(turnDir * SPEED_TURN, -turnDir * SPEED_TURN);
        enter(TURNING);
      }
      break;

    case TURNING:
      if (inState >= TURN_MS) {
        if (distanceCm > CLEAR_CM) {
          enter(FORWARD);
        } else {
          if (millis() - turnStartMs > MAX_TURN_MS) {   // 長く回っても空かない → 逆回り
            turnDir = -turnDir;
            turnStartMs = millis();
          }
          drive(turnDir * SPEED_TURN, -turnDir * SPEED_TURN);
          enter(TURNING);            // もう TURN_MS だけ回って、また確かめる
        }
      }
      break;
  }
}
