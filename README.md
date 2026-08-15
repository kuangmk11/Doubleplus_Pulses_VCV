# Doubleplus Pulses — VCV Rack module

A software port of the hardware **++PULSES** gate router for the Music Thing
Turing Machine (see the [design write-up](https://github.com/kuangmk11/Doubleplus_Pulses/blob/main/docs/pulses-plus-design.md)
for the circuit it emulates). Eight pulse channels, each routed to one of two
merge buses; each bus computes OR **or** AND of whatever is routed to it, chosen
live.

Missing Mile Modular. Plugin slug `MissingMileModular`, module slug
`DoubleplusPulses`, 8 HP.

## Patching it up

VCV's Turing Machine (**Stellare Modular**) hands its shift register to its
expanders over a private module bus, not as a patchable ribbon, so this module
**rebuilds the eight bits from two cables**:

1. Patch the **same clock** that drives the Turing Machine into **CLOCK**.
2. Patch the TM's **stage-1 bit** — the first step output on the **Pulses**
   expander (BIT1) — into **BIT**.

Each clock the module shifts its own 8-stage register and shifts in whether BIT
pulsed during the period just ended. Because stage *k* is stage 1 delayed by *k*−1
clocks, the local register mirrors the TM's BIT1…BIT8 — bit 8 included, which the
hardware TM exposes on the bus but never uses. The eight channel LEDs show the
reconstructed register marching down.

Stellare's Pulses emits a **hair-thin trigger** per step, not the full-width ribbon
level a hardware TM presents. The module **latches** any BIT pulse across the clock
period, so those slivers register and — because the register holds each bit until
the next clock — the outputs come out as **full-width gates** that actually trigger
downstream modules.

## Using it

The thing worth understanding is that the two buses are **two independent reads of
the same register**. Every pattern either one produces is built from the same eight
bits, on the same loop, so they can never drift apart — but pick a different subset
for each, or put one in AND and the other in OR, and they come out at different
densities. Related, not identical. That is where most of the musical mileage is.

### Gates on A, note changes on B

The patch this module turned out to be best at, and not one it was designed for:

1. **OUT A → your envelope / VCA gate.** Route a few channels to Bus A in **OR** —
   a busy, rhythmic gate stream.
2. **OUT B → a quantizer's trigger / sample input**, with the Turing Machine's CV
   output going into that quantizer's CV input. Route a *different*, smaller set of
   channels to Bus B, in **AND** for something sparser still.

The quantizer only samples when Bus B fires, so the note is **held** across every
gate that Bus A produces in between. You get a melody that changes on its own
sparser rhythm while the gates keep articulating underneath it — and because both
rhythms are subsets of one shift register, the note changes always land on beats the
gate pattern already emphasises. It reads as a phrase rather than as two things
running at once.

Then, because it is a Turing Machine underneath, the loop-length and randomness
controls act on the whole thing at once: lock the register and you have a repeating
riff, open it a crack and the melody mutates while staying inside its scale.

**Things to reach for:**

- **B in AND with two or three channels** is the sweet spot for note changes. AND of
  several bits fires rarely, which is exactly what you want for a melody that moves
  every few bars instead of every step.
- **Swap which bus is which** for the inverse feel — sparse stabs with a fast-moving
  pitch underneath.
- **MUTE on B** freezes the pitch without touching the gate pattern, so you can drop
  the melody in and out live from the panel. That is what the centre position is for.
- Note that an **AND bus with nothing routed to it sits high** rather than pulsing
  (the hardware quirk this port keeps), so it will not ping anything. Route at least
  one channel to a bus you want triggers from.

## Panel

Drawn to the same house style as the hardware — **PANEL_STYLE v1.04**, kept with
the board in [Doubleplus_Pulses](https://github.com/kuangmk11/Doubleplus_Pulses) —
so the module reads the same in Rack as it does on the rails: white silkscreen on
black soldermask, one ink and one weight, every string letterspaced a character at
a time, a ring on the outputs and nothing else closed, names below the things they
name, and the `MMM` wordmark in its two-lead component frame at the foot.

Two toggle columns zig-zag down the panel with the channel numbers and LEDs on the
centre spine, `A`/`B` throw marks beside every routing toggle, and the AND/MUTE/OR
stack between the two bus toggles.

Three things depart from the hardware panel, all forced by the port:

- **the input row** — the module is fed CLOCK + BIT (it rebuilds the register
  locally) where the hardware has its EXT jack;
- **the toggle columns sit 10.5 mm off the spine**, not 12.28. Rack's Befaco lever
  is 10.7 mm wide against the board's 4.95 mm sub-miniature toggle, and the throw
  marks need room outboard of it;
- **no wires.** The board draws a wire from each toggle to its LED and down each
  bus column. At Rack's component sizes the first would have to run backwards and
  the second is under 1.3 mm — a segment that short reads as fab dirt, so the
  style's own escape clause applies: *check that a wire does not cross a control,
  or drop it.*

| Control | What it does |
|---|---|
| **CLOCK** input | The clock feeding the Turing Machine — advances the local shift register. |
| **BIT** input | The TM's stage-1 output (Pulses BIT1) — sampled each clock. |
| **Routing toggles 1–8** | Horizontal Befaco levers: **left → Bus A**, centre → off, **right → Bus B**. |
| **Channel LEDs** | Show each reconstructed bit **pre-switch**, regardless of routing. |
| **Bus A / Bus B toggles** | Vertical Befaco levers: **up → AND**, centre → **MUTE**, down → **OR**. |
| **OUT A / OUT B** | The two bus outputs — clock-width gates (0 / 10 V). |

## Behaviour notes

- **Outputs are gated by the clock.** Like the stock Pulses expander (bit AND
  clock), each output passes only while CLOCK is high, so the pulse width follows
  whatever clock/gate you feed CLOCK, and consecutive high steps come out as
  separate pulses that re-fire downstream envelopes. Turn this off in the right-click
  menu (*"Gate outputs with clock"*) to hold each bus for the full step instead.
- **Levels vs. edges.** The bus merge itself is combinational: OR/AND of the current
  bit *levels*, gated by the clock at the very end. CLOCK and BIT use a Schmitt-style
  threshold (high > 1 V, low < 0.2 V).
- **Clock phase.** The module and the Turing Machine see the same clock in the same
  audio block, so the local register may sit within one clock of the TM's phase.
  The reproduced pattern is faithful; only the alignment can be off by a step.
  This applies whether or not clock-gating is on.
- **AND of an empty bus is high — and steady.** Faithful to the hardware ("AND of
  zero terms is vacuously true"): a bus set to AND with nothing routed to it is held
  high by its pull-up, not driven by any clocked bit, so it sits at **DC high** and
  bypasses the clock gate rather than pulsing on every clock. Toggle this off in the
  right-click menu (*"AND of empty bus is high"*) to treat an empty bus as low.

## Building

Needs the [VCV Rack SDK](https://vcvrack.com/manual/Building#Setting-up-your-development-environment).

```sh
export RACK_DIR=/path/to/Rack-SDK
make            # builds plugin.so / .dylib / .dll
make dist       # packages a distributable ZIP
make install    # copies into your Rack user plugins folder
```

## Panel artwork

`res/DoubleplusPulses.svg` is generated by [`res-src/gen_panel.py`](res-src/gen_panel.py).
The layout is authored in millimetres there and the C++ widget places components
with `mm2px()` using the **same** coordinates, so graphics and hitboxes cannot
drift. It also runs a body-clearance check (like the hardware's `panel_geom.py`).

> **NanoSVG has no `<text>`.** VCV renders panels with NanoSVG, which ignores text
> elements — so every label is baked to vector **paths** (DejaVu outlines via
> `fonttools`). Regenerating the panel therefore needs `fonttools` and the DejaVu
> fonts installed; the committed SVG already carries the paths, so a normal build
> does not. If you edit labels and see nothing in Rack, you left them as `<text>`.

Edit the geometry in one place, keep both in sync, and re-run:

```sh
python3 res-src/gen_panel.py
```

The horizontal routing toggles are the stock **BefacoSwitch** frames rotated 90°
by [`res-src/rotate_befaco.py`](res-src/rotate_befaco.py) (inputs `res-src/bef_*.svg`,
outputs `res/BefacoSwitchHoriz_*.svg`) so the lever throws left = A / right = B.
The vertical bus-mode toggles use the stock `BefacoSwitch` directly.

---

## Related repositories

- **[Doubleplus_Pulses](https://github.com/kuangmk11/Doubleplus_Pulses)** — the hardware this
  ports: KiCad schematic, PCB, panel, BOM, gerbers and the full design write-up.
- **[Turing-Pulse-Expander](https://github.com/kuangmk11/Turing-Pulse-Expander)** — the archive:
  Tom Whitwell's original Rev 2 expander, plus the superseded studies the design grew out of.

## Licence

GPL-3.0-or-later — see [`LICENSE`](LICENSE). Note this differs from the hardware,
which is CC BY-NC-SA 4.0; the VCV Rack plugin library does not accept
NonCommercial terms.
