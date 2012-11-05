#!/usr/bin/gnuplot

set terminal fig color
set title "decorrelation passes"
set xlabel "time"
set ylabel "intensity"
set border 3
set xtics nomirror
set ytics nomirror

plot "wavpack/figures/decorrelation0.dat" title 'residuals' with steps,"wavpack/figures/decorrelation1.dat" title 'pass 1' with steps, "wavpack/figures/decorrelation2.dat" title 'pass 2' with steps, "wavpack/figures/decorrelation3.dat" title 'pass 3' with steps, "wavpack/figures/decorrelation4.dat" title 'pass 4' with steps;
