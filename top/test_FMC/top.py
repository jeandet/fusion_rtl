#!/usr/bin/env python3

from migen import *
from litex.gen import *
from litex.build.generic_platform import *
from litex.build.lattice import LatticeECP5Platform
import os

__HERE__ = os.path.abspath(os.path.dirname(__file__))

import sys

sys.path.append(os.path.join(__HERE__, "../"))
sys.path.append(os.path.join(__HERE__, "../../HDL/"))

from fusion_platform import FusionPlatform
from nor_interface import Stm32FmcNorInterface


class TopModule(LiteXModule):
    def __init__(self, platform):
        self.nor_if = Stm32FmcNorInterface(pads=platform.fmc_pads)
        self.submodules += self.nor_if
        self.comb += platform.b2b_connector_pads.BANK7[11].eq(platform.fmc_pads.clk)
        self.comb += platform.b2b_connector_pads.BANK7[9].eq(platform.fmc_pads.ne)
        self.comb += platform.b2b_connector_pads.BANK7[7].eq(platform.fmc_pads.noe)
        self.comb += platform.b2b_connector_pads.BANK7[5].eq(self.nor_if._data_w[0])
        self.comb += platform.b2b_connector_pads.BANK7[3].eq(self.nor_if._data_w[1])

        self._cptr = Signal(self.nor_if.fifo_din.nbits, reset=0)
        self.fsm = FSM(reset_state="IDLE")
        self.fsm.act(
            "IDLE",
            self.nor_if.fifo_we.eq(0),
            If(self.nor_if.fifo_writable, NextState("write_fifo")),
        )
        self.fsm.act(
            "write_fifo",
            NextState("IDLE"),
            self.nor_if.fifo_we.eq(1),
            NextValue(self._cptr, self._cptr + 1),
        )
        self.comb += self.nor_if.fifo_din.eq(self._cptr)


platform = FusionPlatform()
top = TopModule(platform)
platform.register_main_clock(top)

# Build --------------------------------------------------------------------------------------------

platform.build(top)
