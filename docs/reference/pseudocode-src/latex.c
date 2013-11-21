#include "latex.h"

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

void
escape_latex_square_brackets(FILE *output, const char *string)
{
    /*escape underscores, square brackets and dollar signs*/

    char c;

    while ((c = string[0]) != '\0') {
        switch (c) {
        case '$':
        case '[':
        case ']':
            fprintf(output, "\\%c", c);
            break;
        default:
            putc(c, output);
        }

        string++;
    }
}


void
escape_latex_curly_brackets(FILE *output, const char *string)
{
    /*escape underscores, curly brackets and dollar signs*/

    char c;

    while ((c = string[0]) != '\0') {
        switch (c) {
        case '_':
        case '$':
        case '{':
        case '}':
            fprintf(output, "\\%c", c);
            break;
        default:
            putc(c, output);
        }

        string++;
    }
}

void
escape_latex_identifier(FILE *output, const char *identifier)
{
    /*escape underscores*/

    char c;

    while ((c = identifier[0]) != '\0') {
        if (c == '_') {
            fputs("\\_", output);
        } else {
            putc(c, output);
        }

        identifier++;
    }
}

void
escape_latex_variable(FILE *output, unsigned variable_id)
{
    const static char id_chars[] =
        "abcdefghijklmnopqrstuvwxyzABCDEF";

    fputs("VAR", output);
    do {
        fputc(id_chars[variable_id & 0x1F], output);
        variable_id >>= 5;
    } while (variable_id > 0);
}
