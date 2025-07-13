# Fusion Boards RTL designs 

This repository contains the RTL designs for the Fusion Boards developed within the Laboratory of Plasma Physics (LPP) at Ecole Polytechnique.

Fusion boards are FPGA-based platforms optimized for low-noise measurements and designed to be modular and flexible. They address a range of needs, including ultra-low noise amplifier characterization, particularly for low-frequency, low-noise ASICs developed for space mission search-coils and support various laboratory experiments. The designs primarily target the Lattice ECP5 FPGA family and leverage liteX and Yosys for development.

# Directory Structure
- `fusion_rtl/`: Contains the RTL designs for the Fusion Board.
- `fusion_rtl/platforms/`: Contains platform-specific files for different Fusion Board designs.
- `fusion_rtl/com/`: Contains communication interfaces and protocols.
- `fusion_rtl/ecp5/`: Contains ECP5 specific files, such as clock management.
- `fusion_rtl/memories/`: Contains memory interfaces and FIFO implementations.
- `top/`: Contains the top-level designs and Makefiles for building the Fusion Board.
  - `pcb_lob/`: Contains the PCB LOB specific designs and Makefiles.
  - `analog_two/`: Contains the Analog Two specific designs and Makefiles.
- `tests/`: Contains testbenches and simulation files for the RTL designs.
- `docker/`: Contains build environments for building the RTL designs.