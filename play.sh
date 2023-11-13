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
			tank_oil.csv tank_bwater.csv ruuvi.csv
        ;;
    "3")
        # Boat/Motorhome demo 2
		start demo2_alternator.csv demo2_diesel.csv demo2_solarcharger.csv \
			demo2_battery.csv demo2_freezer.csv demo2_vebus.csv \
			demo2_blackwater.csv demo2_fridge.csv demo2_water.csv \
			demo2_hydropack_battery.csv demo2_cabin.csv demo2_outside.csv
        ;;
    *)
        # ESS demo
        start grid.csv pvinverter.csv solarcharger.csv vebus.csv battery.csv
        ;;
esac
