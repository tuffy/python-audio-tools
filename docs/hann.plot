#!/usr/bin/gnuplot

set terminal postscript color eps
set title "the Hann Window"
set border 3
set xtics nomirror
set ytics nomirror
set ylabel "multiplier"
set xlabel "sample"
hann(x) = 0.5 - (0.5 * cos((2.0 * pi * x) / 1023))
plot [0:1024] hann(x)
