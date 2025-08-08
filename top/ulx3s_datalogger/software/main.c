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

static void reboot_cmd(void)
{
	ctrl_reset_write(1);
}

static inline uint8_t spi_xfer(uint8_t byte) {
    /* Write byte on MOSI */
    spisdcard_mosi_write(byte);
    /* Initiate SPI Xfer */
    spisdcard_control_write(8*SPI_LENGTH | SPI_START);
    /* Wait SPI Xfer to be done */
    while((spisdcard_status_read() & SPI_DONE) != SPI_DONE);
    /* Read MISO and return it */
    return spisdcard_miso_read();
}

static inline uint8_t spi_send(uint8_t byte) {
    /* Write byte on MOSI */
    spisdcard_mosi_write(byte);
    /* Initiate SPI Xfer */
    spisdcard_control_write(8*SPI_LENGTH | SPI_START);
    /* Wait SPI Xfer to be done */
    while((spisdcard_status_read() & SPI_DONE) != SPI_DONE);
}
/*-----------------------------------------------------------------------*/
/* SPI SDCard Select/Deselect functions                                  */
/*-----------------------------------------------------------------------*/

static void spisdcard_deselect(void) {
    /* Set SPI CS High */
    spisdcard_cs_write(SPI_CS_HIGH);
    /* Generate 8 dummy clocks */
    spi_send(0xff);
}

static int spisdcard_select(void) {
    uint16_t timeout;

    /* Set SPI CS Low */
    spisdcard_cs_write(SPI_CS_LOW);

    /* Generate 8 dummy clocks */
    spi_send(0xff);

    /* Wait 500ms for the card to be ready */
    timeout = 500;
    while(timeout > 0) {
        if (spi_xfer(0xff) == 0xff)
            return 1;
        busy_wait(1);
        timeout--;
    }

    /* Deselect card on error */
    spisdcard_deselect();

    return 0;
}

/*-----------------------------------------------------------------------*/
/* SPI SDCard bytes Xfer functions                                       */
/*-----------------------------------------------------------------------*/

static void spisdcardwrite_bytes(uint8_t* buf, uint16_t n) {
    uint16_t i;
    for (i=0; i<n; i++)
        spi_send(buf[i]);
}

static void spisdcardread_bytes(uint8_t* buf, uint16_t n) {
    uint16_t i;
    for (i=0; i<n; i++)
        buf[i] = spi_xfer(0xff);
}

/*-----------------------------------------------------------------------*/
/* SPI SDCard blocks Xfer functions                                      */
/*-----------------------------------------------------------------------*/


static uint8_t spisdcard_write_block(char *buf, char start_token) 
{
    uint16_t i;
    uint8_t response;

    /* Wait for card to be ready */
    uint16_t timeout = 500;
    while (timeout > 0) {
        if (spi_xfer(0xFF) == 0xFF)
            break;
        busy_wait_us(1);
        timeout--;
    }
    
    if (timeout == 0) {
        #ifdef SPISDCARD_DEBUG
        putsnonl("Card not ready for write\n");
        #endif
        return 0;
    }

    /* Send start block token */
    spi_send(start_token);

    /* Send 512 bytes of data */
    spisdcardwrite_bytes((uint8_t *)buf, 512);
    
    /* Send dummy CRC (use proper CRC if available) */
    spi_send(0xFF);
    spi_send(0xFF);

    /* Wait for data response (not 0xFF) */
    timeout = 10;
    do {
        response = spi_xfer(0xFF);
        timeout--;
    } while ((response == 0xFF) && (timeout > 0));

    
    /* Check if data was accepted (xxx00101) */
    if ((response & 0x1F) != 0x05) {
        #ifdef SPISDCARD_DEBUG
        printf("Data response error: 0x%02X\n", response);
        #endif
        return 0;
    }

    /* Wait for write completion (card not busy) */
    timeout = 100000;
    while (timeout > 0) {
        if (spi_xfer(0xFF) == 0xFF)
            break;
        busy_wait_us(1);
        timeout--;
    }
    
    if (timeout == 0) {
        #ifdef SPISDCARD_DEBUG
        putsnonl("Write timeout\n");
        #endif
        return 0;
    }

    return 1;
}

/*-----------------------------------------------------------------------*/

static uint8_t spisdcardsend_cmd(uint8_t cmd, uint32_t arg)
{
    uint8_t byte;
    uint8_t buf[6];
    uint8_t timeout;

    /* Send CMD55 for ACMD */
    if (cmd & 0x80) {
        cmd &= 0x7f;
        byte = spisdcardsend_cmd(CMD55, 0);
        if (byte > 1)
            return byte;
    }

    /* Select the card and wait for it, except for:
       - CMD12: STOP_TRANSMISSION.
       - CMD0 : GO_IDLE_STATE.
    */
    if (cmd != CMD12 && cmd != CMD0) {
        spisdcard_deselect();
        if (spisdcard_select() == 0)
            return 0xff;
    }

    /* Send Command */
    buf[0] = 0x40 | cmd;            /* Start + Command */
    buf[1] = (uint8_t)(arg >> 24);  /* Argument[31:24] */
    buf[2] = (uint8_t)(arg >> 16);  /* Argument[23:16] */
    buf[3] = (uint8_t)(arg >> 8);   /* Argument[15:8] */
    buf[4] = (uint8_t)(arg >> 0);   /* Argument[7:0] */
    if (cmd == CMD0)
        buf[5] = 0x95;      /* Valid CRC for CMD0 */
    else if (cmd == CMD8)
        buf[5] = 0x87;      /* Valid CRC for CMD8 (0x1AA) */
    else
        buf[5] = 0x01;      /* Dummy CRC + Stop */
    spisdcardwrite_bytes(buf, 6);

    /* Receive Command response */
    if (cmd == CMD12)
        spisdcardread_bytes(&byte, 1);  /* Read stuff byte */
    timeout = 10; /* Wait for a valid response (up to 10 attempts) */
    while (timeout > 0) {
        spisdcardread_bytes(&byte, 1);
        if ((byte & 0x80) == 0)
            break;

        timeout--;
    }
    return byte;
}

static int sd_write_blocks(char *buf, uint32_t block, uint32_t count) {
  uint32_t sent = 0;
  if (spisdcardsend_cmd(CMD25, block) == 0) {
    while (count > 0) {
      if (!spisdcard_write_block(buf, 0xFC))
        break;
      buf += 512;
      count--;
      sent++;
    }
    spi_send(0xFD);
    /* Wait not busy */
    uint32_t timeout = 1000000;
    while (timeout--) {
      if (spi_xfer(0xFF) == 0xFF)
        break;
      busy_wait_us(1);
    }
  } else {
    putsnonl("CMD failed\n");
  }
  spisdcard_deselect();
  return sent;
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
	if(sdcard_init()==0) 
    {
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