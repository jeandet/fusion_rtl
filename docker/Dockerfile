FROM gcr.io/hdl-containers/impl

ADD https://raw.githubusercontent.com/enjoy-digital/litex/master/litex_setup.py /usr/bin/litex_setup.py 

RUN chmod +x /usr/bin/litex_setup.py &&\
    apt update && apt install -y python3-pip &&\
    /usr/bin/litex_setup.py  --init --install --user --config=full