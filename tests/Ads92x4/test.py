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


def cha_value(index):
    return int(np.cos(2 * np.pi * index / 16) * 32765)


def chb_value(index):
    return index & 0xFFFF


async def emulate_adc(dut):
    index = 0
    while True:
        await RisingEdge(dut.pads_conv_st)
        await Timer(315, units="ns")
        dut.pads_ready_strobe.value = 1
        if dut.pads_cs == 1:
            await FallingEdge(dut.pads_cs)
        dut.pads_ready_strobe.value = 0
        await Timer(12, units="ns")
        value_cha = cha_value(index)
        value_chb = chb_value(index)
        for i in range(16):
            dut.pads_miso_a.value = (value_cha >> (15 - i)) & 1
            dut.pads_miso_b.value = (value_chb >> (15 - i)) & 1
            await RisingEdge(dut.pads_sclk)
            await Timer(15.8, units="ns")

        index += 1


@cocotb.test()
async def test_Ads92x4(dut):
    dut.pads_ready_strobe.value = 0
    adc = cocotb.start_soon(emulate_adc(dut))
    clk_gen = cocotb.start_soon(Clock(dut.sys_clk, 16.7, units="ns").start())
    smp_clk = Clock(dut.smp_clk, 0.666, units="us")
    smp_clk_gen = cocotb.start_soon(smp_clk.start())
    dut.sys_rst.value = 1
    await Timer(100, units="ns")
    dut.sys_rst.value = 0
    values = []
    for i in range(1000):
        await RisingEdge(dut.smp_clk)
        values.append(
            (dut.data_cha.value.signed_integer, dut.data_chb.value.signed_integer)
        )
    assert np.all(
        np.array(values)
        == np.array([(cha_value(i), chb_value(i)) for i in range(1000)])
    )
