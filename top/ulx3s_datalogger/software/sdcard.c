
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

#ifndef CUSTOM_SPI

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

int sd_write_blocks(char *buf, uint32_t block, uint32_t count) {
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


uint8_t custom_spisdcard_init(void) {
    uint8_t  i;
    uint8_t  buf[4];
    uint16_t timeout;

    timeout = 1000;
    while (timeout) {
        /* Set SDCard in SPI Mode (generate 80 dummy clocks) */
        spisdcard_cs_write(SPI_CS_HIGH);
        for (i=0; i<10; i++)
            spi_xfer(0xff);
        spisdcard_cs_write(SPI_CS_LOW);

        /* Set SDCard in Idle state */
        if (spisdcardsend_cmd(CMD0, 0) == 0x1)
            break;

        timeout--;
    }
    if (timeout == 0)
        return 0;

    /* Set SDCard voltages, only supported by ver2.00+ SDCards */
    if (spisdcardsend_cmd(CMD8, 0x1AA) != 0x1)
        return 0;
    spisdcardread_bytes(buf, 4); /* Get additional bytes of R7 response */

    /* Set SDCard in Operational state (1s timeout) */
    timeout = 1000;
    while (timeout > 0) {
        if (spisdcardsend_cmd(ACMD41, 1 << 30) == 0)
            break;
        busy_wait(1);
        timeout--;
    }
    if (timeout == 0)
        return 0;

    /* Set SPI clk freq to operational frequency */
    spi_set_clk_freq(SPISDCARD_CLK_FREQ);

    return 1;
}

#endif