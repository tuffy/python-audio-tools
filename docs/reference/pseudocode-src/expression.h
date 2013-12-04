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

struct expressionlist*
expressionlist_new(struct expression *expression, struct expressionlist *next);

unsigned
expressionlist_len(const struct expressionlist *self);

int
expressionlist_is_tall(const struct expressionlist *self);

void
expressionlist_free(struct expressionlist *self);

int
expression_is_tall(const struct expression *self);

int
expression_isnt_tall(const struct expression *self);


struct expression*
expression_new_constant(const_t constant);

void
expression_output_latex_constant(const struct expression *self,
                                 const struct definitions *defs,
                                 FILE *output);

void
expression_free_constant(struct expression *self);


struct expression*
expression_new_variable(struct variable *variable);

void
expression_output_latex_variable(const struct expression *self,
                                 const struct definitions *defs,
                                 FILE *output);

void
expression_free_variable(struct expression *self);


struct expression*
expression_new_integer(long long integer);

void
expression_output_latex_integer(const struct expression *self,
                                const struct definitions *defs,
                                FILE *output);

void
expression_free_integer(struct expression *self);


struct expression*
expression_new_float(char *float_);

void
expression_output_latex_float(const struct expression *self,
                              const struct definitions *defs,
                              FILE *output);

void
expression_free_float(struct expression *self);


struct expression*
expression_new_bytes(struct intlist *intlist);

void
expression_output_latex_bytes(const struct expression *self,
                              const struct definitions *defs,
                              FILE *output);

void
expression_free_bytes(struct expression *self);


struct expression*
expression_new_wrapped(wrap_type_t wrapper, struct expression *sub);

void
expression_output_latex_wrapped(const struct expression *self,
                                const struct definitions *defs,
                                FILE *output);

int
expression_is_tall_wrapped(const struct expression *self);

void
expression_free_wrapped(struct expression *self);


struct expression*
expression_new_function(func_type_t function, struct expression *arg);

void
expression_output_latex_function(const struct expression *self,
                                 const struct definitions *defs,
                                 FILE *output);

int
expression_is_tall_function(const struct expression *self);

void
expression_free_function(struct expression *self);


struct expression*
expression_new_fraction(struct expression *numerator,
                        struct expression *denominator);


void
expression_output_latex_fraction(const struct expression *self,
                                 const struct definitions *defs,
                                 FILE *output);

void
expression_free_fraction(struct expression *self);


struct expression*
expression_new_comparison(cmp_op_t operator,
                          struct expression *sub1,
                          struct expression *sub2);

void
expression_output_latex_comparison(const struct expression *self,
                                   const struct definitions *defs,
                                   FILE *output);

int
expression_is_tall_comparison(const struct expression *self);

void
expression_free_comparison(struct expression *self);


struct expression*
expression_new_boolean(bool_op_t operator,
                       struct expression *sub1,
                       struct expression *sub2);

void
expression_output_latex_boolean(const struct expression *self,
                                const struct definitions *defs,
                                FILE *output);

int
expression_is_tall_boolean(const struct expression *self);

void
expression_free_boolean(struct expression *self);


struct expression*
expression_new_not(struct expression *not);

void
expression_output_latex_not(const struct expression *self,
                            const struct definitions *defs,
                            FILE *output);

int
expression_is_tall_not(const struct expression *self);

void
expression_free_not(struct expression *self);


struct expression*
expression_new_math(math_op_t operator,
                    struct expression *sub1,
                    struct expression *sub2);

void
expression_output_latex_math(const struct expression *self,
                             const struct definitions *defs,
                             FILE *output);

int
expression_is_tall_math(const struct expression *self);

void
expression_free_math(struct expression *self);


struct expression*
expression_new_pow(struct expression *sub1,
                   struct expression *sub2);

void
expression_output_latex_pow(const struct expression *self,
                            const struct definitions *defs,
                            FILE *output);

int
expression_is_tall_pow(const struct expression *self);

void
expression_free_pow(struct expression *self);


struct expression*
expression_new_log(struct expression *subscript,
                   struct expression *expression);

void
expression_output_latex_log(const struct expression *self,
                            const struct definitions *defs,
                            FILE *output);

int
expression_is_tall_log(const struct expression *self);

void
expression_free_log(struct expression *self);


struct expression*
expression_new_sum(struct variable *variable,
                   struct expression *from,
                   struct expression *to,
                   struct expression *func);

void
expression_output_latex_sum(const struct expression *self,
                            const struct definitions *defs,
                            FILE *output);

void
expression_free_sum(struct expression *self);


struct expression*
expression_new_read(io_t type, struct expression *to_read);

void
expression_output_latex_read(const struct expression *self,
                             const struct definitions *defs,
                             FILE *output);

int
expression_is_tall_read(const struct expression *self);

void
expression_free_read(struct expression *self);


struct expression*
expression_new_read_unary(int stop_bit);

void
expression_output_latex_read_unary(const struct expression *self,
                                   const struct definitions *defs,
                                   FILE *output);

void
expression_free_read_unary(struct expression *self);


struct intlist*
intlist_new(int integer, struct intlist *next);

void
intlist_free(struct intlist *intlist);
