"""
Interactive terminal Snake, driven by the *actual* tt_um_snake Verilog --
not a re-implementation. Keypresses are written straight to `ui_in`
exactly like a physical button press would be, and the ASCII grid is
rendered by reading the design's real internal signals (`body`, `length`,
`food_x/y`, `game_over`).

Run with:
    make MODULE=play

Controls: W/A/S/D to move, R to restart after a game over, Q or Ctrl+C to quit.

Notes:
- Requires a real terminal (a TTY) for live key capture. If stdin isn't a
  TTY (e.g. piped input, some CI runners), this falls back to a short,
  non-interactive smoke run so `make MODULE=play` never hangs a pipeline.
- The 8-ish-moves/second pacing here comes from a real `time.sleep()` in
  this Python harness, independent of the design's own TICK_DIV (which
  the Makefile already speeds up for simulation). That's what makes the
  game *feel* like real time even though the simulator itself has no
  concept of a wall clock.
"""

import os
import sys
import time
import queue
import threading

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge

UP, DOWN, LEFT, RIGHT, RESTART = 0, 1, 2, 3, 4
KEYMAP = {"w": UP, "a": LEFT, "s": DOWN, "d": RIGHT, "r": RESTART}

GRID_W, GRID_H = 20, 15
FRAME_DELAY_S = 0.15  # ~6-7 moves/sec, comfortable to react to

_key_q: "queue.Queue[str]" = queue.Queue()


def _reader_thread(stop_flag):
    import termios
    import tty

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        while not stop_flag["stop"]:
            ch = sys.stdin.read(1)
            if ch:
                _key_q.put(ch)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _render(dut):
    length = int(dut.length.value)
    body = []
    for i in range(min(length, 48)):
        raw = int(dut.body[i].value)
        x = (raw >> 4) & 0x1F
        y = raw & 0xF
        body.append((x, y))

    fx, fy = int(dut.food_x.value), int(dut.food_y.value)
    game_over = int(dut.game_over.value)

    grid = [["." for _ in range(GRID_W)] for _ in range(GRID_H)]
    if 0 <= fy < GRID_H and 0 <= fx < GRID_W:
        grid[fy][fx] = "*"
    for idx, (x, y) in enumerate(body):
        if 0 <= y < GRID_H and 0 <= x < GRID_W:
            grid[y][x] = "@" if idx == 0 else "#"

    sys.stdout.write("\x1b[H\x1b[2J")  # cursor home + clear, less flicker than os.system('clear')
    print("TinyTapeout Snake  |  W A S D to move, R to restart, Q to quit")
    print("+" + "-" * GRID_W + "+")
    for row in grid:
        print("|" + "".join(row) + "|")
    print("+" + "-" * GRID_W + "+")
    status = "GAME OVER -- press R to restart" if game_over else f"length={length}"
    print(status)
    sys.stdout.flush()


@cocotb.test()
async def play_interactively(dut):
    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())

    dut.ena.value = 1
    dut.uio_in.value = 0
    dut.ui_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)

    interactive = sys.stdin.isatty()
    stop_flag = {"stop": False}
    reader = None
    if interactive:
        reader = threading.Thread(target=_reader_thread, args=(stop_flag,), daemon=True)
        reader.start()
    else:
        print(
            "stdin is not a TTY, so live keyboard input isn't available here "
            "(this happens under some CI/pipe setups). Running a short "
            "automatic demo instead so the harness itself is exercised."
        )

    quit_requested = False
    frames = 0
    max_frames = None if interactive else 40  # bounded fallback demo

    try:
        while not quit_requested and (max_frames is None or frames < max_frames):
            while not _key_q.empty():
                ch = _key_q.get_nowait().lower()
                if ch == "q" or ch == "\x03":
                    quit_requested = True
                elif ch in KEYMAP:
                    dut.ui_in.value = 1 << KEYMAP[ch]

            if not interactive and frames % 8 == 0:
                # keep the non-interactive fallback moving so it terminates
                dut.ui_in.value = 1 << RIGHT

            await RisingEdge(dut.tick)
            await ClockCycles(dut.clk, 1)
            _render(dut)
            frames += 1
            time.sleep(FRAME_DELAY_S if interactive else 0)
    except KeyboardInterrupt:
        pass
    finally:
        stop_flag["stop"] = True
        print("\nExiting.")
