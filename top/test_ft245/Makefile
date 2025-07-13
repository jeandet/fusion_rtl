ifeq ($(container),)
  PODMAN = podman
else
  PODMAN = podman --remote
endif

TOP:=$(shell realpath --relative-to $(CURDIR)/../ $(CURDIR))

# include cocotb's make rules to take care of the simulator setup
.PHONY: bitstream

# include $(shell cocotb-config --makefiles)/Makefile.sim


bitstream:
	$(PODMAN) run  --rm -t -v $(CURDIR)/../..:/src -w /src/top/$(TOP) localhost/lpp/fusion_bitstream_builder  python3 top.py


sim: bitstream
	$(MAKE) -f $(CURDIR)/Makefile.sim $@