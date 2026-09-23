import time
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles
from pynput import keyboard

pressed_keys = set()

def get_key_name(key):
    """Normalize character keys, number keys (0,1,2,3), and arrow keys."""
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
    """
    Translates WASD, Arrow Keys, and Numbers 0/1/2/3 to FPGA ui_in pins:
      ui_in[0] (0b00000001) = UP    ('w', 'up', '0')
      ui_in[1] (0b00000010) = DOWN  ('s', 'down', '1')
      ui_in[2] (0b00000100) = LEFT  ('a', 'left', '2')
      ui_in[3] (0b00001000) = RIGHT ('d', 'right', '3')
    """
    ui = 0b00000000
    
    # UP -> bit 0
    if any(k in pressed_keys for k in ('w', 'up', '0')):
        ui |= 0b00000001
        
    # DOWN -> bit 1
    if any(k in pressed_keys for k in ('s', 'down', '1')):
        ui |= 0b00000010
        
    # LEFT -> bit 2
    if any(k in pressed_keys for k in ('a', 'left', '2')):
        ui |= 0b00000100
        
    # RIGHT -> bit 3
    if any(k in pressed_keys for k in ('d', 'right', '3')):
        ui |= 0b00001000
        
    return ui

@cocotb.test()
async def test_interactive_play(dut):
    """Interactive simulation with real-time feedback."""
    
    # 1. Start clock (25MHz)
    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())

    # 2. Enable chip
    dut.ena.value = 1

    # 3. Start keyboard listener
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()

    # 4. Reset chip
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)

    print("\n[+] Controller Active!")
    print("    Controls: WASD | Arrow Keys | Numbers 0 (Up), 1 (Down), 2 (Left), 3 (Right)")
    print("    Press Ctrl+C in terminal to exit.\n")

    try:
        while True:
            ui_val = calculate_ui_in()
            dut.ui_in.value = ui_val
            
            # Read internal hardware direction & position state
            dir_val = dut.dir.value.integer if hasattr(dut, 'dir') else 0
            x_pos = dut.head_x.value.integer if hasattr(dut, 'head_x') else 0
            y_pos = dut.head_y.value.integer if hasattr(dut, 'head_y') else 0

            # Print live diagnostic line in terminal
            print(f"\r[INPUT] ui_in=0b{ui_val:08b} | Keys={list(pressed_keys)} | Snake Pos=({x_pos},{y_pos}) | Dir={dir_val}   ", end="")

            # Step clock & throttle real-time speed
            await ClockCycles(dut.clk, 2000)
            time.sleep(0.03)

    except KeyboardInterrupt:
        print("\n\nExiting simulation.")
    finally:
        listener.stop()
