#!/usr/bin/gnuplot

set terminal fig color
set title "Decorrelation Pass 1"
set xlabel "i"
set ylabel "value"
set border 3
set xtics nomirror
set ytics nomirror

plot "wavpack/figures/decorr_pass1.dat" title 'pass 1' with lines;
