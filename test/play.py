import time
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles
from pynput import keyboard

# Store active keys in a set to handle smooth key transitions
pressed_keys = set()

def get_key_name(key):
    """Normalize character and special arrow keys to a simple string name."""
    if hasattr(key, 'char') and key.char is not None:
        return key.char.lower()
    elif key == keyboard.Key.up:
        return 'up'
    elif key == keyboard.Key.down:
        return 'down'
    elif key == keyboard.Key.left:
        return 'left'
    elif key == keyboard.Key.right:
        return 'right'
    return None

def on_press(key):
    name = get_key_name(key)
    if name:
        pressed_keys.add(name)

def on_release(key):
    name = get_key_name(key)
    if name in pressed_keys:
        pressed_keys.remove(name)

def calculate_ui_in():
    """Bitmask mapping matching tt_um_snake pinout: UP=0, DOWN=1, LEFT=2, RIGHT=3."""
    ui = 0b00000000
    if 'w' in pressed_keys or 'up' in pressed_keys:
        ui |= 0b00000001  # ui_in[0] = UP
    if 's' in pressed_keys or 'down' in pressed_keys:
        ui |= 0b00000010  # ui_in[1] = DOWN
    if 'a' in pressed_keys or 'left' in pressed_keys:
        ui |= 0b00000100  # ui_in[2] = LEFT
    if 'd' in pressed_keys or 'right' in pressed_keys:
        ui |= 0b00001000  # ui_in[3] = RIGHT
    return ui

@cocotb.test()
async def test_interactive_play(dut):
    """Interactive mode allowing WASD & Arrow keyboard control during simulation."""
    
    # 1. Start clock generator (25MHz / 40ns period)
    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())

    # 2. Enable chip
    dut.ena.value = 1

    # 3. Start background keyboard listener
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()

    # 4. Apply hardware reset sequence
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)

    print("\n[+] Keyboard Control Active! Use WASD or Arrow Keys to play. Press Ctrl+C to stop.\n")

    try:
        while True:
            # Drive hardware inputs from pressed keys
            dut.ui_in.value = calculate_ui_in()
            
            # Step simulation clock forward by 1000 cycles
            await ClockCycles(dut.clk, 1000)
            
            # Throttle Python execution loop to match human reaction time (~30 FPS)
            time.sleep(0.03)
    except KeyboardInterrupt:
        print("\nExiting simulation.")
    finally:
        listener.stop()
