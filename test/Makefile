SIM ?= icarus
TOPLEVEL_LANG ?= verilog

SRC_DIR = $(PWD)/../src
PROJECT_SOURCES = project.v

ifneq ($(GATES),yes)
VERILOG_SOURCES += $(addprefix $(SRC_DIR)/,$(PROJECT_SOURCES))
else
    $(error "GATES=yes gate-level simulation not set up in this minimal example -- use the full tt-verilog-template for that")
endif

TOPLEVEL = tt_um_snake
MODULE ?= test

# Speed up simulation time: override the default ~8Hz (3,125,000-cycle)
# tick divider down to a few hundred cycles so cocotb tests run in seconds
# instead of simulating millions of clock edges per snake move.
COMPILE_ARGS += -P$(TOPLEVEL).TICK_DIV=200

include $(shell cocotb-config --makefiles)/Makefile.sim
