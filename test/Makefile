SIM ?= icarus
TOPLEVEL_LANG ?= verilog

SRC_DIR = $(PWD)/../src
PROJECT_SOURCES = project.v
ifeq ($(GATES),yes)
  VERILOG_SOURCES += $(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/verilog/primitives.v
  VERILOG_SOURCES += $(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/verilog/sky130_fd_sc_hd.v
  VERILOG_SOURCES += $(PWD)/gate_level_netlist.v
else
  VERILOG_SOURCES += $(PWD)/../src/project.v
endif

TOPLEVEL = tt_um_snake
MODULE ?= test

# Speed up simulation time: override the default ~8Hz (3,125,000-cycle)
# tick divider down to a few hundred cycles so cocotb tests run in seconds
# instead of simulating millions of clock edges per snake move.
COMPILE_ARGS += -P$(TOPLEVEL).TICK_DIV=200

include $(shell cocotb-config --makefiles)/Makefile.sim
