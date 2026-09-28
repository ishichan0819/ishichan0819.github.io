// hello_esp32 — 配線なしで動く最初の確認
// ・シリアルモニタ (115200bps) にチップの情報を表示する
// ・基板の BOOT ボタン (GPIO0) を押すたびに回数を表示する
// ボード: ESP32 Dev Module / ESP32 Arduino core 3.x

const int BOOT_BUTTON = 0;   // DevKitC の BOOT ボタン。押すと LOW になる

int pressCount = 0;
bool lastPressed = false;

void setup() {
  Serial.begin(115200);
  delay(500);                        // シリアルモニタの接続を少し待つ
  pinMode(BOOT_BUTTON, INPUT_PULLUP);

  Serial.println();
  Serial.println("=== hello, ESP32 ===");
  Serial.printf("chip    : %s rev %d, %d core(s)\n",
                ESP.getChipModel(), ESP.getChipRevision(), ESP.getChipCores());
  Serial.printf("cpu     : %lu MHz\n", (unsigned long)ESP.getCpuFreqMHz());
  Serial.printf("flash   : %lu KB\n", (unsigned long)(ESP.getFlashChipSize() / 1024));
  Serial.printf("heap    : %lu bytes free\n", (unsigned long)ESP.getFreeHeap());
  uint64_t mac = ESP.getEfuseMac();
  Serial.printf("mac     : %02X:%02X:%02X:%02X:%02X:%02X\n",
                (int)(mac & 0xFF), (int)((mac >> 8) & 0xFF), (int)((mac >> 16) & 0xFF),
                (int)((mac >> 24) & 0xFF), (int)((mac >> 32) & 0xFF), (int)((mac >> 40) & 0xFF));
  Serial.println("BOOT ボタンを押してみてください");
}

void loop() {
  bool pressed = (digitalRead(BOOT_BUTTON) == LOW);
  if (pressed && !lastPressed) {     // 押した瞬間だけ数える (立ち下がりの検出)
    pressCount++;
    Serial.printf("BOOT pressed: %d 回目 (起動から %lu ms)\n", pressCount, millis());
  }
  lastPressed = pressed;
  delay(20);                         // 20ms ごとに見ることで、ボタンのチャタリングを無視する
}
