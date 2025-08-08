FROM fedora:42
LABEL maintainer="Alexis Jeandet <alexis.jeandet@member.fsf.org>"

RUN DATE=$(date +%Y-%m-%d) && \
    DATE_NO_HYPHEN=$(echo ${DATE} | tr -d '-') && \
    curl -L https://github.com/YosysHQ/oss-cad-suite-build/releases/download/${DATE}/oss-cad-suite-linux-x64-${DATE_NO_HYPHEN}.tgz -o /tmp/oss-cad-suite.tgz && \
    tar -xzf /tmp/oss-cad-suite.tgz -C /usr/local &&\
    rm /tmp/oss-cad-suite.tgz &&\
    ln -s /usr/local/oss-cad-suite/bin/* /usr/local/bin/

ENV PATH="/usr/local/oss-cad-suite/bin:${PATH}"

# Install LiteX

ADD https://raw.githubusercontent.com/enjoy-digital/litex/master/litex_setup.py /usr/bin/litex_setup.py 
ADD ulx3s_patch.patch /tmp/ulx3s_patch.patch

RUN chmod +x /usr/bin/litex_setup.py &&\
    dnf update -y && \
    dnf install -y python3-pip meson patch make git gcc-riscv32-linux-gnu.x86_64 gcc-c++-riscv32-linux-gnu.x86_64 binutils-riscv32-linux-gnu.x86_64 &&\
    mkdir -p /opt/litex_install && cd /opt/litex_install &&\
    /usr/bin/python3 /usr/bin/litex_setup.py --init --install --config=full &&\
    cd /opt/litex_install/litex-boards &&\
    patch -p1 < /tmp/ulx3s_patch.patch

RUN echo "source /usr/local/oss-cad-suite/environment" >> /etc/profile.d/oss-cad-suite.sh
