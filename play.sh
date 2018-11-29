#!/bin/bash

dir=$(dirname $0)

start() {
        ${dir}/dbusrecorder.py -p --file="${dir}/$1" &
}

# Stop an existing demo (if any)
pgrep -f dbusrecorder.py | xargs -r kill -9

# Start services
case "$1" in
	"2")
		# Boat/Motorhome demo 1
		start solarcharger.dat
		start vebus.dat
		start battery-house.dat
		start battery-hydraulic.dat
		start tank_fwater.dat
		start tank_fuel.dat
		start tank_oil.dat
		start tank_bwater.dat
		;;
	"3")
		# Boat/Motorhome demo 2
        start solarcharger.dat
        start vebus-marine.dat
        start battery-marine.dat
        start tank_fwater.dat
        start tank_fuel.dat
        start tank_oil.dat
        start tank_bwater.dat
        ;;
	*)
        # ESS demo
        start grid.dat
        start pvinverter.dat
        start solarcharger.dat
        start vebus.dat
        start battery.dat
        ;;
esac
