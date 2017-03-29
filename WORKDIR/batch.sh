#!/bin/bash

MAX=100
BREAK=0

stopit() { BREAK=1; }


trap stopit SIGINT

for i in $(seq $MAX); do 
    # { time virltester allnodes.yml ;} >>main.log 2>&1
    { time virltester nxosv-9000-single-test.yml ;} >>main.log 2>&1
    test $BREAK -eq 1 && break
done
