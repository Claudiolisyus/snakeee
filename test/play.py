import cocotb
from cocotb.triggers import ClockCycles, RisingEdge
from pynput import keyboard

# Global variable to track active direction inputs
# Bit positions typically correspond to input pins (e.g., Up, Down, Left, Right)
current_ui_in = 0b00000000

def on_press(key):
    global current_ui_in
    try:
        if key == keyboard.Key.up:
            current_ui_in = 0b00000001  # Up pin
        elif key == keyboard.Key.down:
            current_ui_in = 0b00000010  # Down pin
        elif key == keyboard.Key.left:
            current_ui_in = 0b00000100  # Left pin
        elif key == keyboard.Key.right:
            current_ui_in = 0b00001000  # Right pin
    except AttributeError:
        pass

def on_release(key):
    global current_ui_in
    # Reset input when key is released
    current_ui_in = 0b00000000

@cocotb.test()
async def test_interactive_play(dut):
    """Interactive mode allowing keyboard control during simulation."""
    
    # Start non-blocking keyboard listener
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()

    # Reset hardware sequence
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)

    print("\n[+] Keyboard Control Active! Use Arrow Keys to play. Press Ctrl+C to stop.\n")

    # Simulation loop driving inputs every clock cycle
    try:
        while True:
            # Map global keyboard state directly to circuit's ui_in input bus
            dut.ui_in.value = current_ui_in
            await RisingEdge(dut.clk)
    except KeyboardInterrupt:
        print("\n Exiting simulation.")
    finally:
        listener.stop()
