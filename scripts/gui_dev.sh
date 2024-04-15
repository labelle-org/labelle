#!/usr/bin/env bash

while true; do
    DEV_MODE_NO_MARGINS=$DEV_MODE_NO_MARGINS \
    LABELLE_VERBOSE=$LABELLE_VERBOSE \
        labelle-gui -v;
    sleep 1
 done
