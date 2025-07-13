TOP:=$(shell realpath --relative-to $(CURDIR)/../ $(CURDIR))

SIM ?= icarus
TOPLEVEL_LANG ?= verilog
WAVES = 1

VITALS_PATH = /usr/share/yosys/ecp5
VERILOG_INCLUDE_DIRS = $(VITALS_PATH)
VERILOG_SOURCES =  $(CURDIR)/build/Ads92x4.v $(VITALS_PATH)/cells_sim.v 

TOPLEVEL = top

MODULE = test

$(CURDIR)/build/Ads92x4.v: $(CURDIR)/../../HDL/ads92x4.py
	mkdir -p build
	cd build && PYTHONPATH=$(CURDIR)/../../HDL python $(CURDIR)/../../HDL/ads92x4.py

include $(shell cocotb-config --makefiles)/Makefile.sim

