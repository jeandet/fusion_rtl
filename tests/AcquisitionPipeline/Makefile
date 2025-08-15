TOP:=$(shell realpath --relative-to $(CURDIR)/../ $(CURDIR))

SIM ?= icarus
TOPLEVEL_LANG ?= verilog
WAVES = 1

VITALS_PATH = /usr/share/yosys/ecp5
VERILOG_INCLUDE_DIRS = $(VITALS_PATH)
VERILOG_SOURCES =  $(CURDIR)/build/AcquisitionPipeline.v $(VITALS_PATH)/cells_sim.v 

TOPLEVEL = top

MODULE = test

include $(shell cocotb-config --makefiles)/Makefile.sim

$(CURDIR)/build/AcquisitionPipeline.v: $(CURDIR)/../../HDL/acquisition_pipeline.py
	mkdir -p build
	cd build && PYTHONPATH=$(CURDIR)/../../HDL python $(CURDIR)/../../HDL/acquisition_pipeline.py



