#!/bin/env bash

ifndef container
  PODMAN=podman
else
  PODMAN=podman --remote
endif

TOP:=$(shell realpath --relative-to $(CURDIR)/../ $(CURDIR))
ROOT:=$(shell realpath $(CURDIR)/../..)
BIOS:=CUSTOM

ifeq (${BIOS}, CUSTOM)
  BIOS_DEP=build/app.bin
  INTEGRATED_ROM_INIT=--integrated-rom-init=build/app.bin
else ifeq (${BIOS}, DEFAULT)
  BIOS_DEP=
  INTEGRATED_ROM_INIT=
endif

# include cocotb's make rules to take care of the simulator setup

# include $(shell cocotb-config --makefiles)/Makefile.sim


bitstream:
	@echo "Using BIOS: $(BIOS)"
	$(PODMAN) run  --rm -t -v $(ROOT):/src:z -w /src/top/$(TOP) localhost/lpp/fusion_bitstream_builder  make BIOS=${BIOS} _bitstream

build/radiona_ulx3s/software/include/generated/variables.mak: Makefile
	@echo "Generating variables.mak"
	PYTHONPATH=/src PATH=/usr/bin:${PATH} python3 top.py --build --no-compile-gateware --integrated-rom-size=131072

build/radiona_ulx3s/gateware/radiona_ulx3s.bit: *.py /src/fusion_rtl/**/*.py Makefile ${BIOS_DEP}
	PYTHONPATH=/src PATH=/usr/bin:${PATH} python3 top.py --build ${INTEGRATED_ROM_INIT}

_bitstream: build/radiona_ulx3s/gateware/radiona_ulx3s.bit

bitstream-help:
	$(PODMAN) run --rm -t -v $(ROOT):/src:z -w /src/top/$(TOP) localhost/lpp/fusion_bitstream_builder  make _bitstream-help

_bitstream-help:
	PYTHONPATH=/src PATH=/usr/bin:${PATH} python3 top.py --help

sim:
	$(PODMAN) run --rm -t -v $(ROOT):/src:z -w /src/top/$(TOP) localhost/lpp/fusion_bitstream_builder  make _sim

_sim:
	PYTHONPATH=/src PATH=/usr/bin:${PATH} litex_sim --integrated-main-ram-size=0x10000 --cpu-type=vexriscv --no-compile-gateware

flash: bitstream
	openFPGALoader -b ulx3s -f build/radiona_ulx3s/gateware/radiona_ulx3s.bit

flash-ram: bitstream
	openFPGALoader -b ulx3s build/radiona_ulx3s/gateware/radiona_ulx3s.bit

clean:
	rm -rf __pycache__ *.pyc *.pyo results.xml build sim_build

all: bitstream

software:
	$(PODMAN) run --rm -t -v $(ROOT):/src:z -w /src/top/$(TOP) localhost/lpp/fusion_bitstream_builder  make _software

_software:build/app.bin

build/app.bin:Makefile software/* build/radiona_ulx3s/software/include/generated/variables.mak
	cd build && PYTHONPATH=/src PATH=/usr/bin:${PATH} python3 ../software/ulx3s_datalogger.py --build-path=radiona_ulx3s --mem=rom

help:
	@echo "Makefile targets:"
	@echo "  bitstream - Build the bitstream for the ULX3S board"
	@echo "  flash     - Flash the built bitstream to the ULX3S board"
	@echo "  clean     - Clean up generated files"

.PHONY: software
