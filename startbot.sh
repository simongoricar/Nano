#!/bin/bash
cp my.log my.log.bak
rm -f my.log
nohup python3 nano.py > my.log 2>&1&
echo $! > save_pid.txt
