from litex.gen import *
from litex.soc.cores.clock.common import *
from migen.fhdl.specials import Tristate
from migen.genlib.fifo import SyncFIFO



class FifoOutputReg(LiteXModule):
    def __init__(self, width, fifo:SyncFIFO):
        self.re = Signal()
        self.readable = Signal()
        self.dout = Signal(width)
        
        self.sync += If(fifo.re , self.dout.eq(fifo.dout))
        self.sync += self.readable.eq(fifo.readable)
        self.comb += fifo.re.eq(self.re | (fifo.readable & ~self.readable))




class ft245(LiteXModule):
    def __init__(self, threshold, fifo_depth=2**14):
        self._data_r = Signal(8)
        self._data_w = Signal(8)
        self.rd = Signal()
        self.wr = Signal(reset=1)
        self.txf = Signal()
        self.data_oe = Signal()
        

        self.fifo_din = Signal(8)
        self.fifo_we = Signal()
        self.fifo_writable = Signal()
        self.fifo_has_enough_space = Signal()

        self._fifo_re = Signal(reset=0)

        self.fifo = SyncFIFO(width=8, depth=fifo_depth)
        self.submodules += self.fifo
        
        self.fifo_reg = FifoOutputReg(8, self.fifo)
        self.submodules += self.fifo_reg
        
        
        self.sync += self.fifo_has_enough_space.eq(self.fifo.level<(fifo_depth-threshold-1))
        
        self._connect(self.rd, 1)
        self._connect(self.data_oe, 1)
        self._connect(self._data_w, self.fifo_reg.dout)
        self._connect(self.fifo_reg.re, self._fifo_re)
        self._connect(self.fifo.din, self.fifo_din)
        self._connect(self.fifo.we, self.fifo_we)
        self._connect(self.fifo_writable, self.fifo.writable)
        
        self._tx = Signal(reset=0)
        
        self.comb += self._tx.eq(~self.txf  & self.fifo.readable)
        self.comb += self._fifo_re.eq(self._tx)
        self.comb += self.wr.eq(~self._tx)
        




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
