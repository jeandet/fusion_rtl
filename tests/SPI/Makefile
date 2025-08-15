ROOT:=$(shell realpath $(CURDIR)/../..)

SIM ?= icarus
TOPLEVEL_LANG ?= verilog
WAVES = 1

VITALS_PATH = /usr/share/yosys/ecp5
VERILOG_INCLUDE_DIRS = $(VITALS_PATH)
VERILOG_SOURCES =  $(CURDIR)/build/SPI.v $(VITALS_PATH)/cells_sim.v 
COMPILE_ARGS += -pfileline=1 -DICARUS_VCD

TOPLEVEL = top

MODULE = test

PYTHONPATH=$(ROOT)

$(CURDIR)/build/SPI.v: $(ROOT)/fusion_rtl/sdcard/spi.py
	mkdir -p build
	cd build && PYTHONPATH=$(PYTHONPATH) python $(ROOT)/fusion_rtl/sdcard/spi.py

include $(shell cocotb-config --makefiles)/Makefile.sim

