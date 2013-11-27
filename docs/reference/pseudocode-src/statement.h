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

struct funcdef*
funcdef_new(char *identifier,
            char *description,
            char *address,
            struct funcdef *next);

void
funcdef_free(struct funcdef *def);


struct statlist*
statlist_new(struct statement *statement, struct statlist *next);

void
statlist_output_latex(const struct statlist *self,
                      const struct definitions *defs,
                      FILE *output);

void
statlist_free(struct statlist *self);

unsigned
statlist_aligned(const struct statlist *statlist);

void
statement_output_latex_aligned(const struct statement *self,
                               const struct definitions *defs,
                               FILE *output);


struct statement*
statement_new_blankline(void);

void
statement_output_latex_blankline(const struct statement *self,
                                 const struct definitions *defs,
                                 FILE *output);

void
statement_free_blankline(struct statement *self);


struct statement*
statement_new_comment(char *comment);

void
statement_output_latex_comment(const struct statement *self,
                               const struct definitions *defs,
                               FILE *output);


void
statement_free_comment(struct statement *self);


struct statement*
statement_new_break(char *comment);

void
statement_output_latex_break(const struct statement *self,
                             const struct definitions *defs,
                             FILE *output);

void
statement_free_break(struct statement *self);


struct statement*
statement_new_assign_in(struct variablelist *variablelist,
                        struct expression *expression,
                        char *comment);

void
statement_output_latex_assign_in(const struct statement *self,
                                 const struct definitions *defs,
                                 FILE *output);

void
statement_free_assign_in(struct statement *self);


struct statement*
statement_new_functioncall(char *identifier,
                           struct expressionlist *input_args,
                           struct variablelist *output_args,
                           char *comment);

void
statement_output_latex_functioncall(const struct statement *self,
                                    const struct definitions *defs,
                                    FILE *output);

void
statement_output_latex_functioncall_name(const struct statement *self,
                                         const struct definitions *defs,
                                         FILE *output);

void
statement_output_latex_functioncall_args(const struct statement *self,
                                         const struct definitions *defs,
                                         FILE *output);

void
statement_free_functioncall(struct statement *self);


struct statement*
statement_new_if(struct expression *condition,
                 struct statlist *then,
                 char *then_comment,
                 struct elselist *elselist);

void
statement_output_latex_if(const struct statement *self,
                          const struct definitions *defs,
                          FILE *output);

void
statement_free_if(struct statement *self);


struct elselist*
elselist_new(struct expression *condition,
             char *else_comment,
             struct statlist *else_,
             struct elselist *next);

void
elselist_output_latex(const struct elselist *self,
                      const struct definitions *defs,
                      FILE *output);

void
elselist_free(struct elselist *self);


struct statement*
statement_new_switch(struct expression *condition,
                     char *switch_comment,
                     struct caselist *cases);

void
statement_output_latex_switch(const struct statement *self,
                              const struct definitions *defs,
                              FILE *output);

void
statement_free_switch(struct statement *self);


struct caselist*
caselist_new(struct expression *expression,
             char *case_comment,
             struct statlist *case_,
             struct caselist* next);

void
caselist_output_latex(const struct caselist *self,
                      const struct definitions *defs,
                      FILE *output);

void
caselist_free(struct caselist *self);

/*returns true if the given case expression is suitable for inlining*/
int
caselist_inline_condition(const struct expression *condition);

/*returns true if the given statement list is suitable for inlining*/
int
caselist_inline_case(const struct statlist *case_);


struct statement*
statement_new_while(struct expression *condition,
                    char *condition_comment,
                    struct statlist *statements);

void
statement_output_latex_while(const struct statement *self,
                             const struct definitions *defs,
                             FILE *output);

void
statement_free_while(struct statement *self);


struct statement*
statement_new_do_while(struct expression *condition,
                       char *condition_comment,
                       struct statlist *statements,
                       char *statments_comment);

void
statement_output_latex_do_while(const struct statement *self,
                                const struct definitions *defs,
                                FILE *output);

void
statement_free_do_while(struct statement *self);


struct statement*
statement_new_for(for_direction_t direction,
                  struct variable *variable,
                  struct expression *start,
                  struct expression *finish,
                  char *for_comment,
                  struct statlist *statements);

void
statement_output_latex_for(const struct statement *self,
                           const struct definitions *defs,
                           FILE *output);

void
statement_free_for(struct statement *self);


struct statement*
statement_new_return(struct expressionlist *toreturn,
                     char *return_comment);

void
statement_output_latex_return(const struct statement *self,
                              const struct definitions *defs,
                              FILE *output);

void
statement_free_return(struct statement *self);


struct statement*
statement_new_assert(struct expression *condition,
                     char *assert_comment);

void
statement_output_latex_assert(const struct statement *self,
                              const struct definitions *defs,
                              FILE *output);

void
statement_free_assert(struct statement *self);


struct statement*
statement_new_write(io_t type,
                    struct expression *value,
                    struct expression *to_write,
                    char *comment);

void
statement_output_latex_write(const struct statement *self,
                             const struct definitions *defs,
                             FILE *output);

void
statement_free_write(struct statement *self);


struct statement*
statement_new_write_unary(int stop_bit,
                          struct expression *value,
                          char *comment);

void
statement_output_latex_write_unary(const struct statement *self,
                                   const struct definitions *defs,
                                   FILE *output);

void
statement_free_write_unary(struct statement *self);


struct statement*
statement_new_skip(struct expression *expression,
                   io_t type,
                   char *skip_comment);

void
statement_output_latex_skip(const struct statement *self,
                            const struct definitions *defs,
                            FILE *output);

void
statement_free_skip(struct statement *self);
