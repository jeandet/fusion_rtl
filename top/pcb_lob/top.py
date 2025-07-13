#!/usr/bin/env python3

from migen import *
from litex.gen import *
from litex.build.generic_platform import *
from litex.build.lattice import LatticeECP5Platform
import os
import argparse

parser = argparse.ArgumentParser(description="Analog Two Top Module")
parser.add_argument("--sim", action="store_true", help="Produce simulation verilog")
parser.add_argument("--smp_clk", help="Target ADC sampling frequency",type=float, default=3e6)
parser.add_argument("--adc_zone", help="ADS92x4R zone", type=int, default=2, choices=[1,2])
parser.add_argument("--adc_oversampling", help="ADS92x4R oversampling", type=int, default=0, choices=[0,2,4])
parser.add_argument("--external_smp_clk", action="store_true", help="Use external sampling clock", default=False)

args = parser.parse_args()


__HERE__ = os.path.abspath(os.path.dirname(__file__))



from fusion_rtl.platforms.PCB_LOB import PCB_LOB_Platform
from fusion_rtl.acquisition_pipeline import AcquisitionPipelineFT245


class ClkDiv(LiteXModule):
    def __init__(self, MaxValue):
        assert 2*(MaxValue//2)==MaxValue
        self.clk_out = Signal(reset=0)
        self.counter = Signal(reset=0, max=(MaxValue//2)-1)
        self.sync += If(self.counter==0, self.clk_out.eq(~self.clk_out))
        self.sync += If(self.counter<((MaxValue//2)-1), self.counter.eq(self.counter + 1)).Else(self.counter.eq(0))

class Blink(LiteXModule):
    def __init__(self):
        self.led = Signal()
        self.counter = Signal(24)
        self.comb += self.led.eq(self.counter[23])
        self.sync += self.counter.eq(self.counter + 1)
        


class TopModule(LiteXModule):
    def __init__(
        self, platform, smp_clk_div=60, external_smp_clk=False, over_sampling=1, zone=2
    ):
        self.blink = Blink()
        self.submodules += self.blink
        self.clkdiv=ClkDiv(MaxValue=smp_clk_div)
        self.submodules+=self.clkdiv
        
        self.smp_clk = Signal()

        if external_smp_clk:
            self.comb += self.smp_clk.eq(platform.Trig1)
        else:
            self.comb += self.smp_clk.eq(self.clkdiv.clk_out)

        self.acquisition_pipeline = AcquisitionPipelineFT245(
            adc_count=2,
            fifo_depth=2**13,
            smp_clk_is_synchronous=not external_smp_clk,
            oversampling=over_sampling,
            zone=zone,
        )

        self.submodules += self.acquisition_pipeline

        platform.connect_adc1(self.acquisition_pipeline.adcs[0])
        platform.connect_adc2(self.acquisition_pipeline.adcs[1])
        
        self.comb += self.acquisition_pipeline.ft245.txf.eq(platform.FIFOA_pads.TXF)
        self.comb += platform.FIFOA_pads.WR.eq(self.acquisition_pipeline.ft245.wr)
        self.comb += platform.FIFOA_pads.RD.eq(self.acquisition_pipeline.ft245.rd)
        self.comb += platform.FIFOA_pads.OE.eq(1)
        self.comb += platform.FIFOA_pads.SIWU.eq(1)
        self.acquisition_pipeline.ft245.connect_data_pads(platform.FIFOA_pads.DATA)
        
        self.comb += platform.request("LED1").eq(self.blink.led)
        self.comb += platform.request("LED2").eq(self.acquisition_pipeline.ft245.wr)

        self.comb += self.acquisition_pipeline.smp_clk.eq(self.smp_clk)




# Build --------------------------------------------------------------------------------------------


if __name__ == "__main__":
    
    platform = PCB_LOB_Platform()
    smp_clk_div = round(1./(platform.default_clk_period*1e-9 * args.smp_clk))
    assert smp_clk_div > 1, "Sampling frequency too high"
    actual_sampling_frequency = 1./(platform.default_clk_period*1e-9 * smp_clk_div)
    error = 100*abs(actual_sampling_frequency - args.smp_clk)/args.smp_clk
    assert error < 1, f"Sampling frequency too far from target, error: {error}%, actual: {actual_sampling_frequency/1e3} KHz target: {args.smp_clk/1e3} KHz"
    print(f"Actual sampling frequency: {actual_sampling_frequency/1e3} KHz")
    
    top = TopModule(platform, smp_clk_div=smp_clk_div, zone=args.adc_zone, over_sampling=args.adc_oversampling, external_smp_clk=args.external_smp_clk)
    
    if args.sim:
        from migen.fhdl.verilog import convert

        convert(top).write("TopModule.v")
    else:
        platform.build(top)

        print(f"Actual sampling frequency: {actual_sampling_frequency/1e3} KHz")