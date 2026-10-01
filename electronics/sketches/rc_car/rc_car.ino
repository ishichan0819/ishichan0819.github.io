// rc_car — コントローラー (rc_controller) から ESP-NOW で操縦する車
// 配線は障害物回避カーとまったく同じ。スケッチを書き替えるだけ。
//   スティックを前に倒す → 前進、横に倒す → 曲がる (その場で回ることもできる)
//   スティックを押し込む → 「ぶつからないモード」の ON / OFF (最初は ON)
//     ON のときは、前に STOP_CM より近いものがあると前進だけ止める (下がる・回るはできる)
//   コントローラーからの電波が FAILSAFE_MS 届かない → 止まる
//
// ボード: ESP32 Dev Module / ESP32 Arduino core 3.x

#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>

// ---- 無線の設定 (コントローラーと同じにする) ----
const uint8_t GROUP_ID = 7;
const uint8_t CHANNEL = 1;
const uint8_t BROADCAST[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

// ---- 送るもの・受け取るもの (rc_controller と同じ形にする) ----
struct __attribute__((packed)) ControlMsg {   // コントローラー → 車
  uint8_t magic;                     // 'J'
  uint8_t group;
  int8_t x;                          // -100〜100。右が +
  int8_t y;                          // -100〜100。前が +
  uint8_t presses;                   // スティックを押し込んだ回数
};
struct __attribute__((packed)) StatusMsg {    // 車 → コントローラー
  uint8_t magic;                     // 'C'
  uint8_t group;
  uint16_t distanceCm;
  uint8_t assist;
  uint8_t blocked;
};

// ---- ピン (障害物回避カーと同じ) ----
const int L_PHASE = 33;
const int L_ENABLE = 25;
const int R_PHASE = 26;
const int R_ENABLE = 27;
const int TRIG_PIN = 32;
const int ECHO_PIN = 35;

// ---- motor_test で決めた向き ----
bool LEFT_REVERSED = false;
bool RIGHT_REVERSED = true;

// ---- 走り方 ----
const int MAX_DUTY = 200;            // 単3×4本 (約6V) に対して平均 約4.7V まで
const int MIN_DUTY = 70;             // 少しでも倒したらこの強さから回す。動き出さないなら上げる
const float TURN_RATE = 0.7f;        // 横に倒したときの曲がり方 (1.0 で最大)。曲がりすぎるなら下げる
const float STOP_CM = 20;            // ぶつからないモード: これより近いと前進しない
const float SLOW_CM = 45;            // ぶつからないモード: これより近いと前進を半分の速さに
const unsigned long FAILSAFE_MS = 300;   // 電波がこれだけ途切れたら止まる
const unsigned long STATUS_MS = 100;     // コントローラーへ状態を返す間隔

const uint32_t PWM_HZ = 20000;
const uint8_t PWM_BITS = 8;
const float US_PER_CM = 58.3f;
const unsigned long ECHO_TIMEOUT_US = 25000;
const unsigned long MEASURE_MS = 200;
const float FAR_CM = 400;

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

// -1.0〜1.0 → デューティ。0 のときだけ止め、少しでも動かすなら MIN_DUTY から
int toDuty(float v) {
  if (fabsf(v) < 0.01f) return 0;
  int d = MIN_DUTY + (int)(fabsf(v) * (MAX_DUTY - MIN_DUTY));
  return (v > 0) ? d : -d;
}

// ---- 距離 (障害物回避カーと同じ) ----
float distanceCm = FAR_CM;
unsigned long lastMeasureMs = 0;

void updateDistance() {
  if (millis() - lastMeasureMs < MEASURE_MS) return;
  lastMeasureMs = millis();
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(12);
  digitalWrite(TRIG_PIN, LOW);
  unsigned long us = pulseIn(ECHO_PIN, HIGH, ECHO_TIMEOUT_US);
  distanceCm = (us == 0) ? FAR_CM : us / US_PER_CM;
}

// ---- 受信 (rc_controller と同じしくみ。最新の 1 つだけを箱に入れる) ----
QueueHandle_t controlBox;

void onReceive(const esp_now_recv_info_t *, const uint8_t *data, int len) {
  if (len != (int)sizeof(ControlMsg)) return;
  ControlMsg m;
  memcpy(&m, data, sizeof m);
  if (m.magic != 'J' || m.group != GROUP_ID) return;
  xQueueOverwrite(controlBox, &m);
}

void startEspNow() {
  WiFi.mode(WIFI_STA);
  esp_wifi_set_channel(CHANNEL, WIFI_SECOND_CHAN_NONE);
  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW を始められませんでした");
    while (true) delay(1000);
  }
  esp_now_peer_info_t peer = {};
  memcpy(peer.peer_addr, BROADCAST, 6);
  peer.channel = CHANNEL;
  peer.encrypt = false;
  esp_now_add_peer(&peer);
  esp_now_register_recv_cb(onReceive);
}

