#!/bin/bash
export PYTHONPATH=/opt/color-control/pythonshared
/opt/color-control/dbusrecorder/dbusrecorder.py --record com.victronenergy.gps --file=/opt/color-control/dbusrecorder/gps.dat --duration=2700 &
