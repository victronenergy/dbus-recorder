#!/bin/sh

# Stop services
svc -d /service/serial-starter
svc -d /service/mk2-dbus.$(basename $(cat /etc/venus/mkx_port))
svc -d /service/vecan
killall vedirect_dbus
killall gps_dbus

# Start the demo
$(dirname $0)/play.sh "$@"
