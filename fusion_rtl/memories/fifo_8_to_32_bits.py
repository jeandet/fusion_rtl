from litex.gen import *
from litex.soc.cores.clock.common import *


class Fifo8to32Bits(LiteXModule):
    def __init__(self):
        self.din = Signal(8)
        self.dout = Signal(32)
        self.input_fifo_has_word = Signal()
        self.re = Signal()
        self.we = Signal()
        self.readable = Signal()
        self.output_fifo_has_enough_space = Signal()

        self.fsm = FSM("IDLE")
        self.fsm.act(
            "IDLE",
            If(
                self.input_fifo_has_word & self.output_fifo_has_enough_space,
                NextState("read_byte_3"),
            ).Else(),
            NextValue(self.we, 0),
        )
        self.fsm.act(
            "read_byte_3",
            NextState("read_byte_2"),
            NextValue(self.dout[:8], self.din),
        )
        self.fsm.act(
            "read_byte_2",
            NextState("read_byte_1"),
            NextValue(self.dout[8:16], self.din),
        )
        self.fsm.act(
            "read_byte_1",
            NextState("write_word"),
            NextValue(self.dout[16:24], self.din),
        )
        self.fsm.act(
            "write_word",
            NextValue(self.dout[24:], self.din),
            NextState("IDLE"),
            NextValue(self.we, 1),
        )

        self.comb += self.re.eq(~self.fsm.ongoing("IDLE"))


if __name__ == "__main__":
    from migen.fhdl.verilog import convert

    convert(Fifo8to32Bits()).write("Fifo8to32Bits.v")
