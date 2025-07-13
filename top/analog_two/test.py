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


async def consume_FMC(dut, count):
    values = []
    while count:
        if dut.have_data.value == 0:
            await RisingEdge(dut.have_data)
        await RisingEdge(dut.FMC_clk)
        for _ in range(32):
            dut.FMC_ne.value = 0
            dut.FMC_data.value = 0xADD00
            await RisingEdge(dut.FMC_clk)
            await RisingEdge(dut.FMC_clk)
            dut.FMC_data.value = LogicArray("Z" * 32)
            dut.FMC_noe.value = 0
            await RisingEdge(dut.FMC_clk)
            values.append(int(dut.FMC_data.value))
            dut.FMC_noe.value = 1
            dut.FMC_ne.value = 1
            await RisingEdge(dut.FMC_clk)
            await RisingEdge(dut.FMC_clk)
            count -= 1
    return values


async def write_FMC(dut, start_value=0):
    values = []
    await RisingEdge(dut.FMC_clk)
    for _ in range(32):
        dut.syncfifo_din.value = start_value
        dut.syncfifo_we.value = 1
        await RisingEdge(dut.FMC_clk)
        start_value += 1
    dut.syncfifo_we.value = 0
    return start_value


@cocotb.test()
async def test_fmc(dut):
    adc = cocotb.start_soon(
        emulate_adc(
            conv_st=dut.ADC1_conv_st,
            ready_strobe=dut.ADC1_ready_strobe,
            cs=dut.ADC1_cs,
            sclk=dut.ADC1_sclk,
            miso_a=dut.ADC1_miso_a,
            miso_b=dut.ADC1_miso_b,
        )
    )
    clk = Clock(dut.FMC_clk, 23.8, units="ns")
    clk_gen = cocotb.start_soon(clk.start())
    dut.reset.value = 0
    dut.FMC_ne.value = 1
    dut.FMC_noe.value = 1
    dut.FMC_nwe.value = 1
    dut.FMC_address.value = 0
    await Timer(100, units="ns")
    dut.reset.value = 1
    values = []
    for _ in range(100):
        await Timer(randint(1,1000), units="us")
        # cptr = await write_FMC(dut, cptr)
        values += await with_timeout(consume_FMC(dut, 64), 1000, "us")
    # assert values[0] == 0
    # assert np.all(np.gradient(values) == 1)
    assert values[0] == 0xF0000000
    print([hex(v) for v in values])
    values = np.frombuffer(np.array(values, dtype=np.uint32), dtype=np.uint8)
    print(values[:100])
    adc1 = values[1::5]
    frames = values[0::5]
    print(frames)
    assert np.all(adc1 == np.array([cha_value(i) for i in range(len(adc1))]))
