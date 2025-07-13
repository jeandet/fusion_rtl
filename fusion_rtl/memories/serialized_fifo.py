from litex.gen import *
from litex.soc.cores.clock.common import *
from migen.genlib.fifo import SyncFIFO


class FifoChainElement(LiteXModule):
    def __init__(self, width=32, fifo_depth=32, burst_size=8):
        self.we = Signal()
        self.next_fifo_we = Signal(reset=0)
        self.next_fifo_writable = Signal()
        self.next_fifo_level = Signal(max=fifo_depth)
        self.writable = Signal()
        self.din = Signal(width, reset_less=True)
        self.dout = Signal(width, reset_less=True)

        self._fifo = SyncFIFO(width=width, depth=fifo_depth)
        self.level = Signal(self._fifo.level.nbits)
        self.submodules.fifo = self._fifo

        self._has_enough_data = Signal()
        self._has_enough_space = Signal()

        self.comb += self._has_enough_data.eq(self._fifo.level >= burst_size)
        self.comb += self._has_enough_space.eq(
            self.next_fifo_level < fifo_depth - burst_size
        )

        self._fw = Signal(reset=0)
        self._burst_cptr = Signal(max=burst_size, reset=0)

        self.comb += self._fifo.we.eq(self.we)
        self.comb += self._fifo.re.eq(self._fw)
        self.sync += self.next_fifo_we.eq(self._fw)
        self.comb += self._fifo.din.eq(self.din)
        self.comb += self.writable.eq(self._fifo.writable)
        self.comb += self.level.eq(self._fifo.level)

        self.sync += self.dout.eq(self._fifo.dout)

        self.fsm = FSM(reset_state="IDLE")
        self.fsm.act(
            "IDLE",
            If(
                self._has_enough_data & self._has_enough_space,
                NextState("BURST"),
                NextValue(self._fw, 0),
            ).Else(
                NextValue(self._fw, 0),
            ),
            NextValue(self._burst_cptr, 0),
        )

        self.fsm.act(
            "BURST",
            If(
                self._burst_cptr == burst_size - 1,
                NextState("IDLE"),
                NextValue(self._burst_cptr, 0),
            ).Else(
                NextValue(self._fw, 1),
                NextValue(self._burst_cptr, self._burst_cptr + 1),
            ),
        )


class SerializeFifo(LiteXModule):
    def __init__(self, width=32, fifo_depth=32, fifo_count=4):
        assert fifo_count >= 2

        self.head = FifoChainElement(width=width, fifo_depth=fifo_depth)
        self.tail = SyncFIFO(width=width, depth=fifo_depth)

        precedent = self.head
        for i in range(fifo_count - 2):
            element = FifoChainElement(width=width, fifo_depth=fifo_depth)
            setattr(self.submodules, f"element_{i}", element)
            setattr(self, f"element_{i}", element)
            self.comb += element.we.eq(precedent.next_fifo_we)
            self.comb += precedent.next_fifo_writable.eq(element.writable)
            self.comb += precedent.next_fifo_level.eq(element.level)
            self.comb += element.din.eq(precedent.dout)
            precedent = element

        self.comb += self.tail.we.eq(precedent.next_fifo_we)
        self.comb += self.tail.din.eq(precedent.dout)
        self.comb += precedent.next_fifo_writable.eq(self.tail.writable)
        self.comb += precedent.next_fifo_level.eq(self.tail.level)

        self.dout = Signal(width)
        self.re = Signal()
        self.readable = Signal()
        self.level = Signal(self.tail.level.nbits)
        self.head_level = Signal(self.head.level.nbits)
        

        self.din = Signal(width)
        self.we = Signal()
        self.writable = Signal()

        self.comb += self.head.din.eq(self.din)
        self.comb += self.head.we.eq(self.we)
        self.comb += self.writable.eq(self.head.writable)

        self.comb += self.dout.eq(self.tail.dout)
        self.comb += self.tail.re.eq(self.re)
        self.comb += self.readable.eq(self.tail.readable)
        self.comb += self.level.eq(self.tail.level)
        self.comb += self.head_level.eq(self.head.level)
        


if __name__ == "__main__":
    from migen.fhdl.verilog import convert

    convert(SerializeFifo()).write("SerializeFifo.v")
