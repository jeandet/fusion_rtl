
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

#ifdef CUSTOM_SPI

/*-----------------------------------------------------------------------*/
/* SPI SDCard Commands                                                   */
/*-----------------------------------------------------------------------*/

#define CMD0    (0)         /* GO_IDLE_STATE */
#define CMD1    (1)         /* SEND_OP_COND */
#define ACMD41  (0x80 + 41) /* SEND_OP_COND (SDC) */
#define CMD8    (8)         /* SEND_IF_COND */
#define CMD9    (9)         /* SEND_CSD */
#define CMD10   (10)        /* SEND_CID */
#define CMD12   (12)        /* STOP_TRANSMISSION */
#define CMD13   (13)        /* SEND_STATUS */
#define ACMD13  (0x80 + 13) /* SD_STATUS (SDC) */
#define CMD16   (16)        /* SET_BLOCKLEN */
#define CMD17   (17)        /* READ_SINGLE_BLOCK */
#define CMD18   (18)        /* READ_MULTIPLE_BLOCK */
#define CMD23   (23)        /* SET_BLOCK_COUNT */
#define ACMD23  (0x80 + 23) /* SET_WR_BLK_ERASE_COUNT (SDC) */
#define CMD24   (24)        /* WRITE_BLOCK */
#define CMD25   (25)        /* WRITE_MULTIPLE_BLOCK */
#define CMD32   (32)        /* ERASE_ER_BLK_START */
#define CMD33   (33)        /* ERASE_ER_BLK_END */
#define CMD38   (38)        /* ERASE */
#define CMD55   (55)        /* APP_CMD */
#define CMD58   (58)        /* READ_OCR */

#define CS_LOW() custom_spi_control_csr_write(0)
#define CS_HIGH() custom_spi_control_csr_write(2)
#define SPI_READY_FLAG (1 << 0)
#define SPI_READY() ((custom_spi_status_csr_read() & SPI_READY_FLAG)==SPI_READY_FLAG)

static inline void spi_write8(uint8_t byte)
{
    while (!SPI_READY())
    {
    }
    custom_spi_spi_data_wr_8_write(byte);
}

static inline uint8_t spi_xfer8(uint8_t byte)
{
    while (!SPI_READY())
    {
    }
    custom_spi_spi_data_wr_8_write(byte);
    while (!SPI_READY())
    {
    }
    return (uint8_t)custom_spi_spi_data_rd_read();
}

static inline void spi_write16(uint16_t word)
{
    while (!SPI_READY())
    {
    }
    custom_spi_spi_data_wr_16_write(word);
}

static inline void spi_write32(uint32_t word)
{
    while (!SPI_READY())
    {
    }
    custom_spi_spi_data_wr_32_write(word);
}

static inline uint32_t spi_xfer32(uint32_t word)
{
    while (!SPI_READY())
    {
    }
    custom_spi_spi_data_wr_32_write(word);
    while (!SPI_READY())
    {
    }
    return (uint32_t)custom_spi_spi_data_rd_read();
}


/*-----------------------------------------------------------------------*/
/* SPI SDCard Select/Deselect functions                                  */
/*-----------------------------------------------------------------------*/

static void spisdcard_deselect(void) {
    CS_HIGH();
    /* Generate 8 dummy clocks */
    spi_write8(0xFF);

}

