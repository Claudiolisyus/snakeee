import cocotb
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
    """Bitmask mapping for active input pins (Up, Down, Left, Right)."""
    ui = 0b00000000
    if 'w' in pressed_keys or 'up' in pressed_keys:
        ui |= 0b00000001
    if 's' in pressed_keys or 'down' in pressed_keys:
        ui |= 0b00000010
    if 'a' in pressed_keys or 'left' in pressed_keys:
        ui |= 0b00000100
    if 'd' in pressed_keys or 'right' in pressed_keys:
        ui |= 0b00001000
    return ui

@cocotb.test()
async def test_interactive_play(dut):
    """Interactive mode allowing WASD & Arrow keyboard control during simulation."""
    
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()

    # Apply reset sequence
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)

    print("\n[+] Keyboard Control Active! Use WASD or Arrow Keys to play. Press Ctrl+C to stop.\n")

    try:
        while True:
            # Update hardware input pins
            dut.ui_in.value = calculate_ui_in()
            
            # Step simulation in short cycle blocks to keep Python execution fast
            await ClockCycles(dut.clk, 50)
    except KeyboardInterrupt:
        print("\nExiting simulation.")
    finally:
        listener.stop()
