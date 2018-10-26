#!/bin/bash

dir=$(dirname $0)

start() {
        ${dir}/dbusrecorder.py -p --file="${dir}/$1" &
}

# Start services
start solarcharger.dat
start vebus-marine.dat
start battery-marine.dat
start tank_fwater.dat
start tank_fuel.dat
start tank_oil.dat
start tank_bwater.dat
