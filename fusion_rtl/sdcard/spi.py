from migen import *
from migen.fhdl.structure import Cat, Replicate
from migen.genlib.resetsync import AsyncResetSynchronizer

from litex.gen import *


from litex.soc.cores.dma import WishboneDMAWriter
from litex.soc.cores.clock import *
from litex.soc.interconnect.csr import CSRStorage, CSRStatus, CSRField, CSR, AutoCSR
from litex.soc.interconnect.csr import bits_for
from litex.soc.interconnect import stream

from fusion_rtl.clk import Counter

class _SERDES_WITH_CLK_DIV(LiteXModule):
    def __init__(self):
        self.clock = Signal()
        self.data_in = Signal(32, name="serdes_data_in")
        self.data_out = Signal(32, reset=0, name="serdes_data_out")
        self.sdo = Signal(reset=1, name="serdes_sdo")
        self.sdi = Signal(name="serdes_sdi")
        self.sck = Signal(name="serdes_sck")
        self.ready = Signal(reset=1, name="serdes_ready")
        self.start = Signal(name="serdes_start")
        self.bit_cntr = Signal(max=32, reset=0)

        self._sdi_reg = Signal(name="serdes_sdi_reg")
        self._shift_reg = Signal(32, name="serdes_shift_reg")
        
        self._bit_cntr = Signal(max=32, reset=0)

        self._clock_reg = Signal(name="serdes_clock_reg")
        self._clock_falling = Signal(name="serdes_clock_falling")
        self._clock_rising = Signal(name="serdes_clock_rising")

        self.sync += [
            self._clock_reg.eq(self.clock),
        ]
        self.comb += [
            self._clock_falling.eq(~self.clock & self._clock_reg),
            self._clock_rising.eq(self.clock & ~self._clock_reg)
        ]

        self.submodules.fsm = fsm = FSM(reset_state="IDLE")
        fsm.act(
            "IDLE",
            If(self.start,
                NextValue(self._bit_cntr, self.bit_cntr),
                NextValue(self._shift_reg, self.data_in),
                NextValue(self.ready, 0),
                NextState("LATCH"),
            ).Else(
                NextState("IDLE"),
                NextValue(self.data_out, self._shift_reg),
                NextValue(self.ready, 1)
            )
        )
        fsm.act("LATCH",
            If(self._clock_rising,
                NextState("SHIFT"),
                NextValue(self._sdi_reg, self.sdi),
            )
        )
        fsm.act(
            "SHIFT",
            If(
                self._clock_falling,
                If(
                    self._bit_cntr > 0,
                    NextValue(
                        self._shift_reg, Cat(self._sdi_reg, self._shift_reg[:-1])
                    ),
                    NextValue(self._bit_cntr, self._bit_cntr - 1),
                ).Else(
                    NextState("PAUSE"),
                    NextValue(
                        self._shift_reg, Cat(self._sdi_reg, self._shift_reg[:-1])
                    ),
                ),
            ).Elif(self._clock_rising,
                NextValue(self._sdi_reg, self.sdi),
            ),
        )
        fsm.act("PAUSE",
            If(self._clock_rising,
                NextState("IDLE"),
                NextValue(self.ready, 1),
                NextValue(self.data_out, self._shift_reg),
            )
        )
        
        self.comb += [
            self.sdo.eq(self._shift_reg[-1]),
            self.sck.eq(self._clock_reg & fsm.ongoing("SHIFT")),
        ]

class _SERDES_NO_CLK_DIV(LiteXModule):
    def __init__(self):
        self.clock = Signal()
        self.data_in = Signal(32, name="serdes_data_in")
        self.data_out = Signal(32, reset=0, name="serdes_data_out")
        self.sdo = Signal(reset=1, name="serdes_sdo")
        self.sdi = Signal(name="serdes_sdi")
        self.sck = Signal(name="serdes_sck")
        self.ready = Signal(reset=1, name="serdes_ready")
        self.start = Signal(name="serdes_start")
        self.bit_cntr = Signal(max=32, reset=0)

        self._shift_reg = Signal(32, name="serdes_shift_reg")
        
        self.submodules.fsm = fsm = FSM(reset_state="IDLE")

        fsm.act("IDLE",
            If(self.start,
                NextValue(self._shift_reg, self.data_in),
                NextValue(self.ready, 0),
                NextState("SHIFT"),
            ).Else(
                NextState("IDLE"),
                NextValue(self.data_out, self._shift_reg),
                NextValue(self.ready, 1)
            )
        )
        fsm.act(
            "SHIFT",
            If(self.bit_cntr > 0,
                NextValue(self._shift_reg, Cat(self.sdi, self._shift_reg[:-1])),
                NextValue(self.bit_cntr, self.bit_cntr - 1),
            ).Else(
                NextState("IDLE"),
                NextValue(self._shift_reg, Cat(self.sdi, self._shift_reg[:-1])),
            ),
        )
        
        self.comb += [
            self.sdo.eq(self._shift_reg[-1]),
            self.sck.eq(~self.clock & fsm.ongoing("SHIFT")),
        ]


