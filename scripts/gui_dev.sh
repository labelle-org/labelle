#!/usr/bin/env bash

while true; do
    LABELLE_DEV_MODE_NO_MARGINS=$LABELLE_DEV_MODE_NO_MARGINS \
    LABELLE_VERBOSE=$LABELLE_VERBOSE \
        labelle-gui -v;
    sleep 1
 done
