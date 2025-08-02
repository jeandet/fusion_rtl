from migen import *
from migen.genlib.resetsync import AsyncResetSynchronizer

from litex.gen import *


from litex.soc.cores.clock import *
from litex.soc.interconnect.csr import *

from .ads92x4 import Ads92x4


class ADC(LiteXModule):
    def __init__(self, sys_clk_freq, oversampling=1, zone=2):
        super().__init__()
        self.sys_clk_freq = sys_clk_freq
        self.analog = Ads92x4(
            smp_clk_is_synchronous=True,
            oversampling=oversampling,
            zone=zone
        )
        self.pads = self.analog.pads
        self.data_cha = self.analog.data_cha
        self.data_chb = self.analog.data_chb
        self.smp_clk = self.analog.smp_clk_out
        self.reset = Signal(reset=1)
        self.enable = Signal(reset=0)
        self._CTRL_REG = CSRStorage(1, reset=0)
        self._DATA_REG = CSRStatus(fields=[
            CSRField("data_a", size=16, reset=0),
            CSRField("data_b", size=16, reset=0),
        ])
        self.comb += self._DATA_REG.fields.data_a.eq(self.data_cha)
        self.comb += self._DATA_REG.fields.data_b.eq(self.data_chb)
        self.submodules += self.analog
        
        # Clock generation for the ADC
        # We need to generate a ~3MHz clock for the ADC from the sys_clk.
        # The divisor is calculated based on the sys_clk frequency.
        # This module must be instantiated with the sys_clk_freq parameter.

        target_freq = 3e6  # Target ADC clock frequency ~3MHz
        divisor = int(self.sys_clk_freq // target_freq)

        # Ensure divisor is even for a 50% duty cycle
        if divisor % 2 != 0:
            divisor += 1

        smp_clk = Signal()
        counter = Signal(max=divisor)

        self.sync += [
            counter.eq(counter + 1),
            If(counter == (divisor // 2 - 1),
            smp_clk.eq(0)
            ).Elif(counter == (divisor - 1),
            smp_clk.eq(1),
            counter.eq(0)
            )
        ]
        self.comb += self.analog.smp_clk.eq(smp_clk)

        
        
        