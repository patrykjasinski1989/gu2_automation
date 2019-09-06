#!/bin/bash
# Tested on Ubuntu 18.04 and 16.04

username=$$$
password=$$$

sudo apt-get update && sudo apt-get install -y git python3 python3-pip libaio1 unzip

git clone https://${username}:${password}@bitbucket.org/zxnak37/gu2_automation.git
cd gu2_automation || exit 37
mv config_sample.py config.py
pip3 install --no-cache-dir -r requirements.txt

mkdir -p /opt/remedy && tar xvfz lib/api811linux.tar.gz  -C /opt/remedy --strip 1
bash -c "echo '# Remedy ARS support' > /etc/ld.so.conf.d/remedy.conf"
bash -c "echo /opt/remedy/lib >> /etc/ld.so.conf.d/remedy.conf"
bash -c "echo /opt/remedy/bin >> /etc/ld.so.conf.d/remedy.conf"

mkdir -p /opt/oracle && unzip lib/instantclient-basiclite-linux.x64-18.3.0.0.0dbru.zip -d /opt/oracle
sh -c "echo /opt/oracle/instantclient_18_3 > /etc/ld.so.conf.d/oracle-instantclient.conf"

ldconfig

git clone https://github.com/lewyg/pyremedy.git
pip3 install pyremedy/
