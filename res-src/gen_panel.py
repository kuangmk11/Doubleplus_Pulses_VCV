#!/usr/bin/env python3
"""Generate res/DoubleplusPulses.svg — the ++PULSES panel in the house style.

This is the software twin of the hardware panel. It follows PANEL_STYLE v1.04
(kept with the hardware, in the Doubleplus_Pulses repo) rather than inventing a
VCV-specific look, so the module reads the same in Rack as on the rails:

  * white silkscreen on black soldermask, single weight, no colour coding;
  * every string set one character at a time on a fixed pitch, uppercase, each
    glyph centred in its own cell — stroke faces are proportional and the
    reference lettering is widely tracked, so tracking is imposed by hand;
  * a ring means signal leaves here, and is the only closed circle on the panel;
  * a name goes below the thing it names, measured from the drawn extent (an
    output's ring) and not from the hole;
  * position marks go where the position is — A/B beside every routing toggle,
    the AND/MUTE/OR stack between the two mode toggles;
  * the wordmark is MMM letterspaced inside a two-lead component frame.

Three deliberate departures from the hardware panel, all forced by the port:

  1. The hardware's EXT jack becomes the CLK + BIT input pair — the module
     rebuilds the Turing Machine's shift register locally rather than taking a
     ribbon, so it needs the clock and the stage-1 bit.
  2. The toggle columns sit 10.5 mm off the spine rather than the hardware's
     12.28 — Rack's Befaco lever is twice the width of the sub-miniature toggle
     the board uses, and the A/B throw marks need room outboard of it.
  3. No wires, where the board routes toggle-to-LED and down each bus column.
     See the note at the point they would have been drawn.

The mode stack reads AND / MUTE / OR top to bottom, as the corrected hardware
panel does. (The hardware prototype had the switch inverted; the panel was
fixed, and this port was carrying the prototype's order until it was flipped to
match — see MODE_AND in DoubleplusPulses.cpp.)

Authored in millimetres and emitted in VCV pixels (1 mm = 75/25.4 px). The C++
widget places components with mm2px() using the SAME coordinates below, so the
two must be edited together.

VCV renders panels with NanoSVG, which does not draw <text>. Every label is
therefore baked to vector <path> outlines from DejaVu; regenerating needs
fonttools and the DejaVu fonts, but the committed SVG carries the paths so a
normal build does not.
"""

import glob
import os
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

MM = 75.0 / 25.4          # px per mm
HP = 8

# --- style tokens, from PANEL_STYLE v1.04 ------------------------------------
LINE_W, RULE_W = 0.25, 0.20
LABEL_SIZE, PITCH_LABEL = 2.0, 2.2
SMALL_SIZE, PITCH_SMALL = 1.6, 1.7
TITLE_SIZE, PITCH_TITLE = 3.2, 3.4
LOGO_SIZE, PITCH_LOGO = 1.3, 1.45
RING_GAP = 1.2
EDGE_MARGIN = 0.6
LABEL_GAP = 1.2           # drawn extent -> nearest edge of the label cell

# Silkscreen on soldermask. Single ink: the house style has no colour coding,
# and a second colour would be the first thing to break the "reads like the
# hardware" premise.
SILK = "#f0f0f0"
MASK = "#0b0b0b"

# DejaVu cap height (1493/2048). KiCad centres gr_text on its anchor, so a cell
# whose centre is at y needs its baseline half a cap-height lower.
CAP = 0.729

TITLE = "++PULSES"
TITLE_Y = 7.5
WORDMARK = "MMM"


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


FONT = _load("DejaVuSans.ttf")

W_MM = HP * 5.08          # 40.64
H_MM = 128.5
W = HP * 15.0             # 120 px
H = 380.0                 # RACK_GRID_HEIGHT
CX = W_MM / 2             # 20.32 centre spine

