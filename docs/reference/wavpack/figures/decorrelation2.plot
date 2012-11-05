#!/usr/bin/gnuplot

set terminal fig color
set title "Decorrelation Pass 2"
set xlabel "i"
set ylabel "value"
set border 3
set xtics nomirror
set ytics nomirror

plot "figures/wavpack/decorr_pass2.dat" title 'pass 2' with lines;
