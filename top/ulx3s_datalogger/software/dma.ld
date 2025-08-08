INCLUDE generated/output_format.ld

INCLUDE generated/regions.ld

SECTIONS
{
	/* Dedicated DMA buffer area in main_ram */
	.dma (NOLOAD) :
	{
		. = ALIGN(64);
		_fdma = .;
		KEEP(*(.dma .dma.*))
		. = ALIGN(64);
		_edma = .;
	} > main_ram
}