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
from litex.soc.interconnect import wishbone

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
    (
        "sdcard_1", 0,
        Subsignal("clk",  Pins("J1"),Misc("DRIVE=8")),
        Subsignal("cmd",  Pins("J3"), Misc("PULLMODE=UP DRIVE=8")),
        Subsignal("data", Pins("K2 K1 H2 H1"), Misc("PULLMODE=UP DRIVE=8")),
        Misc("SLEWRATE=FAST"),
        IOStandard("LVCMOS33"),
    ),
    (
        "spisdcard_1", 0,
        Subsignal("clk",  Pins("J1"), Misc("DRIVE=8")),
        Subsignal("mosi", Pins("J3"), Misc("PULLMODE=UP DRIVE=8")),
        Subsignal("cs_n", Pins("H1"), Misc("PULLMODE=UP DRIVE=8")),
        Subsignal("miso", Pins("K2"), Misc("PULLMODE=UP DRIVE=8")),
        Misc("SLEWRATE=FAST"),
        IOStandard("LVCMOS33"),
    ),
    (
        "sdcard_2", 0,
        Subsignal("clk",  Pins("A4"), Misc("DRIVE=8")),
        Subsignal("cmd",  Pins("A6"), Misc("PULLMODE=UP DRIVE=8")),
        Subsignal("data", Pins("A2 C4 C8 C6"), 
                  Misc("PULLMODE=UP DRIVE=8")),
        IOStandard("LVCMOS33"),
        Misc("SLEW=FAST"),
    ),
    (
        "spisdcard_2", 0,
        Subsignal("clk",  Pins("A4")),
        Subsignal("mosi", Pins("A6"), Misc("PULLMODE=UP DRIVE=4")),
        Subsignal("cs_n", Pins("C6"), Misc("PULLMODE=UP DRIVE=4")),
        Subsignal("miso", Pins("A2"), Misc("PULLMODE=UP DRIVE=4")),
        Misc("SLEWRATE=FAST"),
        IOStandard("LVCMOS33"),
    ),
    
]

class Top(BaseSoC):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.platform.add_extension(_extra_ios)
        # self.add_sdcard(sdcard_name="sdcard_1",software_debug=True)
        # self.add_sdcard(software_debug=True)
        # self.add_spi_sdcard(name="spisdcard_2")
        self.add_spi_sdcard(software_debug=True)
        self.add_timer(name="timer1")
        self.add_adc()

    def add_adc(self):
        from fusion_rtl.adc import ADC
        
        self.submodules.adc = ADC(
            sys_clk_freq=self.sys_clk_freq,
            oversampling=1,
            zone=2,
            fifo_depth=16
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
        revision='2.0',
        toolchain= args.toolchain,
        sys_clk_freq=60e6,
        sdram_module_cls="IS42S16160",
        sdram_rate="1:2",
        **parser.soc_argdict)
    builder = Builder(soc, **parser.builder_argdict)
    if args.build:
        builder.build(**parser.toolchain_argdict)
    
    
if __name__ == "__main__":
    main()