#!/bin/bash

dir=$(dirname $0)

start() {
        ${dir}/dbusrecorder.py -p --file="${dir}/$1" &
}

# Start services
start grid.dat
start pvinverter.dat
start solarcharger.dat
start vebus.dat
start battery.dat
