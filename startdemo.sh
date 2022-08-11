#!/bin/sh

# Stop services
svc -d /service/serial-starter
svc -d /service/mk2-dbus.*
svc -d /service/vecan-dbus.*
killall vedirect_dbus
killall gps_dbus

# Start the demo
$(dirname $0)/play.sh "$@"
