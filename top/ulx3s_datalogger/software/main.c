// This file is Copyright (c) 2020 Florent Kermarrec <florent@enjoy-digital.fr>
// License: BSD

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <irq.h>
#include <libbase/uart.h>
#include <libbase/console.h>
#include <liblitesdcard/sdcard.h>
#include <liblitesdcard/spisdcard.h>
#include <liblitedram/sdram.h>
#include <generated/csr.h>

#define SDCARD_TOTAL_BLOCKS (64*1024*1024*1024/512) // 64GB SDCard

#define DMA_BUFFER_SIZE (1024*1024*4)
char DMA_buffer1[DMA_BUFFER_SIZE] __attribute__((section(".dma"), aligned(64)));
char DMA_buffer2[DMA_BUFFER_SIZE] __attribute__((section(".dma"), aligned(64)));

int sd_write_blocks(char *buf, uint32_t block, uint32_t count);
uint8_t custom_spisdcard_init(void);

static void reboot_cmd(void)
{
	ctrl_reset_write(1);
}

char block[512*8] __attribute__((aligned(4))) = "Hello, World @60Mbps!\n";

void start_timer1(void)
{
    timer1_en_write(0);
	timer1_reload_write(0);
	timer1_load_write(0xFFFFFFFF);
	timer1_en_write(1);
	timer1_update_value_write(1);
}

uint32_t elapsed_time(void)
{
    // Calculate and return the elapsed time since the timer started
    timer1_update_value_write(1);
    return (0xFFFFFFFF - timer1_value_read());
}

static inline void restart_adc_DMA(char *buffer, size_t size)
{
    adc__dma_writer_enable_write(0);
    adc__dma_writer_base_write((uint64_t)buffer);
    adc__dma_writer_length_write(size);
    adc__dma_writer_enable_write(1);
    adc_enable_csr_write(1);
}

static inline uint32_t push_on_sdcard(char *buffer, size_t size, uint32_t block_address)
{
    // Write the contents of the DMA buffer to the SDCard
    if (sd_write_blocks(buffer, block_address, size / 512) == 0)
    {
        putsnonl("Failed to write DMA buffer to SDCard\n");
    }
    return block_address + (size / 512);
}

static void test_sdcard_write_speed(char *buffer, size_t size)
{
    start_timer1();
    push_on_sdcard(buffer, size, 0);
    uint32_t elapsed = elapsed_time();
    printf("Write Speed: %d KB/s\n", size / (elapsed / (CONFIG_CLOCK_FREQUENCY/1000)));
}

static inline void swap_buffers(char** current_buffer, char** next_buffer)
{
    char* temp = *current_buffer;
    *current_buffer = *next_buffer;
    *next_buffer = temp;
}

int main(void)
{
#ifdef CONFIG_CPU_HAS_INTERRUPT
	irq_setmask(0);
	irq_setie(1);
#endif	
    uart_init();
    sdram_init();

	putsnonl("ULX3S Datalogger\n");
	putsnonl("Initializing SDCard...\n");
	#ifdef CSR_SPISDCARD_BASE
	if(spisdcard_init()==0) 
    {
    #else 
        #ifdef CUSTOM_SPI
	    if(custom_spisdcard_init()==0) 
        {
        #else
        if(sdcard_init()==0) 
        {
        #endif 
    #endif
		putsnonl("SDCard initialization failed\n");
	}
	else 
    {
		putsnonl("SDCard initialized successfully\n");
        uint32_t block_address = 0;
        char* current_buffer = DMA_buffer1;
        char* next_buffer = DMA_buffer2;
        restart_adc_DMA(next_buffer, DMA_BUFFER_SIZE);
        while (block_address < 1024 * 64)
        {
           while (adc__dma_writer_done_read() == 0);
           swap_buffers(&current_buffer, &next_buffer);
           restart_adc_DMA(next_buffer, DMA_BUFFER_SIZE);
           block_address = push_on_sdcard(current_buffer, DMA_BUFFER_SIZE, block_address);
        }
        
        putsnonl("Data acquisition completed\n");
        
	}

	return 0;
}