#!/usr/bin/gnuplot

set terminal postscript color eps
set title "A 16-bit Sine Audio Wave"
set xlabel "time"
set ylabel "intensity"
set samples 30
plot [0:30] sin(x / 5) * 32768 title 'PCM samples' with boxes,\
sin(x / 5) * 32768 title 'original audio' with lines