// ---- 本体 ----
ControlMsg ctrl = {};
unsigned long lastControlMs = 0;
bool linked = false;
bool assist = true;
bool blocked = false;
bool havePresses = false;
uint8_t lastPresses = 0;
unsigned long lastStatusMs = 0;

void setup() {
  Serial.begin(115200);
  pinMode(L_PHASE, OUTPUT);
  pinMode(R_PHASE, OUTPUT);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  ledcAttach(L_ENABLE, PWM_HZ, PWM_BITS);
  ledcAttach(R_ENABLE, PWM_HZ, PWM_BITS);
  drive(0, 0);
  controlBox = xQueueCreate(1, sizeof(ControlMsg));
  startEspNow();
  Serial.printf("車 起動 (グループ %d, チャンネル %d)。コントローラーを待っています\n", GROUP_ID, CHANNEL);
}

void loop() {
  updateDistance();

  ControlMsg m;
  if (xQueueReceive(controlBox, &m, 0) == pdTRUE) {
    ctrl = m;
    lastControlMs = millis();
    if (!linked) Serial.println("コントローラーとつながりました");
    linked = true;
    // 押し込んだ回数が変わったら モード切り替え (最初の 1 回は数を覚えるだけ)
    if (havePresses && m.presses != lastPresses) {
      assist = !assist;
      Serial.printf("ぶつからないモード: %s\n", assist ? "ON" : "OFF");
    }
    lastPresses = m.presses;
    havePresses = true;
  }

  if (linked && millis() - lastControlMs > FAILSAFE_MS) {
    linked = false;
    havePresses = false;             // コントローラーが再起動すると回数が 0 に戻るので、覚え直す
    Serial.println("電波が途切れたので止まります");
  }

  if (!linked) {
    drive(0, 0);
    blocked = false;
  } else {
    // スティック → 左右のモーター (前後の量 ± 曲がる量)
    float fwd = ctrl.y / 100.0f;
    float turn = ctrl.x / 100.0f * TURN_RATE;
    blocked = assist && fwd > 0 && distanceCm < STOP_CM;
    if (blocked) fwd = 0;                                   // 前進だけやめる
    else if (assist && fwd > 0 && distanceCm < SLOW_CM) fwd *= 0.5f;
    float l = fwd + turn;
    float r = fwd - turn;
    float big = max(fabsf(l), fabsf(r));
    if (big > 1.0f) { l /= big; r /= big; }                 // どちらかが 1 を超えたら、比は保ったまま縮める
    drive(toDuty(l), toDuty(r));
  }

  if (millis() - lastStatusMs >= STATUS_MS) {
    lastStatusMs = millis();
    StatusMsg s;
    s.magic = 'C';
    s.group = GROUP_ID;
    s.distanceCm = (uint16_t)distanceCm;
    s.assist = assist ? 1 : 0;
    s.blocked = blocked ? 1 : 0;
    esp_now_send(BROADCAST, (const uint8_t *)&s, sizeof s);
  }
}
