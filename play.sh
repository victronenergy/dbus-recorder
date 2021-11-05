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
        start solarcharger.csv vebus.csv battery-house.csv \
			battery-hydraulic.csv tank_fwater.csv tank_fuel.csv \
			tank_oil.csv tank_bwater.csv
        ;;
    "3")
        # Boat/Motorhome demo 2
        start solarcharger.csv vebus-marine.csv battery-marine.csv \
			tank_fwater.csv tank_fuel.csv tank_oil.csv tank_bwater.csv
        ;;
    *)
        # ESS demo
        start grid.csv pvinverter.csv solarcharger.csv vebus.csv battery.csv
        ;;
esac
