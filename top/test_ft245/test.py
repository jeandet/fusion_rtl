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

#    input  wire    [9:0] B2B_CONNECTOR_BANK0,
#    input  wire    [2:0] FMC_address,
#    input  wire          FMC_clk,
#    input  wire   [31:0] FMC_data,
#    input  wire          FMC_ne,
#    input  wire          FMC_noe,
#    input  wire          FMC_nwe,
#    input  wire          reset


async def read_FMC(dut):
    values = []
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
    clk = Clock(dut.FMC_clk, 10, units="ns")
    clk_gen = cocotb.fork(clk.start())
    dut.reset.value = 0
    dut.FMC_ne.value = 1
    dut.FMC_noe.value = 1
    dut.FMC_nwe.value = 1
    dut.FMC_address.value = 0
    await Timer(100, units="ns")
    dut.reset.value = 1
    values = []
    for _ in range(8):
        #cptr = await write_FMC(dut, cptr)
        values += await read_FMC(dut)
        await Timer(randint(1, 100), units="ns")
    assert values[0] == 0
    assert np.all(np.gradient(values) == 1)
