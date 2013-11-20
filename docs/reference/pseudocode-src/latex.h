#ifndef PSEUDOCODE_LATEX
#define PSEUDOCODE_LATEX

#include <stdio.h>

/********************************************************
 Audio Tools, a module and set of tools for manipulating audio data
 Copyright (C) 2007-2013  Brian Langenberger

 This program is free software; you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation; either version 2 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program; if not, write to the Free Software
 Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
*******************************************************/

/*given a string object "some amount of text"
  escapes it for a LaTeX square bracket block, like [some amount of text]*/
void
escape_latex_square_brackets(FILE *output, const char *string);

/*given a string object "some amount of text"
  escapes it for a LaTeX curly bracket block, like {some amount of text}*/
void
escape_latex_curly_brackets(FILE *output, const char *string);

/*given an identifier object, escapes it for any LaTeX block
  (identifiers can only contain underscores that need to be handled)*/
void
escape_latex_identifier(FILE *output, const char *identifier);

void
escape_latex_variable(FILE *output, unsigned variable_id);

#endif
