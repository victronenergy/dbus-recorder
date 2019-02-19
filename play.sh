#!/bin/bash

dir=$(dirname $0)

start() {
        ${dir}/play.py "${@/#/$dir/}" &
}

# Stop an existing demo (if any)
pgrep -f play.py | xargs -r kill

# Start services
case "$1" in
    "2")
        # Boat/Motorhome demo 1
        start solarcharger.dat vebus.dat battery-house.dat \
			battery-hydraulic.dat tank_fwater.dat tank_fuel.dat \
			tank_oil.dat tank_bwater.dat
        ;;
    "3")
        # Boat/Motorhome demo 2
        start solarcharger.dat vebus-marine.dat battery-marine.dat \
			tank_fwater.dat tank_fuel.dat tank_oil.dat tank_bwater.dat
        ;;
    *)
        # ESS demo
        start grid.dat pvinverter.dat solarcharger.dat vebus.dat battery.dat
        ;;
esac
