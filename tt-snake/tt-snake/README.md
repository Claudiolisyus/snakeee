# TinyTapeout Snake

A fully playable game of Snake, synthesized down to a TinyTapeout tile and
rendered live over VGA. No CPU, no framebuffer memory — the whole game
(sync generator, movement, collision, food, rendering) is built from
plain combinational/sequential logic.

## How it plays

- The screen is a **20 x 15 grid** of 32x32 pixel cells (20*32 = 640,
  15*32 = 480 — an exact fit for 640x480 VGA).
- The snake starts 3 cells long, heading right, in the middle of the board.
- Move with the 4 direction buttons on `ui_in`. You can't reverse directly
  into yourself (pressing DOWN while heading UP is ignored).
- Eating the red food cell grows the snake by one segment and drops a new
  food cell at a pseudo-random location (16-bit LFSR).
- Hitting a wall or your own tail ends the game: the screen flashes red.
  Press RESTART (`ui_in[4]`) to play again.

## Pinout

| Pin | Function |
|---|---|
| `ui_in[0]` | UP |
| `ui_in[1]` | DOWN |
| `ui_in[2]` | LEFT |
| `ui_in[3]` | RIGHT |
| `ui_in[4]` | RESTART |
| `uo_out` | [TinyVGA PMOD](https://github.com/mole99/tiny-vga) — bit order `{hsync, B0, G0, R0, vsync, B1, G1, R1}` |
| `uio_out[0]` | `game_over` flag (1 = dead, waiting for restart) |

Wire `uo_out` to a TinyVGA PMOD and `ui_in[4:0]` to five buttons/switches
(active-high, so use pull-downs) and you have a complete, self-contained
arcade cabinet on a single TinyTapeout tile.

## Clocking

The design expects a **25.175 MHz** clock (the standard VGA 640x480@60Hz
pixel clock — 25 MHz is close enough that most monitors tolerate it fine).
Internally, a free-running counter divides this down to roughly 8 snake
moves per second.

## How it's built

- **VGA timing**: a standard `hcount`/`vcount` free-running counter drives
  `hsync`/`vsync` and a `video_active` window, per the usual 640x480@60Hz
  timing table.
- **Snake body**: stored as a small "history buffer" — a 48-entry shift
  register array. Every game tick, every entry copies from its neighbour
  and the new head position is pushed into slot 0. Growing the snake is
  then just a matter of incrementing a `length` counter — the tail is
  already sitting there in history, so no extra bookkeeping is needed.
- **Collision**: wall collisions are just range checks on the next head
  position; self-collision is a combinational compare of the candidate
  head position against every live body segment.
- **Food**: a 16-bit LFSR free-runs every clock; when food is eaten a new
  (x, y) is drawn from it (folded into the 20x15 grid range without a
  divider, since the grid dimensions aren't powers of two).
- **Rendering**: for every pixel, its cell coordinate is derived from
  `hcount`/`vcount` via a simple shift (cells are 32x32, a power of two)
  and compared against the head, body, and food positions to pick a
  6-bit RGB color (2 bits/channel, matching the TinyVGA PMOD).

## Repo layout

```
src/project.v      -- the whole design (tt_um_snake)
test/tb.v          -- Icarus Verilog testbench: checks VGA sync timing
test/tb_game.v      -- Icarus Verilog testbench: checks movement/food/collision
info.yaml           -- TinyTapeout project metadata
```

## Simulating locally

Both testbenches were used during development and pass under
[Icarus Verilog](http://iverilog.icarus.com/):

```bash
# VGA sync-timing check (real ~25MHz clock, watches for 2 vsync pulses)
iverilog -g2012 -o sim.out src/project.v test/tb.v
vvp sim.out

# Fast game-logic check (overrides TICK_DIV so ticks happen quickly in sim)
iverilog -g2012 -o sim_game.out src/project.v test/tb_game.v
vvp sim_game.out
```

`tb_game.v` drives the snake to the right, confirms it moves once per
tick, confirms `length` increases and a new food location is drawn when
the head reaches the food cell, and confirms a wall collision correctly
freezes the game (`game_over` stays high and the head stops moving) —
all observed in a real simulation run, not just eyeballed from the code.

A synthesis sanity pass with [Yosys](https://yosyshq.net/yosys/)
(`synth -top tt_um_snake`) completes with **0 problems** from the `check`
pass — no inferred latches, no multi-driven nets. The only note Yosys
prints is that the `body` history buffer is implemented as flip-flops
rather than a memory macro, which is expected and desired for a shift
register of this size.

## Using with the official TinyTapeout template

This repo mirrors the file layout of the
[tt-verilog-template](https://github.com/TinyTapeout/tt-verilog-template).
To submit it for a real shuttle:

1. Start from the official template repo.
2. Drop `src/project.v` in as your `src/project.v`, and merge `info.yaml`'s
   `project:` section into the template's `info.yaml` (fill in your name
   and GitHub Discord handle).
3. The template's GitHub Actions will run gate-level synthesis (OpenLane)
   and the official `cocotb`-based test harness — you'll likely want to
   port `test/tb_game.v`'s checks into a `test/test.py` cocotb test to
   match that harness (the template's `test/` folder expects Python/cocotb
   rather than a plain Verilog testbench).
4. Push, let CI run, then follow TinyTapeout's submission instructions at
   https://tinytapeout.com/faq/ to get it queued for a shuttle.

## Ideas for extending it

- Score display (e.g. drive a 7-segment style readout on part of the
  screen, or output the binary score on the `uio` pins).
- Wrap-around walls instead of instant death.
- A second, slower-growing "obstacle" snake for a harder mode.
- Use `uio_in` as a difficulty/speed selector feeding into `TICK_DIV`.
