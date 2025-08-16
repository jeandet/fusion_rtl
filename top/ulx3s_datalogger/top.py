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
    )
]

class Top(BaseSoC):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.platform.add_extension(_extra_ios)
        # self.add_sdcard(sdcard_name="sdcard_1",software_debug=True)
        # self.add_sdcard(software_debug=True)
        # self.add_spi_sdcard(name="spisdcard_2")
        # self.add_spi_sdcard(software_debug=True)
        self.add_custom_spi(loopback=kwargs.get("custom_spi_loopback", False), no_clk_div=kwargs.get("custom_spi_no_clk_div", False))
        self.add_timer(name="timer1")
        self.add_adc()
        
    def add_custom_spi(self, software_debug=True, loopback=False, no_clk_div=False):
        from fusion_rtl.sdcard.spi import SPI 
        self.submodules.custom_spi = SPI(sys_clk_freq=self.sys_clk_freq, with_clk_div=not no_clk_div)
        if loopback:
            self.comb += [
                self.custom_spi.miso.eq(self.custom_spi.mosi)
            ]
        else:
            spi_pads = self.platform.request("spisdcard")
            self.comb += [
                spi_pads.mosi.eq(self.custom_spi.mosi),
                self.custom_spi.miso.eq(spi_pads.miso),
                spi_pads.cs_n.eq(self.custom_spi.cs),
                spi_pads.clk.eq(self.custom_spi.sck),
            ]
        self.add_constant("CUSTOM_SPI")
        if software_debug:
            self.add_constant("SPISDCARD_DEBUG")
        if no_clk_div:
            self.add_constant("SPISDCARD_NO_CLK_DIV")

    def add_adc(self):
        from fusion_rtl.adc import ADC
        
        self.submodules.adc = adc = ADC(
            sys_clk_freq=self.sys_clk_freq,
            oversampling=4,
            zone=2,
            target_freq=3e6,
            fifo_depth=4096,
            with_dma=True,
            soc=self,
            only_ch="cha"
        )
        self.add_constant("ADC_WITH_DMA")
        self.add_constant("ADC")
        for key, value in adc.defines.items():
            self.add_constant(key, value)
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
    parser.add_target_argument("--custom-spi-loopback", action="store_true", default=False, help="Enable custom SPI loopback mode.")
    parser.add_target_argument("--custom-spi-no-clk-div", action="store_true", default=True, help="Enable custom SPI no clock division mode, for faster data transfer.")
    args = parser.parse_args()
    soc = Top(
        device="LFE5U-85F",
        revision='2.0',
        toolchain= args.toolchain,
        sys_clk_freq=60e6,
        sdram_module_cls="IS42S16160",
        sdram_rate="1:2",
        custom_spi_loopback=args.custom_spi_loopback,
        custom_spi_no_clk_div=args.custom_spi_no_clk_div,
        **parser.soc_argdict)
    builder = Builder(soc, **parser.builder_argdict)
    if args.build:
        builder.build(**parser.toolchain_argdict)
    
    
if __name__ == "__main__":
    main()