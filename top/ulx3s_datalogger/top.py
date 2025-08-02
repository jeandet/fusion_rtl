from migen import *
from migen.genlib.resetsync import AsyncResetSynchronizer

from litex.gen import *

from litex.build.io import DDROutput

from litex_boards.platforms import radiona_ulx3s

from litex.build.generic_platform import *
from litex.soc.cores.clock import *
from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *

from litedram import modules as litedram_modules
from litedram.phy import GENSDRPHY, HalfRateGENSDRPHY

from litex_boards.targets.radiona_ulx3s import BaseSoC


_extra_ios = [
    ("ADC", 0,
         Subsignal(
                "ready_strobe",
                Pins("H18"),
            ),
            Subsignal(
                "conv_st",
                Pins("B17"),
            ),
            Subsignal(
                "cs",
                Pins("D17"),
            ),
            Subsignal(
                "sclk",
                Pins("D18"),
            ),
            Subsignal(
                "mosi",
                Pins("C18"),
            ),
            Subsignal(
                "miso_a",
                Pins("F17"),
            ),
            Subsignal(
                "miso_b",
                Pins("C17"),
            ),
    ),
]

class Top(BaseSoC):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.platform.add_extension(_extra_ios)
        self.add_sdcard()
        self.add_adc()

    def add_adc(self):
        from fusion_rtl.adc import ADC
        self.submodules.adc = ADC(
            sys_clk_freq=self.sys_clk_freq,
            oversampling=1,
            zone=2
        )
        adc_pads = self.platform.request("ADC")
        self.comb += [
            adc_pads.conv_st.eq(self.adc.pads.conv_st),
            adc_pads.cs.eq(self.adc.pads.cs),
            adc_pads.sclk.eq(self.adc.pads.sclk),
            adc_pads.mosi.eq(self.adc.pads.mosi),
            self.adc.pads.miso_a.eq(adc_pads.miso_a),
            self.adc.pads.miso_b.eq(adc_pads.miso_b),
            self.adc.pads.ready_strobe.eq(adc_pads.ready_strobe),
        ]
        self.add_csr("adc")
        
        


def main():
    from litex.build.parser import LiteXArgumentParser
    parser = LiteXArgumentParser(platform=radiona_ulx3s.Platform, description="LiteX SoC on ULX3S")
    args = parser.parse_args()
    soc = Top(
        device="LFE5U-85F",
        revision='1.7',
        toolchain= args.toolchain,
        sys_clk_freq=50e6,
        sdram_module_cls="IS42S16160",
        **parser.soc_argdict)
    builder = Builder(soc, **parser.builder_argdict)
    if args.build:
        builder.build(**parser.toolchain_argdict)
    
    
if __name__ == "__main__":
    main()