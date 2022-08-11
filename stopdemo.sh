#!/bin/sh

# Stop demo
pgrep -f play.py | xargs -r kill

if [ "$1" != "booting" ]; then
    # Start services
    svc -u /service/mk2-dbus.*
    svc -u /service/vecan-dbus.*
    svc -u /service/serial-starter
fi