# --- layout (mm), shared with the C++ widget ---------------------------------
# The hardware puts its toggle columns 12.28 mm off the spine, but its toggles
# are 4.95 mm sub-miniatures. Rack's Befaco lever is 10.69 mm wide, which leaves
# no room outboard for the A/B throw marks the style requires — they fell 0.7 mm
# off the panel. The columns come in to 10.5, spending slack that was sitting
# unused between the toggles and the centre spine.
COL_OFF = 10.5
COL_L = CX - COL_OFF      # 9.82
COL_R = CX + COL_OFF      # 30.82

ROW0 = 16.5               # first routing-toggle row
PITCH = 7.2               # row pitch (same-column toggles sit 2*PITCH apart)
LED_RISE = 2.5            # channel LED rides above its toggle's row, on the spine
ROWS = [ROW0 + i * PITCH for i in range(8)]

IN_X = 6.5                # CLK / BIT sit either side of the spine
IN_Y = 78.0
BUS_LED_Y = 88.0
BUS_SW_Y = 97.5
OUT_Y = 109.0
MODE_STEP = 5.1           # AND / MUTE / OR stack spacing, from the hardware panel

# widget body half-sizes (px -> mm) for the clearance check
SWH_HX, SWH_HY = 31.5642 / MM / 2, 27.99345 / MM / 2   # horizontal toggle 5.34 x 4.74
SWV_HX, SWV_HY = 27.99345 / MM / 2, 31.5642 / MM / 2   # vertical toggle   4.74 x 5.34
JK = 8.7 / 2                                            # PJ301M ~4.35
LD = 2.7 / 2                                            # MediumLight ~1.35

RING_R = JK + RING_GAP    # 5.55 — the drawn extent of an output

out = []


def px(mm):
    return f"{mm * MM:.3f}"


def cells(s, cx, cy, size, pitch, fill=SILK):
    """Set `s` one character at a time on a fixed pitch, each glyph centred in
    its own cell. `cy` is the centre of the line, not the baseline."""
    gs, cmap, upm, hmtx = FONT
    s = s.upper()
    scale = (size * MM) / upm
    base = cy * MM + (CAP * size / 2.0) * MM
    n = len(s)
    for i, ch in enumerate(s):
        if ch == " ":
            continue
        gn = cmap.get(ord(ch)) or cmap.get(ord(" "))
        adv = hmtx[gn][0] * scale
        cell_cx = (cx + (i - (n - 1) / 2.0) * pitch) * MM
        spen = SVGPathPen(gs)
        gs[gn].draw(TransformPen(spen, (scale, 0, 0, -scale, cell_cx - adv / 2.0, base)))
        d = spen.getCommands()
        if d:
            out.append(f'<path d="{d}" fill="{fill}"/>')
    return n * pitch


def ring(cx, cy, r, width=LINE_W):
    out.append(f'<circle cx="{px(cx)}" cy="{px(cy)}" r="{px(r)}" fill="none" '
               f'stroke="{SILK}" stroke-width="{px(width)}"/>')


def line(x1, y1, x2, y2, width=LINE_W):
    out.append(f'<line x1="{px(x1)}" y1="{px(y1)}" x2="{px(x2)}" y2="{px(y2)}" '
               f'stroke="{SILK}" stroke-width="{px(width)}" stroke-linecap="round"/>')


def rect(x1, y1, x2, y2, width=RULE_W):
    out.append(f'<rect x="{px(x1)}" y="{px(y1)}" width="{px(x2 - x1)}" '
               f'height="{px(y2 - y1)}" fill="none" stroke="{SILK}" '
               f'stroke-width="{px(width)}"/>')


def below(drawn_r, size):
    """Centre-to-centre offset for a name sitting below what it names, measured
    from the drawn extent (a ring, not the hole) per PANEL_STYLE."""
    return drawn_r + LABEL_GAP + size / 2.0


def led_y(row_y):
    return row_y - LED_RISE


