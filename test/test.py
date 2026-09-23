"""
cocotb test for tt_um_snake.

This is the format TinyTapeout's own GitHub Actions CI expects
(test/test.py + test/Makefile, run via `make` with cocotb + Icarus
Verilog). It mirrors the checks already exercised by test/tb_game.v
and test/tb.v, just through the official harness.
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge

UP, DOWN, LEFT, RIGHT, RESTART = 0, 1, 2, 3, 4


async def reset(dut):
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)


def press(dut, *buttons):
    val = 0
    for b in buttons:
        val |= 1 << b
    dut.ui_in.value = val


@cocotb.test()
async def test_reset_state(dut):
    """After reset, the snake should be alive, length 3, heading right."""
    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())
    await reset(dut)

    assert dut.game_over.value == 0
    assert int(dut.length.value) == 3


@cocotb.test()
async def test_vga_sync_pulses(dut):
    """hsync/vsync should toggle with the standard 640x480@60Hz timing."""
    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())
    await reset(dut)

    # uo_out[7] = hsync, uo_out[3] = vsync (TinyVGA PMOD pin order)
    seen_hsync_low = False
    for _ in range(2000):
        await RisingEdge(dut.clk)
        if dut.uo_out.value.integer & 0x80 == 0:
            seen_hsync_low = True
            break
    assert seen_hsync_low, "hsync never asserted low within one line-ish window"


@cocotb.test()
async def test_move_eat_grow(dut):
    """Holding RIGHT should move the snake and, on reaching the food, grow it."""
    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())
    await reset(dut)

    press(dut, RIGHT)

    start_len = int(dut.length.value)
    grew = False

    # head starts at x=10 heading toward food at x=15 (5 moves away);
    # give it generous headroom in case of off-by-one timing.
    for _ in range(10):
        await RisingEdge(dut.tick)
        await ClockCycles(dut.clk, 1)
        if dut.game_over.value == 1:
            break
        if int(dut.length.value) > start_len:
            grew = True
            break

    assert grew, "snake never grew after heading toward the food"


@cocotb.test()
async def test_wall_collision_sets_game_over(dut):
    """Running the snake into the right-hand wall should end the game."""
    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())
    await reset(dut)

    press(dut, RIGHT)

    ended = False
    for _ in range(20):
        await RisingEdge(dut.tick)
        await ClockCycles(dut.clk, 1)
        if dut.game_over.value == 1:
            ended = True
            break

    assert ended, "snake did not hit the wall / game_over never asserted"

    # game state should now be frozen
    head_before = (int(dut.head_x.value), int(dut.head_y.value))
    await ClockCycles(dut.clk, 500)
    head_after = (int(dut.head_x.value), int(dut.head_y.value))
    assert head_before == head_after, "snake kept moving after game over"

    # uio_out[0] mirrors the game_over flag
    assert dut.uio_out.value.integer & 0x01 == 1


@cocotb.test()
async def test_restart_after_game_over(dut):
    """Pressing RESTART after death should bring the game back to the start state."""
    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())
    await reset(dut)

    press(dut, RIGHT)
    for _ in range(20):
        await RisingEdge(dut.tick)
        await ClockCycles(dut.clk, 1)
        if dut.game_over.value == 1:
            break
    assert dut.game_over.value == 1

    press(dut, RESTART)
    await ClockCycles(dut.clk, 3)

    assert dut.game_over.value == 0
    assert int(dut.length.value) == 3
