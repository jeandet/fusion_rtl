import math
import os
from random import getrandbits, randint, shuffle
import numpy as np
import cocotb
from cocotb.binary import BinaryValue
from cocotb.clock import Clock
from cocotb.regression import TestFactory
from cocotb.triggers import RisingEdge, ReadOnly, Timer, FallingEdge
from cocotb.types import LogicArray

def compare_lists(list1, list2):
    assert len(list1) == len(list2), f"Length mismatch: {len(list1)} != {len(list2)}"
    for index, (a, b) in enumerate(zip(list1, list2)):
        assert a == b, f"Element mismatch at index {index}: {a} != {b}, \n{list1} != {list2}"
    return True

class SPISlave:
    def __init__(self, dut, data_to_send):
        assert len(data_to_send) > 0
        self.dut = dut
        self._received_data = []
        self._sent_data = []
        self._data_to_send = data_to_send
        self._receive_task = cocotb.start_soon(self.receive())
        self._send_task = cocotb.start_soon(self.send())

    @property
    def received_bytes(self):
        _bytes = self._received_data
        self._received_data = []
        return _bytes

    @property
    def sent_bytes(self):
        _bytes = self._sent_data
        self._sent_data = []
        return _bytes

    async def receive(self):
        await FallingEdge(self.dut.sys_rst)
        while True:
            if self.dut.spi_cs.value == 1:
                await FallingEdge(self.dut.spi_cs)
            next_byte = 0
            for i in range(8):
                await RisingEdge(self.dut.spi_sck)
                next_byte = (next_byte << 1) | self.dut.spi_mosi.value
            self._received_data.append(next_byte)

    async def send(self):
        index = 0
        await FallingEdge(self.dut.sys_rst)
        while True:
            next_byte = self._data_to_send[index]
            if self.dut.spi_cs.value == 1:
                await FallingEdge(self.dut.spi_cs)
            for i in range(8):
                self.dut.spi_miso.value = (next_byte >> (7 - i)) & 1
                await FallingEdge(self.dut.spi_sck)
            self._sent_data.append(next_byte)
            index = (index + 1) % len(self._data_to_send)


async def pulse(dut, signal):
    await RisingEdge(dut.sys_clk)
    signal.value = 1
    await RisingEdge(dut.sys_clk)
    signal.value = 0


async def write(dut, size, value):
    if dut.csrfield_ready.value == 0:
        await RisingEdge(dut.csrfield_ready)
        await RisingEdge(dut.sys_clk)
    getattr(dut, f"data_write_{size}_storage").value = value
    await pulse(dut, getattr(dut, f"data_write_{size}_re"))
    await FallingEdge(dut.csrfield_ready)
    await RisingEdge(dut.csrfield_ready)
    return dut.spi_data_rd.value

def split_32_to_8(data):
    return [(data >> (i * 8)) & 0xFF for i in range(4)][::-1]

async def test_write_auto_cs(dut, spi_slave: SPISlave):
    _ = spi_slave.received_bytes # flush
    _ = spi_slave.sent_bytes # flush
    data_to_send = spi_slave._data_to_send.copy()
    shuffle(data_to_send)
    dut_received_data = [await write(dut, 8, data) for data in data_to_send]
    assert compare_lists(spi_slave.received_bytes, data_to_send)
    assert compare_lists(dut_received_data, spi_slave.sent_bytes)

    dut_received_data =  split_32_to_8(await write(dut, 32, 0b10101010101010101010101010101010))
    assert compare_lists(spi_slave.received_bytes, [0b10101010] * 4)
    assert compare_lists(dut_received_data, spi_slave.sent_bytes)


async def test_write_manual_cs(dut, spi_slave: SPISlave):
    dut.csrfield_cs_auto.value = 0
    dut.csrfield_cs_value.value = 0
    
    _ = spi_slave.received_bytes # flush
    data_to_send = spi_slave._data_to_send.copy()
    shuffle(data_to_send)
    dut_received_data = [await write(dut, 8, data) for data in data_to_send]
    assert compare_lists(spi_slave.received_bytes, data_to_send)
    assert compare_lists(dut_received_data, spi_slave.sent_bytes)

    dut_received_data = split_32_to_8(await write(dut, 32, 0b10101010101010101010101010101010))
    assert compare_lists(spi_slave.received_bytes, [0b10101010] * 4)
    assert compare_lists(dut_received_data, spi_slave.sent_bytes)

    dut.csrfield_cs_value.value = 1
    for _ in range(3):
        await RisingEdge(dut.sys_clk)
    dut.csrfield_cs_auto.value = 1


@cocotb.test()
async def test_SPI(dut):
    clk_gen = cocotb.start_soon(Clock(dut.sys_clk, 1000 // 60, units="ns").start())
    dut.sys_rst.value = 1
    dut.csrfield_cs_auto.value = 1
    dut.data_write_8_storage.value = 0
    dut.data_write_16_storage.value = 0
    dut.data_write_32_storage.value = 0
    slave = SPISlave(dut, data_to_send=[0b10000001 , 0, 1, 2, 4, 8, 16, 32, 64, 128, 0xAA, 0xFF, 0x55])
    for _ in range(3):
        await RisingEdge(dut.sys_clk)
    dut.sys_rst.value = 0
    for speed in range(7):
        dut.csrfield_clk_div.value = speed
        await test_write_auto_cs(dut, slave)
        await test_write_manual_cs(dut, slave)