def main():
    o_head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.3f}" '
              f'height="{H:.3f}" viewBox="0 0 {W:.3f} {H:.3f}">')
    out.clear()

    # --- title ---------------------------------------------------------------
    # Eight characters at full TITLE_SIZE: 27.2 mm on a 40.64 mm panel. The long
    # form DOUBLEPLUS++PULSES needs 61 mm and would have to wrap or shrink; the
    # short form is what the hardware panel carries too.
    assert PITCH_TITLE * len(TITLE) <= W_MM - 2 * EDGE_MARGIN, "title too wide"
    cells(TITLE, CX, TITLE_Y, TITLE_SIZE, PITCH_TITLE)

    # --- channels 1..8 -------------------------------------------------------
    # Number below its LED; A/B beside the toggle it belongs to. Channel 8 is
    # plain here — the hardware's EXT normalling has no counterpart in the port.
    dx = SWH_HX + LABEL_GAP + SMALL_SIZE / 2.0
    for i, ry in enumerate(ROWS):
        cells(str(i + 1), CX, led_y(ry) + below(LD, LABEL_SIZE), LABEL_SIZE, PITCH_LABEL)
        sx = COL_L if i % 2 == 0 else COL_R
        cells("A", sx - dx, ry, SMALL_SIZE, PITCH_SMALL)
        cells("B", sx + dx, ry, SMALL_SIZE, PITCH_SMALL)

    # --- inputs: no ring, they are inputs ------------------------------------
    cells("CLK", CX - IN_X, IN_Y + below(JK, LABEL_SIZE), LABEL_SIZE, PITCH_LABEL)
    cells("BIT", CX + IN_X, IN_Y + below(JK, LABEL_SIZE), LABEL_SIZE, PITCH_LABEL)

    # --- mode stack, one legend serving both switches ------------------------
    # Both mode toggles carry the same three positions and the centre position
    # cannot be marked where it is — that is the control. So the three words sit
    # in the centre column on the switches' own baselines, serving both.
    cells("AND", CX, BUS_SW_Y - MODE_STEP, LABEL_SIZE, PITCH_LABEL)
    cells("MUTE", CX, BUS_SW_Y, LABEL_SIZE, PITCH_LABEL)
    cells("OR", CX, BUS_SW_Y + MODE_STEP, LABEL_SIZE, PITCH_LABEL)

    # --- outputs: a ring means signal leaves here ----------------------------
    for cx in (COL_L, COL_R):
        ring(cx, OUT_Y, RING_R)
    cells("A", COL_L, OUT_Y + below(RING_R, LABEL_SIZE), LABEL_SIZE, PITCH_LABEL)
    cells("B", COL_R, OUT_Y + below(RING_R, LABEL_SIZE), LABEL_SIZE, PITCH_LABEL)
    # The bus indicator LEDs take no label: each bus is a column — indicator,
    # mode switch, output jack — and the jack at its foot is already named.

    # --- no wires ------------------------------------------------------------
    # The hardware panel routes a wire from each toggle to its indicator LED,
    # and down each bus column. Neither survives the port, and the style's own
    # escape clause covers it: "check that a wire does not cross a control, or
    # drop it."
    #
    #   toggle -> LED: with the Befaco lever's width plus its throw marks, the
    #   run would have to start at x=19.8 to clear them and end at x=18.7 at the
    #   LED — it runs backwards. There is no room left to draw it in.
    #
    #   down each bus column: Rack's spacing leaves 0.8 mm between the LED and
    #   the mode toggle and 1.3 mm between the toggle and the output ring. At
    #   that length a segment reads as fab dirt, not as a connection — the same
    #   reason the style turns the star-field off.
    #
    # Nothing is lost: the LED sits directly between the two toggles it serves,
    # and each bus is already a single column read top to bottom.

    # --- wordmark, letterspaced inside a two-lead component frame ------------
    # MISSING MILE MODULAR needs 29 mm of cells before the frame and leads; at
    # 8 HP the short form is what fits, as on the hardware panel.
    wm_y = H_MM - 7.0
    half_w = (len(WORDMARK) * PITCH_LOGO) / 2.0 + 1.4
    half_h = LOGO_SIZE / 2.0 + 0.85
    rect(CX - half_w, wm_y - half_h, CX + half_w, wm_y + half_h)
    for sign in (-1, 1):
        x0 = CX + sign * half_w
        line(x0, wm_y, x0 + sign * 3.5, wm_y)
    cells(WORDMARK, CX, wm_y, LOGO_SIZE, PITCH_LOGO)

    body = "\n".join(out)
    svg = (f'{o_head}\n'
           f'<rect x="0" y="0" width="{W:.3f}" height="{H:.3f}" fill="{MASK}"/>\n'
           f'{body}\n</svg>\n')

    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dst = os.path.join(here, "res", "DoubleplusPulses.svg")
    with open(dst, "w") as f:
        f.write(svg)
    print(f"wrote {os.path.relpath(dst, here)}  ({len(out)} marks)")


