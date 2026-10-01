// light_rx — CdS で光の点滅を読んで、文字に戻す (受け取る側)
// light_tx が送った文字を、シリアルモニタ (115200bps) に 1 行ずつ出す。
// 明るさの「しきい値」は、直近 3 秒間のいちばん明るい値と暗い値のまん中に自動で合わせる。
// TEST_MODE = true にすると、"0123456789" と比べて、1 行ごとに誤りの数を出す。
//
// 配線: 3V3 ─ CdS ─┬─ IO34        CdS は送る側の LED に 1cm くらいまで近づけて向ける。
//                  └─ 10kΩ ─ GND   紙の筒でつなぐと、部屋の明かりや影の影響を受けにくい。
// ボード: ESP32 Dev Module (Freenove ESP32 WROOM) / ESP32 Arduino core 3.x

const int CDS_PIN = 34;

// ★ 送る側 (light_tx) と同じ値にする
int BIT_MS = 100;
bool TEST_MODE = false;

const char *TEST_LINE = "0123456789";

// ---- 光 → 文字 (rxSample に 2ms ごとの電圧を入れると、1 文字そろうたびに onRxByte を呼ぶ) ----
const int MIN_SWING_MV = 120;        // 明るいと暗いの差がこれより小さいときは、暗さ + これ を超えたら「点灯」
const int WINDOW_BLOCKS = 30;        // 100ms × 30 = 3 秒間の 明るい / 暗い を覚えておく

void onRxByte(uint8_t b, bool ok);

int blockHi[WINDOW_BLOCKS], blockLo[WINDOW_BLOCKS];
int blockIdx = 0;
uint32_t blockStart = 0;
int curHi = 0, curLo = 4000;
int rxState = 0;                     // 0: 暗くなるのを待つ  1: スタートビットを待つ  2: 1 文字を読んでいる
uint32_t lowSince = 0, t0 = 0;
int bitNo = 0;
uint8_t value = 0;
int smooth[3] = {0, 0, 0};
int smoothIdx = 0;
bool rxInit = false;

void rxSample(uint32_t now, int mvRaw) {
  if (!rxInit) {
    for (int i = 0; i < WINDOW_BLOCKS; i++) { blockHi[i] = mvRaw; blockLo[i] = mvRaw; }
    for (int i = 0; i < 3; i++) smooth[i] = mvRaw;
    blockStart = now;
    rxInit = true;
  }
  smooth[smoothIdx] = mvRaw;                         // 3 回分の平均でざらつきを減らす
  smoothIdx = (smoothIdx + 1) % 3;
  int mv = (smooth[0] + smooth[1] + smooth[2]) / 3;

  // 直近 3 秒の いちばん明るい / 暗い
  curHi = max(curHi, mv);
  curLo = min(curLo, mv);
  if (now - blockStart >= 100) {
    blockHi[blockIdx] = curHi;
    blockLo[blockIdx] = curLo;
    blockIdx = (blockIdx + 1) % WINDOW_BLOCKS;
    curHi = 0;
    curLo = 4000;
    blockStart = now;
  }
  int hi = curHi, lo = curLo;
  for (int i = 0; i < WINDOW_BLOCKS; i++) { hi = max(hi, blockHi[i]); lo = min(lo, blockLo[i]); }
  int threshold = (hi - lo >= MIN_SWING_MV * 2) ? (hi + lo) / 2 : lo + MIN_SWING_MV;
  bool on = mv > threshold;

  switch (rxState) {
    case 0:                                          // 1 ビット分 暗いのが続いたら、受け付け開始
      if (on) lowSince = 0;
      else if (lowSince == 0) lowSince = now;
      else if (now - lowSince >= (uint32_t)BIT_MS) rxState = 1;
      break;
    case 1:                                          // 明るくなった = スタートビット
      if (on) { t0 = now; bitNo = 0; value = 0; rxState = 2; }
      break;
    case 2:                                          // 各ビットのまん中 (t0 + 1.5, 2.5, ... ビット) で読む
      if (now - t0 >= (uint32_t)(BIT_MS * 3 / 2 + BIT_MS * bitNo)) {
        if (bitNo < 8) {
          if (on) value |= (1 << bitNo);
          bitNo++;
        } else {                                     // ストップビットは暗いはず
          onRxByte(value, !on);
          rxState = on ? 0 : 1;
          lowSince = 0;
        }
      }
      break;
  }
}
// ---- ここまで ----

String line;
int errLines = 0, totalLines = 0;
long errChars = 0, totalChars = 0;

void onRxByte(uint8_t b, bool ok) {
  if (!ok) { line += '?'; return; }                  // ストップビットが合わない = 区切りがずれた
  if (b == '\n') {
    if (TEST_MODE) {
      int n = max((int)line.length(), (int)strlen(TEST_LINE)), errors = 0;
      for (int i = 0; i < n; i++) {
        char want = (i < (int)strlen(TEST_LINE)) ? TEST_LINE[i] : 0;
        char got = (i < (int)line.length()) ? line[i] : 0;
        if (want != got) errors++;
      }
      errChars += errors;
      totalChars += strlen(TEST_LINE);
      Serial.printf("%-14s 誤り %d 文字   (累計 %.1f%%)\n", line.c_str(), errors, 100.0 * errChars / totalChars);
    } else {
      Serial.println(line);
    }
    line = "";
  } else if (b >= 0x20 && b != 0x7F) {               // 制御文字 (頭の 0x01 など) は表示しない。日本語 (UTF-8) は通す
    line += (char)b;
  }
}

void setup() {
  Serial.begin(115200);
  Serial.printf("1 ビット %d ms で受け取ります\n", BIT_MS);
}

uint32_t lastSampleMs = 0;

void loop() {
  if (millis() - lastSampleMs >= 2) {
    lastSampleMs = millis();
    rxSample(lastSampleMs, analogReadMilliVolts(CDS_PIN));
  }
}
