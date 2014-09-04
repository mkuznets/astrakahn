#!/bin/bash

i=0
for var in "$@"
do
	taskset -pc $i $var
	echo $i
	i=$(($i + 1))
done
