// light_loopback — 自分の LED の点滅を、自分の CdS で読む (1 台で試す)
// 基板のフルカラー LED (IO16) を BIT_MS ごとに 点く・消える をくり返し、CdS (IO34) の電圧を 2ms ごとに読む。
//   PLOT = true  : シリアルプロッタに mV (CdS) と led (点いているとき 明るさの目安) を出す。波形の「遅れ」が見える
//   PLOT = false : シリアルモニタに、点いてから / 消えてから 半分まで変わるのにかかった時間 (ms) を出す
// CdS はオス-メス線で延長して、基板の LED の真上 1cm くらいに向ける。紙の筒をかぶせると部屋の明かりが入らない。
//
// 配線: 3V3 ─ CdS ─┬─ IO34
//                  └─ 10kΩ ─ GND
// ボード: ESP32 Dev Module (Freenove ESP32 WROOM) / ESP32 Arduino core 3.1 以降 (rgbLedWrite を使う)

const int CDS_PIN = 34;
const int RGB_LED = 16;
const uint8_t ON_LEVEL = 255;        // 白でいちばん明るく
int BIT_MS = 100;                    // 点いている時間 = 消えている時間
bool PLOT = true;

bool ledOn = false;
unsigned long switchedMs = 0;
int brightMv = 0, darkMv = 4000;     // 1 周期の中でのいちばん明るい / 暗い値
int prevBright = 0, prevDark = 0;    // 1 つ前の周期の値 (「半分」の基準)
int riseMs = -1, fallMs = -1;
bool crossed = false;

void setLed(bool on) {
  uint8_t v = on ? ON_LEVEL : 0;
  rgbLedWrite(RGB_LED, v, v, v);
  ledOn = on;
  switchedMs = millis();
  crossed = false;
}

void setup() {
  Serial.begin(115200);
  setLed(false);
}

unsigned long lastSampleMs = 0, lastPlotMs = 0;

void loop() {
  if (millis() - switchedMs >= (unsigned long)BIT_MS) {
    if (!ledOn) {                                   // 1 周期が終わった → 結果を出して、次の周期へ
      if (!PLOT && prevBright > 0) {
        Serial.printf("点いてから %3d ms / 消えてから %3d ms で半分まで変化  (明るい %4d mV / 暗い %4d mV)\n",
                      riseMs, fallMs, prevBright, prevDark);
      }
      prevBright = brightMv;
      prevDark = darkMv;
      brightMv = 0;
      darkMv = 4000;
      riseMs = fallMs = -1;
    }
    setLed(!ledOn);
  }

  if (millis() - lastSampleMs >= 2) {
    lastSampleMs = millis();
    int mv = analogReadMilliVolts(CDS_PIN);
    brightMv = max(brightMv, mv);
    darkMv = min(darkMv, mv);
    int half = (prevBright + prevDark) / 2;
    if (!crossed && prevBright > 0) {
      if (ledOn && mv > half) { riseMs = millis() - switchedMs; crossed = true; }
      if (!ledOn && mv < half) { fallMs = millis() - switchedMs; crossed = true; }
    }
    if (PLOT && millis() - lastPlotMs >= 6) {
      lastPlotMs = millis();
      Serial.printf("mV:%d,led:%d\n", mv, ledOn ? prevBright : prevDark);
    }
  }
}
