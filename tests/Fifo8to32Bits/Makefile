TOP:=$(shell realpath --relative-to $(CURDIR)/../ $(CURDIR))

SIM ?= icarus
TOPLEVEL_LANG ?= verilog
WAVES = 1

VITALS_PATH = /usr/share/yosys/ecp5
VERILOG_INCLUDE_DIRS = $(VITALS_PATH)
VERILOG_SOURCES =  $(CURDIR)/build/Fifo8to32Bits.v $(VITALS_PATH)/cells_sim.v 

TOPLEVEL = top

MODULE = test

$(CURDIR)/build/SerializeFifo.v: $(CURDIR)/../../HDL/fifo_8_to_32_bits.py
	mkdir -p build
	cd build && PYTHONPATH=$(CURDIR)/../../HDL python $(CURDIR)/../../HDL/fifo_8_to_32_bits.py

include $(shell cocotb-config --makefiles)/Makefile.sim