def check():
    """Body- and label-clearance check — all gaps must be >= 0."""
    ch_bot = ROWS[7] + SWH_HY
    num_half = LABEL_SIZE / 2.0
    title_bot = TITLE_Y + TITLE_SIZE / 2.0
    in_label_bot = IN_Y + below(JK, LABEL_SIZE) + num_half
    out_label_bot = OUT_Y + below(RING_R, LABEL_SIZE) + num_half
    wm_top = (H_MM - 7.0) - (LOGO_SIZE / 2.0 + 0.85)
    throw_x = (COL_L - SWH_HX - LABEL_GAP - SMALL_SIZE / 2.0) - SMALL_SIZE / 2.0
    return [
        ("title <-> SW1 body", (ROWS[0] - SWH_HY) - title_bot),
        ("title <-> panel top", TITLE_Y - TITLE_SIZE / 2.0 - EDGE_MARGIN),
        ("same-column toggles", 2 * PITCH - 2 * SWH_HY),
        ("ch number <-> toggle body", (COL_R - SWH_HX) - (CX + PITCH_LABEL / 2.0)),
        ("ch LED <-> toggle body", (COL_R - SWH_HX) - (CX + LD)),
        ("throw mark <-> panel edge", throw_x - EDGE_MARGIN),
        ("throw mark <-> ch number",
         (CX - PITCH_LABEL / 2.0)
         - (COL_L + SWH_HX + LABEL_GAP + SMALL_SIZE / 2.0 + SMALL_SIZE / 2.0)),
        ("ch8 toggle <-> input jack", (IN_Y - JK) - ch_bot),
        ("input label <-> bus LED", (BUS_LED_Y - LD) - in_label_bot),
        ("bus LED <-> mode toggle", (BUS_SW_Y - SWV_HY) - (BUS_LED_Y + LD)),
        ("mode toggle <-> out ring", (OUT_Y - RING_R) - (BUS_SW_Y + SWV_HY)),
        ("out ring <-> panel edge", COL_L - RING_R - EDGE_MARGIN),
        ("out label <-> wordmark", wm_top - out_label_bot),
        ("wordmark <-> panel bottom", H_MM - ((H_MM - 7.0) + LOGO_SIZE / 2.0 + 0.85)),
        ("wordmark leads <-> edge", (CX - ((len(WORDMARK) * PITCH_LOGO) / 2.0 + 1.4)
                                     - 3.5) - EDGE_MARGIN),
        ("horiz toggle <-> panel edge", COL_L - SWH_HX),
    ]


if __name__ == "__main__":
    main()
    print(f"\n{HP} HP {W_MM:.2f} x {H_MM} mm, CX {CX:.2f}, columns {COL_L:.2f}/{COL_R:.2f}")
    print(f"rows {[round(r, 1) for r in ROWS]}")
    bad = 0
    print("clearances:")
    for label, g in check():
        bad += g < 0
        print(f"  {label:32} {g:6.2f} mm{'  *** FAIL ***' if g < 0 else ''}")
    print("ALL CLEAR" if not bad else f"{bad} FAILURES")
