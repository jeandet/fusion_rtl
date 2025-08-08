from migen import *
from migen.fhdl.structure import Cat
from migen.genlib.resetsync import AsyncResetSynchronizer

from litex.gen import *


from litex.soc.cores.dma import WishboneDMAWriter
from litex.soc.cores.clock import *
from litex.soc.interconnect.csr import CSRStorage, CSRStatus, CSRField, CSR, AutoCSR
from litex.soc.interconnect.csr import bits_for
from litex.soc.interconnect import stream
from litex.soc.interconnect import wishbone


from .ads92x4 import Ads92x4
from ..dsp.simple_iir import SimpleIIR
from ..streams import Stream2CSR, TestStreamCounter
from ..clk import ClkDiv


class ADC(LiteXModule):
    def __init__(self, sys_clk_freq, oversampling=1, zone=2, fifo_depth=4096, target_freq=3e6):
        """
        ADC module for interfacing with the ADS92x4 ADC chip.
        
        TODO: make it configurable to support different ADCs.
        
        :param sys_clk_freq: System clock frequency.
        :param oversampling: Oversampling factor (1, 2, or 4).
        :param zone: Zone for the ADC (1 or 2).
        :param fifo_depth: Depth of the FIFO buffer for ADC data.
        :param target_freq: Target frequency for the ADC clock, default is 3MHz (maximum for ADS92x4).
        """
        super().__init__()
        assert oversampling in [1, 2, 4], "Oversampling must be one of [1, 2, 4]"
        assert zone in [1, 2], "Zone must be one of [1, 2]"
        assert fifo_depth > 0, "FIFO depth must be greater than 0"
        assert target_freq > 0, "Target frequency must be greater than 0"
        assert target_freq <= 3e6, "Target frequency must be less than or equal to 3MHz for ADS92x4"
        
        self.sys_clk_freq = sys_clk_freq
        analog = Ads92x4(
            smp_clk_is_synchronous=True, oversampling=oversampling, zone=zone
        )
        self.pads = analog.pads
        self.data_cha = analog.data_cha
        self.data_chb = analog.data_chb
        self.smp_clk = analog.smp_clk_out
        self.reset = Signal(reset=1)
        self.enable = Signal(reset=0)
        self.overflow = Signal(reset=0)
        self._ctrl_reg = CSRStorage(1, reset=0)

        read_fifo = stream.SyncFIFO(
            layout=[
            ("data_a", 16),
            ("data_b", 16),
            ],
            depth=fifo_depth,
            buffered=True,
        )
        
        self._stream_to_csr = Stream2CSR(read_fifo.source)

        # Connect FIFO and CSR signals
        self.comb += [
            read_fifo.sink.data_a.eq(self.data_cha),
            read_fifo.sink.data_b.eq(self.data_chb),
        ]
        
        self._push_to_fifo_fsm = FSM(reset_state="IDLE")
        self._push_to_fifo_fsm.act("IDLE",
            If(self.smp_clk,
                read_fifo.sink.valid.eq(1),
                NextState("Wait for ready")
            )
        )
        self._push_to_fifo_fsm.act("Wait for ready",
            If(read_fifo.sink.ready,
                read_fifo.sink.valid.eq(0),
                NextState("IDLE")
            )
        )

        self.submodules += [analog, read_fifo]

        divisor = int(self.sys_clk_freq // target_freq)

        self.submodules.clk_div = clk_div = ClkDiv(MaxValue=divisor)
        self.comb += analog.smp_clk.eq(clk_div.clk_out)
