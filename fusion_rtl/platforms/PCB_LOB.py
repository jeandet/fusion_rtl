#!/usr/bin/env python3

from migen import *
from migen.genlib.resetsync import AsyncResetSynchronizer

from litex.soc.cores.clock import *
from litex.build.generic_platform import *
from litex.build.lattice import LatticeECP5Platform

import os

__HERE__ = os.path.abspath(os.path.dirname(__file__))

from ..ecp5.ecp5_clock import *


# IOs ----------------------------------------------------------------------------------------------

_io = [
    #("reset", 0, Pins("34"), IOStandard("LVCMOS33")),
    ("LED1", 0, Pins("107"), IOStandard("LVCMOS33")),
    ("LED2", 0, Pins("106"), IOStandard("LVCMOS33")),
    ("clk", 0, Pins("88"), IOStandard("LVCMOS33")),
    ("ftdi_clk", 0, Pins("128"), IOStandard("LVCMOS33")),
    ("Trig0", 0, Pins("95"), IOStandard("LVCMOS33")),
    ("Trig1", 0, Pins("94"), IOStandard("LVCMOS33")),
]


# Platform -----------------------------------------------------------------------------------------


def io():
    return _io + [
        (
            "ADC1",
            0,
            Subsignal(
                "ready_strobe",
                Pins("48"),
            ),
            Subsignal(
                "conv_st",
                Pins("28"),
            ),
            Subsignal(
                "cs",
                Pins("30"),
            ),
            Subsignal(
                "sclk",
                Pins("33"),
            ),
            Subsignal(
                "mosi",
                Pins("31"),
            ),
            Subsignal(
                "miso_a",
                Pins("45"),
            ),
            Subsignal(
                "miso_b",
                Pins("39"),
            ),
            IOStandard("LVCMOS33"),
        ),
        (
            "ADC2",
            0,
            Subsignal(
                "ready_strobe",
                Pins("81"),
            ),
            Subsignal(
                "conv_st",
                Pins("67"),
            ),
            Subsignal(
                "cs",
                Pins("68"),
            ),
            Subsignal(
                "sclk",
                Pins("71"),
            ),
            Subsignal(
                "mosi",
                Pins("69"),
            ),
            Subsignal(
                "miso_a",
                Pins("80"),
            ),
            Subsignal(
                "miso_b",
                Pins("76"),
            ),
            IOStandard("LVCMOS33"),
        ),
        (
            "FIFOA",
            0,
            Subsignal(
                "RD",
                Pins("140"),
            ),
            Subsignal(
                "WR",
                Pins("136"),
            ),
            Subsignal(
                "TXF",
                Pins("142"),
            ),
            Subsignal(
                "OE",
                Pins("126"),
            ),
            Subsignal(
                "SIWU",
                Pins("134"),
            ),
            Subsignal(
                "DATA",
                Pins("3", "2", "1", "127", "133", "135", "139", "141"),
            ),
        ),
        (
            "FIFOB",
            0,
            Subsignal(
                "RD",
                Pins("125"),
            ),
            Subsignal(
                "WR",
                Pins("112"),
            ),
            Subsignal(
                "TXF",
                Pins("121"),
            ),
            Subsignal(
                "DATA",
                Pins("124", "120", "118", "116", "114", "113", "115", "117"),
            ),
        )
    ]


class PCB_LOB_Platform(LatticeECP5Platform):
    #default_clk_name   = "clk"
    #default_clk_period = 1e9/50e6
    
    default_clk_name   = "ftdi_clk"
    default_clk_period = 1e9/60e6
    
    def __init__(self, internal_smp_clk=True):
        super().__init__("LFE5U-12F-6TQFP144", io(), toolchain="trellis")
        self.adc1_pads = self.request("ADC1")
        self.adc2_pads = self.request("ADC2")
        self.FIFOA_pads = self.request("FIFOA")
        self.FIFOB_pads = self.request("FIFOB")
        self.Trig0 = self.request("Trig0")
        self.Trig1 = self.request("Trig1")
        

    def connect_adc1(self, adc1):
        adc1.comb += adc1.pads.ready_strobe.eq(self.adc1_pads.ready_strobe)
        adc1.comb += self.adc1_pads.conv_st.eq(adc1.pads.conv_st)
        adc1.comb += self.adc1_pads.cs.eq(adc1.pads.cs)
        adc1.comb += self.adc1_pads.sclk.eq(adc1.pads.sclk)
        adc1.comb += self.adc1_pads.mosi.eq(adc1.pads.mosi)
        adc1.comb += adc1.pads.miso_a.eq(self.adc1_pads.miso_a)
        adc1.comb += adc1.pads.miso_b.eq(self.adc1_pads.miso_b)

    def connect_adc2(self, adc2):
        adc2.comb += adc2.pads.ready_strobe.eq(self.adc2_pads.ready_strobe)
        adc2.comb += self.adc2_pads.conv_st.eq(adc2.pads.conv_st)
        adc2.comb += self.adc2_pads.cs.eq(adc2.pads.cs)
        adc2.comb += self.adc2_pads.sclk.eq(adc2.pads.sclk)
        adc2.comb += self.adc2_pads.mosi.eq(adc2.pads.mosi)
        adc2.comb += adc2.pads.miso_a.eq(self.adc2_pads.miso_a)
        adc2.comb += adc2.pads.miso_b.eq(self.adc2_pads.miso_b)


# Design -------------------------------------------------------------------------------------------
