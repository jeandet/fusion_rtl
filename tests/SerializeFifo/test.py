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


async def write_FIFO(dut):
    value = 0
    dut.we.value = 0
    if dut.sys_rst.value == 1:
        await FallingEdge(dut.sys_rst)
    await RisingEdge(dut.sys_clk)
    await RisingEdge(dut.sys_clk)
    while True:
        if dut.writable.value == 0:
            await RisingEdge(dut.writable)
        await FallingEdge(dut.sys_clk)
        dut.din.value = value
        dut.we.value = 1
        await RisingEdge(dut.sys_clk)
        await FallingEdge(dut.sys_clk)
        dut.we.value = 0
        value += 1
        await RisingEdge(dut.sys_clk)
        await Timer(randint(1, 1000), units="ns")


async def burst_write_FIFO(dut, count, value=0):
    dut.we.value = 0
    while count:
        await FallingEdge(dut.sys_clk)
        if dut.writable.value == 0:
            dut.we.value = 0
            await RisingEdge(dut.writable)
        dut.din.value = value
        dut.we.value = 1
        value += 1
        count -= 1
    await FallingEdge(dut.sys_clk)
    dut.we.value = 0


async def read_FIFO(dut, count):
    values = []
    await FallingEdge(dut.sys_clk)
    while count:
        await FallingEdge(dut.sys_clk)
        if dut.readable.value == 1:
            if dut.dout.value.is_resolvable:
                values.append(int(dut.dout.value))
            else:
                values.append(-1)
                print("dout is not resolvable")
            dut.re.value = 1
            count -= 1
        else:
            dut.re.value = 0
    await FallingEdge(dut.sys_clk)
    dut.re.value = 0
    return values


@cocotb.test()
async def test_SerializeFifo(dut):
    dut.we.value = 0
    dut.re.value = 0
    dut.sys_rst.value = 1
    clk = Clock(dut.sys_clk, 10, units="ns")
    clk_gen = cocotb.start_soon(clk.start())
    await Timer(100, units="ns")
    dut.sys_rst.value = 0
    values = []
    for i in range(32):
        await burst_write_FIFO(dut, 32, i * 32)
        values += await read_FIFO(dut, 32)
    print(values)
    assert np.all(np.array(values) == np.arange(len(values)))
