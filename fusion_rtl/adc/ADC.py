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


from .ads92x4 import Ads92x4_Stream
from ..dsp.simple_iir import SimpleIIR
from ..streams import Stream2CSR, TestStreamCounter
from ..clk import ClkDiv


class ADC(LiteXModule):
    def __init__(self, sys_clk_freq, oversampling=1, zone=2, fifo_depth=4096, target_freq=3e6, with_dma=False, soc=None):
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
        self.submodules.analog =analog = Ads92x4_Stream(
            smp_clk_is_synchronous=True, oversampling=oversampling, zone=zone, fifo_depth=fifo_depth
        )
        self.pads = analog.pads
        self.enable = Signal(reset=0)
        self.overflow = Signal(reset=0)
        self.enable_csr = CSRStorage(fields=[
            CSRField("enable", size=1, reset=0, description="Enable ADC data acquisition."),
        ])

        self.comb += [
            self.enable.eq(self.enable_csr.fields.enable),
            self.analog.enable.eq(self.enable)
        ]

        if not with_dma:
            self._stream_to_csr = Stream2CSR(analog.read_fifo.source)
        else:
            bus = wishbone.Interface(
                        data_width = soc.bus.data_width,
                        adr_width  = soc.bus.get_address_width(standard="wishbone"),
                        addressing = "word",
                    )
            self._dma_writer = WishboneDMAWriter(bus=bus, with_csr=True, endianness=soc.cpu.endianness)
            self.comb += [
                self._dma_writer.sink.data.eq(Cat(analog.read_fifo.source.data_a, analog.read_fifo.source.data_b)),
                self._dma_writer.sink.valid.eq(analog.read_fifo.source.valid),
                analog.read_fifo.source.ready.eq(self._dma_writer.sink.ready)
            ]
            dma_bus = getattr(soc, "dma_bus", soc.bus)
            dma_bus.add_master(master=bus)
            

        divisor = int(self.sys_clk_freq // target_freq)

        self.submodules.clk_div = clk_div = ClkDiv(MaxValue=divisor)
        self.comb += analog.smp_clk.eq(clk_div.clk_out)
