import time
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles
from pynput import keyboard

pressed_keys = set()

def on_press(key):
    # Convert whatever the OS sends into a raw, clean string
    # E.g., 'w', 'W', Key.up, etc.
    k_str = str(key).replace("'", "").lower()
    pressed_keys.add(k_str)

def on_release(key):
    k_str = str(key).replace("'", "").lower()
    if k_str in pressed_keys:
        pressed_keys.remove(k_str)

def calculate_ui_in():
    """
    Extremely aggressive bitmask mapping.
    Traps uppercase, lowercase, special keys, and numbers.
    """
    ui = 0b00000000
    
    # UP (ui_in[0])
    if pressed_keys.intersection({'w', 'up', 'key.up', '0'}):
        ui |= 0b00000001
        
    # DOWN (ui_in[1])
    if pressed_keys.intersection({'s', 'down', 'key.down', '1'}):
        ui |= 0b00000010
        
    # LEFT (ui_in[2])
    if pressed_keys.intersection({'a', 'left', 'key.left', '2'}):
        ui |= 0b00000100
        
    # RIGHT (ui_in[3])
    if pressed_keys.intersection({'d', 'right', 'key.right', '3'}):
        ui |= 0b00001000
        
    return ui

@cocotb.test()
async def test_interactive_play(dut):
    """Interactive simulation with raw keyboard debugging."""
    
    # 1. Start clock (25MHz)
    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())

    # 2. Enable chip
    dut.ena.value = 1

    # 3. Start keyboard listener
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()

    # 4. Apply hardware reset
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)

    print("\n" + "="*50)
    print("🎮 CONTROLLER ACTIVE!")
    print("If WASD fails, look at the [RAW KEY] output below")
    print("to see what your keyboard is actually sending.")
    print("="*50 + "\n")

    try:
        while True:
            ui_val = calculate_ui_in()
            dut.ui_in.value = ui_val
            
            # Print EXACTLY what python sees you pressing
            keys_list = list(pressed_keys)
            print(f"\r[RAW KEY DETECTED]: {keys_list} | ui_in={ui_val:08b}     ", end="")

            # Step clock & throttle real-time speed
            await ClockCycles(dut.clk, 2000)
            time.sleep(0.03)

    except KeyboardInterrupt:
        print("\n\nExiting simulation.")
    finally:
        listener.stop()
