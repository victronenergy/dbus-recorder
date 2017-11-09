#!/bin/sh

# Stop services
PID=`pgrep -f dbusrecorder.py | tr '\n' ' '`
echo "PID(dbusrecorder) = $PID"
[ -z "$PID" ] || kill -9 $PID

if [ "$1" != "booting" ]; then
    # Start services
    svc -u /service/serial-starter
    svc -u /service/vecan-mk2.$(basename $(cat /etc/venus/mkx_port))
    svc -u /service/vecan
fi
