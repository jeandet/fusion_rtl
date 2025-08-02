FROM fedora:42

ADD https://github.com/YosysHQ/oss-cad-suite-build/releases/download/2025-08-01/oss-cad-suite-linux-x64-20250801.tgz /tmp/oss-cad-suite.tgz
RUN tar -xzf /tmp/oss-cad-suite.tgz -C /usr/local &&\
    rm /tmp/oss-cad-suite.tgz &&\
    ln -s /usr/local/oss-cad-suite/bin/* /usr/local/bin/

ENV PATH="/usr/local/oss-cad-suite/bin:${PATH}"

# Install LiteX

ADD https://raw.githubusercontent.com/enjoy-digital/litex/master/litex_setup.py /usr/bin/litex_setup.py 

RUN chmod +x /usr/bin/litex_setup.py &&\
    dnf update -y && \
    dnf install -y python3-pip meson make git gcc-riscv32-linux-gnu.x86_64 gcc-c++-riscv32-linux-gnu.x86_64 binutils-riscv32-linux-gnu.x86_64 &&\
    cd /tmp && /usr/bin/python3 /usr/bin/litex_setup.py  --init --install --config=full


RUN echo "source /usr/local/oss-cad-suite/environment" >> /etc/profile.d/oss-cad-suite.sh
