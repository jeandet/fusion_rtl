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
async def test_DataEncoder(dut):
    clk = Clock(dut.sys_clk, 10, units="ns")
    clk_gen = cocotb.fork(clk.start())
    smp_clk = Clock(dut.dataencoder_smp_clk, 100, units="ns")
    smp_clk_gen = cocotb.fork(smp_clk.start())
    dut.sys_rst.value = 1
    await Timer(100, units="ns")
    dut.sys_rst.value = 0
    dut.dataencoder_data_cha.value = 0x1234
    dut.dataencoder_data_chb.value = 0x5678
    await Timer(100, units="us")
