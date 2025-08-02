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

SMP_CLK ?= 3e6
ADC_ZONE ?= 2
ADC_OVERSAMPLING ?= 0

ARGS = --smp_clk=$(SMP_CLK) --adc_zone=$(ADC_ZONE) --adc_oversampling=$(ADC_OVERSAMPLING) #--external_smp_clk

bitstream:
	$(PODMAN) run  --rm -t -ePYTHONPATH=/src -v $(ROOT):/src:z -w /src/top/$(TOP) localhost/lpp/fusion_bitstream_builder  tabbypy3 top.py $(ARGS)

bitstream_lob:
	$(PODMAN) run  --rm -t -ePYTHONPATH=/src -v $(ROOT):/src:z -w /src/top/$(TOP) localhost/lpp/fusion_bitstream_builder  python3 top.py --smp_clk=3e6 --adc_zone=2 --adc_oversampling=0 --external_smp_clk

sim: 
	$(MAKE) -f $(CURDIR)/Makefile.sim $@

all: bitstream sim

clean:
	rm -rf __pycache__ *.pyc *.pyo results.xml build sim_build