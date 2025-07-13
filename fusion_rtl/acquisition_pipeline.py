from litex.gen import *
from litex.soc.cores.clock.common import *
from migen.genlib.fifo import SyncFIFO

from .com.nor_interface import Stm32FmcNorInterface
from .com.ft245 import ft245
from .adc.ads92x4 import Ads92x4
from .com.data_encoder import DataEncoder, DataEncoder2
from .memories.fifo_8_to_32_bits import Fifo8to32Bits
from .memories.fifo_to_fifo import Fifo_to_Fifo
from .memories.serialized_fifo import SerializeFifo


class ADCFifo(LiteXModule):
    def __init__(self, adc:Ads92x4, fifo_depth=256):
        self._fifos = [SyncFIFO(width=16, depth=fifo_depth), SyncFIFO(width=16, depth=fifo_depth)]
        self.submodules.fifo0 = self._fifos[0]
        self.submodules.fifo1 = self._fifos[1]
        self.readable = Signal()
        self.re = Signal(reset=0)
        self.data = [Signal(16), Signal(16)]
        self.comb += self._fifos[0].din.eq(adc.data_cha)
        self.comb += self._fifos[1].din.eq(adc.data_chb)
        for i in (0,1):
            self.comb += self.data[i].eq(self._fifos[i].dout)
            self.comb += self._fifos[i].re.eq(self.re)
        self.comb += self.readable.eq(self._fifos[0].readable)
        
        
        self.fsm = FSM(reset_state="IDLE")
        self.fsm.act("IDLE",
                     If(~adc.smp_clk_out & self._fifos[0].writable, NextState("READY")),
                     NextValue(self._fifos[0].we,0),
                     NextValue(self._fifos[1].we,0),
                     )
        self.fsm.act("READY",
                     If(adc.smp_clk_out, NextState("PUSH")),
                     )
        self.fsm.act("PUSH",
                     NextState("IDLE"),
                     NextValue(self._fifos[0].we,1),
                     NextValue(self._fifos[1].we,1),
                     )
        
        
        


class AcquisitionPipelineFront(LiteXModule):
    def __init__(
        self,
        adc_count,
        fifo_depth=2048,
        smp_clk_is_synchronous=True,
        oversampling=1,
        zone=2,
    ):
        self.smp_clk = Signal()
        self._data_encoder_has_enough_space = Signal()
        self.adcs = []
        self.adcs_fifos = []
        
        for i in range(adc_count):
            adc = Ads92x4(
                smp_clk_is_synchronous=smp_clk_is_synchronous,
                oversampling=oversampling,
                zone=zone,
            )
            self.adcs.append(adc)
            self.submodules+= adc
            self.comb += adc.smp_clk.eq(self.smp_clk)
            adc_fifo = ADCFifo(adc, fifo_depth=fifo_depth)
            self.adcs_fifos.append(adc_fifo)
            self.submodules += adc_fifo


        self.data_encoder = DataEncoder2(inputs=adc_count*2)
        self.submodules.data_encoder = self.data_encoder
        
        for i in range(adc_count):
            self.comb += self.data_encoder.acd_data[i*2].eq(self.adcs_fifos[i].data[0])
            self.comb += self.data_encoder.acd_data[(i*2)+1].eq(self.adcs_fifos[i].data[1])
            self.comb += self.adcs_fifos[i].re.eq(self.data_encoder.adc_data_re)
        
        self.comb += self.data_encoder.adc_data_readable.eq(self.adcs_fifos[0].readable)



class AcquisitionPipelineFT245(AcquisitionPipelineFront):
    def __init__(
        self,
        adc_count,
        fifo_depth=256,
        smp_clk_is_synchronous=True,
        oversampling=1,
        zone=2,
    ):
        super().__init__(
            adc_count=adc_count,
            fifo_depth=fifo_depth,
            smp_clk_is_synchronous=smp_clk_is_synchronous,
            oversampling=oversampling,
            zone=zone
        )
        self.ft245 = ft245(threshold=self.data_encoder.frame_size)
        self.submodules += self.ft245
        
        self.comb += self.ft245.fifo_din.eq(self.data_encoder.fifo_din)
        self.comb += self.ft245.fifo_we.eq(self.data_encoder.fifo_we)
        
        self.comb += self.data_encoder.fifo_has_enough_space.eq(self.ft245.fifo_has_enough_space)
        


class AcquisitionPipeline(LiteXModule):
    def __init__(
        self,
        adc_count,
        fmc_data_width=32,
        fmc_address_width=3,
        use_chained_fifo=True,
        fifo_depth=256,
        fifo_count=16,
        smp_clk_is_synchronous=True,
        oversampling=1,
        zone=2,
    ):
        self.smp_clk = Signal()
        self.have_data = Signal()

        self.nor_if = Stm32FmcNorInterface(
            data_width=fmc_data_width, address_width=fmc_data_width
        )
        self.submodules += self.nor_if
        self.adcs = [
            Ads92x4(
                smp_clk_is_synchronous=smp_clk_is_synchronous,
                oversampling=oversampling,
                zone=2,
            )
            for _ in range(adc_count)
        ]
        for adc in self.adcs:
            self.submodules += adc
            self.comb += adc.smp_clk.eq(self.smp_clk)

        self.data_encoder = DataEncoder(adc_count=adc_count)
        self.submodules.data_encoder = self.data_encoder

        for i, adc in enumerate(self.adcs):
            self.comb += self.data_encoder.acd_data[i][0].eq(adc.data_cha)
            self.comb += self.data_encoder.acd_data[i][1].eq(adc.data_chb)

        if use_chained_fifo:
            self.fifo_8bits = SerializeFifo(
                width=8, fifo_depth=fifo_depth, fifo_count=fifo_count
            )
        else:
            self.fifo_8bits = SyncFIFO(width=8, depth=fifo_depth * fifo_count)
        self.submodules += self.fifo_8bits

        self.comb += self.fifo_8bits.din.eq(self.data_encoder.fifo_din)
        self.comb += self.fifo_8bits.we.eq(self.data_encoder.fifo_we)
        self.comb += self.data_encoder.fifo_writable.eq(self.fifo_8bits.writable)

        self._fifo8to32 = Fifo8to32Bits()
        self.submodules += self._fifo8to32

        self.comb += self._fifo8to32.input_fifo_has_word.eq(self.fifo_8bits.level >= 4)
        self.comb += self._fifo8to32.din.eq(self.fifo_8bits.dout)
        self.comb += self.fifo_8bits.re.eq(self._fifo8to32.re)

        self.nor_if_has_enough_space = Signal()
        self.comb += self.nor_if_has_enough_space.eq(
            self.nor_if.level < self.nor_if.fifo.depth - 4
        )
        self.comb += self._fifo8to32.output_fifo_has_enough_space.eq(
            self.nor_if_has_enough_space
        )
        self.comb += self.nor_if.fifo_din.eq(self._fifo8to32.dout)
        self.comb += self.nor_if.fifo_we.eq(self._fifo8to32.we)
        self.comb += self.data_encoder.smp_clk.eq(self.adcs[0].smp_clk_out)

        self.comb += self.have_data.eq(self.nor_if.have_data)


if __name__ == "__main__":
    from migen.fhdl.verilog import convert

    convert(AcquisitionPipeline(adc_count=2, use_chained_fifo=False)).write(
        "AcquisitionPipeline.v"
    )
