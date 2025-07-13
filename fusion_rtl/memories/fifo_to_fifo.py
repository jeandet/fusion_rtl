from litex.gen import *
from litex.soc.cores.clock.common import *


class Fifo_to_Fifo(LiteXModule):
    def __init__(self, width):
        self.din = Signal(width)
        self.dout = Signal(width)
        self.input_fifo_has_word = Signal()
        self.re = Signal()
        self.we = Signal()
        self.readable = Signal()
        self.output_fifo_has_enough_space = Signal()
        
        self.comb += self.we.eq(self.input_fifo_has_word & self.output_fifo_has_enough_space)
        self.comb += self.re.eq(self.input_fifo_has_word & self.output_fifo_has_enough_space)
        

        self.comb += self.dout.eq(self.din)


if __name__ == "__main__":
    from migen.fhdl.verilog import convert

    convert(Fifo_to_Fifo()).write("Fifo_to_Fifo.v")
