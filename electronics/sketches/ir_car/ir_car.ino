// ir_car — 赤外線リモコンで操縦する車
// 障害物回避カーに受信モジュールを足す。方向キーを押している間だけ、その向きに走る。
// 離すと 0.25 秒で止まる (リモコンは押している間 108ms ごとにリピートを送ってくる)。
// 前に STOP_CM より近いものがあると、前に進むキーを押しても前進しない。
//
// ★ 最初に ir_receive でキーの番号を調べ、下の KEYS と KEY_STOP・KEY_SPEED に書く (-1 は「使わない」)。
//   書いていないキーを押すと、シリアルモニタに番号が出る。
//
// 配線: 障害物回避カーのまま + 受信モジュールをオス-メス線 3 本で
//   OUT → a5 (IO13)、VCC → a8 (IO14)、GND → 上の − ライン
//   受信モジュールは 1.5mA しか使わないので、IO14 を HIGH にして電源の代わりにする (3V3 の穴が空いていないため)
// ボード: ESP32 Dev Module / ESP32 Arduino core 3.x

const int IR_PIN = 13;
const int IR_POWER_PIN = 14;         // 受信モジュールの VCC。HIGH にして 3.3V を出す

// ---- キーの表 ----
struct KeyMove {
  int code;                          // ir_receive で出た「キー 0x??」の番号
  const char *name;
  int8_t fwd;                        // +1 前 / -1 後ろ
  int8_t turn;                       // +1 右 / -1 左
};
KeyMove KEYS[] = {
  {-1, "前", 1, 0},
  {-1, "後ろ", -1, 0},
  {-1, "左 (その場で回る)", 0, -1},
  {-1, "右 (その場で回る)", 0, 1},
  {-1, "左前", 1, -1},
  {-1, "右前", 1, 1},
  {-1, "左後ろ", -1, -1},
  {-1, "右後ろ", -1, 1},
};
const int N_KEYS = sizeof(KEYS) / sizeof(KEYS[0]);
int KEY_STOP = -1;                   // 止まる (機能キーのどれか)
int KEY_SPEED = -1;                  // 速い / ゆっくり を切り替える

// ---- ピン・向き (障害物回避カーと同じ) ----
const int L_PHASE = 33, L_ENABLE = 25, R_PHASE = 26, R_ENABLE = 27;
const int TRIG_PIN = 32, ECHO_PIN = 35;
bool LEFT_REVERSED = false;
bool RIGHT_REVERSED = true;

// ---- 走り方 ----
const int SPEED_SLOW = 130;
const int SPEED_FAST = 190;
const int MAX_DUTY = 200;
const float CURVE = 0.5f;            // 斜めのキーで、内側のタイヤを外側の何割で回すか
const unsigned long HOLD_MS = 250;   // 最後の信号からこれだけ何も来なければ止まる
const float STOP_CM = 20;

const uint32_t PWM_HZ = 20000;
const uint8_t PWM_BITS = 8;
const unsigned long MEASURE_MS = 200;

// ---- NEC の解読 (ir_light_sound・ir_car と同じ) ----
// 受信モジュールは光を受けている間 LOW になる。LOW の長さ (マーク) と HIGH の長さ (スペース) で読む:
//   リーダー: マーク 9ms + スペース 4.5ms     リピート: マーク 9ms + スペース 2.25ms
//   0: マーク 0.56ms + スペース 0.56ms        1: マーク 0.56ms + スペース 1.69ms
//   32 ビット = メーカー 16 ビット + キー 8 ビット + キーの反転 8 ビット (下位ビットから)
volatile uint32_t irLastUs = 0;
volatile uint8_t irState = 0;        // 0: 待ち  1: リーダーのマークの後  2: ビットを読んでいる
volatile bool irMarkOk = false;
volatile uint32_t irBits = 0;
volatile uint8_t irCount = 0;
volatile uint32_t irFrame = 0;       // 読めた 32 ビット
volatile bool irGotFrame = false;
volatile bool irGotRepeat = false;

static inline bool near(uint32_t t, uint32_t target, uint32_t tol) {
  return t + tol >= target && t <= target + tol;
}

