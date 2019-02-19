#!/bin/sh

# Stop demo
pgrep -f play.py | xargs -r kill

if [ "$1" != "booting" ]; then
    # Start services
    svc -u /service/serial-starter
    svc -u /service/mk2-dbus.$(basename $(cat /etc/venus/mkx_port))
    svc -u /service/vecan
fi
