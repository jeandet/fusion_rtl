from litex.gen import *
from litex.soc.cores.clock.common import *
from migen.fhdl.specials import Tristate
from migen.genlib.fifo import SyncFIFO
from ..memories.serialized_fifo import SerializeFifo


class Stm32FmcNorInterface(LiteXModule):
    def __init__(self, data_width, address_width):
        self._data_r = Signal(data_width)
        self._data_w = Signal(data_width)
        self.address = Signal(address_width)
        self.ne = Signal()
        self.noe = Signal()
        self.nwe = Signal()
        self.data_oe = Signal()

        self.fifo_din = Signal(data_width)
        self.fifo_we = Signal()
        self.fifo_writable = Signal()

        self.have_data = Signal()

        self._fifo_re = Signal(reset=0)

        self.fifo = SyncFIFO(width=data_width, depth=64)
        self.level = Signal(self.fifo.level.nbits)
        self.comb += self.level.eq(self.fifo.level)
        
        self.submodules += self.fifo

        self.sync += self.have_data.eq(self.fifo.level >= 32)
        self._connect(self.data_oe, self.noe, invert=True)
        self._connect(self._data_w, self.fifo.dout)
        self._connect(self.fifo.re, self._fifo_re)
        self._connect(self.fifo.din, self.fifo_din)
        self._connect(self.fifo.we, self.fifo_we)
        self._connect(self.fifo_writable, self.fifo.writable)

        self.fsm = FSM(reset_state="IDLE")
        self.fsm.act(
            "IDLE", If(~self.ne, NextState("ADDR")), NextValue(self._fifo_re, 0)
        )
        self.fsm.act("ADDR", NextState("DATA"))
        self.fsm.act(
            "DATA",
            If(
                self.ne,
                NextState("IDLE"),
                NextValue(self._fifo_re, 1),
            ),
        )

    def _connect(self, a, b, invert=False):
        if invert:
            self.comb += a.eq(~b)
        else:
            self.comb += a.eq(b)

    def connect_data_pads(self, data_pads):
        for i in range(self._data_r.nbits):
            self.specials += Tristate(
                target=data_pads[i],
                o=self._data_w[i],
                oe=self.data_oe,
                i=self._data_r[i],
            )
