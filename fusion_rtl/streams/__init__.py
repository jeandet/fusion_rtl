from migen import Signal, If
from migen.fhdl.structure import Cat
from migen.genlib.fsm import FSM, NextState, NextValue
from litex.gen import LiteXModule

from litex.soc.cores.clock import *
from litex.soc.interconnect.csr import CSRStatus, AutoCSR, CSR
from litex.soc.interconnect import stream



class Stream2CSR(LiteXModule, AutoCSR):
    def __init__(self, stream_in, fifo_depth=4):
        payload_layout = stream_in.description.payload_layout
        data_width = sum(width for _, width in payload_layout)
        assert data_width <= 32, "Data width must be <= 32 bits"
        
        # CSR Interface
        self._data = CSRStatus(data_width, description="Data from stream")
        self._empty = CSRStatus(description="FIFO empty status")
        
        # Internal FIFO
        self.submodules.fifo = fifo = stream.SyncFIFO(payload_layout, fifo_depth)
        self.comb += stream_in.connect(fifo.sink)
        
        # Data register and control
        self.data_reg = Signal(data_width)
        
        self.submodules.pop_fsm = _pop_fsm = FSM(reset_state="IDLE")
        
        valid_and_cpu_read = Signal()
        self.comb += valid_and_cpu_read.eq(fifo.source.valid & self._data.we)
        
        _pop_fsm.act("IDLE",
            If(valid_and_cpu_read,
                NextValue(fifo.source.ready, 1),
                NextState("POP")
            ).Else(
                NextValue(self.data_reg, Cat(*[getattr(fifo.source, name) for name, _ in payload_layout])),
                NextValue(fifo.source.ready, 0)
            )
        )
        _pop_fsm.act("POP",
                NextState("IDLE"),
                NextValue(fifo.source.ready, 0)
        )

        
        # Drive outputs
        self.comb += [
            self._data.status.eq(self.data_reg),
            self._empty.status.eq(~fifo.source.valid),
        ]
        
        
        self.debug_fifo_source_valid = Signal()
        self.comb += [
            self.debug_fifo_source_valid.eq(fifo.source.valid),
        ]



class TestStreamCounter(LiteXModule, AutoCSR):
    def __init__(self):
        self.source = stream.Endpoint([("data", 32)])

        self.submodules.csr = strm2csr = Stream2CSR(self.source, fifo_depth=16)

        self.count = Signal(32, reset=0)
        
        self.sync += [
            If(self.source.ready,
                self.count.eq(self.count + 1)
            ),
            self.source.data.eq(self.count)
        ]
        
        self.comb += [
            self.source.valid.eq(1),
        ]
        


