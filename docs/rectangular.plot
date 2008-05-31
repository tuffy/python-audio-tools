#!/usr/bin/gnuplot

set terminal postscript color eps
set title "the Rectangular Window"
set border 3
set xtics nomirror
set ytics nomirror
set ylabel "multiplier"
set xlabel "sample"
set yrange [0.0:1.0]
rectangle(x) = 1.0
plot [0:3072] rectangle(x)
