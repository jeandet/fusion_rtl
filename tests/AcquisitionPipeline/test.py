import math
import os
from random import getrandbits, randint
import numpy as np
import cocotb
from cocotb.binary import BinaryValue
from cocotb.clock import Clock
from cocotb.regression import TestFactory
from cocotb.triggers import RisingEdge, ReadOnly, Timer, FallingEdge
from cocotb.types import LogicArray


@cocotb.test()
async def test_AcquisitionPipeline(dut):
    clk = Clock(dut.sys_clk, 10, units="ns")
    clk_gen = cocotb.fork(clk.start())
    dut.sys_rst.value = 1
