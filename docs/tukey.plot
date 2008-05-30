#!/usr/bin/gnuplot

set terminal postscript color eps
set title "the Tukey Window"
set border 3
set xtics nomirror
set ytics nomirror
set ylabel "multiplier"
set xlabel "sample"
hann(x) = 0.5 - (0.5 * cos((2.0 * pi * x) / 1023))
hann2(x) = 0.5 - (0.5 * cos((2.0 * pi * (x - 3072)) / 1023))
rectangle(x) = 1
tukey(x) = (x < 512) ? hann(x) : (x > 3584) ? hann2(x) : rectangle(x)
plot [0:4096] tukey(x)