// 出力が変わるたびに呼ぶ。high = 変わった後のレベル、dt = 前に変わってからの時間 (µs)
void irEdge(bool high, uint32_t dt) {
  if (high) {                                    // マークが終わった
    if (near(dt, 9000, 1500)) irState = 1;       // リーダー (またはリピート) の始まり
    else if (irState == 2 && near(dt, 560, 300)) irMarkOk = true;
    else irState = 0;
  } else {                                       // スペースが終わった
    if (irState == 1) {
      if (near(dt, 4500, 800)) { irState = 2; irBits = 0; irCount = 0; irMarkOk = false; }
      else if (near(dt, 2250, 500)) { irGotRepeat = true; irState = 0; }
      else irState = 0;
    } else if (irState == 2 && irMarkOk) {
      irMarkOk = false;
      if (near(dt, 1690, 400)) irBits |= (1UL << irCount);
      else if (!near(dt, 560, 300)) { irState = 0; return; }
      irCount = irCount + 1;
      if (irCount == 32) { irFrame = irBits; irGotFrame = true; irState = 0; }
    }
  }
}

void onIrChange() {                  // 割り込みで呼ばれる (出力が変わるたび)
  uint32_t now = micros();
  irEdge(digitalRead(IR_PIN) == HIGH, now - irLastUs);
  irLastUs = now;
}

// 読めたフレームの中身。キーとその反転が合わなければ false
bool irDecode(uint32_t frame, uint16_t &maker, uint8_t &key) {
  maker = (uint16_t)(((frame & 0xFF) << 8) | ((frame >> 8) & 0xFF));   // 送られた順に 0x10EF のように並べる
  key = (frame >> 16) & 0xFF;
  uint8_t inv = (frame >> 24) & 0xFF;
  return (uint8_t)(key ^ inv) == 0xFF;
}
// ---- ここまで ----

// ---- モーター (障害物回避カーと同じ) ----
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
float distanceCm = 400;
unsigned long lastMeasureMs = 0;

void updateDistance() {
  if (millis() - lastMeasureMs < MEASURE_MS) return;
  lastMeasureMs = millis();
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(12);
  digitalWrite(TRIG_PIN, LOW);
  unsigned long us = pulseIn(ECHO_PIN, HIGH, 25000);
  distanceCm = (us == 0) ? 400 : us / 58.3f;
}

// ---- 本体 ----
int fwd = 0, turn = 0;               // いまの指示
int speed = SPEED_SLOW;
unsigned long lastSignalMs = 0;

void setup() {
  Serial.begin(115200);
  pinMode(L_PHASE, OUTPUT);
  pinMode(R_PHASE, OUTPUT);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(IR_POWER_PIN, OUTPUT);
  digitalWrite(IR_POWER_PIN, HIGH);
  pinMode(IR_PIN, INPUT);
  delay(50);                         // 受信モジュールの電源が落ち着くのを待つ
  ledcAttach(L_ENABLE, PWM_HZ, PWM_BITS);
  ledcAttach(R_ENABLE, PWM_HZ, PWM_BITS);
  drive(0, 0);
  attachInterrupt(digitalPinToInterrupt(IR_PIN), onIrChange, CHANGE);
  Serial.println("リモコンの方向キーを押している間、その向きに走ります");
}

void onKey(uint8_t key) {
  lastSignalMs = millis();
  for (int i = 0; i < N_KEYS; i++) {
    if (KEYS[i].code == key) {
      fwd = KEYS[i].fwd;
      turn = KEYS[i].turn;
      Serial.printf("%s\n", KEYS[i].name);
      return;
    }
  }
  fwd = 0;
  turn = 0;
  if (key == KEY_STOP) {
    Serial.println("止まる");
  } else if (key == KEY_SPEED) {
    speed = (speed == SPEED_SLOW) ? SPEED_FAST : SPEED_SLOW;
    Serial.printf("速さ: %s\n", speed == SPEED_FAST ? "速い" : "ゆっくり");
  } else {
    Serial.printf("表にないキー 0x%02X (KEYS に書くと使えます)\n", key);
  }
}

void loop() {
  updateDistance();

  if (irGotFrame) {
    irGotFrame = false;
    uint16_t maker;
    uint8_t key;
    if (irDecode(irFrame, maker, key)) onKey(key);
  }
  if (irGotRepeat) {                             // 押し続けている
    irGotRepeat = false;
    lastSignalMs = millis();
  }
  if (millis() - lastSignalMs > HOLD_MS) {       // 離した
    fwd = 0;
    turn = 0;
  }

  int f = fwd;
  if (f > 0 && distanceCm < STOP_CM) f = 0;      // 前がふさがっていたら前進しない
  int left, right;
  if (f == 0) {                                  // その場で回る
    left = turn * speed;
    right = -turn * speed;
  } else {                                       // 前後 (斜めなら内側を遅く)
    left = f * speed * ((turn < 0) ? CURVE : 1.0f);
    right = f * speed * ((turn > 0) ? CURVE : 1.0f);
  }
  drive(left, right);
}
