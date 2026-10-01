// hello_freenove — Freenove ESP32 WROOM ボードの動作確認 (配線なし)
// ・シリアルモニタ (115200bps) にチップの情報と MAC アドレスを表示する
// ・基板の青い LED (IO2) を 1 秒ごとに点滅させる
// ・フルカラー LED (WS2812, IO16) を 赤 → 緑 → 青 → 白 と順に光らせる
// ・BOOT ボタン (IO0) を押すと色送りを止める / また動かす
// ボード: ESP32 Dev Module / ESP32 Arduino core 3.1 以降 (rgbLedWrite はボードパッケージの関数。ライブラリは要らない)

const int BLUE_LED = 2;              // 基板の青い LED。H で点く
const int RGB_LED = 16;              // 基板のフルカラー LED (WS2812)
const int BOOT_BUTTON = 0;           // 押すと LOW
const uint8_t BRIGHT = 20;           // 0〜255。WS2812 は 255 だと目に痛いほど明るい

const uint8_t COLORS[][3] = {
  {BRIGHT, 0, 0}, {0, BRIGHT, 0}, {0, 0, BRIGHT}, {BRIGHT, BRIGHT, BRIGHT},
};
const char* COLOR_NAME[] = {"赤", "緑", "青", "白"};
const int N_COLORS = 4;

int colorIndex = 0;
bool running = true;
bool lastPressed = false;
unsigned long lastStepMs = 0;

void showColor(int i) {
  rgbLedWrite(RGB_LED, COLORS[i][0], COLORS[i][1], COLORS[i][2]);
  digitalWrite(BLUE_LED, (i % 2 == 0) ? HIGH : LOW);
  Serial.printf("RGB LED: %s\n", COLOR_NAME[i]);
}

void setup() {
  Serial.begin(115200);
  delay(500);
  pinMode(BLUE_LED, OUTPUT);
  pinMode(BOOT_BUTTON, INPUT_PULLUP);

  Serial.println();
  Serial.println("=== hello, Freenove ESP32 ===");
  Serial.printf("chip    : %s rev %d, %d core(s)\n",
                ESP.getChipModel(), ESP.getChipRevision(), ESP.getChipCores());
  Serial.printf("flash   : %lu KB\n", (unsigned long)(ESP.getFlashChipSize() / 1024));
  uint64_t mac = ESP.getEfuseMac();
  Serial.printf("mac     : %02X:%02X:%02X:%02X:%02X:%02X\n",
                (int)(mac & 0xFF), (int)((mac >> 8) & 0xFF), (int)((mac >> 16) & 0xFF),
                (int)((mac >> 24) & 0xFF), (int)((mac >> 32) & 0xFF), (int)((mac >> 40) & 0xFF));
  Serial.println("MAC アドレスは 1 台ずつ違う。紙に書いてボードに貼っておくと、あとで見分けられる");
  showColor(colorIndex);
}

void loop() {
  bool pressed = (digitalRead(BOOT_BUTTON) == LOW);
  if (pressed && !lastPressed) {
    running = !running;
    Serial.println(running ? "色送り: 再開" : "色送り: 停止");
  }
  lastPressed = pressed;

  if (running && millis() - lastStepMs >= 1000) {
    lastStepMs = millis();
    colorIndex = (colorIndex + 1) % N_COLORS;
    showColor(colorIndex);
  }
  delay(20);
}
