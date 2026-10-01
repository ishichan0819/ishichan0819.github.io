// rc_controller — ジョイスティックの向きを ESP-NOW で車に送るコントローラー
// 20 回/秒、スティックの X・Y と「押し込んだ回数」を送る。車からは距離などが返ってくる。
// 基板のフルカラー LED (IO16) で状態がわかる:
//   緑 = 車とつながっている   黄 = 前に障害物があって前進を止めている   赤の点滅 = 車から返事がない
// 起動するときはスティックに触らない。起動したら一度スティックをぐるっと大きく回す。
//
// 配線は joystick_test と同じ (黄 X → IO34 / 白 Y → IO35 / 赤 → 3V3 / 黒 → GND)。
// 車には rc_car を書き込んでおく。GROUP_ID と CHANNEL は車と同じにする。
// ボード: ESP32 Dev Module (Freenove ESP32 WROOM でもこの設定) / ESP32 Arduino core 3.1 以降

#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>

// ---- 無線の設定 (車と同じにする) ----
const uint8_t GROUP_ID = 7;          // 同じ番号どうしだけで話す。近くで別の組を使うなら変える
const uint8_t CHANNEL = 1;           // Wi-Fi のチャンネル (1〜13)
const uint8_t BROADCAST[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};  // 宛先を決めずに全員へ送る

// ---- 送るもの・受け取るもの (rc_car と同じ形にする) ----
struct __attribute__((packed)) ControlMsg {   // コントローラー → 車
  uint8_t magic;                     // 'J'
  uint8_t group;
  int8_t x;                          // -100〜100。右が +
  int8_t y;                          // -100〜100。前が +
  uint8_t presses;                   // スティックを押し込んだ回数 (押すたびに +1)
};
struct __attribute__((packed)) StatusMsg {    // 車 → コントローラー
  uint8_t magic;                     // 'C'
  uint8_t group;
  uint16_t distanceCm;
  uint8_t assist;                    // 1 = ぶつからないモード ON
  uint8_t blocked;                   // 1 = 前に障害物があって前進を止めている
};

// ---- ピン ----
const int JOY_X_PIN = 34;
const int JOY_Y_PIN = 35;
const int RGB_LED = 16;              // Freenove の基板にあるフルカラー LED。DevKitC には無い (光らないだけ)

// ★ joystick_test で決めた向き
bool INVERT_X = false;
bool INVERT_Y = false;

const int PRESS_RAW = 3900;
const int DEAD = 8;
const int START_RANGE = 600;
const unsigned long SEND_MS = 50;        // 20 回/秒
const unsigned long LOST_MS = 500;       // これだけ車から返事がなければ「つながっていない」

// ---- ジョイスティック (joystick_test と同じ) ----
struct Axis {
  int pin;
  bool invert;
  int center, lo, hi;
};
Axis ax = {JOY_X_PIN, false, 0, 0, 0};
Axis ay = {JOY_Y_PIN, false, 0, 0, 0};

int readRaw(int pin) {
  long sum = 0;
  for (int i = 0; i < 4; i++) sum += analogRead(pin);
  return (int)(sum / 4);
}

void calibrate(Axis &a) {
  long sum = 0;
  for (int i = 0; i < 32; i++) { sum += analogRead(a.pin); delay(2); }
  a.center = (int)(sum / 32);
  a.lo = a.center - START_RANGE;
  a.hi = a.center + START_RANGE;
}

int toPercent(Axis &a, int raw) {
  if (raw > a.hi) a.hi = min(raw, PRESS_RAW - 300);
  if (raw < a.lo) a.lo = raw;
  float v = (raw >= a.center) ? (float)(raw - a.center) / max(1, a.hi - a.center)
                              : -(float)(a.center - raw) / max(1, a.center - a.lo);
  int p = (int)(v * 100);
  if (abs(p) <= DEAD) return 0;
  p = (p > 0 ? p - DEAD : p + DEAD) * 100 / (100 - DEAD);
  p = constrain(p, -100, 100);
  return a.invert ? -p : p;
}

// ---- 受信 ----
// 受信の関数は Wi-Fi の裏方 (別のタスク) から呼ばれるので、ここでは「箱」に入れるだけにして、
// 中身は loop() で取り出す。箱は 1 つ分で、新しいのが来たら上書きする (いつも最新だけ見る)
QueueHandle_t statusBox;

void onReceive(const esp_now_recv_info_t *, const uint8_t *data, int len) {
  if (len != (int)sizeof(StatusMsg)) return;
  StatusMsg m;
  memcpy(&m, data, sizeof m);
  if (m.magic != 'C' || m.group != GROUP_ID) return;
  xQueueOverwrite(statusBox, &m);
}

void startEspNow() {
  WiFi.mode(WIFI_STA);                               // ルーターにはつながない。無線だけ使う
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

void led(uint8_t r, uint8_t g, uint8_t b) {
  rgbLedWrite(RGB_LED, r, g, b);
}

// ---- 本体 ----
uint8_t presses = 0;
bool lastPressed = false;
StatusMsg carStatus = {};
unsigned long lastStatusMs = 0;
bool linked = false;
unsigned long lastSendMs = 0;
unsigned long lastPrintMs = 0;

void setup() {
  Serial.begin(115200);
  analogReadResolution(12);
  ax.invert = INVERT_X;
  ay.invert = INVERT_Y;
  statusBox = xQueueCreate(1, sizeof(StatusMsg));
  delay(300);
  calibrate(ax);
  calibrate(ay);
  startEspNow();
  Serial.printf("コントローラー起動 (グループ %d, チャンネル %d)。スティックをぐるっと回してください\n", GROUP_ID, CHANNEL);
}

void loop() {
  // 車からの返事
  StatusMsg m;
  if (xQueueReceive(statusBox, &m, 0) == pdTRUE) {
    carStatus = m;
    lastStatusMs = millis();
    if (!linked) Serial.println("車とつながりました");
    linked = true;
  }
  if (linked && millis() - lastStatusMs > LOST_MS) {
    linked = false;
    Serial.println("車から返事がありません");
  }

  if (millis() - lastSendMs >= SEND_MS) {
    lastSendMs = millis();
    int rx = readRaw(JOY_X_PIN);
    int ry = readRaw(JOY_Y_PIN);
    bool pressed = (rx >= PRESS_RAW);
    if (pressed && !lastPressed) presses++;          // 押した瞬間だけ数える
    lastPressed = pressed;

    ControlMsg c;
    c.magic = 'J';
    c.group = GROUP_ID;
    c.x = (int8_t)(pressed ? 0 : toPercent(ax, rx));
    c.y = (int8_t)toPercent(ay, ry);
    c.presses = presses;
    esp_now_send(BROADCAST, (const uint8_t *)&c, sizeof c);

    // LED: 緑 = OK、黄 = 前進を止めている、赤の点滅 = つながっていない
    if (!linked) led(((millis() / 250) % 2) ? 20 : 0, 0, 0);
    else if (carStatus.blocked) led(20, 12, 0);
    else led(0, 20, 0);

    if (millis() - lastPrintMs >= 300) {
      lastPrintMs = millis();
      if (linked) {
        Serial.printf("x:%4d y:%4d | 車: %3u cm  ぶつからないモード:%s%s\n", c.x, c.y,
                      carStatus.distanceCm, carStatus.assist ? "ON" : "OFF",
                      carStatus.blocked ? "  (前進ストップ中)" : "");
      } else {
        Serial.printf("x:%4d y:%4d | 車: --\n", c.x, c.y);
      }
    }
  }
}
