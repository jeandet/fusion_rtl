
""")
        */
        const double b[3][3]
           = { { 0.0003093761776877881, 0.00027126310014594703, 0.00030937617768778814 },
                { 1.0, -0.9780833528217364, 1.0 }, { 1.0, -1.3786886998937251, 1.0 } };
        const double a[3][3] = { { 1.0, -1.449543617902121, 0.5298911166658338 },
           { 1.0, -1.570227988783793, 0.6515750588208723 },
           { 1.0, -1.7779954896683987, 0.8644540496942458 } };
        double ctx[3][3] = { { 0. } };
"""


from migen import *
from migen.genlib.resetsync import AsyncResetSynchronizer

from litex.gen import *

from litex.soc.cores.clock import *
from litex.soc.interconnect.csr import bits_for


def float_to_fixed(val, frac_bits):
    return int(round(val * (2**frac_bits)))


class _multiply_add(LiteXModule):
    def __init__(self, size_1=16, size_2=16):
        super().__init__()
        self.a = Signal(size_1)
        self.b = Signal(size_2)
        self.output = Signal(size_1 + size_2)

        self.comb += self.output.eq(self.a * self.b)
        
        

class _IIR_Stage(LiteXModule):
    def __init__(self, b, a, frac_bits=14):
        super().__init__()
        self.b = [float_to_fixed(c, frac_bits) for c in b]
        self.a = [float_to_fixed(c, frac_bits) for c in a]
        self.ctx = [Signal(16, reset=0) for _ in range(3)]
        self.input = Signal(16)
        self.output = Signal(16)
        self.smp_clk = Signal()
        
        self.multiply_add = _multiply_add(size_1=16, size_2=16)
        self.submodules += self.multiply_add
        
        self.fsm = FSM(reset_state="IDLE")
        self.submodules += self.fsm
        self.fsm.act("IDLE",
            If(self.smp_clk,
                NextState("PROCESS")
            )
        )
        self.fsm.act("PROCESS",
            self.ctx[0].eq(self.input),
            self.ctx[0].eq(self.ctx[0] * self.b[0] + self.ctx[1] * self.b[1] + self.ctx[2] * self.b[2]),
            self.ctx[1].eq(self.ctx[0]),
            self.ctx[1].eq(self.ctx[1] * self.b[0] + self.ctx[1] * self.b[1] + self.ctx[2] * self.b[2]),
            self.ctx[2].eq(self.ctx[1]),
            self.ctx[2].eq(self.ctx[2] * self.b[0] + self.ctx[2] * self.b[1] + self.ctx[2] * self.b[2]),
            self.output.eq(int(self.ctx[2] * self.a[0] + self.ctx[1] * self.a[1] + self.ctx[2] * self.a[2])),
            NextState("Wait_smp_clk_low")
        )
        self.fsm.act("Wait_smp_clk_low",
            If(~self.smp_clk,
                NextState("IDLE")
            )
        )       


class SimpleIIR(LiteXModule):
    def __init__(self, frac_bits=14):
        super().__init__()


        self.input = Signal(16)
        self.output = Signal(16)
        self.smp_clk = Signal()
        
        self.stages = [
            _IIR_Stage(
                b=[0.0003093761776877881, 0.00027126310014594703, 0.00030937617768778814],
                a=[1.0, -1.449543617902121, 0.5298911166658338],
                frac_bits=frac_bits
            ),
            _IIR_Stage(
                b=[1.0, -0.9780833528217364, 1.0],
                a=[1.0, -1.570227988783793, 0.6515750588208723],
                frac_bits=frac_bits
            ),
            _IIR_Stage(
                b=[1.0, -1.3786886998937251, 1.0],
                a=[1.0, -1.7779954896683987, 0.8644540496942458],
                frac_bits=frac_bits
            )
        ]
        
        self.comb += [
            self.stages[0].input.eq(self.input),
            self.stages[0].smp_clk.eq(self.smp_clk),
            self.stages[1].input.eq(self.stages[0].output),
            self.stages[1].smp_clk.eq(self.smp_clk),
            self.stages[2].input.eq(self.stages[1].output),
            self.stages[2].smp_clk.eq(self.smp_clk),
            self.output.eq(self.stages[2].output)
        ]   
        self.submodules += self.stages
        
        
