from litex.gen import *
from litex.soc.cores.clock.common import *


class DataEncoder(LiteXModule):
    def __init__(self, adc_count=1):
        self.acd_data = [(Signal(16), Signal(16)) for _ in range(adc_count)]

        self.smp_clk = Signal()
        self._smp_clk = Signal()
        self.fifo_din = Signal(8)
        self.fifo_we = Signal()
        self.fifo_writable = Signal()
        self.fifo_has_enough_space = Signal()

        self.comb += self._smp_clk.eq(self.smp_clk)

        self._frame_counter = Signal(16, reset=0)

        self._frame = [Signal(8) for _ in range(4 + adc_count * 4)]

        self.sync += self._frame[0].eq(0xF0)
        self.sync += self._frame[1].eq(0x0F)
        self.sync += self._frame[2].eq(self._frame_counter[:8])
        self.sync += self._frame[3].eq(self._frame_counter[8:])
        self.header_size = 4
        for i in range(adc_count):
            self.sync += self._frame[(i * 4) + self.header_size].eq(
                self.acd_data[i][0][:8]
            )
            self.sync += self._frame[(i * 4) + self.header_size + 1].eq(
                self.acd_data[i][0][8:]
            )
            self.sync += self._frame[(i * 4) + self.header_size + 2].eq(
                self.acd_data[i][1][:8]
            )
            self.sync += self._frame[(i * 4) + self.header_size + 3].eq(
                self.acd_data[i][1][8:]
            )
            
        self.frame_cntr_fsm = FSM(reset_state="IDLE")
        self.frame_cntr_fsm.act(
            "IDLE",
            If(
                self._smp_clk,
                NextState("INC"),
            ),
        )
        self.frame_cntr_fsm.act(
            "INC",
            If(
                ~self._smp_clk,
                NextState("IDLE"),
                NextValue(self._frame_counter, self._frame_counter + 1),
            ),
        )


        self.fsm = FSM(reset_state="IDLE")
        self.fsm.act(
            "IDLE",
            NextValue(self.fifo_we, 0),
            If(
                self._smp_clk & self.fifo_has_enough_space,
                NextState("push_data_1"),
                NextValue(self.fifo_we, 1),
                NextValue(self.fifo_din, self._frame[0]),
            ),
        )
        for i in range(1, len(self._frame) - 1):
            self.fsm.act(
                f"push_data_{i}",
                NextValue(self.fifo_we, 1),
                NextValue(self.fifo_din, self._frame[i]),
                NextState(f"push_data_{i+1}"),
            )

        self.fsm.act(
            f"push_data_{len(self._frame)-1}",
            NextState("wait_for_smp_clk_low"),
            NextValue(self.fifo_din, self._frame[-1]),
            NextValue(self.fifo_we, 1),
        )
        self.fsm.act(
            "wait_for_smp_clk_low",
            NextValue(self.fifo_we, 0),
            If(
                ~self._smp_clk,
                NextState("IDLE"),
            ),
        )
        
    @property
    def frame_size(self):
        return len(self._frame)


class DataEncoder2(LiteXModule):
    def __init__(self, inputs):
        self.acd_data = [Signal(16) for _ in range(inputs)]
        self.adc_data_readable = Signal()
        self.adc_data_re = Signal(reset=0)

        self.fifo_din = Signal(8)
        self.fifo_we = Signal()
        self.fifo_writable = Signal()
        self.fifo_has_enough_space = Signal()

        self.frame_counter = Signal(16, reset=0)

        self.frame = [Signal(8) for _ in range(4 + inputs * 2)]

        self.comb += self.frame[0].eq(0xF0)
        self.comb += self.frame[1].eq(0x0F)
        self.sync += self.frame[2].eq(self.frame_counter[:8])
        self.sync += self.frame[3].eq(self.frame_counter[8:])
        self.header_size = 4
        for i in range(inputs):
            self.sync += self.frame[(i * 2) + self.header_size].eq(
                self.acd_data[i][:8]
            )
            self.sync += self.frame[(i * 2) + self.header_size + 1].eq(
                self.acd_data[i][8:]
            )
            
        self.frame_cntr_fsm = FSM(reset_state="IDLE")
        self.frame_cntr_fsm.act(
            "IDLE",
            If(
                self.adc_data_re,
                NextState("INC"),
            ),
        )
        self.frame_cntr_fsm.act(
            "INC",
            NextState("IDLE"),
            NextValue(self.frame_counter, self.frame_counter + 1),
        )


        self.fsm = FSM(reset_state="IDLE")
        self.fsm.act(
            "IDLE",
            If(
                self.adc_data_readable & self.fifo_has_enough_space,
                NextState("push_data_1"),
                NextValue(self.fifo_we, 1),
                NextValue(self.fifo_din, self.frame[0]),
            ).Else(NextValue(self.fifo_we, 0)),
            NextValue(self.adc_data_re, 0),
        )
        for i in range(1, len(self.frame) - 1):
            self.fsm.act(
                f"push_data_{i}",
                NextValue(self.fifo_we, 1),
                NextValue(self.fifo_din, self.frame[i]),
                NextState(f"push_data_{i+1}"),
            )

        self.fsm.act(
            f"push_data_{len(self.frame)-1}",
            NextState("ACK"),
            NextValue(self.fifo_din, self.frame[-1]),
            NextValue(self.fifo_we, 1),
            NextValue(self.adc_data_re, 1),
        )
        self.fsm.act(
            f"ACK",
            NextState("IDLE"),
            NextValue(self.fifo_we, 0),
            NextValue(self.adc_data_re, 0),
        )
        
        
    @property
    def frame_size(self):
        return len(self.frame)



if __name__ == "__main__":
    from migen.fhdl.verilog import convert

    convert(DataEncoder()).write("DataEncoder.v")
    convert(DataEncoder2(4)).write("DataEncoder2.v")
