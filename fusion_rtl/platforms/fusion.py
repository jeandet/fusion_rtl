#!/usr/bin/env python3

from migen import *

from litex.build.generic_platform import *
from litex.build.lattice import LatticeECP5Platform
import os

__HERE__ = os.path.abspath(os.path.dirname(__file__))


from ..ecp5.ecp5_clock import *

# IOs ----------------------------------------------------------------------------------------------

_io = [
    ("reset", 0, Pins("34"), IOStandard("LVCMOS33")),
    ("LED", 0, Pins("2"), IOStandard("LVCMOS33")),
    ("have_data", 0, Pins("68"), IOStandard("LVCMOS33")),
    (
        "FMC",
        0,
        Subsignal(
            "data",
            Pins(
                "97",
                "95",
                "91",
                "92",
                "39",
                "40",
                "41",
                "44",
                "45",
                "50",
                "51",
                "52",
                "108",
                "102",
                "99",
                "98",
                "107",
                "106",
                "105",
                "104",
                "103",
                "88",
                "84",
                "82",
                "81",
                "80",
                "78",
                "79",
                "77",
                "76",
                "73",
                "74",
            ),
        ),
        Subsignal("address", Pins("72", "71", "69")),
        Subsignal("noe", Pins("90")),
        Subsignal("ne", Pins("89")),
        Subsignal("nwe", Pins("94")),
        Subsignal("clk", Pins("93")),
        IOStandard("LVCMOS33"),
    ),
]


def build_io():
    return _io + [
        (
            "B2B_CONNECTOR",
            0,
            Subsignal(
                "BANK0",
                Pins(
                    "128", "133", "134", "135", "136", "139", "140", "141", "142", "143"
                ),
            ),
            Subsignal(
                "BANK1",
                Pins(
                    "110",
                    "111",
                    "112",
                    "113",
                    "114",
                    "115",
                    "116",
                    "117",
                    "118",
                    "119",
                    "120",
                    "121",
                    "124",
                    "125",
                    "126",
                    "127",
                ),
            ),
            Subsignal(
                "BANK6",
                Pins("18", "19", "22", "23", "24", "25"),
            ),
            Subsignal(
                "BANK7",
                Pins("1", "2", "3", "4", "5", "6", "7", "10", "11", "12", "13", "14"),
            ),
            IOStandard("LVCMOS33"),
        ),
    ]


# Platform -----------------------------------------------------------------------------------------


class FusionPlatform(LatticeECP5Platform):
    def __init__(self, io=None):
        super().__init__("LFE5U-12F-6TQFP144", io or build_io(), toolchain="trellis")
        self.use_default_clk = False
        self.fmc_pads = self.request("FMC")
        try:
            self.b2b_connector_pads = self.request("B2B_CONNECTOR")
        except ConstraintError:
            pass
        self.clk_mod = Module()
        self.reset = self.request("reset")
        self.clk_mod.fmc_clk = ClockDomain("sys")
        self.clk_mod.clock_domains += self.clk_mod.fmc_clk
        self.clk_mod.comb += self.clk_mod.fmc_clk.clk.eq(self.fmc_pads.clk)
        self.clk_mod.comb += self.clk_mod.fmc_clk.rst.eq(~self.reset)
        self.have_data = self.request("have_data")
        self.add_period_constraint(self.fmc_pads.clk, 1e9 / 100e6)

    def register_main_clock(self, module):
        module.submodules.clk_gen = self.clk_mod


def analog_two_build_io():
    return _io + [
        ("IO3", 0, Pins("25"), IOStandard("LVCMOS33")),
        ("IO2", 0, Pins("23"), IOStandard("LVCMOS33")),
        (
            "ADC1",
            0,
            Subsignal(
                "ready_strobe",
                Pins("143"),
            ),
            Subsignal(
                "conv_st",
                Pins("135"),
            ),
            Subsignal(
                "cs",
                Pins("134"),
            ),
            Subsignal(
                "sclk",
                Pins("136"),
            ),
            Subsignal(
                "mosi",
                Pins("139"),
            ),
            Subsignal(
                "miso_a",
                Pins("140"),
            ),
            Subsignal(
                "miso_b",
                Pins("141"),
            ),
            IOStandard("LVCMOS33"),
        ),
        (
            "ADC2",
            0,
            Subsignal(
                "ready_strobe",
                Pins("116"),
            ),
            Subsignal(
                "conv_st",
                Pins("110"),
            ),
            Subsignal(
                "cs",
                Pins("111"),
            ),
            Subsignal(
                "sclk",
                Pins("113"),
            ),
            Subsignal(
                "mosi",
                Pins("112"),
            ),
            Subsignal(
                "miso_a",
                Pins("115"),
            ),
            Subsignal(
                "miso_b",
                Pins("114"),
            ),
            IOStandard("LVCMOS33"),
        ),
    ]


class AnalogTwoPlatform(FusionPlatform):
    def __init__(self, internal_smp_clk=True):
        super().__init__(io=analog_two_build_io())
        self.adc1_pads = self.request("ADC1")
        self.adc2_pads = self.request("ADC2")
        self.io3 = self.request("IO3")
        self.io2 = self.request("IO2")

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
