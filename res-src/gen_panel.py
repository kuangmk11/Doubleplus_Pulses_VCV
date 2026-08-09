#!/usr/bin/env python3
"""Generate res/PulsesPlus.svg — panel laid out to match the hardware.

Mirrors the DOUBLEPLUS++PULSES front panel: two toggle columns zig-zagging down
the board with the channel numbers + LEDs on the centre spine, the OR/MUTE/AND
mode legend between the two bus toggles, and A/B under the output jacks. The one
departure from the hardware is the input row: the VCV module is fed CLOCK + BIT
(it rebuilds the register locally) where the hardware has the EXT jack.

Authored in millimetres and emitted in VCV pixels (1 mm = 75/25.4 px). The C++
widget places components with mm2px() using the SAME coordinates below, so keep the
two in sync. Component body half-sizes (for the clearance check) are the real
widget SVG sizes.
"""

import glob
import os
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

MM = 75.0 / 25.4          # px per mm
HP = 8

# VCV renders panels with NanoSVG, which does NOT draw <text>. So every label is
# baked to vector <path> outlines from DejaVu (regeneration needs fonttools + the
# DejaVu fonts installed; the committed SVG carries the paths so end users don't).


def _find(name):
    for p in (f"/usr/share/fonts/truetype/dejavu/{name}",
              f"/usr/share/fonts/dejavu/{name}",
              f"/Library/Fonts/{name}"):
        if os.path.exists(p):
            return p
    hits = glob.glob(f"/usr/share/fonts/**/{name}", recursive=True)
    if hits:
        return hits[0]
    raise SystemExit(f"font not found: {name} — install DejaVu or edit gen_panel.py")


def _load(name):
    f = TTFont(_find(name))
    return (f.getGlyphSet(), f.getBestCmap(), f["head"].unitsPerEm, f["hmtx"])


FONT_REG = _load("DejaVuSans.ttf")
FONT_BOLD = _load("DejaVuSans-Bold.ttf")
W_MM = HP * 5.08          # 40.64
H_MM = 128.5
W = HP * 15.0             # 120 px
H = 380.0                 # RACK_GRID_HEIGHT
CX = W_MM / 2             # 20.32 centre spine

# --- layout (mm), shared with the C++ widget ---------------------------------
COL_OFF = 12.28
COL_L = CX - COL_OFF      # 8.04
COL_R = CX + COL_OFF      # 32.60

ROW0 = 16.5               # first routing-toggle row
PITCH = 7.2               # row pitch (same-column toggles sit 2*PITCH apart)
LED_RISE = 2.5            # channel LED rides above its toggle's row, on the spine
ROWS = [ROW0 + i * PITCH for i in range(8)]

IN_Y = 78.0              # CLOCK / BIT input row
BUS_LED_Y = 88.0
BUS_SW_Y = 97.5
OUT_Y = 109.0

# widget body half-sizes (px -> mm) for the clearance check
SWH_HX, SWH_HY = 31.5642 / MM / 2, 27.99345 / MM / 2   # horizontal toggle 5.34 x 4.74
SWV_HX, SWV_HY = 27.99345 / MM / 2, 31.5642 / MM / 2   # vertical toggle   4.74 x 5.34
JK = 8.7 / 2                                            # PJ301M ~4.35
LD = 2.7 / 2                                            # MediumLight ~1.35


def x(mm):
    return f"{mm * MM:.3f}"


def txt(cx, cy, s, size=3.2, fill="#e8e8e8", weight="normal", anchor="middle"):
    """Baked vector-path text (cx, cy, size in mm; cy is the baseline)."""
    gs, cmap, upm, hmtx = FONT_BOLD if weight == "bold" else FONT_REG
    scale = (size * MM) / upm

    def gname(ch):
        return cmap.get(ord(ch)) or cmap.get(ord(" "))

    total = sum(hmtx[gname(ch)][0] for ch in s) * scale
    bx, by = cx * MM, cy * MM
    penx = bx - total / 2 if anchor == "middle" else (bx - total if anchor == "end" else bx)

    out = []
    for ch in s:
        gn = gname(ch)
        spen = SVGPathPen(gs)
        gs[gn].draw(TransformPen(spen, (scale, 0, 0, -scale, penx, by)))  # flip y, place
        d = spen.getCommands()
        if d:
            out.append(f'<path d="{d}" fill="{fill}"/>')
        penx += hmtx[gn][0] * scale
    return "".join(out)


