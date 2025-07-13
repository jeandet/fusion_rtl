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

from PCB_LOB_platform import PCB_LOB_Platform
from ft245 import ft245

class Blink(LiteXModule):
    def __init__(self):
        self.led = Signal()
        self.counter = Signal(24)
        self.comb += self.led.eq(self.counter[23])
        self.sync += self.counter.eq(self.counter + 1)

class TopModule(LiteXModule):
    def __init__(self, platform):
        self.fifo_a = ft245(threshold=12, fifo_depth=2**8)
        self.submodules += self.fifo_a
        self.blink = Blink()
        self.submodules += self.blink
        

        self._cptr = Signal(self.fifo_a.fifo_din.nbits, reset=0)
        self.fsm = FSM(reset_state="IDLE")
        self.fsm.act(
            "IDLE",
            self.fifo_a.fifo_we.eq(0),
            If(self.fifo_a.fifo_writable, NextState("write_fifo")),
        )
        self.fsm.act(
            "write_fifo",
            NextState("IDLE"),
            self.fifo_a.fifo_we.eq(1),
            NextValue(self._cptr, self._cptr + 1),
        )
        self.comb += self.fifo_a.fifo_din.eq(self._cptr)
        self.comb += self.fifo_a.txf.eq(platform.FIFOA_pads.TXF)
        self.comb += platform.FIFOA_pads.WR.eq(self.fifo_a.wr)
        self.comb += platform.FIFOA_pads.RD.eq(self.fifo_a.rd)
        self.fifo_a.connect_data_pads(platform.FIFOA_pads.DATA)
        
        self.comb += platform.FIFOA_pads.OE.eq(1)
        self.comb += platform.FIFOA_pads.SIWU.eq(1)
        
        self.comb += platform.request("LED1").eq(self.blink.led)
        self.comb += platform.request("LED2").eq(self.fifo_a.wr)


platform = PCB_LOB_Platform()
top = TopModule(platform)

# Build --------------------------------------------------------------------------------------------

platform.build(top)
