from litex.gen import *
from litex.soc.cores.clock.common import *

class ECP5OSCG(LiteXModule):
    div_range  = (2, 128)
    base_freq = 310e6

    def __init__(self, target_freq=155e6):
        self.logger = logging.getLogger("ECP5OSCG")
        self.logger.info("Creating ECP5OSCG.")
        self.osc = ClockSignal()
        div = round(self.base_freq/target_freq)
        if self.div_range[0]<= div <= self.div_range[1]:
            self.frequency = self.base_freq/div
            self.logger.info(f"Computed DIV = {div}, resulting frequency = {self.frequency}")
            self.params     = {
                "p_DIV":div,
                "o_OSC":self.osc
                               }
            self.specials += Instance("OSCG", **self.params)
        else:
            raise ValueError(f"Computed div is out of range {self.div_range}")
        