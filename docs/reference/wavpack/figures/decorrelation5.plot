#!/usr/bin/gnuplot

set terminal fig color
set title "Decorrelation Pass 5"
set xlabel "i"
set ylabel "value"
set border 3
set xtics nomirror
set ytics nomirror

plot "figures/wavpack/decorr_pass5.dat" title 'pass 5' with lines;
