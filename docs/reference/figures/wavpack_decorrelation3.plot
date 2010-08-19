#!/usr/bin/gnuplot

set terminal fig color
set title "WavPack Decorrelation Pass 5"
set xlabel "time"
set ylabel "intensity"
set border 3
set xtics nomirror
set ytics nomirror

plot "figures/wavpack_decorr_pass4.dat" title "Pass 4" with lines, "figures/wavpack_decorr_pass5.dat" title 'Final Values' with lines;
