#!/usr/bin/env python3

from migen import *
from litex.gen import *
from litex.build.generic_platform import *
from litex.build.lattice import LatticeECP5Platform
import os
import argparse

parser = argparse.ArgumentParser(description="Analog Two Top Module")
parser.add_argument("--sim", action="store_true", help="Produce simulation verilog")
args = parser.parse_args()


__HERE__ = os.path.abspath(os.path.dirname(__file__))

import sys

from fusion_rtl.platforms.fusion import AnalogTwoPlatform
from fusion_rtl.com.nor_interface import Stm32FmcNorInterface
from fusion_rtl.com.data_encoder import DataEncoder
from fusion_rtl.acquisition_pipeline import AcquisitionPipeline


class TopModule(LiteXModule):
    def __init__(
        self, platform, smp_clk_div=7, external_smp_clk=False, over_sampling=1, zone=2
    ):
        self.smp_clk_cntr = Signal(16, reset=0)
        self.sync += self.smp_clk_cntr.eq(self.smp_clk_cntr + 1)

        self.smp_clk = Signal()

        if external_smp_clk:
            self.comb += self.smp_clk.eq(platform.io3)
        else:
            self.comb += self.smp_clk.eq(self.smp_clk_cntr[smp_clk_div])

        self.acquisition_pipeline = AcquisitionPipeline(
            adc_count=2,
            fmc_data_width=platform.fmc_pads.data.nbits,
            fmc_address_width=platform.fmc_pads.address.nbits,
            fifo_depth=2048,
            fifo_count=48,
            use_chained_fifo=True,
            smp_clk_is_synchronous=not external_smp_clk,
            oversampling=over_sampling,
            zone=zone,
        )

        self.submodules += self.acquisition_pipeline

        platform.connect_adc1(self.acquisition_pipeline.adcs[0])
        platform.connect_adc2(self.acquisition_pipeline.adcs[1])

        self.acquisition_pipeline.nor_if.connect_data_pads(platform.fmc_pads.data)
        self.comb += self.acquisition_pipeline.nor_if.address.eq(
            platform.fmc_pads.address
        )
        self.comb += self.acquisition_pipeline.nor_if.ne.eq(platform.fmc_pads.ne)
        self.comb += self.acquisition_pipeline.nor_if.noe.eq(platform.fmc_pads.noe)
        self.comb += self.acquisition_pipeline.nor_if.nwe.eq(platform.fmc_pads.nwe)
        self.comb += self.acquisition_pipeline.smp_clk.eq(self.smp_clk)
        self.comb += platform.have_data.eq(self.acquisition_pipeline.have_data)


platform = AnalogTwoPlatform()
top = TopModule(platform, smp_clk_div=5, over_sampling=4, external_smp_clk=False, zone=2)
platform.register_main_clock(top)

# Build --------------------------------------------------------------------------------------------


if __name__ == "__main__":
    if args.sim:
        from migen.fhdl.verilog import convert

        convert(top).write("TopModule.v")
    else:
        platform.build(top)
