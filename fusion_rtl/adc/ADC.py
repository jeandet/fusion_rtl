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


from .ads92x4 import Ads92x4_Stream_Avg
from ..dsp.simple_iir import SimpleIIR
from ..streams import Stream2CSR, TestStreamCounter
from ..clk import ClkDiv


class ADC(LiteXModule):
    def __init__(self, sys_clk_freq, oversampling=1, zone=2, fifo_depth=4096, target_freq=3e6, with_dma=False, soc=None, only_ch=None):
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
        assert only_ch in [None, 'a', 'b', 'cha', 'chb', 0, 1], "Invalid channel selection"

        self.sys_clk_freq = sys_clk_freq
        self.target_freq = target_freq
        self.sampling_freq = target_freq / oversampling
        self.oversampling = oversampling
        self.zone = zone
        

        self.enable = Signal(reset=0)
        self.overflow = Signal(reset=0)
        
        self.submodules.adc = adc = Ads92x4_Stream_Avg(
            smp_clk_is_synchronous=True, oversampling=oversampling, zone=zone, fifo_depth=fifo_depth
        )
        self.adc = adc
        self.pads = adc.pads

        self.source = adc.source

        self.add_clk_gen()
        self.add_enable_csr()
        if with_dma:
            self.add_dma_interface(soc, only_ch)
        else:
            self.add_stream_csr_interface()
            
        self.defines = {
            "ADC_OVERSAMPLING": oversampling,
            "ADC_ZONE": zone,
            "ADC_ACTIVE_CHANNEL_COUNT": 2 if only_ch is None else 1,
            "ADC_SAMPLING_FREQUENCY": int(self.sampling_freq),
            "ADC_FIFO_DEPTH": fifo_depth
        }

    def add_clk_gen(self):
        divisor = int(self.sys_clk_freq // self.target_freq)
        self.submodules.clk_div = clk_div = ClkDiv(MaxValue=divisor)
        self.comb += self.adc.smp_clk.eq(clk_div.clk_out)
        self.sampling_freq = self.sys_clk_freq / (divisor * self.oversampling)

    def add_enable_csr(self):
        self.enable_csr = CSRStorage(fields=[
            CSRField("enable", size=1, reset=0, description="Enable ADC data acquisition."),
        ], name="enable")

        self.comb += [
            self.enable.eq(self.enable_csr.fields.enable),
            self.adc.enable.eq(self.enable)
        ]

    def add_dma_interface(self, soc, only_ch):
        bus = wishbone.Interface(data_width=soc.bus.data_width, address_width=soc.bus.address_width, addressing='word')
        self.dma = WishboneDMAWriter(bus=bus, with_csr=True, endianness=soc.cpu.endianness)
        dma_bus = getattr(soc, "dma_bus", soc.bus)
        dma_bus.add_master(master=bus)
        
        if only_ch is None:
            self.comb += [
                self.dma.sink.data.eq(Cat(self.source.data_a, self.source.data_b)),
                self.dma.sink.valid.eq(self.source.valid),
                self.source.ready.eq(self.dma.sink.ready)
            ]
        else:
            self.submodules.up_conv = up_conv = stream.Converter(
                nbits_from=16,
                nbits_to=32
            )
            if only_ch.lower() in ('a', 'cha', 0):
                ch= self.source.data_a
            else:
                ch= self.source.data_b
            self.comb += [
                self.dma.sink.data.eq(up_conv.source.data),
                self.dma.sink.valid.eq(up_conv.source.valid),
                up_conv.source.ready.eq(self.dma.sink.ready),
                self.source.ready.eq(up_conv.sink.ready),
                up_conv.sink.valid.eq(self.source.valid),
                up_conv.sink.data.eq(ch)
            ]

    def add_stream_csr_interface(self):
        self._stream_to_csr = Stream2CSR(self.stream)