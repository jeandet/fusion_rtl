import math
import os
from random import getrandbits, randint
import numpy as np
import cocotb
from cocotb.binary import BinaryValue
from cocotb.clock import Clock
from cocotb.regression import TestFactory
from cocotb.triggers import RisingEdge, ReadOnly, Timer, FallingEdge, with_timeout
from cocotb.types import LogicArray

#    input  wire    [9:0] B2B_CONNECTOR_BANK0,
#    input  wire    [2:0] FMC_address,
#    input  wire          FMC_clk,
#    input  wire   [31:0] FMC_data,
#    input  wire          FMC_ne,
#    input  wire          FMC_noe,
#    input  wire          FMC_nwe,
#    input  wire          reset


def cha_value(index):
    return int(np.cos(2 * np.pi * index / 16) * 32765)


def chb_value(index):
    return index & 0xFFFF


async def emulate_adc(conv_st, ready_strobe, cs, sclk, miso_a, miso_b):
    index = 0
    while True:
        await RisingEdge(conv_st)
        await Timer(315, units="ns")
        ready_strobe.value = 1
        if cs == 1:
            await FallingEdge(cs)
        ready_strobe.value = 0
        await Timer(12, units="ns")
        value_cha = cha_value(index)
        value_chb = chb_value(index)
        for i in range(16):
            miso_a.value = (value_cha >> (15 - i)) & 1
            miso_b.value = (value_chb >> (15 - i)) & 1
            await RisingEdge(sclk)
            await Timer(15.8, units="ns")
        index += 1


async def consume_FT245(dut, count):
    values = []
    while count:
        await RisingEdge(dut.sys_clk)
        dut.FIFOA_TXF.value  = 0
        while dut.FIFOA_WR.value == 1:
            await RisingEdge(dut.sys_clk)
        values.append(int(dut.FIFOA_DATA.value))
        count -= 1
        await FallingEdge(dut.sys_clk)
        dut.FIFOA_TXF.value  = 1
        await RisingEdge(dut.sys_clk)
    return values



@cocotb.test()
async def test_pcb_lob(dut):
    adc1 = cocotb.start_soon(
        emulate_adc(
            conv_st=dut.ADC1_conv_st,
            ready_strobe=dut.ADC1_ready_strobe,
            cs=dut.ADC1_cs,
            sclk=dut.ADC1_sclk,
            miso_a=dut.ADC1_miso_a,
            miso_b=dut.ADC1_miso_b,
        )
    )
    adc2 = cocotb.start_soon(
        emulate_adc(
            conv_st=dut.ADC2_conv_st,
            ready_strobe=dut.ADC2_ready_strobe,
            cs=dut.ADC2_cs,
            sclk=dut.ADC2_sclk,
            miso_a=dut.ADC2_miso_a,
            miso_b=dut.ADC2_miso_b,
        )
    )
    clk = Clock(dut.sys_clk, 1e6//60, units="ps")
    clk_gen = cocotb.start_soon(clk.start())
    dut.sys_rst.value = 1
    dut.FIFOA_TXF.value = 1
    await Timer(100, units="ns")
    dut.sys_rst.value = 0
    values = []
    for _ in range(10):
        await Timer(randint(1,1000), units="us")
        for _ in range(10):
            await Timer(randint(1,100), units="us")
            # cptr = await write_FMC(dut, cptr)
            values += await with_timeout(consume_FT245(dut, 512), 1000, "us")
    values = np.frombuffer(np.array(values, dtype=np.uint8), dtype=np.int16)
    print(values)
    np.save('/tmp/test.np', values)