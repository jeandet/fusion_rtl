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

#define TARGET_DURATION (60*10) // 10 minutes
#define TOTAL_SAMPLES (ADC_SAMPLING_FREQUENCY * TARGET_DURATION)
#define BYTES_PER_SAMPLE (2)
#define TOTAL_BLOCKS ((TOTAL_SAMPLES * ADC_ACTIVE_CHANNEL_COUNT * BYTES_PER_SAMPLE / 512)+1) // +1 for header

#define SDCARD_TOTAL_BLOCKS (64*1024*1024*1024/512) // 64GB SDCard

#if TOTAL_BLOCKS > SDCARD_TOTAL_BLOCKS
#error "Total blocks exceed SDCard capacity"
#endif

#define DMA_BUFFER_SIZE (1024*1024*4)
char DMA_buffer1[DMA_BUFFER_SIZE] __attribute__((section(".dma"), aligned(64)));
char DMA_buffer2[DMA_BUFFER_SIZE] __attribute__((section(".dma"), aligned(64)));

int sd_write_blocks(char *buf, uint32_t block, uint32_t count);
uint8_t custom_spisdcard_init(void);

static void reboot_cmd(void)
{
	ctrl_reset_write(1);
}

char header[512] __attribute__((aligned(4)));

void init_header(void)
{
    snprintf(header, sizeof(header),
             "ULX3S Datalogger\n"
             "Record duration= %d seconds\n"
             "Sampling frequency= %d Hz\n"
             "Oversampling= %d x\n"
             "Zone= %d\n"
             "Active channel count= %d\n"
             "Total samples= %d\n"
             "Bytes per sample= %d\n"
             "Total blocks= %d\n",
             TARGET_DURATION,
             ADC_SAMPLING_FREQUENCY,
             ADC_OVERSAMPLING,
             ADC_ZONE,
             ADC_ACTIVE_CHANNEL_COUNT,
             TOTAL_SAMPLES,
             BYTES_PER_SAMPLE,
             TOTAL_BLOCKS);
}

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
    adc_dma_enable_write(0);
    adc_dma_base_write((uint64_t)buffer);
    adc_dma_length_write(size);
    adc_dma_enable_write(1);
    adc_enable_write(1);
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

static inline void stop_leds(void)
{
    leds_out_write(0);
}

static inline void start_leds(void)
{
    leds_out_write(0xFF);
}

int main(void)
{
#ifdef CONFIG_CPU_HAS_INTERRUPT
	irq_setmask(0);
	irq_setie(1);
#endif	
    uart_init();
    sdram_init();
    init_header();

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
        uint32_t block_address = 0;
		putsnonl("SDCard initialized successfully\n");
        putsnonl(header);
        putsnonl("Writing header at block address 0\n");
        block_address = push_on_sdcard(header, sizeof(header), block_address);
        putsnonl("Starting data acquisition...\n");
        stop_leds();
        char* current_buffer = DMA_buffer1;
        char* next_buffer = DMA_buffer2;
        restart_adc_DMA(next_buffer, DMA_BUFFER_SIZE);
        while (block_address < TOTAL_BLOCKS)
        {
           while (adc_dma_done_read() == 0);
           swap_buffers(&current_buffer, &next_buffer);
           restart_adc_DMA(next_buffer, DMA_BUFFER_SIZE);
           block_address = push_on_sdcard(current_buffer, DMA_BUFFER_SIZE, block_address);
        }
        putsnonl("Data acquisition completed\n");
        printf("Total blocks written: %d\n", block_address);
        while (1)
        {
            start_leds();
            busy_wait_us(1000000); // 1 second
            stop_leds();
            busy_wait_us(1000000); // 1 second
        }
        

	}

	return 0;
}