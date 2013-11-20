#include <stdio.h>
#include "types.h"

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

struct vardef*
vardef_new(char *identifier, char *label, struct vardef *next);

void
vardef_free(struct vardef *var);


struct variablelist*
variablelist_new(struct variable *variable, struct variablelist *next);

void
variablelist_output_latex(const struct variablelist *self,
                          const struct definitions *defs,
                          FILE *output);

unsigned
variablelist_len(const struct variablelist *self);

void
variablelist_free(struct variablelist *self);


struct variable*
variable_new(char *identifier, struct subscript* subscript);

void
variable_output_latex(const struct variable *self,
                      const struct definitions *defs,
                      FILE *output);

void
variable_free(struct variable *self);

struct subscript*
subscript_new(struct expression *expression, struct subscript* next);

void
subscript_free(struct subscript* subscript);
