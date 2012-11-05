#!/usr/bin/gnuplot

set terminal fig color
set title "decorrelation passes"
set xlabel "time"
set ylabel "intensity"
set border 3
set xtics nomirror
set ytics nomirror

plot "figures/wavpack/decorrelation0.dat" title 'residuals' with steps,"figures/wavpack/decorrelation1.dat" title 'pass 1' with steps, "figures/wavpack/decorrelation2.dat" title 'pass 2' with steps, "figures/wavpack/decorrelation3.dat" title 'pass 3' with steps, "figures/wavpack/decorrelation4.dat" title 'pass 4' with steps;
