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

#define DMA_BUFFER_SIZE (512*2048*4)
char DMA_buffer[DMA_BUFFER_SIZE] __attribute__((section(".dma"), aligned(64)));

int sd_write_blocks(char *buf, uint32_t block, uint32_t count);
uint8_t custom_spisdcard_init(void);

static void reboot_cmd(void)
{
	ctrl_reset_write(1);
}

char block[512*8] __attribute__((aligned(4))) = "Hello, World!\n";

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
		#ifdef CSR_SPISDCARD_BASE
		putsnonl("Switching to max SPI clock speed\n");
		spisdcard_clk_divider_write(2);
		#endif
		putsnonl("SDCard initialized successfully\n");
        putsnonl("filling DMA buffer\n");
        for (int i = 0; i < sizeof(DMA_buffer); i++) {
            DMA_buffer[i] = i & 0xFF; // Fill with a pattern
        }
        start_timer1();
        if (!sd_write_blocks(DMA_buffer,0, DMA_BUFFER_SIZE/512))
        {
            putsnonl("Failed to write DMA buffer to SDCard\n");
        }
        uint32_t elapsed = elapsed_time();
        printf("Write Speed: %d KB/s\n", DMA_BUFFER_SIZE / (elapsed / 60000));
	}

	return 0;
}