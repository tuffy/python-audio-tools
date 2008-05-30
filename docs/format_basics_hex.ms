.\"This work is licensed under the 
.\"Creative Commons Attribution-Share Alike 3.0 United States License.
.\"To view a copy of this license, visit
.\"http://creativecommons.org/licenses/by-sa/3.0/us/ or send a letter to 
.\"Creative Commons, 
.\"171 Second Street, Suite 300, 
.\"San Francisco, California, 94105, USA.
.SUBSECTION "Hexadecimal"
.PP
In order to understand hexadecimal, it's important to re-familiarize
oneself with decimal, which everyone reading this should be familiar with.
In ordinary decimal numbers, there are a total of ten characters per digit:
0, 1, 2, 3, 4, 5, 6, 7, 8 and 9.
Because there are ten, we'll call it base-10.
So the number 675 is made up of the digits 6, 7 and 5
and can be calculated in the following way:

@(6~\[mu]~10 sup 2 ) + (7~\[mu]~10 sup 1 ) + (5~\[mu]~10 sup 0 ) = 675@

.PP
In hexadecimal, there are sixteen characters per digit:
0, 1, 2, 3, 4, 5, 6, 7, 8, 9, A, B, C, D, E and F.
A, B, C, D, E and F correspond to the decimal numbers
10, 11, 12, 13, 14 and 15, respectively.
Because there are sixteen, we'll call it base-16.
So the number 2A3 is made up of the digits 2, A and 3
and can be calculated in the following way:

@(2~\[mu]~16 sup 2 ) + (10~\[mu]~16 sup 1 ) + (3~\[mu]~16 sup 0 ) = 675@

.PP
Why use hexadecimal?
The reason brings us back to binary file formats, which are
made up of bytes.
Each byte is made up of 8 bits and can have a value from 0 to 255,
in decimal.
Representing a binary file in hexadecimal means a byte requires
exactly two digits with values from 0 to FF.
That saves us a lot of space versus trying to represent bytes
in decimal.
.PP
Hexadecimal has another important property when dealing with
binary data.
Because each digit has 16 possible values, each hexadecimal
digit represents exactly 4 bits (@16 = 2 sup 4@).
.TS
tab(:);
| c s s s s s |
| c | c | c || c | c | c |.
_
Hexadecimal Conversion Table
_
Hex:Binary:Decimal:Hex:Binary:Decimal
=
\fC0: 0 0 0 0 :0:8: 1 0 0 0 :8
1:0 0 0 1:1:9:1 0 0 1:9
2:0 0 1 0:2:A:1 0 1 0:10
3:0 0 1 1:3:B:1 0 1 1:11
4:0 1 0 0:4:C:1 1 0 0:12
5:0 1 0 1:5:D:1 1 0 1:13
6:0 1 1 0:6:E:1 1 1 0:14
7:0 1 1 1:7:F:1 1 1 1:15\fR
_
.TE
This makes it very easy to go back and forth between hexadecimal
and binary.  For instance, let's take the byte \fC6A\fR.
.PSPIC -L "binary.eps" 1.25i

Going from binary to hexadecimal is a simple matter of reversing
the process.
Combining multiple bytes into a single, larger number requires
a similar method, but that brings us to endianness issues.
