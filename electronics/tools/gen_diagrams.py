#!/usr/bin/env python3
"""electronics/ の配線図 (SVG) を生成する。

    python3 electronics/tools/gen_diagrams.py

ブレッドボード EIC-801 (30行 × a〜j + 電源ライン上下2本ずつ) の穴の座標を計算して描くので、
部品や線の位置を変えたいときは、各図の「配線リスト」を書き換えて再生成する。
"""
import math
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'img')

P = 20  # 0.1インチ (2.54mm) = 20px
FONT = "'Hiragino Kaku Gothic ProN','Yu Gothic','Noto Sans JP','Noto Sans CJK JP',Meiryo,sans-serif"
MONO = "'JetBrains Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"

# 線の色 (ネットごと)。どちらのテーマでも見えるよう、図は明るい台紙の上に描く
C = {
    '5V': '#E11D48', '3V3': '#EA8A00', 'GND': '#1F2937', 'VBAT': '#C026D3',
    'IO25': '#16A34A', 'IO26': '#0284C7', 'IO27': '#4F46E5', 'IO33': '#9333EA',
    'IO32': '#B45309', 'IO34': '#0F766E', 'IO35': '#0F766E',
    'MOTOR': '#475569',
}
INK = '#1F2430'
MUTED = '#6B7280'

COLS = 'abcdefghij'
COL_Y = {'a': 0, 'b': 1, 'c': 2, 'd': 3, 'e': 4, 'f': 7, 'g': 8, 'h': 9, 'i': 10, 'j': 11}
RAIL_Y = {'top+': -3.2, 'top-': -2.2, 'bot+': 13.2, 'bot-': 14.2}
RAIL_X = [g * 6 + k + 0.5 for g in range(5) for k in range(5)]  # 行単位 (1行目 = 0)

# ESP32-DevKitC-32E を「USB を左」にして挿したときの J1 列 (b 列, 外側の a 列が空く)。
# 1行目が USB 側。J1 の 19番ピン(5V) から 1番ピン(3V3) へ。
J1 = ['5V', 'CMD', 'SD3', 'SD2', 'IO13', 'GND', 'IO12', 'IO14', 'IO27', 'IO26',
      'IO25', 'IO33', 'IO32', 'IO35', 'IO34', 'VN', 'VP', 'EN', '3V3']
# 反対側の J3 列 (j 列, 空き穴なし)。1行目が USB 側。
J3 = ['CLK', 'SD0', 'SD1', 'IO15', 'IO2', 'IO0', 'IO4', 'IO16', 'IO17', 'IO5',
      'IO18', 'IO19', 'GND', 'IO21', 'RX', 'TX', 'IO22', 'IO23', 'GND']

# Freenove ESP32 WROOM ボード (20 ピン × 2 列、USB Type-C) を同じ向き (USB を左) にしたとき。
# Freenove のピン配置図から。ピン列の間隔は DevKitC と同じ 10 穴ぶんなので、上の a 列だけ空く。
# IO13 から 3V3 までの並びは DevKitC の J1 と同じで、1 行ずつ右にずれる。
FN_TOP = ['5V', '5V', '3V3', '3V3', '3V3', 'IO13', 'GND', 'IO12', 'IO14', 'IO27',
          'IO26', 'IO25', 'IO33', 'IO32', 'IO35', 'IO34', 'VN', 'VP', 'EN', '3V3']
FN_BOT = ['GND', 'GND', 'GND', 'GND', 'IO15', 'IO2', 'IO0', 'IO4', 'IO16', 'IO17',
          'IO5', 'IO18', 'IO19', 'GND', 'IO21', 'RX', 'TX', 'IO22', 'IO23', 'GND']


def esc(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


class SVG:
    def __init__(self, w, h, title, desc):
        self.w, self.h = w, h
        self.parts = []
        self.title, self.desc = title, desc

    def add(self, s):
        self.parts.append(s)

    def text(self, x, y, s, size=11, fill=INK, anchor='middle', weight=400, rotate=None, family=None, cls=None):
        tr = f' transform="rotate({rotate} {x:.1f} {y:.1f})"' if rotate is not None else ''
        fam = f' font-family="{family}"' if family else ''
        c = f' class="{cls}"' if cls else ''
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" '
                 f'dominant-baseline="central" font-weight="{weight}"{fam}{tr}{c}>{esc(s)}</text>')

    def save(self, name):
        head = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" '
                f'width="{self.w}" height="{self.h}" role="img" aria-labelledby="t d" '
                f'font-family="{FONT}">\n<title id="t">{esc(self.title)}</title>\n<desc id="d">{esc(self.desc)}</desc>\n'
                f'<rect width="{self.w}" height="{self.h}" rx="14" fill="#FBFAF7"/>\n')
        with open(os.path.join(OUT, name), 'w', encoding='utf-8') as f:
            f.write(head + '\n'.join(self.parts) + '\n</svg>\n')
        print('wrote', name)


