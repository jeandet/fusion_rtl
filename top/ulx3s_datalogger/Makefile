#!/bin/env bash

ifndef container
  PODMAN=podman
else
  PODMAN=podman --remote
endif

TOP:=$(shell realpath --relative-to $(CURDIR)/../ $(CURDIR))
ROOT:=$(shell realpath $(CURDIR)/../..)

# include cocotb's make rules to take care of the simulator setup

# include $(shell cocotb-config --makefiles)/Makefile.sim


bitstream:
	$(PODMAN) run  --rm -t -v $(ROOT):/src:z -w /src/top/$(TOP) localhost/lpp/fusion_bitstream_builder  make _bitstream


build/radiona_ulx3s/gateware/radiona_ulx3s.bit: *.py Makefile 
	PYTHONPATH=/src PATH=/usr/bin:${PATH} python3 top.py --build

_bitstream: build/radiona_ulx3s/gateware/radiona_ulx3s.bit

bitstream-help:
	$(PODMAN) run --rm -t -v $(ROOT):/src:z -w /src/top/$(TOP) localhost/lpp/fusion_bitstream_builder  make _bitstream-help

_bitstream-help:
	PYTHONPATH=/src PATH=/usr/bin:${PATH} python3 top.py --help

help:
	@echo "Makefile targets:"
	@echo "  bitstream - Build the bitstream for the ULX3S board"
	@echo "  flash     - Flash the built bitstream to the ULX3S board"
	@echo "  clean     - Clean up generated files"

flash: bitstream
	openFPGALoader -b ulx3s -f build/radiona_ulx3s/gateware/radiona_ulx3s.bit

clean:
	rm -rf __pycache__ *.pyc *.pyo results.xml build sim_build

all: bitstream