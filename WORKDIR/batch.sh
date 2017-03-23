#!/bin/bash

for i in $(seq 100); do { time virltester allnodes.yml ;}  >>main.log 2>&1 ; done
