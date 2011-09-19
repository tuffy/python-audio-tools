#!/usr/bin/gnuplot

set terminal fig color
set title "WavPack Decorrelation Passes 1-4"
set xlabel "time"
set ylabel "intensity"
set border 3
set xtics nomirror
set ytics nomirror

plot "figures/wavpack_decorr_pass1.dat" title 'Pass 1' with lines, "figures/wavpack_decorr_pass2.dat" title 'Pass 2' with lines, "figures/wavpack_decorr_pass3.dat" title 'Pass 3' with lines, "figures/wavpack_decorr_pass4.dat" title 'Pass 4' with lines;
