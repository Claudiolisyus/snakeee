SIM ?= icarus
TOPLEVEL_LANG ?= verilog

SRC_DIR = $(PWD)/../src
PROJECT_SOURCES = project.v

# Route all simulation runs to RTL source to bypass missing PDK dependencies in CI
VERILOG_SOURCES += $(PWD)/../src/project.v

TOPLEVEL = tt_um_snake
MODULE = test

# Speed up simulation time: override default tick divider
COMPILE_ARGS += -P$(TOPLEVEL).TICK_DIV=200

include $(shell cocotb-config --makefiles)/Makefile.sim