def col_of(i):
    return COL_L if i % 2 == 0 else COL_R


def main():
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.3f}" height="{H:.3f}" '
         f'viewBox="0 0 {W:.3f} {H:.3f}">']

    # background
    o.append(f'<rect x="0" y="0" width="{W:.3f}" height="{H:.3f}" fill="#20232a"/>')
    o.append(f'<rect x="1.5" y="1.5" width="{W-3:.3f}" height="{H-3:.3f}" '
             f'fill="none" stroke="#3a3f4b" stroke-width="1"/>')

    # header — DOUBLEPLUS++PULSES
    o.append(txt(CX, 6.2, "DOUBLEPLUS", size=2.6, weight="bold", fill="#ffd166"))
    o.append(txt(CX, 10.4, "++ PULSES ++", size=3.4, weight="bold", fill="#ffffff"))

    # channel numbers on the spine (8 = EXT-normalled channel on the hardware)
    for i, ry in enumerate(ROWS):
        o.append(txt(CX, ry + 1.0, str(i + 1) if i < 7 else "8/EX",
                     size=2.4, fill="#9aa0ac"))

    # divider between the channel section and the input / bus section
    o.append(f'<line x1="{x(3)}" y1="{x(72.5)}" x2="{x(W_MM-3)}" y2="{x(72.5)}" '
             f'stroke="#3a3f4b" stroke-width="0.8"/>')

    # CLOCK / BIT inputs — labels beside each jack (VCV rebuilds the register)
    o.append(txt(CX - 6.5 - 5.6, IN_Y + 0.9, "CLK", size=2.6, fill="#c8cdd6", anchor="end"))
    o.append(txt(CX + 6.5 + 5.6, IN_Y + 0.9, "BIT", size=2.6, fill="#c8cdd6", anchor="start"))
    o.append(txt(CX, IN_Y + 7.0, "from TM", size=2.0, fill="#7f8794"))

    # OR / MUTE / AND legend between the two mode toggles
    o.append(txt(CX, BUS_SW_Y - 3.6, "OR", size=2.2, fill="#7f8794"))
    o.append(txt(CX, BUS_SW_Y + 0.8, "MUTE", size=2.2, fill="#7f8794"))
    o.append(txt(CX, BUS_SW_Y + 5.0, "AND", size=2.2, fill="#7f8794"))

    # A / B under the output jacks
    o.append(txt(COL_L, OUT_Y + 6.6, "A", size=3.0, weight="bold", fill="#ffd166"))
    o.append(txt(COL_R, OUT_Y + 6.6, "B", size=3.0, weight="bold", fill="#ffd166"))

    o.append('</svg>')

    with open("res/PulsesPlus.svg", "w") as f:
        f.write("\n".join(o) + "\n")
    print("wrote res/PulsesPlus.svg")


def check():
    """Body-clearance check, panel_geom.py style — all gaps must be >= 0."""
    ch_bot = ROWS[7] + SWH_HY
    rows = [
        ("title <-> SW1 top", (ROWS[0] - SWH_HY) - 10.8),
        ("same-column toggles", 2 * PITCH - 2 * SWH_HY),
        ("centre number <-> toggle body", (CX - SWH_HX) - (2.4 / 2 + 0.3)),
        ("ch8 toggle <-> input jack", (IN_Y - JK) - ch_bot),
        ("input jack <-> bus LED", (BUS_LED_Y - LD) - (IN_Y + JK)),
        ("bus LED <-> mode toggle", (BUS_SW_Y - SWV_HY) - (BUS_LED_Y + LD)),
        ("mode toggle <-> out jack", (OUT_Y - JK) - (BUS_SW_Y + SWV_HY)),
        ("out jack <-> panel bottom", H_MM - (OUT_Y + JK)),
        ("horiz toggle <-> panel edge", COL_L - SWH_HX),
    ]
    return rows


if __name__ == "__main__":
    main()
    print(f"\n{HP} HP {W_MM:.2f} x {H_MM} mm, CX {CX:.2f}, columns {COL_L:.2f}/{COL_R:.2f}")
    print(f"rows {[round(r,1) for r in ROWS]}")
    bad = 0
    print("body clearances:")
    for label, g in check():
        bad += g < 0
        print(f"  {label:34} {g:6.2f} mm{'  *** FAIL ***' if g < 0 else ''}")
    print("ALL CLEAR" if not bad else f"{bad} FAILURES")
