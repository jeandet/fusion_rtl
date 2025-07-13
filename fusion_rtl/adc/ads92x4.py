from litex.gen import *
from litex.soc.cores.clock.common import *


class Ads92x4(LiteXModule):
    def __init__(self, smp_clk_is_synchronous=True, oversampling=1, zone=2):
        super().__init__()
        self.smp_clk = Signal()
        self.smp_clk_out = Signal()
        self.data_cha = Signal(16)
        self.data_chb = Signal(16)
        self._ready_strobe_reg = Signal()

        self.pads = Record(
            [
                ("conv_st", 1),
                ("cs", 1),
                ("ready_strobe", 1),
                ("sclk", 1),
                ("mosi", 1),
                ("miso_a", 1),
                ("miso_b", 1),
            ]
        )

        self.read_cycles = Signal(5, reset=0)
        self.shift_reg_a = Signal(16, reset=0)
        self.shift_reg_b = Signal(16, reset=0)
        if oversampling == 2:
            averaging = 2
        elif oversampling == 4:
            averaging = 3
        else:
            averaging = 0
        self.config_reg = Signal(16, reset=0x1600 + averaging)

        self.comb += self.pads.conv_st.eq(self.smp_clk)
        self.comb += self.pads.mosi.eq(self.config_reg[-1])

        self._smp_clk = Signal()
        if smp_clk_is_synchronous:
            self.comb += self._smp_clk.eq(self.smp_clk)
        else:
            self._smp_clk_reg = Signal()
            self.sync += self._smp_clk_reg.eq(self.smp_clk)
            self.sync += self._smp_clk.eq(self._smp_clk_reg)

        if zone == 1:
            self.sync += self._ready_strobe_reg.eq(self.pads.ready_strobe)
        else:
            if oversampling == 1:
                self.comb += self._ready_strobe_reg.eq(1)
            else:
                self.sync += self._ready_strobe_reg.eq(self.pads.ready_strobe)

        self.fsm = FSM(reset_state="IDLE")
        self.fsm.act(
            "IDLE",
            NextValue(self.data_cha, self.shift_reg_a),
            NextValue(self.data_chb, self.shift_reg_b),
            NextValue(self.smp_clk_out, 1),
            NextValue(self.read_cycles, 0),
            NextValue(self.pads.cs, 1),
            If(self._smp_clk, NextState("WAIT_RDY")),
        )
        self.fsm.act(
            "WAIT_RDY",
            If(
                self._ready_strobe_reg,
                NextState("ASSERT_CS"),
                NextValue(self.pads.cs, 0),
                NextValue(self.smp_clk_out, 0),
            ),
        )
        self.fsm.act(
            "ASSERT_CS",
            NextState("READ"),
            NextValue(self.shift_reg_a, Cat(self.pads.miso_a, self.shift_reg_a[:-1])),
            NextValue(self.shift_reg_b, Cat(self.pads.miso_b, self.shift_reg_b[:-1])),
            NextValue(self.config_reg, Cat(1, self.config_reg[:-1])),
        )
        self.fsm.act(
            "READ",
            If(
                self.read_cycles == 15,
                NextState("ENSURE_SMP_CLK_LOW"),
                NextValue(self.pads.cs, 1),
                NextValue(self.read_cycles, 0),
            ).Else(
                NextValue(self.read_cycles, self.read_cycles + 1),
                NextValue(
                    self.shift_reg_a, Cat(self.pads.miso_a, self.shift_reg_a[:-1])
                ),
                NextValue(
                    self.shift_reg_b, Cat(self.pads.miso_b, self.shift_reg_b[:-1])
                ),
                NextValue(self.config_reg, Cat(1, self.config_reg[:-1])),
            ),
        )
        self.fsm.act(
            "ENSURE_SMP_CLK_LOW",
            NextValue(self.pads.cs, 1),
            If(
                ~self._smp_clk,
                NextState("IDLE"),
            ),
        )

        self.comb += self.pads.sclk.eq(ClockSignal() & self.fsm.ongoing("READ"))


if __name__ == "__main__":
    from migen.fhdl.verilog import convert

    convert(Ads92x4()).write("Ads92x4.v")