class _SPIMaster(LiteXModule):
    def __init__(self, sys_clk_freq, with_clk_div=True):
        self.mosi = Signal()
        self.miso = Signal()
        self.cs = Signal(reset=1)
        self.sck = Signal()
        self.sckin = Signal()

        self.start8bits = Signal()
        self.start16bits = Signal()
        self.start32bits = Signal()

        self.ready = Signal(reset=0)
        
        self.data_wr_8 = Signal(8)
        self.data_wr_16 = Signal(16)
        self.data_wr_32 = Signal(32)

        self.data_rd = Signal(32)

        if with_clk_div:
            self.submodules.serdes = serdes = _SERDES_WITH_CLK_DIV()
        else:
            self.submodules.serdes = serdes = _SERDES_NO_CLK_DIV()

        self.submodules.fsm = fsm = FSM(reset_state="IDLE")
        fsm.act("IDLE",
            If(self.start8bits,
                NextValue(serdes.bit_cntr, 8-1),
                NextValue(serdes.start, 1),
                NextValue(serdes.data_in, Cat([0]*24, self.data_wr_8)),
                NextValue(self.ready, 0),
                NextState("WAIT_FOR_START"),
            ).Elif(self.start16bits,
                NextValue(serdes.bit_cntr, 16-1),
                NextValue(serdes.start, 1),
                NextValue(serdes.data_in, Cat([0]*16, self.data_wr_16)),
                NextValue(self.ready, 0),
                NextState("WAIT_FOR_START"),
            ).Elif(self.start32bits,
                NextValue(serdes.bit_cntr, 32-1),
                NextValue(serdes.start, 1),
                NextValue(serdes.data_in, Cat(self.data_wr_32)),
                NextValue(self.ready, 0),
                NextState("WAIT_FOR_START"),
            ).Else(
                NextValue(self.ready, 1),
                NextValue(serdes.start, 0)
            )
        )
        fsm.act(
            "WAIT_FOR_START",
            If(serdes.ready==0,
                NextState("SHIFT"),
                NextValue(serdes.start, 0)
            )
        )
        fsm.act("SHIFT",
            If(serdes.ready,
                NextState("IDLE"),
                NextValue(serdes.start, 0),
                NextValue(self.ready, 1)
            )
        )

        self.comb += [
            self.data_rd.eq(serdes.data_out),
            self.mosi.eq(serdes.sdo),
            self.sck.eq(serdes.sck),
            serdes.sdi.eq(self.miso),
            serdes.clock.eq(self.sckin),
            self.cs.eq(serdes.ready)
        ]


class SPI(LiteXModule):
    def __init__(self, sys_clk_freq, loopback=False, with_clk_div=True):
        self.mosi = Signal(name="mosi")
        self.miso = Signal(name="miso")
        self.cs = Signal(name="cs")
        self.sck = Signal(name="sck")
        self._sck = Signal()
        if loopback:
            self.comb += self.miso.eq(self.mosi)

        self.status_csr  = CSRStatus(fields=[CSRField("ready", reset=0)])
        self.control_csr = CSRStorage(
            fields=[
                CSRField("cs_auto", reset=1),
                CSRField("cs_value", reset=1)
                ]
            )
        if with_clk_div:
            self.clkdiv_csr = CSRStorage(
                fields=[
                    CSRField("clk_div", reset=7, size=log2_int(8))
                ]
            )

        self.data_read_csr = CSRStatus(32, name="spi_data_rd")
        self.data_write_8 = CSRStorage(32, name="spi_data_wr_8")
        self.data_write_16 = CSRStorage(32, name="spi_data_wr_16")
        self.data_write_32 = CSRStorage(32, name="spi_data_wr_32")

        self.submodules._spi = _SPIMaster(sys_clk_freq=sys_clk_freq, with_clk_div=with_clk_div)
        if with_clk_div:
            self.submodules.counter = counter = Counter(8)
            self._splitted_counter = Array([counter.counter[i] for i in range(8)])
            self.comb += [
                self.sck.eq(self._spi.sck),
                self._spi.sckin.eq(self._sck),
                self._sck.eq(self._splitted_counter[self.clkdiv_csr.fields.clk_div]),
            ]
        else:
            self.comb += [
                self.sck.eq(self._spi.sck),
                self._spi.sckin.eq(self._sck),
                self._sck.eq(ClockSignal("sys")),
            ]

        self.comb += [
            self._spi.start8bits.eq(self.data_write_8.re),
            self._spi.data_wr_8.eq(self.data_write_8.storage[0:8]),
            self._spi.start16bits.eq(self.data_write_16.re),
            self._spi.data_wr_16.eq(self.data_write_16.storage[0:16]),
            self._spi.start32bits.eq(self.data_write_32.re),
            self._spi.data_wr_32.eq(self.data_write_32.storage),
            
            self.data_read_csr.status.eq(self._spi.data_rd),
            
            self.status_csr.fields.ready.eq(self._spi.ready),
            
            
            self.mosi.eq(self._spi.mosi),
            self._spi.miso.eq(self.miso),
            If(self.control_csr.fields.cs_auto,
               self.cs.eq(self._spi.cs),
            ).Else(
               self.cs.eq(self.control_csr.fields.cs_value)
            ),
        ]
        
        
if __name__ == "__main__":
    import argparse
    from migen.fhdl.verilog import convert

    parser = argparse.ArgumentParser(description="Generate Verilog for SPI")
    parser.add_argument("--no-clk-div", action="store_true", help="Disable clock division")
    parser.add_argument("--output", type=str, default="SPI.v", help="Output file name")
    parser.add_argument("--output-dir", type=str, default=".", help="Output directory")
    args = parser.parse_args()

    convert(SPI(sys_clk_freq=60e6, loopback=False, with_clk_div=not args.no_clk_div)).write(f"{args.output_dir}/{args.output}")
