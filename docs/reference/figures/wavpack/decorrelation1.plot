#!/usr/bin/gnuplot

set terminal fig color
set title "WavPack Bitstream Values"
set xlabel "time"
set ylabel "intensity"
set border 3
set xtics nomirror
set ytics nomirror

plot "figures/wavpack_decorr_pass0.dat" title 'Bitstream Values' with lines;