static int spisdcard_select(void) {
    uint16_t timeout;
    CS_LOW();
    /* Generate 8 dummy clocks */
    spi_write8(0xff);

    /* Wait 500ms for the card to be ready */
    timeout = 500;
    while(timeout > 0) {
        if (spi_xfer8(0xff) == 0xff)
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

static inline void _spisdcardwrite_16x4_bytes_aligned32(uint8_t* buf) {
    uint16_t i;
    uint32_t* pbuf = (uint32_t*)buf;
    spi_write32(pbuf[0]);
    spi_write32(pbuf[1]);
    spi_write32(pbuf[2]);
    spi_write32(pbuf[3]);
    spi_write32(pbuf[4]);
    spi_write32(pbuf[5]);
    spi_write32(pbuf[6]);
    spi_write32(pbuf[7]);
    spi_write32(pbuf[8]);
    spi_write32(pbuf[9]);
    spi_write32(pbuf[10]);
    spi_write32(pbuf[11]);
    spi_write32(pbuf[12]);
    spi_write32(pbuf[13]);
    spi_write32(pbuf[14]);
    spi_write32(pbuf[15]);
}

static inline void _spisdcardwrite_bytes_aligned32(uint8_t *buf, uint16_t n) {
  uint16_t i;
  if (n % 64 == 0) {
    for (i = 0; i < n ; i+=64) {
      _spisdcardwrite_16x4_bytes_aligned32(&buf[i]);
    }
  } else {
    uint32_t *pbuf = (uint32_t *)buf;
    for (i = 0; i < n / 4; i++) {
      spi_write32(pbuf[i]);
    }
  }
}

static void spisdcardwrite_bytes(uint8_t* buf, uint16_t n) {
    uint16_t i;
    if (((uint32_t)buf & 0x03)  || (n & 0x03)) {
        for (i=0; i<n; i++)
            spi_write8(buf[i]);
    }
    else {
        // If buf is aligned to 4 bytes and n is a multiple of 4, use 32-bit writes
        _spisdcardwrite_bytes_aligned32(buf, n);
    }
    
    
}

static inline void _spisdcardread_bytes_aligned32(uint8_t* buf, uint16_t n) {
    uint16_t i;
    for (i=0; i<n; i+=4) {
        *((uint32_t*)(buf[i])) = spi_xfer32(0xFFFFFFFF);
    }
}

static void spisdcardread_bytes(uint8_t* buf, uint16_t n) {
    uint16_t i;
    if (((uint32_t)buf & 0x03)  || (n & 0x03)) {
        for (i=0; i<n; i++)
            buf[i] = spi_xfer8(0xff);
    }
    else {
        _spisdcardread_bytes_aligned32(buf, n);
    }
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
        if (spi_xfer8(0xFF) == 0xFF)
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
    spi_write8(start_token);

    /* Send 512 bytes of data */
    spisdcardwrite_bytes((uint8_t *)buf, 512);
    
    /* Send dummy CRC (use proper CRC if available) */
    spi_write16(0xFFFF); // Dummy CRC

    /* Wait for data response (not 0xFF) */
    timeout = 10;
    do {
        response = spi_xfer8(0xFF);
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
        if (spi_xfer8(0xFF) == 0xFF)
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
    spi_write8(0xFD);
    /* Wait not busy */
    uint32_t timeout = 1000000;
    while (timeout--) {
      if (spi_xfer8(0xFF) == 0xFF)
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
    #ifndef SPISDCARD_NO_CLK_DIV
    custom_spi_clkdiv_csr_write(0);
    #endif
    while (timeout) {
        /* Set SDCard in SPI Mode (generate 80 dummy clocks) */
        CS_HIGH();
        for (i=0; i<10; i++)
            spi_xfer8(0xff);
        CS_LOW();

        /* Set SDCard in Idle state */
        char response=spisdcardsend_cmd(CMD0, 0);
        if (response == 0x1)
        {
            break;
        }
        else
        {
            #ifdef SPISDCARD_DEBUG
            printf("Got CMD0 response = %d\n", response);
            #endif
        }
          

        timeout--;
    }
    if (timeout == 0)
    {
        #ifdef SPISDCARD_DEBUG
        putsnonl("CMD0 failed\n");
        #endif
        return 0;
    }
        

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
    {
        #ifdef SPISDCARD_DEBUG
        putsnonl("ACMD41 failed\n");
        #endif
        return 0;
    }
    #ifndef SPISDCARD_NO_CLK_DIV
    custom_spi_clkdiv_csr_write(0);
    #endif
    return 1;
}

#endif