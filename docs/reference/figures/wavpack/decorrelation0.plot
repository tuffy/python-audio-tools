#!/usr/bin/gnuplot

set terminal fig color
set title "Bitstream Values"
set xlabel "i"
set ylabel "value"
set border 3
set xtics nomirror
set ytics nomirror

plot "figures/wavpack/decorr_pass0.dat" title 'residual' with lines;
