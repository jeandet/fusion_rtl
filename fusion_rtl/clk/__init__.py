from migen import *
from litex.gen import *

class ClkDiv(LiteXModule):
    def __init__(self, MaxValue):
        assert 2*(MaxValue//2)==MaxValue
        self.clk_out = Signal(reset=0)
        self.counter = Signal(reset=0, max=(MaxValue//2)-1)
        self.sync += If(self.counter==0, self.clk_out.eq(~self.clk_out))
        self.sync += If(self.counter<((MaxValue//2)-1), self.counter.eq(self.counter + 1)).Else(self.counter.eq(0))