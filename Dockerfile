FROM python:3.6
MAINTAINER patrykjasinski1989

WORKDIR /usr/src/app

RUN apt-get update && apt-get install libaio1

# Install the app and all dependencies from pip
RUN git clone https://github.com/patrykjasinski1989/gu2_automation.git .
RUN pip install --no-cache-dir -r requirements.txt

# Install pyremedy
RUN git clone https://github.com/patrykjasinski1989/pyremedy.git
RUN pip install pyremedy/

RUN rm -rf .git

COPY config.py config.py

# Remedy libs configuration
RUN mkdir -p /opt/remedy && tar xvfz lib/api811linux.tar.gz  -C /opt/remedy --strip 1
RUN bash -c "echo '# Remedy ARS support' > /etc/ld.so.conf.d/remedy.conf"
RUN bash -c "echo /opt/remedy/lib >> /etc/ld.so.conf.d/remedy.conf"
RUN bash -c "echo /opt/remedy/bin >> /etc/ld.so.conf.d/remedy.conf"

# Oracle client configuration
RUN mkdir -p /opt/oracle && unzip lib/instantclient-basiclite-linux.x64-18.3.0.0.0dbru.zip -d /opt/oracle
RUN sh -c "echo /opt/oracle/instantclient_18_3 > /etc/ld.so.conf.d/oracle-instantclient.conf"

RUN ldconfig

ENTRYPOINT ["python"]
CMD ["./gu2_sales_robot.py"]