# ------------------------------------------------------------------ ブレッドボード
class Board:
    """EIC-801 を描いて、穴の座標を返す。行は 1〜30 (左→右)、列は a〜j (上→下)。"""

    def __init__(self, svg, ox, oy):
        self.s, self.ox, self.oy = svg, ox, oy

    def hole(self, name):
        """'a12' のような穴、または 'top+:12' のような電源ライン (12行目付近の穴) の座標。"""
        if ':' in name:
            rail, row = name.split(':')
            r = float(row) - 1
            rx = min(RAIL_X, key=lambda v: abs(v - r))
            return self.ox + rx * P, self.oy + RAIL_Y[rail] * P
        col, row = name[0], int(name[1:])
        return self.ox + (row - 1) * P, self.oy + COL_Y[col] * P

    def draw(self):
        s, ox, oy = self.s, self.ox, self.oy
        x0, x1 = ox - 1.1 * P, ox + 29 * P + 1.1 * P
        y0, y1 = oy - 4.3 * P, oy + 15.3 * P
        s.add(f'<rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" rx="8" fill="#F1EEE6" stroke="#D6D0C2"/>')
        s.add(f'<rect x="{x0}" y="{oy + 4.9 * P}" width="{x1 - x0}" height="{1.2 * P}" fill="#E4DFD2"/>')
        # 電源ラインの赤線・青線 (A 側: 外 +, 内 − / J 側: 内 +, 外 −)
        for key, color, dy in (('top+', '#D63A3A', -0.55), ('top-', '#2F6BD8', 0.55),
                               ('bot+', '#D63A3A', -0.55), ('bot-', '#2F6BD8', 0.55)):
            y = oy + (RAIL_Y[key] + dy) * P
            s.add(f'<line x1="{x0 + 10}" y1="{y}" x2="{x1 - 10}" y2="{y}" stroke="{color}" stroke-width="1.6"/>')
        for key, sign in (('top+', '+'), ('top-', '−'), ('bot+', '+'), ('bot-', '−')):
            s.text(x0 + 5, oy + RAIL_Y[key] * P, sign, size=12, weight=700,
                   fill='#D63A3A' if sign == '+' else '#2F6BD8')
        # 穴
        holes = []
        for row in range(1, 31):
            for col in COLS:
                x, y = self.hole(f'{col}{row}')
                holes.append(f'<rect x="{x - 3}" y="{y - 3}" width="6" height="6" rx="1" fill="#5B6070"/>')
        for key in RAIL_Y:
            for rx in RAIL_X:
                holes.append(f'<rect x="{ox + rx * P - 3}" y="{oy + RAIL_Y[key] * P - 3}" width="6" height="6" rx="1" fill="#5B6070"/>')
        s.add('<g>' + ''.join(holes) + '</g>')
        # 行番号・列記号
        for row in (1, 5, 10, 15, 20, 25, 30):
            x, _ = self.hole(f'a{row}')
            s.text(x, oy + 5.5 * P, row, size=9, fill=MUTED, family=MONO)
        for col in COLS:
            x, y = self.hole(f'{col}30')
            s.text(x + 0.85 * P, y, col, size=9, fill=MUTED, family=MONO)

    def esp32(self, used):
        """DevKitC を 1〜19 行に、J1 を b 列・J3 を j 列にして描く。used: {ピン名: 色}"""
        s = self.s
        bx0 = self.hole('b1')[0] - 1.25 * P
        bx1 = self.hole('b19')[0] + 0.9 * P
        by0 = self.oy + 0.5 * P
        by1 = self.oy + 11.5 * P
        # USB コネクタ
        s.add(f'<rect x="{bx0 - 0.7 * P}" y="{self.oy + 4.9 * P}" width="{1.2 * P}" height="{2.2 * P}" rx="2" fill="#B8BDC7" stroke="#8B919C"/>')
        # 基板
        s.add(f'<rect x="{bx0}" y="{by0}" width="{bx1 - bx0}" height="{by1 - by0}" rx="4" fill="#23262E" opacity=".94"/>')
        # WROOM-32E モジュール (アンテナは基板の端から少しはみ出す)
        mx0, mx1 = self.hole('b12')[0], bx1 + 1.4 * P
        s.add(f'<rect x="{mx0}" y="{by0 + 0.9 * P}" width="{mx1 - mx0}" height="{by1 - by0 - 1.8 * P}" rx="3" fill="#D9DCE3" stroke="#9BA1AD"/>')
        s.add(f'<rect x="{mx0 + 0.5 * P}" y="{by0 + 1.6 * P}" width="{bx1 - mx0 - 1.6 * P}" height="{by1 - by0 - 3.2 * P}" rx="2" fill="#C7CBD4"/>')
        ax = bx1 - 0.6 * P
        s.add(f'<rect x="{ax}" y="{by0 + 0.9 * P}" width="{mx1 - ax}" height="{by1 - by0 - 1.8 * P}" fill="#E9EBF0" stroke="#9BA1AD"/>')
        s.text((mx0 + ax) / 2, self.oy + 5.2 * P, 'ESP32-WROOM-32E', size=10, fill='#3A3F4B', weight=700)
        s.text((ax + mx1) / 2, self.oy + 6.0 * P, 'アンテナ', size=8, fill=MUTED, rotate=-90)
        s.text(self.hole('b6')[0], self.oy + 4.6 * P, 'ESP32-DevKitC-32E', size=11, fill='#F3F4F6', weight=700)
        s.text(self.hole('b6')[0], self.oy + 6.4 * P, 'USB を左に・J1 (3V3/5V 側) を上に挿す', size=9, fill='#C9CDD6')
        # ボタン
        for label, cy in (('EN', 2.4), ('BOOT', 9.6)):
            x = bx0 + 0.75 * P
            s.add(f'<rect x="{x - 6}" y="{self.oy + cy * P - 6}" width="12" height="12" rx="2" fill="#E5E7EB"/>')
            s.text(x + 16, self.oy + cy * P, label, size=8, fill='#C9CDD6', anchor='start')
        # ピンとラベル
        for i, name in enumerate(J1):
            x, y = self.hole(f'b{i + 1}')
            color = used.get(name)
            s.add(f'<rect x="{x - 4.5}" y="{y - 4.5}" width="9" height="9" rx="1.5" fill="{color or "#C9A227"}" stroke="#111" stroke-width=".6"/>')
            if color:
                s.add(f'<rect x="{x - 12}" y="{y + 7}" width="24" height="13" rx="3" fill="{color}"/>')
                s.text(x, y + 13.5, name.replace('IO', ''), size=8.5, fill='#fff', weight=700, family=MONO)
            else:
                s.text(x, y + 13.5, name.replace('IO', ''), size=8, fill='#9AA0AC', family=MONO)
        for i, name in enumerate(J3):
            x, y = self.hole(f'j{i + 1}')
            s.add(f'<rect x="{x - 4.5}" y="{y - 4.5}" width="9" height="9" rx="1.5" fill="#8C7A3A" stroke="#111" stroke-width=".6"/>')
            s.text(x, y - 13, name.replace('IO', ''), size=7.5, fill='#8A909C', family=MONO)
        s.text(self.hole('b6')[0], self.oy + 8.3 * P, '下の列 (J3) は空き穴がないので使わない', size=8.5, fill='#9AA0AC')

    def freenove(self, used):
        """Freenove ESP32 WROOM を 1〜20 行に、上のピン列を b 列・下を j 列にして描く。used: {ピン名: 色}"""
        s = self.s
        bx0 = self.hole('b1')[0] - 0.6 * P
        bx1 = self.hole('b20')[0] + 0.5 * P
        by0 = self.oy + 0.5 * P
        by1 = self.oy + 11.5 * P
        # USB Type-C (細長い角丸)
        s.add(f'<rect x="{bx0 - 0.55 * P}" y="{self.oy + 5.15 * P}" width="{1.0 * P}" height="{1.7 * P}" rx="6" fill="#B8BDC7" stroke="#8B919C"/>')
        s.add(f'<rect x="{bx0}" y="{by0}" width="{bx1 - bx0}" height="{by1 - by0}" rx="4" fill="#15171C" opacity=".95"/>')
        # モジュール。アンテナ部分は基板の端から約 2.9 穴ぶん、d〜h 列の上に浮いて張り出す (ピン配置図から測った値)
        mx0, mx1 = self.hole('b13')[0], self.hole('b20')[0] + 2.9 * P
        my0, my1 = self.oy + 2.4 * P, self.oy + 9.6 * P
        ax = bx1 - 0.6 * P
        s.add(f'<rect x="{mx0}" y="{my0}" width="{ax - mx0}" height="{my1 - my0}" rx="3" fill="#D9DCE3" stroke="#9BA1AD"/>')
        s.add(f'<rect x="{mx0 + 0.5 * P}" y="{my0 + 0.6 * P}" width="{ax - mx0 - 1.0 * P}" height="{my1 - my0 - 1.2 * P}" rx="2" fill="#C7CBD4"/>')
        s.add(f'<rect x="{ax}" y="{my0}" width="{mx1 - ax}" height="{my1 - my0}" rx="2" fill="#2A2D35" opacity=".82" stroke="#6B7280" stroke-dasharray="3 2"/>')
        s.add(f'<path d="M{ax + 6} {my0 + 12} h{mx1 - ax - 18} v8 h-{mx1 - ax - 26} v8 h{mx1 - ax - 26} v8" fill="none" stroke="#C9A227" stroke-width="1.5" opacity=".8"/>')
        s.text((mx0 + ax) / 2, self.oy + 5.2 * P, 'ESP32-WROOM-32E', size=10, fill='#3A3F4B', weight=700)
        s.text((ax + mx1) / 2, self.oy + 7.4 * P, 'アンテナ', size=8.5, fill='#E5E7EB', weight=700)
        s.text((ax + mx1) / 2, self.oy + 8.3 * P, '(浮いている)', size=7.5, fill='#C9CDD6')
        s.text(self.hole('b7')[0], self.oy + 4.3 * P, 'Freenove ESP32 WROOM', size=11, fill='#F3F4F6', weight=700)
        s.text(self.hole('b7')[0], self.oy + 5.9 * P, 'USB-C を左・3V3/5V の列を上に挿す', size=9, fill='#C9CDD6')
        # ボタン (USB の上下)
        for label, cy in (('EN', 3.2), ('BOOT', 8.8)):
            x = bx0 + 0.7 * P
            s.add(f'<rect x="{x - 7}" y="{self.oy + cy * P - 7}" width="14" height="14" rx="2" fill="#E5E7EB"/>')
            s.text(x + 17, self.oy + cy * P, label, size=8, fill='#C9CDD6', anchor='start')
        # 基板の LED: 青 (IO2) とフルカラー (IO16)
        lx, ly = self.hole('b9')[0], self.oy + 7.4 * P
        s.add(f'<rect x="{lx - 7}" y="{ly - 7}" width="14" height="14" rx="2" fill="#F8FAFC" stroke="#9CA3AF"/>')
        s.add(f'<circle cx="{lx}" cy="{ly}" r="3.5" fill="url(#rgb)"/>')
        s.add('<defs><linearGradient id="rgb"><stop offset="0" stop-color="#EF4444"/><stop offset=".5" stop-color="#22C55E"/><stop offset="1" stop-color="#3B82F6"/></linearGradient></defs>')
        s.text(lx + 12, ly, 'RGB (16)', size=8, fill='#C9CDD6', anchor='start')
        s.add(f'<rect x="{lx - 4}" y="{ly + 14}" width="8" height="5" rx="1" fill="#3B82F6"/>')
        s.text(lx + 12, ly + 17, 'LED (2)', size=8, fill='#C9CDD6', anchor='start')
        for i, name in enumerate(FN_TOP):
            x, y = self.hole(f'b{i + 1}')
            color = used.get(name)
            s.add(f'<rect x="{x - 4.5}" y="{y - 4.5}" width="9" height="9" rx="1.5" fill="{color or "#C9A227"}" stroke="#111" stroke-width=".6"/>')
            label = name.replace('IO', '')
            if color:
                s.add(f'<rect x="{x - 12}" y="{y + 7}" width="24" height="13" rx="3" fill="{color}"/>')
                s.text(x, y + 13.5, label, size=8.5, fill='#fff', weight=700, family=MONO)
            else:
                s.text(x, y + 13.5, label, size=8, fill='#9AA0AC', family=MONO)
        for i, name in enumerate(FN_BOT):
            x, y = self.hole(f'j{i + 1}')
            s.add(f'<rect x="{x - 4.5}" y="{y - 4.5}" width="9" height="9" rx="1.5" fill="#8C7A3A" stroke="#111" stroke-width=".6"/>')
            s.text(x, y - 13, name.replace('IO', ''), size=7.5, fill='#8A909C', family=MONO)

    # ---- 部品 ----
    def cap_e(self, plus, minus, label='470µF'):
        """電解コンデンサーを上から見た絵。+ の足を plus、− の足を minus の穴に"""
        (x1, y1), (x2, y2) = self.hole(plus), self.hole(minus)
        cx, cy = (x1 + x2) / 2 + 22, (y1 + y2) / 2
        s = self.s
        for x, y in ((x1, y1), (x2, y2)):
            s.add(f'<line x1="{x}" y1="{y}" x2="{cx - 8}" y2="{cy + (y - cy) * .4}" stroke="#8A8F99" stroke-width="1.6"/>')
            s.add(f'<circle cx="{x}" cy="{y}" r="2.6" fill="#8A8F99"/>')
        s.add(f'<circle cx="{cx}" cy="{cy}" r="13" fill="#1F3F8A" stroke="#14295C"/>')
        # − 側の帯 (白い弧)
        side = 1 if y2 > y1 else -1
        s.add(f'<path d="M{cx - 11} {cy + side * 6} A13 13 0 0 {0 if side > 0 else 1} {cx + 11} {cy + side * 6}" fill="none" stroke="#E5E7EB" stroke-width="4"/>')
        s.text(cx, cy - side * 4, '+', size=10, fill='#fff', weight=700)
        s.text(cx + 18, cy, label, size=9, weight=700, anchor='start')

    def resistor(self, a, b, bands=('#6B3E26', '#111', '#E07A1F'), label='10kΩ', label_dx=0, label_dy=-14):
        (x1, y1), (x2, y2) = self.hole(a), self.hole(b)
        ang = math.degrees(math.atan2(y2 - y1, x2 - x1))
        L = math.hypot(x2 - x1, y2 - y1)
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        body = min(28, L - 8)
        s = self.s
        s.add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#8A8F99" stroke-width="2"/>')
        g = [f'<g transform="translate({cx:.1f} {cy:.1f}) rotate({ang:.1f})">',
             f'<rect x="{-body / 2}" y="-5" width="{body}" height="10" rx="4" fill="#E7C98E" stroke="#A88A52" stroke-width=".8"/>']
        for i, c in enumerate(list(bands) + ['#C9A227']):
            bx = -body / 2 + 5 + i * (body - 10) / 3
            g.append(f'<rect x="{bx - 1.5}" y="-5" width="3" height="10" fill="{c}"/>')
        g.append('</g>')
        s.add(''.join(g))
        for x, y in ((x1, y1), (x2, y2)):
            s.add(f'<circle cx="{x}" cy="{y}" r="2.6" fill="#8A8F99"/>')
        if label:
            s.text(cx + label_dx, cy + label_dy, label, size=9, fill=INK, weight=700)

    def cds(self, a, b, label='CdS', below=False):
        (x1, y1), (x2, y2) = self.hole(a), self.hole(b)
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2 - 12
        s = self.s
        for x, y in ((x1, y1), (x2, y2)):
            s.add(f'<line x1="{x}" y1="{y}" x2="{cx + (x - cx) * .35}" y2="{cy + 6}" stroke="#8A8F99" stroke-width="1.6"/>')
            s.add(f'<circle cx="{x}" cy="{y}" r="2.6" fill="#8A8F99"/>')
        s.add(f'<circle cx="{cx}" cy="{cy}" r="9" fill="#F4E9C8" stroke="#B89B4E"/>')
        s.add(f'<path d="M{cx - 5} {cy - 3} q2.5 -4 5 0 t5 0 M{cx - 5} {cy + 3} q2.5 -4 5 0 t5 0" fill="none" stroke="#B5462C" stroke-width="1.3"/>')
        s.text(cx, cy + 22 if below else cy - 16, label, size=9, weight=700)

    def module(self, rows, top_labels, bottom_labels, name):
        """DIP モジュールを e 列・f 列にまたがって置く (DRV8835 など)"""
        s = self.s
        xa, _ = self.hole(f'e{rows[0]}')
        xb, _ = self.hole(f'e{rows[-1]}')
        ya, yb = self.hole('e1')[1], self.hole('f1')[1]
        s.add(f'<rect x="{xa - 0.6 * P}" y="{ya - 0.55 * P}" width="{xb - xa + 1.2 * P}" height="{yb - ya + 1.1 * P}" rx="3" fill="#1C8A4A" stroke="#0E5A2F"/>')
        s.text(xa - 1.25 * P, (ya + yb) / 2, name, size=9, fill='#0E5A2F', weight=700, rotate=-90)
        for r, t, b in zip(rows, top_labels, bottom_labels):
            x, y = self.hole(f'e{r}')
            s.add(f'<circle cx="{x}" cy="{y}" r="4" fill="#D8C27A" stroke="#6B5A1E" stroke-width=".7"/>')
            s.text(x, y + 19, t, size=7, fill='#FFFFFF', rotate=-90, weight=700, family=MONO)
            x, y = self.hole(f'f{r}')
            s.add(f'<circle cx="{x}" cy="{y}" r="4" fill="#D8C27A" stroke="#6B5A1E" stroke-width=".7"/>')
            s.text(x, y - 19, b, size=7, fill='#FFFFFF', rotate=-90, weight=700, family=MONO)

    def dip(self, rows, e_labels, f_labels, name, notch='right'):
        """DIP の IC を e 列・f 列にまたがって置く。e_labels / f_labels は rows の順のピン名"""
        s = self.s
        xa, _ = self.hole(f'e{rows[0]}')
        xb, _ = self.hole(f'e{rows[-1]}')
        ya, yb = self.hole('e1')[1], self.hole('f1')[1]
        x0, x1 = xa - 0.35 * P, xb + 0.35 * P
        s.add(f'<rect x="{x0}" y="{ya - 0.25 * P}" width="{x1 - x0}" height="{yb - ya + 0.5 * P}" rx="3" fill="#202329" stroke="#0B0C0F"/>')
        nx = x1 if notch == 'right' else x0
        s.add(f'<path d="M{nx} {(ya + yb) / 2 - 7} a7 7 0 0 {1 if notch == "right" else 0} 0 14" fill="#4B5060"/>')
        s.text((x0 + x1) / 2, (ya + yb) / 2, name, size=10, fill='#E5E7EB', weight=700)
        for r, t, b in zip(rows, e_labels, f_labels):
            for col, lab, dy in (('e', t, 15), ('f', b, -15)):
                x, y = self.hole(f'{col}{r}')
                s.add(f'<rect x="{x - 3.5}" y="{y - 3.5}" width="7" height="7" fill="#C9CDD6" stroke="#6B7280" stroke-width=".6"/>')
                s.text(x, y + dy, lab, size=7, fill='#E5E7EB', weight=700, family=MONO)

    def thermistor(self, a, b, label='サーミスター'):
        (x1, y1), (x2, y2) = self.hole(a), self.hole(b)
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2 + 13
        s = self.s
        for x, y in ((x1, y1), (x2, y2)):
            s.add(f'<line x1="{x}" y1="{y}" x2="{cx + (x - cx) * .3}" y2="{cy - 3}" stroke="#8A8F99" stroke-width="1.4"/>')
            s.add(f'<circle cx="{x}" cy="{y}" r="2.6" fill="#8A8F99"/>')
        s.add(f'<ellipse cx="{cx}" cy="{cy + 2}" rx="5" ry="7" fill="#D7E8EF" stroke="#7FA7B8"/>')
        s.add(f'<ellipse cx="{cx}" cy="{cy + 2}" rx="2" ry="3" fill="#3B4252"/>')
        s.text(cx, cy + 20, label, size=9, weight=700)

    def ir_module(self, rows, lens='down'):
        """赤外線受信モジュールを c 列に 3 本挿したところ (上から見た図)。lens='down' でレンズが j 側"""
        s = self.s
        x0, y = self.hole(f'c{rows[0]}')
        x1, _ = self.hole(f'c{rows[-1]}')
        s.add(f'<rect x="{x0 - 9}" y="{y - 9}" width="{x1 - x0 + 18}" height="14" rx="2" fill="#1F2937"/>')
        cx = (x0 + x1) / 2
        s.add(f'<path d="M{cx - 9} {y + 5} a9 9 0 0 0 18 0 z" fill="#374151" stroke="#111827"/>')
        for r in rows:
            x, yy = self.hole(f'c{r}')
            s.add(f'<circle cx="{x}" cy="{yy}" r="2.6" fill="#C9CDD6"/>')

    def connector2(self, a, b):
        (x1, y1), (x2, y2) = self.hole(a), self.hole(b)
        self.s.add(f'<rect x="{min(x1, x2) - 7}" y="{min(y1, y2) - 7}" width="{abs(x2 - x1) + 14}" height="{abs(y2 - y1) + 14}" rx="2" fill="#20232A"/>')

    # ---- 線 ----
    def wire(self, a, b, color, lift=1.2, straight=False, width=4):
        (x1, y1), (x2, y2) = (self.hole(a) if isinstance(a, str) else a), (self.hole(b) if isinstance(b, str) else b)
        if straight:
            d = f'M{x1:.1f} {y1:.1f} L{x2:.1f} {y2:.1f}'
        else:
            top = min(y1, y2) - lift * P
            d = f'M{x1:.1f} {y1:.1f} C{x1:.1f} {top:.1f} {x2:.1f} {top:.1f} {x2:.1f} {y2:.1f}'
        self.s.add(f'<path d="{d}" fill="none" stroke="#FFFFFF" stroke-width="{width + 2.4}" stroke-linecap="round" opacity=".85"/>')
        self.s.add(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round"/>')
        for x, y in ((x1, y1), (x2, y2)):
            self.s.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.2" fill="{color}" stroke="#fff" stroke-width="1"/>')

    def path(self, pts, color, width=4, dots=True):
        d = 'M' + ' L'.join(f'{x:.1f} {y:.1f}' for x, y in pts)
        self.s.add(f'<path d="{d}" fill="none" stroke="#FFFFFF" stroke-width="{width + 2.4}" stroke-linecap="round" stroke-linejoin="round" opacity=".85"/>')
        self.s.add(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"/>')
        if dots:
            x, y = pts[0]
            self.s.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.2" fill="{color}" stroke="#fff" stroke-width="1"/>')


def tag(s, x, y, text, color, anchor='middle'):
    """線の途中に付けるラベル (白抜き)"""
    w = 7 * len(text) + 10
    x0 = x - w / 2 if anchor == 'middle' else (x if anchor == 'start' else x - w)
    s.add(f'<rect x="{x0:.1f}" y="{y - 8:.1f}" width="{w}" height="16" rx="8" fill="{color}"/>')
    s.text(x0 + w / 2, y, text, size=9, fill='#fff', weight=700, family=MONO)


def legend(s, x, y, items):
    for label, color in items:
        s.add(f'<rect x="{x}" y="{y - 3}" width="22" height="6" rx="3" fill="{color}"/>')
        s.text(x + 28, y, label, size=10, anchor='start')
        x += 34 + 7.2 * len(label) + 14


def usb_cable(s, b, label):
    x, y = b.hole('b1')[0] - 1.95 * P, b.oy + 6 * P
    s.add(f'<path d="M{x} {y} C{x - 30} {y} {x - 30} {y + 60} {x - 40} {y + 120}" fill="none" stroke="#9CA3AF" stroke-width="7" stroke-linecap="round"/>')
    s.text(x - 40, y + 136, label[0], size=10, weight=700, anchor='middle')
    s.text(x - 40, y + 151, label[1], size=9, fill=MUTED, anchor='middle')


def route(b, pts, color, width=4):
    """穴や座標を順に結ぶ折れ線 (始点と終点に丸)。pts には穴の名前も書ける"""
    xy = [b.hole(p) if isinstance(p, str) else p for p in pts]
    b.path(xy, color, width=width)
    x, y = xy[-1]
    b.s.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.2" fill="{color}" stroke="#fff" stroke-width="1"/>')


# ------------------------------------------------------------------ 部品の絵 (ブレッドボードの外)
def servo_icon(s, x, y, w=120, h=58):
    s.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="#2F6FDB" stroke="#1D4FA8"/>')
    s.add(f'<circle cx="{x + 30}" cy="{y + h / 2}" r="12" fill="#F3F4F6" stroke="#9CA3AF"/>')
    s.add(f'<rect x="{x + 18}" y="{y + h / 2 - 24}" width="58" height="8" rx="4" fill="#F9FAFB" stroke="#9CA3AF" transform="rotate(-18 {x + 30} {y + h / 2})"/>')
    s.text(x + 84, y + h / 2 - 8, 'SG90', size=12, fill='#fff', weight=700)
    s.text(x + 84, y + h / 2 + 9, 'サーボ', size=9, fill='#DCE7FB')


def hcsr04_icon(s, x, y):
    """HC-SR04 を上から見た絵。ピンは下の辺に 左から VCC Trig Echo GND。ピン先の座標を返す"""
    s.add(f'<rect x="{x}" y="{y}" width="220" height="80" rx="5" fill="#1E5FB4" stroke="#123E7A"/>')
    for cx in (x + 40, x + 180):
        s.add(f'<circle cx="{cx}" cy="{y + 40}" r="27" fill="#D1D5DB" stroke="#6B7280" stroke-width="2"/>')
        s.add(f'<circle cx="{cx}" cy="{y + 40}" r="18" fill="#6B7280"/>')
    s.text(x + 110, y + 13, 'HC-SR04', size=10, fill='#fff', weight=700)
    pins = {}
    for i, name in enumerate(('VCC', 'Trig', 'Echo', 'GND')):
        px = x + 71 + i * 26
        s.add(f'<rect x="{px - 3}" y="{y + 80}" width="6" height="12" fill="#C9A227"/>')
        s.text(px, y + 56, name, size=8, fill='#fff', weight=700, family=MONO, rotate=-90)
        pins[name] = (px, y + 92)
    return pins


# ------------------------------------------------------------------ 首振りガジェット
def light_seeker_breadboard():
    s = SVG(1060, 632, '首振りガジェットのブレッドボード配線',
            'ESP32-DevKitC を 1〜19 行に挿し、CdS を c24–c25、10kΩ を b25 と上の − ラインの間に置く。'
            'サーボは IO25・5V・GND に、CdS の分圧点 (25 行) は IO34 につなぐ。')
    b = Board(s, 190, 210)
    b.draw()
    b.esp32({'5V': C['5V'], 'GND': C['GND'], '3V3': C['3V3'], 'IO25': C['IO25'], 'IO34': C['IO34']})

    # 電源: 5V → 上の + ライン (外側)、GND → 上の − ライン (内側)
    b.wire('a1', 'top+:1', C['5V'], straight=True)
    b.wire('a6', 'top-:6', C['GND'], straight=True)
    # 3V3 → 24 行、CdS c24–c25、10kΩ b25 → − ライン、IO34 ← 25 行
    b.wire('a19', 'a24', C['3V3'], lift=0.6)
    b.cds('c24', 'c25')
    b.resistor('b25', 'top-:25.6', label='10kΩ', label_dx=26, label_dy=2)
    b.wire('a15', 'a25', C['IO34'], lift=1.15)

    # サーボ: コネクタのメス穴 (上から 橙・赤・茶) にオス-オスのジャンパー線を挿す
    servo_icon(s, 880, 40)
    kx, ky = 800, 58                       # コネクタの左上
    s.add(f'<rect x="{kx}" y="{ky}" width="22" height="46" rx="2" fill="#1F2937"/>')
    s.text(kx + 11, ky - 10, 'メス', size=8, fill=MUTED)
    leads = (('#F08A24', '橙 信号'), ('#DC2626', '赤 5V'), ('#6B3E26', '茶 GND'))
    for i, (col, lab) in enumerate(leads):
        y = ky + 9 + i * 14
        s.add(f'<path d="M{kx + 22} {y} C{kx + 50} {y} {850} {60 + i * 8} {880} {60 + i * 8}" fill="none" stroke="{col}" stroke-width="3"/>')
        s.text(1012, 52 + i * 14, lab, size=9, fill=col, anchor='start', weight=700)
    pin = lambda i: (kx, ky + 9 + i * 14)
    route(b, ['a11', (b.hole('a11')[0], pin(0)[1]), pin(0)], C['IO25'])
    route(b, ['top+:27.5', (b.hole('top+:27.5')[0], pin(1)[1]), pin(1)], C['5V'])
    route(b, ['top-:29.5', (b.hole('top-:29.5')[0], pin(2)[1]), pin(2)], C['GND'])
    tag(s, b.hole('a11')[0] + 70, pin(0)[1], 'IO25 → 橙 (信号)', C['IO25'])

    tag(s, b.hole('a1')[0] + 36, b.hole('top+:1')[1] - 14, '5V', C['5V'])
    tag(s, b.hole('a6')[0] + 40, b.hole('top-:6')[1] - 14, 'GND', C['GND'])
    tag(s, (b.hole('a19')[0] + b.hole('a24')[0]) / 2, b.hole('a19')[1] - 0.6 * P - 11, '3V3', C['3V3'])
    tag(s, (b.hole('a15')[0] + b.hole('a25')[0]) / 2, b.hole('a15')[1] - 1.15 * P - 11, 'IO34', C['IO34'])

    usb_cable(s, b, ('USB → PC', '書き込み・電源・シリアル'))

    # light_seeker 用: CdS をサーボの腕に移す
    ix, iy = 560, 510
    s.add(f'<rect x="{ix}" y="{iy}" width="480" height="104" rx="10" fill="#FFFFFF" stroke="#D6D0C2"/>')
    s.text(ix + 14, iy + 18, 'light_seeker のとき: CdS を c24–c25 から抜き、オス-メス線 2 本で延長してサーボの腕に貼る', size=10, anchor='start', weight=700)
    servo_icon(s, ix + 20, iy + 32, w=110, h=50)
    s.add(f'<circle cx="{ix + 96}" cy="{iy + 34}" r="7" fill="#F4E9C8" stroke="#B89B4E"/>')
    for i, col in enumerate((C['3V3'], C['IO34'])):
        s.add(f'<path d="M{ix + 96 + (i * 6 - 3)} {iy + 40} C{ix + 170} {iy + 50 + i * 10} {ix + 230} {iy + 62 + i * 10} {ix + 300} {iy + 62 + i * 10}" fill="none" stroke="{col}" stroke-width="3"/>')
    s.text(ix + 308, iy + 62, 'c24 へ (3V3 側)', size=9.5, anchor='start', fill=C['3V3'], weight=700)
    s.text(ix + 308, iy + 76, 'c25 へ (IO34 側)', size=9.5, anchor='start', fill=C['IO34'], weight=700)
    s.text(ix + 145, iy + 88, 'テープで腕の先に。首振りでケーブルが引っかからない長さに', size=8.5, anchor='start', fill=MUTED)

    legend(s, 190, 540, [('5V', C['5V']), ('3V3', C['3V3']), ('GND', C['GND'])])
    legend(s, 190, 562, [('IO25 サーボ信号', C['IO25']), ('IO34 明るさ', C['IO34'])])
    s.save('light-seeker-breadboard.svg')


def light_seeker_schematic():
    s = SVG(760, 380, '首振りガジェットの回路図',
            'ESP32 の 5V と GND をサーボに、IO25 をサーボの信号に。3V3 から CdS と 10kΩ で分圧し、その中点を IO34 に入れる。')
    ex, ey, ew, eh = 40, 40, 150, 300
    s.add(f'<rect x="{ex}" y="{ey}" width="{ew}" height="{eh}" rx="8" fill="#23262E"/>')
    s.text(ex + ew / 2, ey + 22, 'ESP32', size=14, fill='#fff', weight=700)
    s.text(ex + ew / 2, ey + 40, 'DevKitC-32E', size=10, fill='#C9CDD6')
    pins = [('5V', 90, C['5V']), ('GND', 140, C['GND']), ('IO25', 190, C['IO25']), ('3V3', 250, C['3V3']), ('IO34', 300, C['IO34'])]
    for name, y, col in pins:
        s.add(f'<circle cx="{ex + ew}" cy="{y}" r="5" fill="{col}"/>')
        s.text(ex + ew - 12, y, name, size=11, fill='#fff', anchor='end', weight=700, family=MONO)

    def line(pts, col):
        d = 'M' + ' L'.join(f'{x} {y}' for x, y in pts)
        s.add(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="3" stroke-linejoin="round"/>')

    vx, vy = 500, 40
    s.add(f'<rect x="{vx}" y="{vy}" width="200" height="175" rx="10" fill="#2F6FDB"/>')
    s.text(vx + 100, vy + 20, 'SG90 サーボ', size=13, fill='#fff', weight=700)
    for name, y, col, wire in (('赤  +5V', 90, C['5V'], '#DC2626'), ('茶  GND', 140, C['GND'], '#6B3E26'), ('橙  信号', 190, C['IO25'], '#F08A24')):
        s.add(f'<circle cx="{vx}" cy="{y}" r="6" fill="{wire}" stroke="#fff" stroke-width="1.5"/>')
        s.text(vx + 14, y, name, size=11, fill='#fff', anchor='start', weight=700)
        line([(ex + ew, y), (vx - 6, y)], col)
    s.text(345, 178, '20ms ごとに 0.5〜2.4ms のパルス', size=10, fill=MUTED)
    s.text(345, 206, '→ パルス幅で 0〜180° が決まる', size=10, fill=MUTED)

    nx = 310
    line([(ex + ew, 250), (nx, 250), (nx, 262)], C['3V3'])
    s.add(f'<circle cx="{nx}" cy="280" r="18" fill="#FFF7DF" stroke="#B89B4E"/>')
    s.add(f'<path d="M{nx} 262 l0 4 l-6 3 l12 5 l-12 5 l12 5 l-6 3 l0 5" fill="none" stroke="{INK}" stroke-width="1.6"/>')
    s.add(f'<path d="M{nx - 38} 257 l14 10 M{nx - 28} 268 l-5 -1 l2 -4 M{nx - 40} 270 l14 10 M{nx - 30} 281 l-5 -1 l2 -4" fill="none" stroke="#E0A100" stroke-width="1.6"/>')
    s.text(nx + 26, 274, 'CdS', size=11, anchor='start', weight=700)
    s.text(nx + 26, 289, '明るい 10〜20kΩ / 暗い 約1MΩ', size=9, fill=MUTED, anchor='start')
    line([(nx, 297), (nx, 300), (ex + ew, 300)], C['IO34'])
    s.add(f'<circle cx="{nx}" cy="300" r="4.5" fill="{C["IO34"]}"/>')
    line([(nx, 300), (nx, 310)], C['GND'])
    s.add(f'<path d="M{nx} 310 l-6 3 l12 5 l-12 5 l12 5 l-6 3 l0 4" fill="none" stroke="{INK}" stroke-width="1.6"/>')
    s.text(nx + 14, 322, '10kΩ', size=11, anchor='start', weight=700)
    line([(nx, 335), (nx, 344)], C['GND'])
    s.add(f'<path d="M{nx - 12} 344 h24 M{nx - 8} 349 h16 M{nx - 4} 354 h8" stroke="{INK}" stroke-width="1.8"/>')
    s.text(nx + 18, 350, 'GND', size=10, anchor='start', fill=MUTED)
    s.text(480, 290, 'IO34 の電圧 = 3.3V × 10k ÷ (CdS + 10k)', size=10.5, anchor='start', weight=700)
    s.text(480, 310, '明るい → CdS が小さい → 電圧が上がる', size=10, anchor='start', fill=MUTED)
    s.text(480, 328, '(実際の値は部屋で変わるので、シリアルモニタで確かめる)', size=9.5, anchor='start', fill=MUTED)
    s.save('light-seeker-schematic.svg')


# ------------------------------------------------------------------ 障害物回避カー
DRV_TOP = ['VCC', 'MODE', 'AIN1', 'AIN2', 'BIN1', 'BIN2']      # e 列 (ESP32 側)
DRV_BOT = ['VM', 'AOUT1', 'AOUT2', 'BOUT1', 'BOUT2', 'GND']    # f 列 (モーター側)


def car_breadboard(ir=False):
    if ir:
        s = SVG(1100, 760, '障害物回避カーに赤外線受信モジュールを足した配線',
                '障害物回避カーの配線はそのまま。受信モジュールをオス-メス線 3 本で、OUT を a5 (IO13)、GND を上の − ライン、'
                'VCC を a8 (IO14) につなぐ。IO14 は HIGH にして受信モジュールの電源にする。')
    else:
        s = SVG(1100, 760, '障害物回避カーのブレッドボード配線',
                'ESP32 を 1〜19 行、DRV8835 を 23〜28 行に置く。上の − ラインが GND。電池の + は DRV8835 の VM 行 (j23) に直接、'
                '− は下の − ラインへ。HC-SR04 は 3.3V で動かし、Trig を IO32、Echo を IO35 に直接つなぐ。')
    b = Board(s, 190, 250)
    b.draw()
    used = {'GND': C['GND'], '3V3': C['3V3'], 'IO25': C['IO25'], 'IO26': C['IO26'],
            'IO27': C['IO27'], 'IO33': C['IO33'], 'IO32': C['IO32'], 'IO35': C['IO35']}
    if ir:
        used.update({'IO13': C['IO13'], 'IO14': C['IO14']})
    b.esp32(used)
    b.module(range(23, 29), DRV_TOP, DRV_BOT, 'DRV8835')

    # 上の − ライン = GND
    b.wire('a6', 'top-:6', C['GND'], straight=True)
    # 3V3 → DRV の VCC (23 行)。MODE (24 行) は VCC とつないで H にする
    b.wire('a19', 'a23', C['3V3'], lift=0.55)
    b.wire('b23', 'b24', C['3V3'], lift=0.45, width=3)
    # 制御線: 外側ほど遠くへ (入れ子にして交差させない)
    b.wire('a12', 'a25', C['IO33'], lift=0.85)     # AIN1 = 左の向き
    b.wire('a11', 'a26', C['IO25'], lift=1.15)     # AIN2 = 左の速さ (PWM)
    b.wire('a10', 'a27', C['IO26'], lift=1.45)     # BIN1 = 右の向き
    b.wire('a9', 'a28', C['IO27'], lift=1.75)      # BIN2 = 右の速さ (PWM)
    # DRV の GND (28 行) → 下の − ライン
    b.wire('j28', 'bot-:28.5', C['GND'], straight=True)
    # 上下の − ラインをつなぐ (29〜30 行のすき間を通す)
    gx = b.hole('a30')[0] - 0.5 * P
    b.path([(gx, b.hole('top-:29.5')[1]), (gx, b.hole('bot-:29.5')[1])], C['GND'])
    for yy in (b.hole('top-:29.5')[1], b.hole('bot-:29.5')[1]):
        s.add(f'<circle cx="{gx}" cy="{yy}" r="3.2" fill="{C["GND"]}" stroke="#fff"/>')
    s.text(b.hole('j30')[0] + 26, b.oy + 5.5 * P, '上下の GND を', size=9, anchor='start', weight=700, fill=C['GND'])
    s.text(b.hole('j30')[0] + 26, b.oy + 6.3 * P, 'つなぐ線', size=9, anchor='start', weight=700, fill=C['GND'])

    # モーター: コネクタを h24–h25 (左) / h26–h27 (右) に
    b.connector2('h24', 'h25')
    b.connector2('h26', 'h27')
    my = 610
    for label, a, bb, mx, side in (('左モーター', 'h24', 'h25', 560, -1), ('右モーター', 'h26', 'h27', 840, 1)):
        (x1, y1), (x2, y2) = b.hole(a), b.hole(bb)
        s.add(f'<rect x="{mx - 36}" y="{my}" width="72" height="44" rx="6" fill="#F4C430" stroke="#B8901A"/>')
        s.add(f'<rect x="{mx + 36 * side - (26 if side < 0 else 0)}" y="{my + 10}" width="26" height="24" rx="4" fill="#C0C4CC" stroke="#8B919C"/>')
        s.text(mx, my + 22, label, size=10, weight=700)
        yy_near, yy_far = 568, 580
        # 曲がる向きの外側の線ほど上の段を通すと、2 本が交差しない
        if side < 0:   # 左へ曲がる: h24 (左の穴) が上の段で左端の端子へ
            b.path([(x1, y1 + 8), (x1, yy_near), (mx - 8, yy_near), (mx - 8, my)], '#DC2626', width=3, dots=False)
            b.path([(x2, y2 + 8), (x2, yy_far), (mx + 8, yy_far), (mx + 8, my)], '#111827', width=3, dots=False)
        else:          # 右へ曲がる: h27 (右の穴) が上の段で右端の端子へ
            b.path([(x2, y2 + 8), (x2, yy_near), (mx + 8, yy_near), (mx + 8, my)], '#DC2626', width=3, dots=False)
            b.path([(x1, y1 + 8), (x1, yy_far), (mx - 8, yy_far), (mx - 8, my)], '#111827', width=3, dots=False)
    s.text(700, 672, 'モーターのコネクタを h24–h25 (左) / h26–h27 (右) に挿す。', size=9.5, fill=MUTED)
    s.text(700, 687, '前進のはずが逆回りなら、スケッチの REVERSED で直す (配線はそのまま)', size=9.5, fill=MUTED)

    # 電池 (左下): + → j23 (VM 行) に直接、− → 下の − ライン
    bx, by = 250, 600
    s.add(f'<rect x="{bx}" y="{by}" width="150" height="70" rx="6" fill="#2B2E35"/>')
    for i in range(4):
        s.add(f'<rect x="{bx + 10}" y="{by + 8 + i * 14}" width="130" height="11" rx="5" fill="#9CA3AF"/>')
    s.text(bx + 75, by + 84, '単3×4本 (約6V)', size=10, weight=700)
    s.text(bx + 75, by + 99, 'モーター専用。3V3 には絶対つながない', size=9, fill='#B91C1C')
    vx, vy = b.hole('j23')
    ly = b.oy + 12.1 * P
    b.path([(bx + 120, by), (bx + 120, ly), (vx, ly), (vx, vy)], C['VBAT'], width=3, dots=False)
    s.add(f'<circle cx="{vx}" cy="{vy}" r="3.2" fill="{C["VBAT"]}" stroke="#fff"/>')
    tag(s, (bx + 120 + vx) / 2, ly, '電池 + → j23 (VM)', C['VBAT'])
    gxh, gyh = b.hole('bot-:12.5')
    b.path([(bx + 40, by), (bx + 40, by - 20), (gxh, by - 20), (gxh, gyh)], '#111827', width=3, dots=False)
    s.add(f'<circle cx="{gxh}" cy="{gyh}" r="3.2" fill="#111827" stroke="#fff"/>')
    tag(s, gxh + 60, by - 20, '電池 − → − ライン', '#111827')

    # HC-SR04 (右上。車の前向きに付けて、オス-メスのジャンパー線 4 本で)
    pins = hcsr04_icon(s, 840, 30)
    s.text(950, 20, '車の前に向けて付ける (3.3V で動かす)', size=9.5, fill=MUTED)
    route(b, ['a13', (b.hole('a13')[0], 150), (pins['Trig'][0], 150), pins['Trig']], C['IO32'])
    route(b, ['a14', (b.hole('a14')[0], 164), (pins['Echo'][0], 164), pins['Echo']], C['IO35'])
    route(b, ['c23', (b.hole('c23')[0], 178), (pins['VCC'][0], 178), pins['VCC']], C['3V3'])
    route(b, ['top-:27.5', (b.hole('top-:27.5')[0], 196), (pins['GND'][0], 196), pins['GND']], C['GND'])
    tag(s, b.hole('a13')[0] + 64, 150, 'IO32 → Trig', C['IO32'])
    tag(s, b.hole('a14')[0] + 96, 164, 'IO35 ← Echo', C['IO35'])
    tag(s, b.hole('c23')[0] + 74, 178, '3V3 → VCC', C['3V3'])

    tag(s, b.hole('a6')[0] + (-52 if ir else 40), b.hole('top-:6')[1] - 14, 'GND', C['GND'])
    tag(s, (b.hole('a19')[0] + b.hole('a23')[0]) / 2, b.hole('a19')[1] - 0.55 * P - 11, '3V3', C['3V3'])
    s.text(b.hole('c24')[0] + 4, b.hole('c24')[1] + 1, 'MODE', size=8, anchor='start', fill=C['3V3'], weight=700)

    if ir:
        # 受信モジュール (前から見た図: 左から OUT・GND・VCC)。オス-メス線 3 本で
        px = {'OUT': 290, 'GND': 320, 'VCC': 350}
        py = 104
        s.add(f'<rect x="{px["OUT"] - 16}" y="{py - 34}" width="{px["VCC"] - px["OUT"] + 32}" height="26" rx="3" fill="#1F2937"/>')
        s.add(f'<circle cx="{px["GND"]}" cy="{py - 21}" r="9" fill="#374151" stroke="#111827"/>')
        for name, x in px.items():
            s.add(f'<line x1="{x}" y1="{py - 8}" x2="{x}" y2="{py}" stroke="#9CA3AF" stroke-width="2"/>')
            s.text(x, py - 44, name, size=8, weight=700, family=MONO)
        s.text(px['VCC'] + 24, py - 30, '受信モジュール (前から見た図)', size=9.5, weight=700, anchor='start')
        s.text(px['VCC'] + 24, py - 15, 'リモコンの光が届く向きに付ける', size=9, fill=MUTED, anchor='start')
        route(b, ['a5', (b.hole('a5')[0], 146), (px['OUT'], 146), (px['OUT'], py)], C['IO13'])
        route(b, ['top-:7.5', (px['GND'], py)], C['GND'])
        route(b, ['a8', (b.hole('a8')[0], 158), (px['VCC'], 158), (px['VCC'], py)], C['IO14'])
        tag(s, 214, 146, 'IO13 ← OUT', C['IO13'])
        tag(s, 402, 128, 'IO14 → VCC', C['IO14'])

    usb_cable(s, b, ('USB → PC / モバイルバッテリー', '走らせるときはモバイルバッテリー'))
    legend(s, 190, 724, [('3V3', C['3V3']), ('GND', C['GND']), ('電池 6V', C['VBAT']),
                         ('IO33 左向き', C['IO33']), ('IO25 左速さ', C['IO25']), ('IO26 右向き', C['IO26']),
                         ('IO27 右速さ', C['IO27'])])
    legend(s, 190, 744, [('IO32 Trig', C['IO32']), ('IO35 Echo', C['IO35'])] +
           ([('IO13 ← 受信', C['IO13']), ('IO14 → 受信の電源', C['IO14'])] if ir else []))
    s.save('ir-car-breadboard.svg' if ir else 'car-breadboard.svg')


def car_schematic():
    s = SVG(900, 540, '障害物回避カーの回路図',
            'ESP32 から DRV8835 に左右2組の向き(PHASE)と速さ(ENABLE)を送る。モーターは単3×4本から。HC-SR04 は 3.3V で動かし、Trig と Echo を直接つなぐ。')

    def line(pts, col, w=3):
        d = 'M' + ' L'.join(f'{x} {y}' for x, y in pts)
        s.add(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{w}" stroke-linejoin="round"/>')

    def dot(x, y, col):
        s.add(f'<circle cx="{x}" cy="{y}" r="4.5" fill="{col}"/>')

    def gnd(x, y):
        s.add(f'<path d="M{x - 12} {y} h24 M{x - 8} {y + 5} h16 M{x - 4} {y + 10} h8" stroke="{INK}" stroke-width="1.8"/>')

    ex, ey, ew, eh = 30, 40, 150, 400
    s.add(f'<rect x="{ex}" y="{ey}" width="{ew}" height="{eh}" rx="8" fill="#23262E"/>')
    s.text(ex + ew / 2, ey + 22, 'ESP32', size=14, fill='#fff', weight=700)
    s.text(ex + ew / 2, ey + 40, 'DevKitC-32E', size=10, fill='#C9CDD6')
    P_ = {'3V3': 90, 'IO33': 150, 'IO25': 185, 'IO26': 220, 'IO27': 255, 'GND': 290, 'IO32': 370, 'IO35': 400}
    for name, y in P_.items():
        dot(ex + ew, y, C.get(name, INK))
        s.text(ex + ew - 12, y, name, size=11, fill='#fff', anchor='end', weight=700, family=MONO)
    s.text(ex + ew / 2, ey + eh + 18, 'USB ← モバイルバッテリー', size=10, fill=MUTED)

    dx, dy, dw, dh = 340, 60, 160, 250
    s.add(f'<rect x="{dx}" y="{dy}" width="{dw}" height="{dh}" rx="8" fill="#1C8A4A"/>')
    s.text(dx + dw / 2, dy + 20, 'DRV8835', size=13, fill='#fff', weight=700)
    s.text(dx + dw / 2, dy + 36, 'PHASE/ENABLE モード', size=9, fill='#D7F5E2')
    left = {'VCC': 90, 'MODE': 118, 'AIN1': 150, 'AIN2': 185, 'BIN1': 220, 'BIN2': 255, 'GND': 290}
    right = {'VM': 90, 'AOUT1': 140, 'AOUT2': 175, 'BOUT1': 220, 'BOUT2': 255}
    for name, y in left.items():
        dot(dx, y, '#fff')
        s.text(dx + 10, y, name, size=10, fill='#fff', anchor='start', weight=700, family=MONO)
    for name, y in right.items():
        dot(dx + dw, y, '#fff')
        s.text(dx + dw - 10, y, name, size=10, fill='#fff', anchor='end', weight=700, family=MONO)
    notes = {'AIN1': 'APHASE 左の向き', 'AIN2': 'AENBL 左の速さ', 'BIN1': 'BPHASE 右の向き', 'BIN2': 'BENBL 右の速さ'}
    line([(ex + ew, 90), (dx, 90)], C['3V3'])
    line([(300, 90), (300, 118), (dx, 118)], C['3V3'])
    dot(300, 90, C['3V3'])
    s.text(262, 118, 'MODE=H', size=9, fill=C['3V3'], weight=700)
    for io, pin in (('IO33', 'AIN1'), ('IO25', 'AIN2'), ('IO26', 'BIN1'), ('IO27', 'BIN2')):
        line([(ex + ew, P_[io]), (dx, left[pin])], C[io])
        s.text(262, left[pin] - 9, notes[pin], size=8.5, fill=MUTED)
    # GND: ESP32 と DRV8835 を直結し、電池の − もここへ
    line([(ex + ew, 290), (dx, 290)], C['GND'])

    for label, a, b_, my in (('左', 140, 175, 157), ('右', 220, 255, 237)):
        mx = 600
        line([(dx + dw, a), (mx, a), (mx, my - 16)], C['MOTOR'])
        line([(dx + dw, b_), (mx, b_), (mx, my + 16)], C['MOTOR'])
        s.add(f'<circle cx="{mx}" cy="{my}" r="16" fill="#F4C430" stroke="#B8901A" stroke-width="2"/>')
        s.text(mx, my, 'M', size=13, weight=700)
        s.text(mx + 26, my, f'{label}モーター', size=11, anchor='start', weight=700)

    bx = 720
    line([(dx + dw, 90), (bx, 90), (bx, 100)], C['VBAT'])
    s.add(f'<path d="M{bx - 18} 100 h36 M{bx - 10} 108 h20 M{bx - 18} 116 h36 M{bx - 10} 124 h20" stroke="{INK}" stroke-width="2.2"/>')
    s.text(bx - 28, 100, '+', size=13, weight=700, fill=C['VBAT'])
    s.text(bx - 28, 124, '−', size=13, weight=700)
    s.text(bx + 26, 106, '単3×4本', size=11, anchor='start', weight=700)
    s.text(bx + 26, 121, '約 6V (モーター用)', size=9, anchor='start', fill=MUTED)
    line([(bx, 124), (bx, 330), (318, 330), (318, 290)], C['GND'])
    dot(318, 290, C['GND'])
    s.text(bx + 10, 316, 'GND はすべて 1 本にまとめる', size=10, anchor='start', fill=C['GND'], weight=700)

    hx, hy = 620, 380
    s.add(f'<rect x="{hx}" y="{hy}" width="170" height="140" rx="8" fill="#1E5FB4"/>')
    s.text(hx + 85, hy + 20, 'HC-SR04', size=13, fill='#fff', weight=700)
    s.text(hx + 85, hy + 38, '3〜5.5V 対応品 / GPIO モード', size=8.5, fill='#DCE7FB')
    hp = {'VCC': 410, 'Trig': 440, 'Echo': 470, 'GND': 500}
    for name, y in hp.items():
        dot(hx, y, '#fff')
        s.text(hx + 12, y, name, size=10, fill='#fff', anchor='start', weight=700, family=MONO)
    line([(606, 410), (hx, 410)], C['3V3'])
    tag(s, 592, 410, '3V3', C['3V3'])
    line([(ex + ew, 370), (560, 370), (560, 440), (hx, 440)], C['IO32'])
    line([(ex + ew, 400), (530, 400), (530, 470), (hx, 470)], C['IO35'])
    line([(hx - 26, 500), (hx, 500)], C['GND'])
    gnd(hx - 26, 504)
    s.text(40, 490, 'HC-SR04 を 3.3V で動かすので、Echo も 3.3V で返ってくる → IO35 に直接つないでよい', size=10, anchor='start', fill=C['IO35'], weight=700)
    s.text(40, 508, '(5V で動かすと Echo も 5V になり、ESP32 の入力には入れられない)', size=9.5, anchor='start', fill=MUTED)
    s.save('car-schematic.svg')


def esp32_pinmap():
    s = SVG(820, 300, 'ESP32-DevKitC-32E をブレッドボードに挿したときに使えるピン',
            'USB を左、J1 列を上にして挿すと、J1 列の外側に 1 穴ずつ空く。使えるのは J1 列のピンだけ。')
    ox, oy = 60, 120
    s.add(f'<rect x="{ox - 30}" y="{oy - 30}" width="{19 * 36 + 40}" height="140" rx="8" fill="#23262E"/>')
    s.add(f'<rect x="{ox - 60}" y="{oy + 20}" width="34" height="40" rx="3" fill="#B8BDC7"/>')
    s.text(ox - 43, oy + 76, 'USB', size=9, fill=MUTED)
    s.text(ox + 9 * 36, oy + 40, 'ESP32-DevKitC-32E (上から見た図、USB が左)', size=11, fill='#E5E7EB', weight=700)
    kinds = {
        '5V': '#E11D48', '3V3': '#EA8A00', 'GND': '#374151',
        'IO13': '#16A34A', 'IO14': '#16A34A', 'IO27': '#16A34A', 'IO26': '#16A34A',
        'IO25': '#16A34A', 'IO33': '#16A34A', 'IO32': '#16A34A',
        'IO35': '#0F766E', 'IO34': '#0F766E', 'VN': '#0F766E', 'VP': '#0F766E',
        'IO12': '#B45309', 'EN': '#6B7280', 'CMD': '#9CA3AF', 'SD3': '#9CA3AF', 'SD2': '#9CA3AF',
    }
    for i, name in enumerate(J1):
        x = ox + i * 36
        col = kinds[name]
        s.add(f'<rect x="{x - 15}" y="{oy - 72}" width="30" height="22" rx="4" fill="{col}"/>')
        s.text(x, oy - 61, name.replace('IO', ''), size=10, fill='#fff', weight=700, family=MONO)
        s.add(f'<rect x="{x - 5}" y="{oy - 5}" width="10" height="10" rx="2" fill="#D8C27A"/>')
        s.add(f'<line x1="{x}" y1="{oy - 50}" x2="{x}" y2="{oy - 6}" stroke="{col}" stroke-width="1.5" stroke-dasharray="3 3"/>')
        s.text(x, oy - 88, i + 1, size=8.5, fill=MUTED, family=MONO)
    s.text(ox - 40, oy - 88, '行', size=8.5, fill=MUTED)
    s.text(ox - 40, oy - 61, 'J1', size=10, fill=INK, weight=700)
    for i in range(19):
        x = ox + i * 36
        s.add(f'<rect x="{x - 5}" y="{oy + 85}" width="10" height="10" rx="2" fill="#8C7A3A"/>')
    s.text(ox + 9 * 36, oy + 70, 'J3 列: ブレッドボードに挿すと外側に穴が残らないので、このページの配線では使わない', size=10, fill='#9AA0AC')
    x = 40
    for label, col in (('電源', '#E11D48'), ('GND', '#374151'), ('自由に使える', '#16A34A'), ('入力専用 (ADC1)', '#0F766E'),
                       ('起動時に影響 (避ける)', '#B45309'), ('内部フラッシュ用 (触らない)', '#9CA3AF')):
        s.add(f'<rect x="{x}" y="272" width="14" height="14" rx="3" fill="{col}"/>')
        s.text(x + 20, 279, label, size=10, anchor='start')
        x += 38 + 11 * len(label)
    s.save('esp32-pinmap.svg')


# ------------------------------------------------------------------ 追いかけ型 (CdS 2 個)
IO35_B = '#7C3AED'   # この図だけ、IO34 (CdS A) と見分けるために IO35 を紫にする


def light_follower_breadboard():
    s = SVG(1060, 720, '追いかけ型の首振りガジェットのブレッドボード配線',
            '首振りガジェットに CdS をもう 1 組足す。e24 から e27 へ 3V3、CdS B を c27–c28、10kΩ を b28 と上の − ラインの間、'
            'a14 (IO35) から a28。上の + と − のラインにまたがって 470µF を挿す。')
    b = Board(s, 190, 210)
    b.draw()
    b.esp32({'5V': C['5V'], 'GND': C['GND'], '3V3': C['3V3'], 'IO25': C['IO25'], 'IO34': C['IO34'], 'IO35': IO35_B})

    b.wire('a1', 'top+:1', C['5V'], straight=True)
    b.wire('a6', 'top-:6', C['GND'], straight=True)
    # CdS A (いままでと同じ)
    b.wire('a19', 'a24', C['3V3'], lift=0.6)
    b.cds('c24', 'c25', label='CdS A', below=True)
    b.resistor('b25', 'top-:25.6', label='', label_dx=26, label_dy=2)
    b.wire('a15', 'a25', C['IO34'], lift=1.15)
    # CdS B (足す)
    b.wire('e24', 'e27', C['3V3'], lift=0.5, width=3)
    b.cds('c27', 'c28', label='CdS B', below=True)
    b.resistor('b28', 'top-:28.6', label='', label_dx=26, label_dy=2)
    b.wire('a14', 'a28', IO35_B, lift=1.45)
    s.text(b.hole('a30')[0] + 30, b.hole('top-:29.5')[1] + 26, '10kΩ × 2', size=9, weight=700, anchor='start')
    # 470µF: 上の + と − にまたがって (足の長い方 = + を + ラインへ)
    b.cap_e('top+:19', 'top-:19')

    servo_icon(s, 880, 40)
    kx, ky = 800, 58
    s.add(f'<rect x="{kx}" y="{ky}" width="22" height="46" rx="2" fill="#1F2937"/>')
    s.text(kx + 11, ky - 10, 'メス', size=8, fill=MUTED)
    for i, (col, lab) in enumerate((('#F08A24', '橙 信号'), ('#DC2626', '赤 5V'), ('#6B3E26', '茶 GND'))):
        y = ky + 9 + i * 14
        s.add(f'<path d="M{kx + 22} {y} C{kx + 50} {y} {850} {60 + i * 8} {880} {60 + i * 8}" fill="none" stroke="{col}" stroke-width="3"/>')
        s.text(1012, 52 + i * 14, lab, size=9, fill=col, anchor='start', weight=700)
    pin = lambda i: (kx, ky + 9 + i * 14)
    route(b, ['a11', (b.hole('a11')[0], pin(0)[1]), pin(0)], C['IO25'])
    route(b, ['top+:27.5', (b.hole('top+:27.5')[0], pin(1)[1]), pin(1)], C['5V'])
    route(b, ['top-:29.5', (b.hole('top-:29.5')[0], pin(2)[1]), pin(2)], C['GND'])
    tag(s, b.hole('a11')[0] + 70, pin(0)[1], 'IO25 → 橙 (信号)', C['IO25'])

    tag(s, b.hole('a1')[0] + 36, b.hole('top+:1')[1] - 14, '5V', C['5V'])
    tag(s, b.hole('a6')[0] + 40, b.hole('top-:6')[1] - 14, 'GND', C['GND'])
    s.text(b.hole('e27')[0] + 12, b.hole('e27')[1] + 14, '3V3 を 27 行へ', size=8.5, anchor='start', fill=C['3V3'], weight=700)

    usb_cable(s, b, ('USB → PC', '書き込み・電源・シリアル'))

    # CdS を腕に付けるようす
    ix, iy = 520, 540
    s.add(f'<rect x="{ix}" y="{iy}" width="520" height="164" rx="10" fill="#FFFFFF" stroke="#D6D0C2"/>')
    s.text(ix + 14, iy + 18, 'CdS A・B を抜いて、オス-メス線 4 本で延長し、サーボの腕に付ける', size=10, anchor='start', weight=700)
    hx, hy = ix + 120, iy + 124                      # 腕の付け根
    s.add(f'<rect x="{hx - 70}" y="{hy - 6}" width="140" height="34" rx="6" fill="#2F6FDB"/>')
    s.add(f'<circle cx="{hx}" cy="{hy}" r="9" fill="#F3F4F6" stroke="#9CA3AF"/>')
    s.add(f'<rect x="{hx - 52}" y="{hy - 50}" width="104" height="10" rx="5" fill="#F9FAFB" stroke="#9CA3AF"/>')
    s.add(f'<line x1="{hx}" y1="{hy}" x2="{hx}" y2="{hy - 45}" stroke="#9CA3AF" stroke-width="6"/>')
    s.add(f'<rect x="{hx - 2}" y="{hy - 78}" width="4" height="30" fill="#8B5E3C"/>')   # 仕切り
    for dx, rot, lab in ((-26, -25, 'A'), (26, 25, 'B')):
        cx, cy = hx + dx, hy - 60
        s.add(f'<g transform="rotate({rot} {cx} {cy})"><circle cx="{cx}" cy="{cy}" r="8" fill="#F4E9C8" stroke="#B89B4E"/>'
              f'<path d="M{cx - 4} {cy - 2} q2 -3 4 0 t4 0 M{cx - 4} {cy + 2} q2 -3 4 0 t4 0" fill="none" stroke="#B5462C" stroke-width="1.1"/></g>')
        s.text(cx + dx * 0.9, cy - 6, lab, size=10, weight=700)
    s.text(hx + 2, hy - 86, '厚紙の仕切り', size=8.5, fill='#8B5E3C', anchor='start')
    s.text(ix + 250, iy + 54, 'A と B を少し外向き (左右に 20〜30°) に開いて貼り、', size=9.5, anchor='start')
    s.text(ix + 250, iy + 70, '間に厚紙を立てる。光が片側から来ると片方だけ影になる', size=9.5, anchor='start')
    s.text(ix + 250, iy + 96, 'A の 2 本 → c24 と c25', size=9.5, anchor='start', fill=C['IO34'], weight=700)
    s.text(ix + 250, iy + 112, 'B の 2 本 → c27 と c28', size=9.5, anchor='start', fill=IO35_B, weight=700)
    s.text(ix + 250, iy + 136, '首振りでケーブルが引っかからない長さに', size=8.5, anchor='start', fill=MUTED)

    legend(s, 190, 572, [('5V', C['5V']), ('3V3', C['3V3']), ('GND', C['GND'])])
    legend(s, 190, 594, [('IO25 サーボ', C['IO25']), ('IO34 CdS A', C['IO34'])])
    legend(s, 190, 616, [('IO35 CdS B', IO35_B)])
    s.save('light-follower-breadboard.svg')


# ------------------------------------------------------------------ ワイヤレス操縦
GROVE = {'X': ('#EAB308', '黄'), 'Y': ('#F3F4F6', '白'), 'VCC': ('#DC2626', '赤'), 'GND': ('#111827', '黒')}
JOY_ROWS = {'X': 24, 'Y': 25, 'VCC': 26, 'GND': 27}   # 変換ケーブルのピンヘッダーを c24〜c27 に


def grove_wire(s, pts, key, width=3.4):
    """Grove ケーブルの 1 本。白い線も見えるよう、細い灰色のふちを付ける"""
    col = GROVE[key][0]
    d = 'M' + ' L'.join(f'{x:.1f} {y:.1f}' for x, y in pts)
    s.add(f'<path d="{d}" fill="none" stroke="#6B7280" stroke-width="{width + 1.6}" stroke-linecap="round" stroke-linejoin="round"/>')
    s.add(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"/>')


def joystick_icon(s, x, y):
    """Grove ジョイスティックを上から見た絵。左の辺に Grove のソケット。ソケットの 4 本の y を返す"""
    s.add(f'<rect x="{x}" y="{y}" width="150" height="150" rx="8" fill="#2B6CB0" stroke="#1E4E80"/>')
    s.add(f'<circle cx="{x + 82}" cy="{y + 75}" r="46" fill="#1F2937"/>')
    s.add(f'<circle cx="{x + 82}" cy="{y + 75}" r="30" fill="#4B5563" stroke="#111827" stroke-width="2"/>')
    s.add(f'<circle cx="{x + 82}" cy="{y + 75}" r="17" fill="#6B7280"/>')
    for ang, lab in ((0, 'X+'), (90, 'Y+')):
        ex = x + 82 + 62 * math.cos(math.radians(-ang))
        ey = y + 75 + 62 * math.sin(math.radians(-ang))
        s.text(ex, ey, lab, size=8.5, fill='#DCE7FB', weight=700, family=MONO)
    s.text(x + 82, y + 165, 'Grove ジョイスティック', size=10, weight=700)
    s.text(x + 82, y + 180, '向きは joystick_test で確かめる', size=8.5, fill=MUTED)
    sx, sy = x - 14, y + 44
    s.add(f'<rect x="{sx}" y="{sy}" width="20" height="62" rx="3" fill="#F3F4F6" stroke="#9CA3AF"/>')
    return {k: sy + 10 + i * 14 for i, k in enumerate(('X', 'Y', 'VCC', 'GND'))}, sx


def rc_controller_breadboard():
    s = SVG(1100, 580, 'ワイヤレス操縦のコントローラーの配線',
            'Freenove ESP32 を 1〜20 行に挿す。a5 (3V3) から上の + ライン、a7 (GND) から上の − ライン。'
            'ジョイスティックの変換ケーブルを c24〜c27 (黄 X・白 Y・赤 VCC・黒 GND) に挿し、a16 (IO34) → a24、a15 (IO35) → a25、'
            '+ ライン → a26、− ライン → a27。')
    b = Board(s, 190, 150)
    b.draw()
    b.freenove({'3V3': C['3V3'], 'GND': C['GND'], 'IO34': C['IO34'], 'IO35': IO35_B})

    # 3V3 と GND を上の電源ラインに (このコントローラーでは + ラインが 3.3V)
    b.wire('a5', 'top+:5', C['3V3'], straight=True)
    b.wire('a7', 'top-:7', C['GND'], straight=True)
    b.wire('a16', 'a24', C['IO34'], lift=0.95)
    b.wire('a15', 'a25', IO35_B, lift=1.3)
    b.wire('top+:26.5', 'a26', C['3V3'], straight=True)
    b.wire('top-:27.5', 'a27', C['GND'], straight=True)

    # 変換ケーブルのピンヘッダー (c24〜c27) とジョイスティック
    x24, yc = b.hole('c24')
    x27, _ = b.hole('c27')
    s.add(f'<rect x="{x24 - 8}" y="{yc - 7}" width="{x27 - x24 + 16}" height="14" rx="2" fill="#20232A"/>')
    pins, sx = joystick_icon(s, 900, 190)
    for i, key in enumerate(('GND', 'VCC', 'Y', 'X')):          # 右の穴ほど浅く曲げると交差しない
        px, py = b.hole(f'c{JOY_ROWS[key]}')
        turn_y = py + (0.55 + i * 0.38) * P
        grove_wire(s, [(px, py), (px, turn_y), (sx - 40 - i * 8, turn_y), (sx - 40 - i * 8, pins[key]), (sx, pins[key])], key)
        s.add(f'<circle cx="{px}" cy="{py}" r="3.2" fill="{GROVE[key][0]}" stroke="#374151" stroke-width="1"/>')
    s.text(x27 + 14, yc, 'ヘッダー', size=8.5, weight=700, anchor='start')
    s.text(840, b.oy + 9.6 * P, '変換ケーブル', size=9.5, weight=700)
    s.text(840, b.oy + 10.4 * P, '(Grove を切って', size=8.5, fill=MUTED)
    s.text(840, b.oy + 11.1 * P, 'ピンヘッダーに)', size=8.5, fill=MUTED)
    gx = 900 + 160
    for i, key in enumerate(('X', 'Y', 'VCC', 'GND')):
        col, name = GROVE[key]
        y = 410 + i * 16
        s.add(f'<rect x="{gx - 150}" y="{y - 3}" width="18" height="6" rx="3" fill="{col}" stroke="#6B7280" stroke-width=".8"/>')
        s.text(gx - 126, y, f'{name}  {key}', size=9.5, anchor='start', weight=700)

    tag(s, b.hole('a5')[0] + 36, b.hole('top+:5')[1] - 14, '3V3', C['3V3'])
    tag(s, b.hole('a7')[0] + 44, b.hole('top-:7')[1] + 12, 'GND', C['GND'])
    s.text(b.hole('a26')[0] - 4, b.hole('top+:26.5')[1] - 16, '+ ラインは 3.3V', size=9, fill=C['3V3'], weight=700, anchor='end')

    usb_cable(s, b, ('USB', 'PC かモバイルバッテリー'))
    legend(s, 190, 500, [('3V3', C['3V3']), ('GND', C['GND']), ('IO34 ← X (黄)', C['IO34']), ('IO35 ← Y (白)', IO35_B)])
    s.text(190, 528, 'このコントローラーでは上の + ラインに 3.3V を流す。5V はどこにもつながない', size=10, anchor='start', fill='#B91C1C', weight=700)
    s.save('rc-controller-breadboard.svg')


def rc_system():
    s = SVG(900, 360, 'ワイヤレス操縦のしくみ',
            'コントローラー (Freenove ESP32 + ジョイスティック) が 1 秒に 20 回、X・Y・押した回数を ESP-NOW で送る。'
            '車 (障害物回避カーの配線のまま) は 1 秒に 10 回、距離とモードを送り返す。0.3 秒届かなければ車は止まる。')
    # コントローラー
    cx, cy, cw, ch = 30, 50, 250, 230
    s.add(f'<rect x="{cx}" y="{cy}" width="{cw}" height="{ch}" rx="12" fill="#FFFFFF" stroke="#D6D0C2"/>')
    s.text(cx + cw / 2, cy + 22, 'コントローラー', size=14, weight=700)
    s.text(cx + cw / 2, cy + 41, 'Freenove ESP32 + ジョイスティック', size=9.5, fill=MUTED)
    s.add(f'<rect x="{cx + 20}" y="{cy + 60}" width="96" height="96" rx="8" fill="#2B6CB0"/>')
    s.add(f'<circle cx="{cx + 68}" cy="{cy + 108}" r="30" fill="#1F2937"/><circle cx="{cx + 68}" cy="{cy + 108}" r="18" fill="#6B7280"/>')
    s.text(cx + 130, cy + 76, 'X → IO34', size=10, anchor='start', fill=C['IO34'], weight=700, family=MONO)
    s.text(cx + 130, cy + 94, 'Y → IO35', size=10, anchor='start', fill=IO35_B, weight=700, family=MONO)
    s.text(cx + 130, cy + 112, '押し込み = X が', size=9, anchor='start', fill=MUTED)
    s.text(cx + 130, cy + 126, '3.3V いっぱい', size=9, anchor='start', fill=MUTED)
    for i, (col, lab) in enumerate((('#22C55E', '緑: つながっている'), ('#EAB308', '黄: 前進ストップ中'), ('#EF4444', '赤の点滅: 返事がない'))):
        y = cy + 176 + i * 17
        s.add(f'<circle cx="{cx + 28}" cy="{y}" r="6" fill="{col}"/>')
        s.text(cx + 42, y, lab, size=9.5, anchor='start')
    # 車
    vx, vy, vw, vh = 620, 50, 250, 230
    s.add(f'<rect x="{vx}" y="{vy}" width="{vw}" height="{vh}" rx="12" fill="#FFFFFF" stroke="#D6D0C2"/>')
    s.text(vx + vw / 2, vy + 22, '車', size=14, weight=700)
    s.text(vx + vw / 2, vy + 41, 'ESP32-DevKitC + DRV8835 + HC-SR04', size=9.5, fill=MUTED)
    s.add(f'<rect x="{vx + 30}" y="{vy + 70}" width="140" height="64" rx="10" fill="#F4C430" stroke="#B8901A"/>')
    for wx in (vx + 22, vx + 170):
        s.add(f'<rect x="{wx}" y="{vy + 78}" width="16" height="48" rx="4" fill="#1F2937"/>')
    s.add(f'<rect x="{vx + 182}" y="{vy + 84}" width="46" height="36" rx="4" fill="#1E5FB4"/>')
    s.add(f'<circle cx="{vx + 194}" cy="{vy + 102}" r="8" fill="#D1D5DB"/><circle cx="{vx + 216}" cy="{vy + 102}" r="8" fill="#D1D5DB"/>')
    s.text(vx + 100, vy + 102, '配線はそのまま', size=10, weight=700)
    s.text(vx + 20, vy + 160, '前後 = Y、曲がる = X', size=10, anchor='start')
    s.text(vx + 20, vy + 178, '左 = 前後 + 曲がる、右 = 前後 − 曲がる', size=9.5, anchor='start', fill=MUTED)
    s.text(vx + 20, vy + 200, 'ぶつからないモード:', size=10, anchor='start', weight=700)
    s.text(vx + 20, vy + 217, '20cm より近いと前進だけ止める', size=9.5, anchor='start', fill=MUTED)

    # 電波
    def arrow(y, x1, x2, col):
        d = 1 if x2 > x1 else -1
        s.add(f'<line x1="{x1}" y1="{y}" x2="{x2 - d * 10}" y2="{y}" stroke="{col}" stroke-width="3" stroke-dasharray="7 5"/>')
        s.add(f'<path d="M{x2} {y} l{-d * 14} -8 l0 16 z" fill="{col}"/>')
    arrow(110, cx + cw + 12, vx - 12, '#0F766E')
    s.text(450, 88, 'ESP-NOW  20 回/秒', size=11, weight=700, fill='#0F766E')
    s.text(450, 130, 'x (-100〜100), y (-100〜100), 押した回数', size=9.5, fill=MUTED, family=MONO)
    arrow(210, vx - 12, cx + cw + 12, '#B45309')
    s.text(450, 188, '10 回/秒', size=11, weight=700, fill='#B45309')
    s.text(450, 230, '距離 (cm), モード, 前進ストップ中か', size=9.5, fill=MUTED, family=MONO)
    s.text(450, 302, 'ルーターは要らない。宛先を決めずに全員へ送り (ブロードキャスト)、GROUP_ID が同じものだけ受け取る', size=10, weight=700)
    s.text(450, 324, '車は 0.3 秒コントローラーの電波が届かなければ止まる (フェイルセーフ)', size=10, fill='#B91C1C', weight=700)
    s.save('rc-system.svg')


def grove_adapter():
    s = SVG(900, 300, 'Grove ケーブルからジョイスティック用の変換ケーブルを作る',
            'Grove ケーブル (両端コネクタ) を真ん中で切ると 2 本できる。切った側の 4 本の皮をむいて予備はんだし、'
            '1×40 のピンヘッダーから切り出した 4 ピンにはんだ付けする。並びは 黄・白・赤・黒。')
    order = ('X', 'Y', 'VCC', 'GND')

    def plug(x, y):
        s.add(f'<rect x="{x}" y="{y - 22}" width="30" height="44" rx="4" fill="#F3F4F6" stroke="#9CA3AF"/>')
        s.add(f'<rect x="{x + 6}" y="{y - 16}" width="18" height="32" rx="2" fill="#E5E7EB" stroke="#9CA3AF"/>')

    def bundle(x1, x2, y):
        for i, k in enumerate(order):
            grove_wire(s, [(x1, y - 9 + i * 6), (x2, y - 9 + i * 6)], k, width=3.4)

    # 1. 切る
    s.text(30, 30, '1. 真ん中で切る (1 本から 2 本できる)', size=12, weight=700, anchor='start')
    y = 90
    plug(40, y)
    bundle(70, 380, y)
    plug(380, y)
    s.add(f'<line x1="225" y1="{y - 30}" x2="225" y2="{y + 30}" stroke="#B91C1C" stroke-width="2" stroke-dasharray="5 4"/>')
    s.text(225, y + 44, 'ここで切る', size=10, fill='#B91C1C', weight=700)
    # 2. むいて予備はんだ
    s.text(470, 30, '2. 先を 5mm むいて、ねじって、はんだを薄くのせる', size=12, weight=700, anchor='start')
    plug(480, y)
    bundle(510, 700, y)
    for i, k in enumerate(order):
        yy = y - 9 + i * 6
        s.add(f'<line x1="700" y1="{yy}" x2="{722 + i * 4}" y2="{yy + (i - 1.5) * 6}" stroke="#A3A3A3" stroke-width="2.6" stroke-linecap="round"/>')
    s.text(790, y - 6, '芯線に', size=9.5, anchor='start', fill=MUTED)
    s.text(790, y + 9, '予備はんだ', size=9.5, anchor='start', fill=MUTED)
    # 3. ピンヘッダーに付ける
    s.text(30, 160, '3. ピンヘッダーを 4 ピン分に折って、1 本ずつはんだ付け。むき出しの所をテープで巻く', size=12, weight=700, anchor='start')
    y2 = 225
    plug(40, y2)
    bundle(70, 300, y2)
    hx = 330
    s.add(f'<rect x="{hx - 6}" y="{y2 - 30}" width="20" height="60" rx="2" fill="#20232A"/>')
    for i, k in enumerate(order):
        py = y2 - 22 + i * 14.5
        grove_wire(s, [(300, y2 - 9 + i * 6), (316, py), (hx - 6, py)], k, width=3)
        s.add(f'<rect x="{hx + 14}" y="{py - 1.6}" width="34" height="3.2" fill="#C9A227"/>')
        col, name = GROVE[k]
        s.text(hx + 58, py, f'{name} → {k}', size=10, anchor='start', weight=700, family=MONO)
    s.text(hx + 150, y2 - 18, '並びは コネクタと同じ 黄・白・赤・黒 (ジョイスティックでは X・Y・VCC・GND)', size=10, anchor='start')
    s.text(hx + 150, y2 + 2, 'できたら テスターの導通ブザーで 4 本とも鳴るか、', size=10, anchor='start')
    s.text(hx + 150, y2 + 18, '隣どうしで鳴らない (ショートしていない) かを確かめる', size=10, anchor='start')
    s.text(hx + 150, y2 + 42, 'ブレッドボードに挿したヘッダーの上ではんだ付けすると、ピンが熱で動かない', size=9.5, anchor='start', fill=MUTED)
    s.save('grove-adapter.svg')


def freenove_pinmap():
    s = SVG(900, 330, 'Freenove ESP32 WROOM と DevKitC の上の列のピンの比べ',
            'どちらも USB を左にして 1 行目から挿したとき、上の列 (a 列の隣) に並ぶピン。'
            'Freenove は 20 ピンで、IO13 から 3V3 までが DevKitC より 1 行右にずれる。')
    ox, step = 150, 36
    kinds = {
        '5V': '#E11D48', '3V3': '#EA8A00', 'GND': '#374151',
        'IO13': '#16A34A', 'IO14': '#16A34A', 'IO27': '#16A34A', 'IO26': '#16A34A',
        'IO25': '#16A34A', 'IO33': '#16A34A', 'IO32': '#16A34A',
        'IO35': '#0F766E', 'IO34': '#0F766E', 'VN': '#0F766E', 'VP': '#0F766E',
        'IO12': '#B45309', 'EN': '#6B7280', 'CMD': '#9CA3AF', 'SD3': '#9CA3AF', 'SD2': '#9CA3AF',
    }
    for i in range(20):
        s.text(ox + i * step, 40, i + 1, size=9, fill=MUTED, family=MONO)
    s.text(ox - 50, 40, '行', size=9, fill=MUTED)

    def row(y, pins, title, sub):
        s.add(f'<rect x="{ox - 26}" y="{y - 26}" width="{20 * step + 14}" height="52" rx="8" fill="#23262E"/>')
        s.text(ox - 34, y - 7, title, size=11, weight=700, anchor='end')
        s.text(ox - 34, y + 10, sub, size=9, fill=MUTED, anchor='end')
        for i, name in enumerate(pins):
            x = ox + i * step
            col = kinds[name]
            s.add(f'<rect x="{x - 15}" y="{y - 11}" width="30" height="22" rx="4" fill="{col}"/>')
            s.text(x, y, name.replace('IO', ''), size=10, fill='#fff', weight=700, family=MONO)

    row(90, FN_TOP, 'Freenove', '20 ピン・USB-C')
    row(190, J1, 'DevKitC', '19 ピン・micro-B')
    # 同じピンを線で結ぶ (13〜3V3 は 1 行ずれる)
    for i, name in enumerate(J1):
        if name in ('5V', 'CMD', 'SD3', 'SD2'):
            continue
        j = i + 1
        s.add(f'<line x1="{ox + i * step}" y1="{178}" x2="{ox + j * step}" y2="{102}" stroke="#9CA3AF" stroke-width="1.4" stroke-dasharray="3 3"/>')
    s.add(f'<rect x="{ox + 12 * step - 190}" y="129" width="380" height="22" rx="11" fill="#FBFAF7"/>')
    s.text(ox + 12 * step, 140, 'IO13 から 3V3 までは同じ並びで、Freenove が 1 行右', size=10.5, weight=700, fill=INK)
    x = 30
    for label, col in (('電源', '#E11D48'), ('GND', '#374151'), ('自由に使える', '#16A34A'), ('入力専用 (ADC1)', '#0F766E'),
                       ('起動時に影響 (避ける)', '#B45309'), ('内部フラッシュ用 (触らない)', '#9CA3AF')):
        s.add(f'<rect x="{x}" y="{246}" width="14" height="14" rx="3" fill="{col}"/>')
        s.text(x + 20, 253, label, size=10, anchor='start')
        x += 38 + 11 * len(label)
    s.text(30, 290, 'このノートの配線表は DevKitC の行番号。Freenove で組むときは、ESP32 側の穴だけ 1 行右にずらす (例: a6 → a7、a19 → a20)。', size=10, anchor='start', weight=700)
    s.text(30, 310, '部品側 (21 行目より右) の穴はそのまま。5V は Freenove でも 1 行目 (2 行目も 5V)。', size=10, anchor='start', fill=MUTED)
    s.save('freenove-pinmap.svg')


# ------------------------------------------------------------------ 針で指す温度計
C['IO14'] = '#A16207'
C['IO13'] = '#0891B2'
MOTOR_WIRE = {'赤': '#DC2626', '橙': '#F97316', '黄': '#EAB308', 'ピンク': '#EC4899', '青': '#2563EB'}
ULN_E = ['E', '7B', '6B', '5B', '4B', '3B', '2B', '1B']          # e 列 (23 → 30 行)。切り欠きは右
ULN_F = ['COM', '7C', '6C', '5C', '4C', '3C', '2C', '1C']        # f 列


def motor_icon(s, cx, cy, needle=True):
    s.add(f'<rect x="{cx - 52}" y="{cy - 8}" width="104" height="16" rx="8" fill="#C7CBD1" stroke="#8B919C"/>')
    for dx in (-44, 44):
        s.add(f'<circle cx="{cx + dx}" cy="{cy}" r="3.5" fill="#FBFAF7"/>')
    s.add(f'<circle cx="{cx}" cy="{cy}" r="34" fill="#D9DCE1" stroke="#8B919C" stroke-width="1.5"/>')
    s.add(f'<circle cx="{cx}" cy="{cy - 12}" r="7" fill="#B8913A" stroke="#7A5E1E"/>')
    if needle:
        s.add(f'<path d="M{cx} {cy - 12} L{cx + 48} {cy - 46}" stroke="#B91C1C" stroke-width="3.5" stroke-linecap="round"/>')
        s.text(cx + 58, cy - 54, '紙の針', size=9, fill='#B91C1C', weight=700, anchor='start')
    s.text(cx, cy + 14, '28BYJ-48', size=10, weight=700)
    s.add(f'<rect x="{cx - 22}" y="{cy + 26}" width="44" height="12" rx="2" fill="#2563EB" opacity=".85"/>')


def needle_breadboard():
    s = SVG(1100, 700, '針で指す温度計のブレッドボード配線',
            'Freenove ESP32 を 1〜20 行、ULN2003AN を 23〜30 行に切り欠きを右にして挿す。IO14・IO27・IO26・IO25 を 1B〜4B へ。'
            '上の − ラインから a23 (E)。上の + ライン (5V) を右端で下の + ラインにつなぎ、j23 (COM) へ。'
            'モーターの赤を h23、橙・黄・ピンク・青を h27〜h30。サーミスターを c21–c22、10kΩ を b22–d23、IO34 を a22。')
    b = Board(s, 190, 170)
    b.draw()
    b.freenove({'5V': C['5V'], 'GND': C['GND'], '3V3': C['3V3'], 'IO14': C['IO14'], 'IO27': C['IO27'],
                'IO26': C['IO26'], 'IO25': C['IO25'], 'IO34': C['IO34']})
    b.dip(range(23, 31), ULN_E, ULN_F, 'ULN2003AN')

    b.wire('a1', 'top+:1', C['5V'], straight=True)
    b.wire('a7', 'top-:7', C['GND'], straight=True)
    # IO → 1B〜4B (外側ほど遠く。入れ子にして交差させない)
    b.wire('a9', 'a30', C['IO14'], lift=1.75)
    b.wire('a10', 'a29', C['IO27'], lift=1.45)
    b.wire('a11', 'a28', C['IO26'], lift=1.15)
    b.wire('a12', 'a27', C['IO25'], lift=0.85)
    # サーミスター: 3V3 (a20) → a21、c21–c22、10kΩ b22–d23 (23 行は GND)、IO34 → a22
    b.wire('a16', 'a22', C['IO34'], lift=0.6)
    b.wire('a20', 'a21', C['3V3'], lift=0.35, width=3)
    b.thermistor('c21', 'c22', label='')
    b.resistor('b22', 'd23', label='')
    for text, (tx, ty), target in (('サーミスター (c21–c22)', (470, 36), b.hole('c21')), ('10kΩ (b22–d23)', (690, 36), b.hole('d23'))):
        s.add(f'<line x1="{tx}" y1="{ty + 9}" x2="{target[0] + 10}" y2="{target[1] + 8}" stroke="#6B7280" stroke-width="1" stroke-dasharray="3 3"/>')
        s.add(f'<rect x="{tx - 62}" y="{ty - 10}" width="124" height="20" rx="10" fill="#FFFFFF" stroke="#9CA3AF"/>')
        s.text(tx, ty, text, size=9.5, weight=700)
    # E (23 行) に GND
    b.wire('top-:23.5', 'a23', C['GND'], straight=True)
    # 上の + (5V) を右端で下の + へ。下の + から j23 (COM)
    xr = b.ox + 29 * P + 1.7 * P
    route(b, ['top+:29.5', (xr, b.hole('top+:29.5')[1]), (xr, b.hole('bot+:29.5')[1]), 'bot+:29.5'], C['5V'])
    b.wire('bot+:23.5', 'j23', C['5V'], straight=True)

    # モーター: コネクタの穴にオス-オス線を挿して h23 (赤) と h27〜h30 へ
    order = (('赤', 'h23'), ('橙', 'h27'), ('黄', 'h28'), ('ピンク', 'h29'), ('青', 'h30'))
    kx0, ky = 650, 520
    s.add(f'<rect x="{kx0 - 12}" y="{ky - 8}" width="{4 * 20 + 24}" height="20" rx="3" fill="#F3F4F6" stroke="#9CA3AF"/>')
    for i, (name, hole) in enumerate(order):
        kx = kx0 + i * 20
        hx, hy = b.hole(hole)
        col = MOTOR_WIRE[name]
        s.add(f'<path d="M{kx} {ky} L{hx} {hy}" stroke="#FFFFFF" stroke-width="6" stroke-linecap="round" opacity=".85"/>')
        s.add(f'<path d="M{kx} {ky} L{hx} {hy}" stroke="{col}" stroke-width="3.6" stroke-linecap="round"/>')
        s.add(f'<circle cx="{hx}" cy="{hy}" r="3.2" fill="{col}" stroke="#fff"/>')
        s.add(f'<rect x="{kx - 5}" y="{ky - 4}" width="10" height="10" rx="1" fill="#374151"/>')
        s.text(kx, ky + 20 + (i % 2) * 12, name, size=8.5, fill=col, weight=700)
    mcx, mcy = 960, ky + 96
    for i in range(5):
        s.add(f'<path d="M{kx0 + 92} {ky + 2 + (i - 2) * 3} C{kx0 + 150} {ky + (i - 2) * 3} {mcx - 60} {mcy - 40 + i * 3} {mcx - 34} {mcy - 8 + i * 3}" '
              f'fill="none" stroke="{MOTOR_WIRE[order[i][0]]}" stroke-width="2"/>')
    motor_icon(s, mcx, mcy)
    s.text(kx0 + 40, ky + 58, 'コネクタの穴の並びは、線の色で確かめる', size=9, fill=MUTED)

    tag(s, b.hole('a1')[0] + 36, b.hole('top+:1')[1] - 14, '5V', C['5V'])
    tag(s, b.hole('a7')[0] + 40, b.hole('top-:7')[1] + 12, 'GND', C['GND'])
    s.text(xr + 8, (b.hole('top+:29.5')[1] + b.hole('bot+:29.5')[1]) / 2 - 8, '5V を', size=9, fill=C['5V'], weight=700, anchor='start')
    s.text(xr + 8, (b.hole('top+:29.5')[1] + b.hole('bot+:29.5')[1]) / 2 + 8, '下の + へ', size=9, fill=C['5V'], weight=700, anchor='start')
    s.text(b.hole('top-:23.5')[0] + 8, b.hole('top-:23.5')[1] + 16, 'E', size=9, fill=C['GND'], weight=700, anchor='start')

    usb_cable(s, b, ('USB', 'PC かモバイルバッテリー'))
    legend(s, 190, 610, [('5V', C['5V']), ('3V3', C['3V3']), ('GND', C['GND']), ('IO34 温度', C['IO34'])])
    legend(s, 190, 634, [('IO14 → 1B', C['IO14']), ('IO27 → 2B', C['IO27']), ('IO26 → 3B', C['IO26']), ('IO25 → 4B', C['IO25'])])
    s.text(190, 664, 'ULN2003AN は切り欠き (半円のくぼみ) を右 (30 行側) に向ける', size=10, anchor='start', weight=700)
    s.save('needle-breadboard.svg')


def needle_schematic():
    s = SVG(900, 440, '針で指す温度計の回路図',
            'ESP32 の IO14・IO27・IO26・IO25 を ULN2003AN の 1B〜4B に。1C〜4C をモーターの青・ピンク・黄・橙に。'
            'モーターの赤と COM は 5V、E は GND。3V3 からサーミスターと 10kΩ で分圧し、中点を IO34 へ。')

    def line(pts, col, w=3):
        d = 'M' + ' L'.join(f'{x} {y}' for x, y in pts)
        s.add(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{w}" stroke-linejoin="round"/>')

    def dot(x, y, col):
        s.add(f'<circle cx="{x}" cy="{y}" r="4.5" fill="{col}"/>')

    ex, ey, ew, eh = 30, 40, 150, 360
    s.add(f'<rect x="{ex}" y="{ey}" width="{ew}" height="{eh}" rx="8" fill="#15171C"/>')
    s.text(ex + ew / 2, ey + 22, 'ESP32', size=14, fill='#fff', weight=700)
    s.text(ex + ew / 2, ey + 40, 'Freenove WROOM', size=10, fill='#C9CDD6')
    pins = {'5V': 80, 'IO14': 130, 'IO27': 165, 'IO26': 200, 'IO25': 235, 'GND': 280, '3V3': 320, 'IO34': 365}
    for name, y in pins.items():
        dot(ex + ew, y, C.get(name, INK))
        s.text(ex + ew - 12, y, name, size=11, fill='#fff', anchor='end', weight=700, family=MONO)

    ux, uy, uw, uh = 330, 100, 170, 210
    s.add(f'<rect x="{ux}" y="{uy}" width="{uw}" height="{uh}" rx="8" fill="#202329"/>')
    s.text(ux + uw / 2, uy + 20, 'ULN2003AN', size=13, fill='#fff', weight=700)
    s.text(ux + uw / 2, uy + 36, '電流を流す役 (7 回路)', size=9, fill='#C9CDD6')
    bins = {'1B': 130, '2B': 165, '3B': 200, '4B': 235, 'E': 280}
    couts = {'1C': 130, '2C': 165, '3C': 200, '4C': 235, 'COM': 280}
    for name, y in bins.items():
        dot(ux, y, '#fff')
        s.text(ux + 10, y, name, size=10, fill='#fff', anchor='start', weight=700, family=MONO)
    for name, y in couts.items():
        dot(ux + uw, y, '#fff')
        s.text(ux + uw - 10, y, name, size=10, fill='#fff', anchor='end', weight=700, family=MONO)
    for io, pin in (('IO14', '1B'), ('IO27', '2B'), ('IO26', '3B'), ('IO25', '4B')):
        line([(ex + ew, pins[io]), (ux, bins[pin])], C[io])
    line([(ex + ew, 280), (ux, 280)], C['GND'])

    # モーター (コイル 2 つ、まん中の赤が 5V)
    mx = 690
    coil_y = {'青': 130, 'ピンク': 165, '黄': 200, '橙': 235}
    for (cname, out) in (('青', '1C'), ('ピンク', '2C'), ('黄', '3C'), ('橙', '4C')):
        y = coil_y[cname]
        line([(ux + uw, couts[out]), (mx - 40, y)], MOTOR_WIRE[cname])
        s.text(mx - 46, y - 10, cname, size=9, fill=MOTOR_WIRE[cname], weight=700, anchor='end')
    # コイルは ピンク–橙 と 黄–青 の 2 組 (まん中が赤)。図はつなぎ方だけを示す
    s.add(f'<rect x="{mx - 40}" y="{110}" width="150" height="145" rx="10" fill="#EEF0F3" stroke="#9CA3AF"/>')
    s.text(mx + 35, 128, '28BYJ-48', size=12, weight=700)
    s.text(mx + 35, 146, '青 → ピンク → 黄 → 橙 の順に', size=9, fill=MUTED)
    s.text(mx + 35, 160, '1 本ずつ電気を流すと回る', size=9, fill=MUTED)
    for y in (130, 165, 200, 235):
        dot(mx - 40, y, '#6B7280')
    s.text(mx + 35, 196, 'コイル 2 つ', size=9.5, weight=700)
    s.text(mx + 35, 212, '(ピンク–橙、黄–青)', size=9, fill=MUTED)
    s.text(mx + 35, 236, 'まん中の赤 = 5V', size=9.5, weight=700, fill=MOTOR_WIRE['赤'])
    # 5V: ESP32 5V → COM、モーターの赤
    line([(ex + ew, 80), (620, 80), (620, 280), (ux + uw, 280)], C['5V'])
    line([(620, 80), (mx + 35, 80), (mx + 35, 110)], MOTOR_WIRE['赤'])
    dot(620, 80, C['5V'])
    s.text(560, 70, '5V', size=10, fill=C['5V'], weight=700)
    s.text(600, 328, 'COM にも 5V (中のダイオードがコイルの逆電圧を逃がす)', size=9, fill=MUTED, anchor='middle')

    # サーミスター
    nx = 300
    line([(ex + ew, 320), (nx, 320), (nx, 330)], C['3V3'])
    s.add(f'<rect x="{nx - 7}" y="330" width="14" height="22" rx="3" fill="#D7E8EF" stroke="#7FA7B8"/>')
    s.add(f'<path d="M{nx - 14} 356 l28 -30" stroke="{INK}" stroke-width="1.4"/>')
    s.text(nx + 20, 338, 'サーミスター (25℃ で 10kΩ)', size=10, anchor='start', weight=700)
    line([(nx, 352), (nx, 365), (ex + ew, 365)], C['IO34'])
    dot(nx, 365, C['IO34'])
    line([(nx, 365), (nx, 372)], C['GND'])
    s.add(f'<path d="M{nx} 372 l-6 3 l12 5 l-12 5 l12 5 l-6 3 l0 4" fill="none" stroke="{INK}" stroke-width="1.6"/>')
    s.text(nx + 14, 384, '10kΩ', size=10, anchor='start', weight=700)
    s.add(f'<path d="M{nx - 12} 400 h24 M{nx - 8} 405 h16 M{nx - 4} 410 h8" stroke="{INK}" stroke-width="1.8"/>')
    line([(nx, 397), (nx, 400)], C['GND'])
    s.text(470, 360, '温かい → サーミスターの抵抗が下がる → IO34 の電圧が上がる', size=10, anchor='start', weight=700)
    s.text(470, 378, '温度 = 1 ÷ (1/298.15 + ln(R/10k) ÷ 3960) − 273.15  (B 定数の式)', size=9.5, anchor='start', fill=MUTED)
    s.save('needle-schematic.svg')


def needle_dial():
    """実寸で印刷する目盛り板 (mm 単位)。半円で 10〜40℃"""
    W, H, cx, cy, R = 130, 92, 65, 68, 52
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}mm" height="{H}mm" '
             f'font-family="{FONT}" role="img" aria-labelledby="t d">',
             '<title id="t">温度計の目盛り板 (印刷用)</title>',
             '<desc id="d">半円の目盛り。左端 10℃、右端 40℃、1℃ ごとに目盛り。中心にモーターの軸を通す。100% の大きさで印刷する。</desc>',
             f'<rect width="{W}" height="{H}" fill="#fff"/>',
             f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" fill="none" stroke="#9CA3AF" stroke-width=".3" stroke-dasharray="2 1.5"/>']
    # 色の帯 (寒い・ちょうどいい・暑い)
    def arc(t0, t1, r, col, w):
        a0 = math.pi * (1 - (t0 - 10) / 30)
        a1 = math.pi * (1 - (t1 - 10) / 30)
        x0, y0 = cx + r * math.cos(a0), cy - r * math.sin(a0)
        x1, y1 = cx + r * math.cos(a1), cy - r * math.sin(a1)
        parts.append(f'<path d="M{x0:.2f} {y0:.2f} A{r} {r} 0 0 1 {x1:.2f} {y1:.2f}" fill="none" stroke="{col}" stroke-width="{w}"/>')
    arc(10, 18, R - 3, '#BFDBFE', 4)
    arc(18, 26, R - 3, '#BBF7D0', 4)
    arc(26, 40, R - 3, '#FECACA', 4)
    for t in range(10, 41):
        a = math.pi * (1 - (t - 10) / 30)
        major = (t % 5 == 0)
        r1 = R - (8 if major else 5)
        x0, y0 = cx + R * math.cos(a), cy - R * math.sin(a)
        x1, y1 = cx + r1 * math.cos(a), cy - r1 * math.sin(a)
        parts.append(f'<line x1="{x0:.2f}" y1="{y0:.2f}" x2="{x1:.2f}" y2="{y1:.2f}" stroke="#111" stroke-width="{0.6 if major else 0.3}"/>')
        if major:
            lx, ly = cx + (R + 5) * math.cos(a), cy - (R + 5) * math.sin(a)
            parts.append(f'<text x="{lx:.2f}" y="{ly:.2f}" font-size="4.2" text-anchor="middle" dominant-baseline="central" font-weight="700">{t}</text>')
    parts.append(f'<text x="{cx}" y="{cy - 22}" font-size="5" text-anchor="middle" font-weight="700">℃</text>')
    parts.append(f'<text x="{cx}" y="{cy - 14}" font-size="2.8" text-anchor="middle" fill="#6B7280">針で指す温度計</text>')
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="3" fill="none" stroke="#111" stroke-width=".3"/>')
    parts.append(f'<path d="M{cx - 5} {cy} h10 M{cx} {cy - 5} v10" stroke="#111" stroke-width=".2"/>')
    parts.append(f'<text x="{cx}" y="{cy + 7}" font-size="2.6" text-anchor="middle" fill="#6B7280">ここに軸を通す (直径 6mm の穴)</text>')
    parts.append(f'<text x="4" y="{H - 4}" font-size="2.6" fill="#6B7280">100% (実寸) で印刷。左端 = 10℃ = 0 ステップ、右端 = 40℃ = 1024 ステップ</text>')
    parts.append('</svg>')
    with open(os.path.join(OUT, 'needle-dial.svg'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(parts) + '\n')
    print('wrote needle-dial.svg')


# ------------------------------------------------------------------ 赤外線リモコン
def piezo_icon(s, cx, cy):
    s.add(f'<rect x="{cx - 40}" y="{cy - 6}" width="80" height="12" rx="6" fill="#1F2937"/>')
    s.add(f'<circle cx="{cx}" cy="{cy}" r="26" fill="#262A31" stroke="#111"/>')
    for r in (20, 15, 10):
        s.add(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#3B4150"/>')
    s.add(f'<circle cx="{cx}" cy="{cy}" r="4" fill="#B8913A"/>')
    s.text(cx + 34, cy - 18, '圧電スピーカー PT08', size=9.5, weight=700, anchor='start')
    s.text(cx + 34, cy - 4, '向きはない', size=8.5, fill=MUTED, anchor='start')


def ir_breadboard():
    s = SVG(1100, 600, '赤外線リモコン受信のブレッドボード配線',
            'Freenove ESP32 を 1〜20 行に挿す。a5 (3V3) から上の + ライン、a7 (GND) から上の − ライン。'
            '受信モジュールを c23〜c25 にレンズを手前 (j 側) に向けて挿し、a16 (IO34) → a23 (OUT)、− ライン → a24 (GND)、+ ライン → a25 (VCC)。'
            '圧電スピーカーの赤を a12 (IO25)、黒を上の − ラインへ。')
    b = Board(s, 190, 170)
    b.draw()
    b.freenove({'3V3': C['3V3'], 'GND': C['GND'], 'IO34': C['IO34'], 'IO25': C['IO25']})
    b.wire('a5', 'top+:5', C['3V3'], straight=True)
    b.wire('a7', 'top-:7', C['GND'], straight=True)
    b.ir_module([23, 24, 25])
    b.wire('a16', 'a23', C['IO34'], lift=0.9)
    b.wire('top-:23.6', 'a24', C['GND'], straight=True)
    b.wire('top+:25.4', 'a25', C['3V3'], straight=True)
    for r, lab in ((23, 'OUT'), (24, 'GND'), (25, 'VCC')):
        x, y = b.hole(f'c{r}')
        s.text(x, y + 30, lab, size=8, weight=700, family=MONO, rotate=-90)
    x23, yc = b.hole('c24')
    s.add(f'<rect x="{x23 + 44}" y="{yc - 2}" width="196" height="38" rx="6" fill="#FFFFFF" stroke="#9CA3AF"/>')
    s.text(x23 + 52, yc + 9, '受信モジュール OSRB38C9AA', size=9.5, weight=700, anchor='start')
    s.text(x23 + 52, yc + 25, 'レンズ (ふくらみ) を手前 = j 側に', size=9, fill=MUTED, anchor='start')

    # 圧電スピーカー: 赤 → a12 (IO25)、黒 → 上の − ライン
    pcx, pcy = 430, 52
    piezo_icon(s, pcx, pcy)
    for col, hole in (('#DC2626', 'a12'), ('#111827', 'top-:13.6')):
        hx, hy = b.hole(hole)
        sx = pcx - 8 if hole == 'a12' else pcx + 8
        s.add(f'<path d="M{sx} {pcy + 24} C{sx} {pcy + 60} {hx} {hy - 50} {hx} {hy}" fill="none" stroke="{col}" stroke-width="2.4"/>')
        s.add(f'<circle cx="{hx}" cy="{hy}" r="3" fill="{col}" stroke="#fff"/>')
    s.text(b.hole('a12')[0] - 8, b.hole('top+:12')[1] - 26, '赤 → a12', size=9, weight=700, fill='#DC2626', anchor='end')
    s.text(b.hole('top-:13.6')[0] + 10, b.hole('top-:13.6')[1] - 30, '黒 → − ライン', size=9, weight=700, anchor='start')

    tag(s, b.hole('a5')[0] + 36, b.hole('top+:5')[1] - 14, '3V3', C['3V3'])
    tag(s, b.hole('a7')[0] + 44, b.hole('top-:7')[1] + 12, 'GND', C['GND'])
    s.text(b.hole('a25')[0] + 8, b.hole('top+:25.4')[1] - 16, '+ ラインは 3.3V', size=9, fill=C['3V3'], weight=700, anchor='start')

    usb_cable(s, b, ('USB → PC', '書き込み・電源・シリアル'))
    legend(s, 190, 520, [('3V3', C['3V3']), ('GND', C['GND']), ('IO34 ← 受信', C['IO34']), ('IO25 → 圧電', C['IO25'])])
    s.text(190, 550, '色は基板のフルカラー LED (IO16) で出すので、LED の配線は要らない', size=10, anchor='start', fill=MUTED)
    s.save('ir-breadboard.svg')


def ir_nec():
    s = SVG(900, 340, 'NEC フォーマットのリモコン信号',
            '受信モジュールの出力は、リモコンが光っている間 LOW になる。9ms の LOW と 4.5ms の HIGH (リーダー) のあと、'
            '0 は 0.56ms LOW + 0.56ms HIGH、1 は 0.56ms LOW + 1.69ms HIGH で 32 ビット。押し続けると 9ms + 2.25ms のリピートが 108ms ごとに来る。')
    s.text(30, 32, '受信モジュールの OUT (ESP32 が見る信号)', size=12, weight=700, anchor='start')
    s.text(30, 52, '光っている間 = LOW。LOW と HIGH の長さで 0 / 1 を見分ける', size=9.5, fill=MUTED, anchor='start')
    yH, yL = 95, 145
    kl, kb = 10.0, 44.0           # リーダーは 1ms = 10px に縮め、ビットは 1ms = 44px で描く
    x = 70
    pts = [(x - 30, yH), (x, yH)]

    def seg(level, ms, k):
        nonlocal x
        y = yL if level == 0 else yH
        pts.append((x, y))
        x += ms * k
        pts.append((x, y))

    x0 = x
    seg(0, 9.0, kl)
    xm = x
    seg(1, 4.5, kl)
    xl = x
    first = [0, 0, 0, 0, 1, 0, 0, 0]               # 0x10 を下位ビットから
    marks = []
    for bit in first:
        xs = x
        seg(0, 0.56, kb)
        seg(1, 1.69 if bit else 0.56, kb)
        marks.append((xs, x, bit))
    xe = x
    d = 'M' + ' L'.join(f'{px:.1f} {py:.1f}' for px, py in pts)
    s.add(f'<path d="{d}" fill="none" stroke="{C["IO34"]}" stroke-width="2.4" stroke-linejoin="round"/>')
    s.add(f'<path d="M{xe} {yH} h34" stroke="{C["IO34"]}" stroke-width="2.4" stroke-dasharray="4 4"/>')
    s.text(xe + 42, yH, '… 残り 24 ビット', size=10, anchor='start', fill=MUTED)
    s.text(x0 - 36, yH, 'H', size=9, fill=MUTED, family=MONO)
    s.text(x0 - 36, yL, 'L', size=9, fill=MUTED, family=MONO)
    s.text((x0 + xm) / 2, yL + 14, '9ms', size=9, family=MONO, weight=700)
    s.text((xm + xl) / 2, yH - 12, '4.5ms', size=9, family=MONO, weight=700)
    for xa in ((x0 + xm) / 2, (xm + xl) / 2):     # 縮めて描いている印
        yy = yL if xa < xm else yH
        s.add(f'<path d="M{xa - 6} {yy - 7} l4 14 M{xa + 2} {yy - 7} l4 14" stroke="#FBFAF7" stroke-width="4"/>')
        s.add(f'<path d="M{xa - 6} {yy - 7} l4 14 M{xa + 2} {yy - 7} l4 14" stroke="{MUTED}" stroke-width="1.2"/>')
    for xs, xe2, bit in marks:
        s.text((xs + xe2) / 2, yL + 22, str(bit), size=12, weight=700, family=MONO, fill=C['IO25'])

    def brace(xa, xb, y, text):
        s.add(f'<path d="M{xa + 2} {y} v6 H{xb - 2} v-6" fill="none" stroke="{MUTED}" stroke-width="1.2"/>')
        s.text((xa + xb) / 2, y + 18, text, size=10, weight=700)
    brace(x0, xl, 182, 'リーダー (縮めて描いた)')
    brace(xl, xe, 182, 'メーカーの最初の 8 ビット = 0x10 (下位のビットから)')

    def bitshape(ox, oy, space, label):
        kk = 44
        p = [(ox, oy), (ox, oy + 30), (ox + 0.56 * kk, oy + 30), (ox + 0.56 * kk, oy), (ox + (0.56 + space) * kk, oy), (ox + (0.56 + space) * kk, oy + 30)]
        s.add('<path d="M' + ' L'.join(f'{a:.1f} {b_:.1f}' for a, b_ in p) + f'" fill="none" stroke="{C["IO34"]}" stroke-width="2.4"/>')
        s.text(ox + 0.28 * kk, oy + 44, '0.56ms', size=8.5, family=MONO)
        s.text(ox + (0.56 + space / 2) * kk, oy - 10, f'{space:.2f}ms', size=8.5, family=MONO)
        s.text(ox - 14, oy + 15, label, size=13, weight=700, anchor='end', family=MONO, fill=C['IO25'])
    s.text(30, 238, '0 と 1 (同じ縮尺)', size=10, weight=700, anchor='start')
    bitshape(110, 262, 0.56, '0')
    bitshape(260, 262, 1.69, '1')
    s.text(470, 250, '32 ビット = メーカー 16 ビット (このリモコンは 0x10EF)', size=10, anchor='start')
    s.text(470, 268, '+ キー 8 ビット + キーを反転した 8 ビット', size=10, anchor='start')
    s.text(470, 292, '押し続けると、108ms ごとに「リピート」(9ms LOW + 2.25ms HIGH) が来る', size=10, anchor='start', fill=MUTED)
    s.text(470, 312, '時間の長さは秋月のリモコンの資料 (NEC フォーマット) より', size=9, anchor='start', fill=MUTED)
    s.save('ir-nec.svg')


# ------------------------------------------------------------------ 光で文字を送る
def mini_freenove(s, x, y, w=210, h=96, label='Freenove A (送る側)'):
    """ブレッドボードに挿さない、基板だけの絵。RGB LED の座標を返す"""
    s.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="5" fill="#15171C"/>')
    s.add(f'<rect x="{x + w - 70}" y="{y + 16}" width="64" height="{h - 32}" rx="3" fill="#D9DCE3" stroke="#9BA1AD"/>')
    s.add(f'<rect x="{x - 10}" y="{y + h / 2 - 12}" width="16" height="24" rx="5" fill="#B8BDC7" stroke="#8B919C"/>')
    for i in range(20):
        px = x + 10 + i * (w - 20) / 19
        s.add(f'<rect x="{px - 2.5}" y="{y + 4}" width="5" height="5" fill="#C9A227"/>')
        s.add(f'<rect x="{px - 2.5}" y="{y + h - 9}" width="5" height="5" fill="#C9A227"/>')
    lx, ly = x + 82, y + h / 2 + 6
    s.add(f'<rect x="{lx - 8}" y="{ly - 8}" width="16" height="16" rx="2" fill="#F8FAFC" stroke="#9CA3AF"/>')
    s.add(f'<circle cx="{lx}" cy="{ly}" r="5" fill="#FEF9C3" stroke="#EAB308"/>')
    s.text(x + 60, y + 30, label, size=9.5, fill='#F3F4F6', weight=700)
    s.text(lx, ly + 20, 'RGB LED', size=8, fill='#C9CDD6')
    return lx, ly


def light_breadboard():
    s = SVG(1100, 680, '光で文字を送るときの配線',
            '受け取る側の Freenove ESP32 を 1〜20 行に挿す。a20 (3V3) → a24、CdS を c24–c25、10kΩ を b25 と上の − ライン、'
            'a16 (IO34) → a25、a7 (GND) → 上の − ライン。送る側の Freenove は配線なしで、基板のフルカラー LED を CdS に向ける。')
    b = Board(s, 190, 170)
    b.draw()
    b.freenove({'3V3': C['3V3'], 'GND': C['GND'], 'IO34': C['IO34']})
    b.wire('a7', 'top-:7', C['GND'], straight=True)
    b.wire('a20', 'a24', C['3V3'], lift=0.6)
    b.cds('c24', 'c25')
    b.resistor('b25', 'top-:25.6', label='10kΩ', label_dx=26, label_dy=2)
    b.wire('a16', 'a25', C['IO34'], lift=1.15)
    tag(s, b.hole('a7')[0] + 44, b.hole('top-:7')[1] + 12, 'GND', C['GND'])
    s.text(b.hole('c24')[0] - 40, 40, 'Freenove B (受け取る側)', size=11, weight=700)
    usb_cable(s, b, ('USB → PC', 'シリアルモニタで文字を見る'))

    # 送る側と、紙の筒
    ix, iy = 330, 512
    s.add(f'<rect x="{ix}" y="{iy}" width="740" height="150" rx="10" fill="#FFFFFF" stroke="#D6D0C2"/>')
    s.text(ix + 14, iy + 18, 'CdS をオス-メス線 2 本で延長し、送る側の LED に向ける (間を紙の筒でつなぐ)', size=10, anchor='start', weight=700)
    lx, ly = mini_freenove(s, ix + 30, iy + 38)
    tx0, tx1 = lx + 14, lx + 150
    s.add(f'<rect x="{tx0}" y="{ly - 18}" width="{tx1 - tx0}" height="36" rx="4" fill="#E5E1D8" stroke="#B9B2A3"/>')
    s.text((tx0 + tx1) / 2, ly + 30, '紙の筒 (3〜5cm)', size=9, fill=MUTED)
    for i in range(4):
        y = ly - 9 + i * 6
        s.add(f'<line x1="{lx + 8}" y1="{y}" x2="{tx1 - 10}" y2="{y}" stroke="#FACC15" stroke-width="1.6" stroke-dasharray="6 5" opacity=".9"/>')
    cx, cy = tx1 + 10, ly
    s.add(f'<circle cx="{cx}" cy="{cy}" r="9" fill="#F4E9C8" stroke="#B89B4E"/>')
    s.add(f'<path d="M{cx - 5} {cy - 3} q2.5 -4 5 0 t5 0 M{cx - 5} {cy + 3} q2.5 -4 5 0 t5 0" fill="none" stroke="#B5462C" stroke-width="1.3"/>')
    for i, (col, txt) in enumerate(((C['3V3'], 'c24 へ'), (C['IO34'], 'c25 へ'))):
        s.add(f'<path d="M{cx + 8} {cy - 4 + i * 8} C{cx + 60} {cy - 4 + i * 8} {cx + 80} {cy - 30 + i * 40} {cx + 130} {cy - 30 + i * 40}" fill="none" stroke="{col}" stroke-width="3"/>')
        s.text(cx + 138, cy - 30 + i * 40, txt, size=9.5, fill=col, weight=700, anchor='start')
    s.text(ix + 470, iy + 120, '段階 1 は 1 台で: B 自身の LED に向ける', size=9.5, anchor='start', fill=MUTED)
    s.text(ix + 470, iy + 136, '送る側は配線なし。USB で電源だけ', size=9.5, anchor='start', fill=MUTED)

    legend(s, 190, 488, [('3V3', C['3V3']), ('GND', C['GND']), ('IO34 明るさ', C['IO34'])])
    s.save('light-breadboard.svg')


def light_frame():
    s = SVG(900, 360, '光で 1 文字を送るときの形',
            "'H' (0x48) を送る例。消灯で待ち、点灯 1 ビットがスタート、データ 8 ビットを下位から、消灯 2 ビットがストップ。"
            'CdS の電圧は遅れてなまるので、スタートで明るくなった時刻から 1.5 ビット後、2.5 ビット後… のまん中で読む。')
    bits = [0, 0] + [1] + [(0x48 >> i) & 1 for i in range(8)] + [0, 0] + [0]
    x0, bw = 70, 52
    yLed1, yLed0 = 70, 100
    s.text(20, yLed1 + 15, 'LED', size=11, weight=700, anchor='start')
    pts = []
    for i, bt in enumerate(bits):
        y = yLed1 if bt else yLed0
        pts += [(x0 + i * bw, y), (x0 + (i + 1) * bw, y)]
    s.add('<path d="M' + ' L'.join(f'{a:.1f} {b_:.1f}' for a, b_ in pts) + '" fill="none" stroke="#EAB308" stroke-width="2.6"/>')
    # CdS の電圧 (立ち上がりは速く、立ち下がりは遅い)
    yHi, yLo = 160, 230
    s.text(20, (yHi + yLo) / 2, 'CdS', size=11, weight=700, anchor='start')
    v, curve = 0.0, []
    steps = 40
    for i, bt in enumerate(bits):
        for k in range(steps):
            tau = 0.18 if bt > v else 0.45
            v += (bt - v) * (1 - math.exp(-(1 / steps) / tau))
            curve.append((x0 + (i + (k + 1) / steps) * bw, yLo - v * (yLo - yHi)))
    s.add('<path d="M' + f'{x0} {yLo} L' + ' L'.join(f'{a:.1f} {b_:.1f}' for a, b_ in curve) + f'" fill="none" stroke="{C["IO34"]}" stroke-width="2.6"/>')
    yth = (yHi + yLo) / 2
    s.add(f'<line x1="{x0}" y1="{yth}" x2="{x0 + len(bits) * bw}" y2="{yth}" stroke="#9CA3AF" stroke-dasharray="5 4"/>')
    s.text(x0 + len(bits) * bw + 6, yth, 'しきい値', size=9, anchor='start', fill=MUTED)
    # スタートを見つけた時刻 (しきい値を超えた所) と、読む位置
    t_start = next(px for px, py in curve if py < yth)
    s.add(f'<line x1="{t_start}" y1="{yHi - 14}" x2="{t_start}" y2="{yLo + 6}" stroke="#B91C1C" stroke-width="1.2"/>')
    s.text(t_start, yHi - 22, 'スタートを見つけた', size=8.5, fill='#B91C1C')
    for k in range(9):
        sx = t_start + (1.5 + k) * bw
        sy = min(curve, key=lambda p: abs(p[0] - sx))[1]
        is_on = sy < yth
        s.add(f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="5" fill="{"#B91C1C" if k < 8 else "#6B7280"}" stroke="#fff" stroke-width="1.2"/>')
        s.text(sx, yLo + 22, ('1' if is_on else '0') if k < 8 else '0?', size=11, weight=700, family=MONO, fill='#B91C1C' if k < 8 else MUTED)

    def brace(i0, i1, text):
        xa, xb = x0 + i0 * bw + 3, x0 + i1 * bw - 3
        s.add(f'<path d="M{xa} 262 v6 H{xb} v-6" fill="none" stroke="{MUTED}" stroke-width="1.2"/>')
        s.text((xa + xb) / 2, 282, text, size=9.5, weight=700)
    brace(0, 2, '待ち (消灯)')
    brace(2, 3, 'スタート')
    brace(3, 11, 'データ 8 ビット (下位のビットから)')
    brace(11, 13, 'ストップ ×2')
    for i in range(8):
        s.text(x0 + (3 + i + 0.5) * bw, yLed1 - 12, f'b{i}', size=8, fill=MUTED, family=MONO)
    s.text(450, 318, "読んだビットを下位から並べる: 0,0,0,1,0,0,1,0 → 0b01001000 = 0x48 = 'H'", size=11, weight=700)
    s.text(450, 340, '赤い丸 = 読む位置。ストップの位置が暗くなければ、区切りがずれたと分かる', size=9.5, fill=MUTED)
    s.save('light-frame.svg')


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    # 開発環境
    esp32_pinmap()
    freenove_pinmap()
    # 首振りガジェット
    light_seeker_breadboard()
    light_seeker_schematic()
    light_follower_breadboard()
    # 障害物回避カー
    car_breadboard()
    car_schematic()
    # ワイヤレス操縦
    rc_system()
    rc_controller_breadboard()
    grove_adapter()
    # 針で指す温度計
    needle_breadboard()
    needle_schematic()
    needle_dial()
    # 赤外線リモコン
    ir_nec()
    ir_breadboard()
    car_breadboard(ir=True)
    # 光で文字を送る
    light_breadboard()
    light_frame()
