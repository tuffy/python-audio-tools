#include <stdlib.h>
#include <string.h>
#include "statement.h"
#include "expression.h"
#include "variable.h"
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

struct funcdef*
funcdef_new(char *identifier,
            char *description,
            char *address,
            struct funcdef *next)
{
    struct funcdef *funcdef = malloc(sizeof(struct funcdef));
    funcdef->identifier = identifier;
    funcdef->description = description;
    funcdef->address = address;
    funcdef->next = next;
    return funcdef;
}

void
funcdef_free(struct funcdef *def)
{
    if (def != NULL) {
        funcdef_free(def->next);
        free(def->identifier);
        free(def->description);
        free(def->address);
        free(def);
    }
}


struct statlist*
statlist_new(struct statement *statement, struct statlist *next)
{
    struct statlist *statlist = malloc(sizeof(struct statlist));
    statlist->statement = statement;
    statlist->next = next;
    statlist->output_latex = statlist_output_latex;
    statlist->free = statlist_free;
    return statlist;
}

void
statlist_output_latex(const struct statlist *self,
                      const struct definitions *defs,
                      FILE *output)
{
    const struct statlist *s = self;

    /*may need to unify mulitple assign_in statements into block*/
    while (s != NULL) {
        unsigned aligned_statements = statlist_aligned(s);
        if (aligned_statements > 1) {
            /*wrap statements in alignment table*/
            fprintf(output, "{\\renewcommand{\\tabcolsep}{0.5mm}");
            fprintf(output, "\\begin{tabular}{rclr}\n");

            /*display aligned statements as rows*/
            for (; aligned_statements > 0; aligned_statements--) {
                statement_output_latex_aligned(s->statement, defs, output);
                s = s->next;
            }

            /*close table*/
            fprintf(output, "\\end{tabular}\\;\n");
            fprintf(output, "}\n");
        } else {
            const struct statement *statement = s->statement;
            statement->output_latex(statement, defs, output);
            s = s->next;
        }
    }
}

void
statlist_free(struct statlist *statlist)
{
    struct statement *statement = statlist->statement;
    statement->free(statement);
    if (statlist->next != NULL)
        statlist->next->free(statlist->next);
    free(statlist);
}

unsigned
statlist_aligned(const struct statlist *statlist)
{
    if (statlist != NULL) {
        const struct statement *statement = statlist->statement;
        switch (statement->type) {
        case STAT_BLANKLINE:
        case STAT_ASSIGN_IN:
        case STAT_WRITE:
        case STAT_WRITE_UNARY:
        case STAT_FUNCTIONCALL_WRITE:
        case STAT_FUNCTIONCALL_WRITE_UNARY:
            return 1 + statlist_aligned(statlist->next);
        case STAT_FUNCTIONCALL:
            if (statement->_.functioncall.output_args != NULL) {
                return 1 + statlist_aligned(statlist->next);
            } else {
                return 0;
            }
        default:
            return 0;
        }
    } else {
        return 0;
    }
}

void
statement_output_latex_aligned(const struct statement *self,
                               const struct definitions *defs,
                               FILE *output)
{
    switch (self->type) {
    case STAT_BLANKLINE:
        fputs("& & & \\\\", output);
        break;
    case STAT_ASSIGN_IN:
        {
            const struct variablelist *variablelist =
                self->_.assign_in.variablelist;
            const struct expression *expression =
                self->_.assign_in.expression;
            const char *comment = self->_.assign_in.comment;

            fprintf(output, "$");
            variablelist->output_latex(variablelist, defs, output);
            fprintf(output, "$ & $\\leftarrow$ & $");
            expression->output_latex(expression, defs, output);
            fprintf(output, "$ & ");
            statement_output_latex_aligned_comment_text(comment, output);
            fprintf(output, "\\\\");
        }
        break;
    case STAT_WRITE:
        {
            io_t type = self->_.write.type;
            const struct expression *value = self->_.write.value;
            const struct expression *to_write = self->_.write.to_write;
            char *comment = self->_.write.comment;

            fprintf(output, "$");
            value->output_latex(value, defs, output);
            fprintf(output, "$ & $\\rightarrow $ & $");
            statement_output_latex_write_args(type,
                                              to_write,
                                              defs,
                                              output);
            fprintf(output, "$ & ");
            statement_output_latex_aligned_comment_text(comment, output);
            fprintf(output, "\\\\");
        }
        break;
    case STAT_WRITE_UNARY:
        {
            int stop_bit = self->_.write_unary.stop_bit;
            const struct expression *value = self->_.write_unary.value;
            const char *comment = self->_.write_unary.comment;

            fprintf(output, "$");
            value->output_latex(value, defs, output);
            fprintf(output, "$ & $\\rightarrow $ & $");
            statement_output_latex_write_args_unary(stop_bit, output);
            fprintf(output, "$ & ");
            statement_output_latex_aligned_comment_text(comment, output);
            fprintf(output, "\\\\");
        }
        break;
    case STAT_FUNCTIONCALL:
        {
            const struct variablelist *output_args =
                self->_.functioncall.output_args;
            const char *comment = self->_.functioncall.functioncall_comment;

            fprintf(output, "$");
            if (output_args != NULL) {
                output_args->output_latex(output_args, defs, output);
                fprintf(output, "$ & $\\leftarrow$ & $");
            } else {
                fprintf(output, "$ & & $");
            }

            statement_output_latex_functioncall_name(
                self->_.functioncall.identifier, defs, output);
            statement_output_latex_functioncall_args(self, defs, output);

            fprintf(output, "$ & ");
            statement_output_latex_aligned_comment_text(comment, output);
            fprintf(output, "\\\\");
        }
        break;
    case STAT_FUNCTIONCALL_WRITE:
        {
            const char *identifier =
                self->_.functioncall_write.identifier;
            const struct expressionlist *input_args =
                self->_.functioncall_write.input_args;
            io_t type =
                self->_.functioncall_write.type;
            const struct expression *to_write =
                self->_.functioncall_write.to_write;
            const char *comment =
                self->_.functioncall_write.comment;

            fputs("$", output);

            statement_output_latex_functioncall_write_args(identifier,
                                                           input_args,
                                                           defs,
                                                           output);

            fputs("$ & $\\rightarrow$ & $", output);

            statement_output_latex_write_args(type, to_write, defs, output);

            fputs("$ & ", output);

            statement_output_latex_aligned_comment_text(comment, output);

            fputs("\\\\", output);
        }
        break;
    case STAT_FUNCTIONCALL_WRITE_UNARY:
        {
            const char *identifier =
                self->_.functioncall_write_unary.identifier;
            const struct expressionlist *input_args =
                self->_.functioncall_write_unary.input_args;
            int stop_bit =
                self->_.functioncall_write_unary.stop_bit;
            const char *comment =
                self->_.functioncall_write_unary.comment;

            fputs("$", output);

            statement_output_latex_functioncall_write_args(identifier,
                                                           input_args,
                                                           defs,
                                                           output);

            fputs("$ & $\\rightarrow$ & $", output);

            statement_output_latex_write_args_unary(stop_bit, output);

            fputs("$ & ", output);

            statement_output_latex_aligned_comment_text(comment, output);

            fputs("\\\\", output);

        }
        break;
    default:
        /*no output*/
        break;
    }
}

struct statement*
statement_new_blankline(void)
{
    struct statement *statement = malloc(sizeof(struct statement));
    statement->type = STAT_BLANKLINE;
    statement->output_latex = statement_output_latex_blankline;
    statement->free = statement_free_blankline;
    return statement;
}

void
statement_output_latex_blankline(const struct statement *self,
                                 const struct definitions *defs,
                                 FILE *output)
{
    fprintf(output, "\\BlankLine");
}

void
statement_free_blankline(struct statement *self)
{
    free(self);
}


struct statement*
statement_new_comment(char *comment)
{
    struct statement *statement = malloc(sizeof(struct statement));
    statement->type = STAT_COMMENT;
    statement->_.comment = comment;
    statement->output_latex = statement_output_latex_comment;
    statement->free = statement_free_comment;
    return statement;
}

void
statement_output_latex_comment(const struct statement *self,
                               const struct definitions *defs,
                               FILE *output)
{
    fprintf(output, "\\tcc{");
    escape_latex_curly_brackets(output, self->_.comment);
    fprintf(output, "}\n");
}

void
statement_free_comment(struct statement *self)
{
    free(self->_.comment);
    free(self);
}


void
statement_output_latex_comment_text(const char *comment, FILE *output)
{
    if (comment != NULL) {
        fputs("\\tcc*{", output);
        escape_latex_curly_brackets(output, comment);
        fputs("}", output);
    } else {
        fputs("\\;", output);
    }
}

void
statement_output_latex_aligned_comment_text(const char *comment, FILE *output)
{
    if (comment != NULL) {
        fprintf(output, "\\tcc*{");
        escape_latex_curly_brackets(output, comment);
        fprintf(output, "}");
    }
}

struct statement*
statement_new_break(char *comment)
{
    struct statement *statement = malloc(sizeof(struct statement));
    statement->type = STAT_BREAK;
    statement->_.comment = comment;
    statement->output_latex = statement_output_latex_break;
    statement->free = statement_free_break;
    return statement;
}

void
statement_output_latex_break(const struct statement *self,
                             const struct definitions *defs,
                             FILE *output)
{
    fputs("\\BREAK", output);
    statement_output_latex_comment_text(self->_.comment, output);
}

void
statement_free_break(struct statement *self)
{
    free(self->_.comment);
    free(self);
}


struct statement*
statement_new_assign_in(struct variablelist *variablelist,
                        struct expression *expression,
                        char *comment)
{
    struct statement *statement = malloc(sizeof(struct statement));
    statement->type = STAT_ASSIGN_IN;
    statement->_.assign_in.variablelist = variablelist;
    statement->_.assign_in.expression = expression;
    statement->_.assign_in.comment = comment;
    statement->output_latex = statement_output_latex_assign_in;
    statement->free = statement_free_assign_in;
    return statement;
}

void
statement_output_latex_assign_in(const struct statement *self,
                                 const struct definitions *defs,
                                 FILE *output)
{
    struct variablelist *variablelist = self->_.assign_in.variablelist;
    struct expression *expression = self->_.assign_in.expression;

    fprintf(output, "$");

    variablelist->output_latex(variablelist, defs, output);

    fprintf(output, " \\leftarrow ");

    expression->output_latex(expression, defs, output);

    fprintf(output, "$");

    statement_output_latex_comment_text(self->_.assign_in.comment, output);

    fprintf(output, "\n");
}

void
statement_free_assign_in(struct statement *self)
{
    struct variablelist *variablelist = self->_.assign_in.variablelist;
    struct expression *expression = self->_.assign_in.expression;
    variablelist->free(variablelist);
    expression->free(expression);
    free(self->_.assign_in.comment);
    free(self);
}

struct statement*
statement_new_functioncall(char *identifier,
                           struct expressionlist *input_args,
                           struct variablelist *output_args,
                           char *comment)
{
    struct statement *statement = malloc(sizeof(struct statement));
    statement->type = STAT_FUNCTIONCALL;
    statement->_.functioncall.identifier = identifier;
    statement->_.functioncall.input_args = input_args;
    statement->_.functioncall.output_args = output_args;
    statement->_.functioncall.functioncall_comment = comment;
    statement->output_latex = statement_output_latex_functioncall;
    statement->free = statement_free_functioncall;
    return statement;
}

void
statement_output_latex_functioncall(const struct statement *self,
                                    const struct definitions *defs,
                                    FILE *output)
{
    const struct variablelist *output_args = self->_.functioncall.output_args;
    const char *comment = self->_.functioncall.functioncall_comment;

    fprintf(output, "$");

    /*display output variables, if any*/
    if (output_args != NULL) {
        output_args->output_latex(output_args, defs, output);

        fprintf(output, " \\leftarrow ");
    }

    statement_output_latex_functioncall_name(self->_.functioncall.identifier,
                                             defs,
                                             output);
    statement_output_latex_functioncall_args(self, defs, output);

    fprintf(output, "$");
    statement_output_latex_comment_text(comment, output);
    fprintf(output, "\n");
}

void
statement_output_latex_functioncall_name(const char *identifier,
                                         const struct definitions *defs,
                                         FILE *output)
{
    const char *description = NULL;
    const char *address = NULL;
    const struct funcdef *func;

    /*perform lookup on identifier to find description, if any*/
    for (func = defs->functions; func != NULL; func = func->next) {
        if (strcmp(identifier, func->identifier) == 0) {
            description = func->description;
            address = func->address;
            break;
        }
    }

    if (description == NULL) {
        fprintf(output, "{\\textnormal{\\texttt{");
        escape_latex_identifier(output, identifier);
        fprintf(output, "}}\\unskip}");
    } else {
        /*wrap description with hyperref if function contains address*/
        if (address == NULL) {
            fprintf(output, "{\\textnormal{\\textsf{");
            escape_latex_curly_brackets(output, description);
            fprintf(output, "}}\\unskip}");
        } else {
            fprintf(output, "{\\textnormal{\\hyperref[");
            escape_latex_square_brackets(output, address);
            fprintf(output, "]{\\textsf{");
            escape_latex_curly_brackets(output, description);
            fprintf(output, "}}}\\unskip}");
        }
    }
}

void
statement_output_latex_functioncall_args(const struct statement *self,
                                         const struct definitions *defs,
                                         FILE *output)
{
    int function_defined = 0;
    const struct funcdef *var;
    const struct expressionlist *input_args = self->_.functioncall.input_args;

    /*perform lookup on identifier to see if function is defined*/
    for (var = defs->functions; var != NULL; var = var->next) {
        if (strcmp(self->_.functioncall.identifier, var->identifier) == 0) {
            function_defined = 1;
            break;
        }
    }

    if (!function_defined) {
        const int is_tall =
            (input_args != NULL) && (input_args->is_tall(input_args));

        if (is_tall) {
            fputs("\\left(", output);
        } else {
            fputs("(", output);
        }

        for (; input_args != NULL; input_args = input_args->next) {
            struct expression *expression = input_args->expression;
            expression->output_latex(expression, defs, output);
            if (input_args->next != NULL) {
                fprintf(output, "~,~");
            }
        }

        if (is_tall) {
            fputs("\\right)", output);
        } else {
            fputs(")", output);
        }
    } else {
        if (input_args != NULL) {
            const struct expressionlist *arg;

            switch (input_args->len(input_args)) {
            case 0:
                /*no arguments, no output*/
                break;
            case 1:
                /*one argument*/
                {
                    const struct expression *expression =
                        input_args->expression;
                    if (expression->is_tall(expression)) {
                        fprintf(output, "\\left(");
                        expression->output_latex(expression, defs, output);
                        fprintf(output, "\\right)");
                    } else {
                        fprintf(output, "(");
                        expression->output_latex(expression, defs, output);
                        fprintf(output, ")");
                    }
                }
                break;
            default:
                /*multiple arguments*/
                {
                    /*divide arguments into columns if there are too many*/
                    const unsigned args = input_args->len(input_args);
                    const unsigned total_columns =
                        (args / ITEMS_PER_COLUMN) +
                        ((args % ITEMS_PER_COLUMN) ? 1 : 0);
                    unsigned i;

                    arg = input_args;

                    fputs("\\left\\lbrace\\begin{tabular}{", output);
                    for (i = 0; i < total_columns; i++) {
                        fputs("l", output);
                    }
                    fputs("}", output);

                    while (arg != NULL) {
                        for (i = 0; i < total_columns; i++) {
                            if (arg != NULL) {
                                const struct expression *expression =
                                    arg->expression;
                                fputs("$", output);
                                expression->output_latex(expression,
                                                         defs,
                                                         output);
                                fputs("$", output);

                                arg = arg->next;
                            } else {
                                fputs(" ", output);
                            }
                            if ((i + 1) < total_columns) {
                                fputs(" & ", output);
                            } else {
                                fputs(" \\\\ ", output);
                            }
                        }
                    }

                    fprintf(output, "\\end{tabular}\\right.");
                }
                break;
            }
        } else {
            /*no arguments, no output*/
        }
    }
}


void
statement_free_functioncall(struct statement *self)
{
    free(self->_.functioncall.identifier);
    if (self->_.functioncall.input_args != NULL) {
        self->_.functioncall.input_args->free(
            self->_.functioncall.input_args);
    }
    if (self->_.functioncall.output_args != NULL) {
        self->_.functioncall.output_args->free(
            self->_.functioncall.output_args);
    }
    free(self->_.functioncall.functioncall_comment);
    free(self);
}


struct statement*
statement_new_functioncall_write(char *identifier,
                                 struct expressionlist *input_args,
                                 io_t type,
                                 struct expression *to_write,
                                 char *comment)
{
    struct statement *statement = malloc(sizeof(struct statement));
    statement->type = STAT_FUNCTIONCALL_WRITE;
    statement->_.functioncall_write.identifier = identifier;
    statement->_.functioncall_write.input_args = input_args;
    statement->_.functioncall_write.type = type;
    statement->_.functioncall_write.to_write = to_write;
    statement->_.functioncall_write.comment = comment;
    statement->output_latex = statement_output_latex_functioncall_write;
    statement->free = statement_free_functioncall_write;
    return statement;
}

void
statement_output_latex_functioncall_write(const struct statement *self,
                                          const struct definitions *defs,
                                          FILE *output)
{
    const char *identifier =
        self->_.functioncall_write.identifier;
    const struct expressionlist *input_args =
        self->_.functioncall_write.input_args;
    io_t type =
        self->_.functioncall_write.type;
    const struct expression *to_write =
        self->_.functioncall_write.to_write;
    const char *comment =
        self->_.functioncall_write.comment;

    fputs("$", output);
    statement_output_latex_functioncall_write_args(identifier,
                                                   input_args,
                                                   defs,
                                                   output);

    fputs(" \\rightarrow ", output);

    statement_output_latex_write_args(type, to_write, defs, output);

    fputs("$", output);

    statement_output_latex_comment_text(comment, output);

    fputs("\n", output);
}

void
statement_output_latex_functioncall_write_args(
    const char *identifier,
    const struct expressionlist *input_args,
    const struct definitions *defs,
    FILE *output)
{
    if (input_args == NULL) {
        /*no input arguments*/
        statement_output_latex_functioncall_name(identifier, defs, output);
    } else if (input_args->len(input_args) == 1) {
        /*one input argument*/
        const struct expression* argument = input_args->expression;

        statement_output_latex_functioncall_name(identifier, defs, output);
        if (argument->is_tall(argument)) {
            fputs("\\left(", output);
            argument->output_latex(argument, defs, output);
            fputs("\\right)", output);
        } else {
            fputs("(", output);
            argument->output_latex(argument, defs, output);
            fputs(")", output);
        }
    } else {
        /*multiple input arguments*/
        /*divide arguments into columns if there are too many*/

        const struct expressionlist *arg = input_args;
        const unsigned args = input_args->len(input_args);
        const unsigned total_columns =
            (args / ITEMS_PER_COLUMN) +
            ((args % ITEMS_PER_COLUMN) ? 1 : 0);
        unsigned i;

        fputs("\\left.\\begin{tabular}{", output);
        for (i = 0; i < total_columns; i++) {
            fputs("l", output);
        }
        fputs("}", output);

        while (arg != NULL) {
            for (i = 0; i < total_columns; i++) {
                if (arg != NULL) {
                    const struct expression *expression = arg->expression;
                    fputs("$", output);
                    expression->output_latex(expression, defs, output);
                    fputs("$", output);

                    arg = arg->next;
                } else {
                    fputs(" ", output);
                }
                if ((i + 1) < total_columns) {
                    fputs(" & ", output);
                } else {
                    fputs(" \\\\ ", output);
                }
            }
        }

        fputs("\\end{tabular}\\right\\rbrace", output);
        statement_output_latex_functioncall_name(identifier, defs, output);
    }
}

void
statement_output_latex_write_args(io_t type,
                                  const struct expression *to_write,
                                  const struct definitions *defs,
                                  FILE *output)
{
    fputs("\\WRITE~", output);
    to_write->output_latex(to_write, defs, output);
    fputs("~", output);

    switch (type) {
    case IO_UNSIGNED:
        if ((to_write->type == EXP_INTEGER) &&
            (to_write->_.integer == 1)) {
            fputs("\\textrm{unsigned bit}", output);
        } else {
            fputs("\\textrm{unsigned bits}", output);
        }
        break;
    case IO_SIGNED:
        /*signed values should always be at least 2 bits*/
        fputs("\\textrm{signed bits}", output);
        break;
    case IO_BYTES:
        if ((to_write->type == EXP_INTEGER) &&
            (to_write->_.integer == 1)) {
            fputs("\\textrm{byte}", output);
        } else {
            fputs("\\textrm{bytes}", output);
        }
        break;
    }
}

void
statement_output_latex_write_args_unary(int stop_bit,
                                        FILE *output)
{
    fprintf(output, "\\WUNARY~\\textrm{with stop bit %d}", stop_bit);
}

void
statement_free_functioncall_write(struct statement *self)
{
    char *identifier = self->_.functioncall_write.identifier;
    struct expressionlist *input_args  = self->_.functioncall_write.input_args;
    struct expression *to_write = self->_.functioncall_write.to_write;
    char *comment = self->_.functioncall_write.comment;

    free(identifier);
    if (input_args != NULL) {
        input_args->free(input_args);
    }
    to_write->free(to_write);
    free(comment);
    free(self);
}


struct statement*
statement_new_functioncall_write_unary(char *identifier,
                                       struct expressionlist *input_args,
                                       long long stop_bit,
                                       char *comment)
{
    struct statement *statement = malloc(sizeof(struct statement));
    statement->type = STAT_FUNCTIONCALL_WRITE_UNARY;
    statement->_.functioncall_write_unary.identifier = identifier;
    statement->_.functioncall_write_unary.input_args = input_args;
    statement->_.functioncall_write_unary.stop_bit = stop_bit;
    statement->_.functioncall_write_unary.comment = comment;
    statement->output_latex = statement_output_latex_functioncall_write_unary;
    statement->free = statement_free_functioncall_write_unary;
    return statement;
}

void
statement_output_latex_functioncall_write_unary(const struct statement *self,
                                                const struct definitions *defs,
                                                FILE *output)
{
    const char *identifier =
        self->_.functioncall_write_unary.identifier;
    const struct expressionlist *input_args =
        self->_.functioncall_write_unary.input_args;
    int stop_bit =
        self->_.functioncall_write_unary.stop_bit;
    const char *comment =
        self->_.functioncall_write_unary.comment;

    fputs("$", output);
    statement_output_latex_functioncall_write_args(identifier,
                                                   input_args,
                                                   defs,
                                                   output);

    fputs(" \\rightarrow ", output);

    statement_output_latex_write_args_unary(stop_bit, output);

    fputs("$", output);

    statement_output_latex_comment_text(comment, output);

    fputs("\n", output);
}

void
statement_free_functioncall_write_unary(struct statement *self)
{
    char *identifier =
        self->_.functioncall_write_unary.identifier;
    struct expressionlist *input_args =
        self->_.functioncall_write_unary.input_args;
    char *comment =
        self->_.functioncall_write_unary.comment;

    free(identifier);
    if (input_args != NULL) {
        input_args->free(input_args);
    }
    free(comment);
    free(self);
}



struct statement*
statement_new_if(struct expression *condition,
                 struct statlist *then,
                 char *then_comment,
                 struct elselist *elselist)
{
    struct statement *statement = malloc(sizeof(struct statement));
    statement->type = STAT_IF;
    statement->_.if_.condition = condition;
    statement->_.if_.then = then;
    statement->_.if_.then_comment = then_comment;
    statement->_.if_.elselist = elselist;
    statement->output_latex = statement_output_latex_if;
    statement->free = statement_free_if;
    return statement;
}

void
statement_output_latex_if(const struct statement *self,
                          const struct definitions *defs,
                          FILE *output)
{
    const struct expression *condition = self->_.if_.condition;
    const struct statlist *then = self->_.if_.then;
    const char *then_comment = self->_.if_.then_comment;
    const struct elselist *elselist = self->_.if_.elselist;

    if (elselist == NULL) {
        /*just a single "if" statement with no "else"s*/
        fprintf(output, "\\If");
        if (then_comment != NULL) {
            fprintf(output, "(\\tcc*[f]{");
            escape_latex_curly_brackets(output, then_comment);
            fprintf(output, "}){$");
        } else {
            fprintf(output, "{$");
        }
        condition->output_latex(condition, defs, output);
        fprintf(output, "$}{");
        then->output_latex(then, defs, output);
        fprintf(output, "}\n");
    } else if (elselist->condition == NULL) {
        /*a single "if" statement followed by a single "else"*/

        const struct statlist *else_then = elselist->else_;
        const char *else_comment = elselist->comment;

        fprintf(output, "\\eIf");
        if (then_comment != NULL) {
            fprintf(output, "(\\tcc*[f]{");
            escape_latex_curly_brackets(output, then_comment);
            fprintf(output, "}){$");
        } else {
            fprintf(output, "{$");
        }
        condition->output_latex(condition, defs, output);
        fprintf(output, "$}{");
        then->output_latex(then, defs, output);
        fprintf(output, "}");
        if (else_comment != NULL) {
            fprintf(output, "(\\tcc*[f]{");
            escape_latex_curly_brackets(output, else_comment);
            fprintf(output, "}){");
        } else {
            fprintf(output, "{");
        }
        else_then->output_latex(else_then, defs, output);
        fprintf(output, "}\n");
    } else {
        /*an "if" statement followed by one or more "elif" blocks*/
        fprintf(output, "\\uIf");
        if (then_comment != NULL) {
            fprintf(output, "(\\tcc*[f]{");
            escape_latex_curly_brackets(output, then_comment);
            fprintf(output, "}){$");
        } else {
            fprintf(output, "{$");
        }
        condition->output_latex(condition, defs, output);
        fprintf(output, "$}{");
        then->output_latex(then, defs, output);
        fprintf(output, "}\n");
        elselist->output_latex(elselist, defs, output);
    }
}

void
statement_free_if(struct statement *self)
{
    self->_.if_.condition->free(self->_.if_.condition);
    self->_.if_.then->free(self->_.if_.then);
    free(self->_.if_.then_comment);
    if (self->_.if_.elselist != NULL) {
        self->_.if_.elselist->free(self->_.if_.elselist);
    }
    free(self);
}


struct elselist*
elselist_new(struct expression *condition,
             char *comment,
             struct statlist *else_,
             struct elselist *next)
{
    struct elselist *elselist = malloc(sizeof(struct elselist));
    elselist->condition = condition;
    elselist->comment = comment;
    elselist->else_ = else_;
    elselist->next = next;
    elselist->output_latex = elselist_output_latex;
    elselist->free = elselist_free;
    return elselist;
}

void
elselist_output_latex(const struct elselist *self,
                      const struct definitions *defs,
                      FILE *output)
{
    const struct expression *condition = self->condition;
    const char *comment = self->comment;
    const struct statlist *then = self->else_;
    const struct elselist *next = self->next;

    if (condition == NULL) {
        /*final "else" block with no more "elif" blocks*/
        fprintf(output, "\\Else");
        if (comment != NULL) {
            fprintf(output, "(\\tcc*[f]{");
            escape_latex_curly_brackets(output, comment);
            fprintf(output, "}){");
        } else {
            fprintf(output, "{");
        }
        then->output_latex(then, defs, output);
        fprintf(output, "}\n");
    } else if (next == NULL) {
        /*final "elif" block with no more "elif" blocks*/
        fprintf(output, "\\ElseIf");
        if (comment != NULL) {
            fprintf(output, "(\\tcc*[f]{");
            escape_latex_curly_brackets(output, comment);
            fprintf(output, "}){$");
        } else {
            fprintf(output, "{$");
        }
        condition->output_latex(condition, defs, output);
        fprintf(output, "$}{");
        then->output_latex(then, defs, output);
        fprintf(output, "}\n");
    } else {
        /*at least one "elif" block follows*/
        fprintf(output, "\\uElseIf");
        if (comment != NULL) {
            fprintf(output, "(\\tcc*[f]{");
            escape_latex_curly_brackets(output, comment);
            fprintf(output, "}){$");
        } else {
            fprintf(output, "{$");
        }
        condition->output_latex(condition, defs, output);
        fprintf(output, "$}{");
        then->output_latex(then, defs, output);
        fprintf(output, "}\n");
        next->output_latex(next, defs, output);
    }
}

void
elselist_free(struct elselist *self)
{
    if (self->condition != NULL)
        self->condition->free(self->condition);
    free(self->comment);
    self->else_->free(self->else_);
    if (self->next != NULL) {
        self->next->free(self->next);
    }
    free(self);
}


struct statement*
statement_new_switch(struct expression *condition,
                     char *switch_comment,
                     struct caselist *cases)
{
    struct statement *statement = malloc(sizeof(struct statement));
    statement->type = STAT_SWITCH;
    statement->_.switch_.condition = condition;
    statement->_.switch_.comment = switch_comment;
    statement->_.switch_.cases = cases;
    statement->output_latex = statement_output_latex_switch;
    statement->free = statement_free_switch;
    return statement;
}

void
statement_output_latex_switch(const struct statement *self,
                              const struct definitions *defs,
                              FILE *output)
{
    const struct expression *condition = self->_.switch_.condition;
    const char *comment = self->_.switch_.comment;
    const struct caselist *cases = self->_.switch_.cases;

    if (cases != NULL) {
        fprintf(output, "\\Switch");
        if (comment != NULL) {
            fprintf(output, "(\\tcc*[f]{");
            escape_latex_curly_brackets(output, comment);
            fprintf(output, "}){$");
        } else {
            fprintf(output, "{$");
        }
        condition->output_latex(condition, defs, output);
        fprintf(output, "$}{");
        cases->output_latex(cases, defs, output);
        fprintf(output, "}\n");
    } else {
        /*no cases to print, so the switch does nothing*/
    }
}

void
statement_free_switch(struct statement *self)
{
    self->_.switch_.condition->free(self->_.switch_.condition);
    free(self->_.switch_.comment);
    if (self->_.switch_.cases != NULL) {
        self->_.switch_.cases->free(self->_.switch_.cases);
    }
    free(self);
}


struct caselist*
caselist_new(struct expression *expression,
             char *case_comment,
             struct statlist *case_,
             struct caselist* next)
{
    struct caselist *caselist = malloc(sizeof(struct caselist));
    caselist->condition = expression;
    caselist->comment = case_comment;
    caselist->case_ = case_;
    caselist->next = next;
    caselist->output_latex = caselist_output_latex;
    caselist->free = caselist_free;
    return caselist;
}

void
caselist_output_latex(const struct caselist *self,
                      const struct definitions *defs,
                      FILE *output)
{
    const struct expression *condition = self->condition;
    const char *comment = self->comment;
    const struct statlist *case_ = self->case_;
    const struct caselist *next = self->next;

    if (condition == NULL) {
        /*"default" switch block with no more case blocks*/

        const int inline_ = caselist_inline_case(case_);

        fprintf(output, "\\%sOther", inline_ ? "l" : "");
        if (comment != NULL) {
            fprintf(output, "(\\tcc*[f]{");
            escape_latex_curly_brackets(output, comment);
            fprintf(output, "}){");
        } else {
            fprintf(output, "{");
        }
        case_->output_latex(case_, defs, output);
        fprintf(output, "}\n");
    } else if (next == NULL) {
        /*final case block with no more cases to follow*/

        const int inline_ = (caselist_inline_condition(condition) &&
                             caselist_inline_case(case_));

        fprintf(output, "\\%sCase", inline_ ? "l" : "");
        if (comment != NULL) {
            fprintf(output, "(\\tcc*[f]{");
            escape_latex_curly_brackets(output, comment);
            fprintf(output, "}){$");
        } else {
            fprintf(output, "{$");
        }
        condition->output_latex(condition, defs, output);
        fprintf(output, "$}{");
        case_->output_latex(case_, defs, output);
        fprintf(output, "}\n");
    } else {
        /*at least one case block follows*/

        const int inline_ = (caselist_inline_condition(condition) &&
                             caselist_inline_case(case_));

        fprintf(output, "\\%sCase", inline_ ? "l" : "u");
        if (comment != NULL) {
            fprintf(output, "(\\tcc*[f]{");
            escape_latex_curly_brackets(output, comment);
            fprintf(output, "}){$");
        } else {
            fprintf(output, "{$");
        }
        condition->output_latex(condition, defs, output);
        fprintf(output, "$}{");
        case_->output_latex(case_, defs, output);
        fprintf(output, "}\n");
        next->output_latex(next, defs, output);
    }
}

int
caselist_inline_condition(const struct expression *condition)
{
    /*FIXME*/
    return !condition->is_tall(condition);
}

int
caselist_inline_case(const struct statlist *case_)
{
    if (case_->next == NULL) {
        const struct statement *statement = case_->statement;
        if (statement->type == STAT_RETURN) {
            const struct expressionlist *toreturn =
                statement->_.return_.toreturn;
            return ((toreturn->len(toreturn) == 1) &&
                    (!toreturn->expression->is_tall(toreturn->expression)));
        } else {
            return 0;
        }
    } else {
        return 0;
    }
}

void
caselist_free(struct caselist *self)
{
    if (self->condition != NULL) {
        self->condition->free(self->condition);
    }
    free(self->comment);
    self->case_->free(self->case_);
    if (self->next != NULL) {
        self->next->free(self->next);
    }
    free(self);
}


struct statement*
statement_new_while(struct expression *condition,
                    char *condition_comment,
                    struct statlist *statements)
{
    struct statement *statement = malloc(sizeof(struct statement));
    statement->type = STAT_WHILE;
    statement->_.while_.condition = condition;
    statement->_.while_.condition_comment = condition_comment;
    statement->_.while_.statements = statements;
    statement->output_latex = statement_output_latex_while;
    statement->free = statement_free_while;
    return statement;
}

void
statement_output_latex_while(const struct statement *self,
                             const struct definitions *defs,
                             FILE *output)
{
    const struct expression *condition = self->_.while_.condition;
    const char *comment = self->_.while_.condition_comment;
    const struct statlist *statements = self->_.while_.statements;

    fprintf(output, "\\While");
    if (comment != NULL) {
        fprintf(output, "(\\tcc*[f]{");
        escape_latex_curly_brackets(output, comment);
        fprintf(output, "}){$");
    } else {
        fprintf(output, "{$");
    }
    condition->output_latex(condition, defs, output);
    fprintf(output, "$}{");
    statements->output_latex(statements, defs, output);
    fprintf(output, "}\n");
}

void
statement_free_while(struct statement *self)
{
    self->_.while_.condition->free(self->_.while_.condition);
    free(self->_.while_.condition_comment);
    self->_.while_.statements->free(self->_.while_.statements);
    free(self);
}


struct statement*
statement_new_do_while(struct expression *condition,
                       char *condition_comment,
                       struct statlist *statements,
                       char *statements_comment)
{
    struct statement *statement = malloc(sizeof(struct statement));
    statement->type = STAT_DO_WHILE;
    statement->_.do_while.condition = condition;
    statement->_.do_while.condition_comment = condition_comment;
    statement->_.do_while.statements = statements;
    statement->_.do_while.statements_comment = statements_comment;
    statement->output_latex = statement_output_latex_do_while;
    statement->free = statement_free_do_while;
    return statement;
}

void
statement_output_latex_do_while(const struct statement *self,
                                const struct definitions *defs,
                                FILE *output)
{
    const struct expression *condition = self->_.do_while.condition;
    const char *condition_comment = self->_.do_while.condition_comment;
    const struct statlist *statements = self->_.do_while.statements;
    const char *statements_comment = self->_.do_while.statements_comment;

    fprintf(output, "\\Repeat");
    if (statements_comment != NULL) {
        fprintf(output, "(\\tcc*[f]{");
        escape_latex_curly_brackets(output, statements_comment);
        fprintf(output, "}){$");
    } else {
        fprintf(output, "{$");
    }
    condition->output_latex(condition, defs, output);
    fprintf(output, "$}{");
    statements->output_latex(statements, defs, output);
    fprintf(output, "}");
    if (condition_comment != NULL) {
        fprintf(output, "(\\tcc*[f]{");
        escape_latex_curly_brackets(output, condition_comment);
        fprintf(output, "})");
    }
}

void
statement_free_do_while(struct statement *self)
{
    struct expression *condition = self->_.do_while.condition;
    struct statlist *statements = self->_.do_while.statements;

    condition->free(condition);
    free(self->_.do_while.condition_comment);
    statements->free(statements);
    free(self->_.do_while.statements_comment);
    free(self);
}

struct statement*
statement_new_for(for_direction_t direction,
                  struct variable *variable,
                  struct expression *start,
                  struct expression *finish,
                  char *for_comment,
                  struct statlist *statements)
{
    struct statement *statement = malloc(sizeof(struct statement));
    statement->type = STAT_FOR;
    statement->_.for_.direction = direction;
    statement->_.for_.variable = variable;
    statement->_.for_.start = start;
    statement->_.for_.finish = finish;
    statement->_.for_.for_comment = for_comment;
    statement->_.for_.statements = statements;
    statement->output_latex = statement_output_latex_for;
    statement->free = statement_free_for;
    return statement;
}

void
statement_output_latex_for(const struct statement *self,
                           const struct definitions *defs,
                           FILE *output)
{
    for_direction_t direction = self->_.for_.direction;
    const struct variable *variable = self->_.for_.variable;
    const struct expression *start = self->_.for_.start;
    const struct expression *finish = self->_.for_.finish;
    const char *comment = self->_.for_.for_comment;
    const struct statlist *statements = self->_.for_.statements;

    fprintf(output, "\\For");
    if (comment != NULL) {
        fprintf(output, "(\\tcc*[f]{");
        escape_latex_curly_brackets(output, comment);
        fprintf(output, "}){$");
    } else {
        fprintf(output, "{$");
    }
    variable->output_latex(variable, defs, output);
    fprintf(output, " \\leftarrow ");
    start->output_latex(start, defs, output);
    switch (direction) {
    case FOR_TO:
        fprintf(output, "~\\emph{\\KwTo}~");
        break;
    case FOR_DOWNTO:
        fprintf(output, "~\\emph{\\KwDownTo}~");
        break;
    }
    finish->output_latex(finish, defs, output);
    fprintf(output, "$}{");
    statements->output_latex(statements, defs, output);
    fprintf(output, "}\n");
}

void
statement_free_for(struct statement *self)
{
    self->_.for_.variable->free(self->_.for_.variable);
    self->_.for_.start->free(self->_.for_.start);
    self->_.for_.finish->free(self->_.for_.finish);
    free(self->_.for_.for_comment);
    self->_.for_.statements->free(self->_.for_.statements);
    free(self);
}

struct statement*
statement_new_return(struct expressionlist *toreturn,
                     char *return_comment)
{
    struct statement *statement = malloc(sizeof(struct statement));
    statement->type = STAT_RETURN;
    statement->_.return_.toreturn = toreturn;
    statement->_.return_.return_comment = return_comment;
    statement->output_latex = statement_output_latex_return;
    statement->free = statement_free_return;
    return statement;
}

void
statement_output_latex_return(const struct statement *self,
                              const struct definitions *defs,
                              FILE *output)
{
    struct expressionlist *toreturn = self->_.return_.toreturn;

    fprintf(output, "$\\Return");
    if (toreturn->len(toreturn) == 1) {
        /*one item to return*/
        fprintf(output, "~");
        toreturn->expression->output_latex(toreturn->expression,
                                           defs,
                                           output);
    } else {
        /*multiple items to return*/
        /*divide items into columns if there are too many*/
        const unsigned args = toreturn->len(toreturn);
        const unsigned total_columns =
            (args / ITEMS_PER_COLUMN) +
            ((args % ITEMS_PER_COLUMN) ? 1 : 0);
        unsigned i;

        fputs("\\left\\lbrace\\begin{tabular}{", output);
        for (i = 0; i < total_columns; i++) {
            fputs("l", output);
        }
        fputs("}", output);

        while (toreturn != NULL) {
            for (i = 0; i < total_columns; i++) {
                if (toreturn != NULL) {
                    const struct expression *expression =
                        toreturn->expression;
                    fputs("$", output);
                    expression->output_latex(expression, defs, output);
                    fputs("$", output);

                    toreturn = toreturn->next;
                } else {
                    fputs(" ", output);
                }
                if ((i + 1) < total_columns) {
                    fputs(" & ", output);
                } else {
                    fputs(" \\\\ ", output);
                }
            }
        }
        fprintf(output, "\\end{tabular}\\right.");
    }

    fprintf(output, "$");

    statement_output_latex_comment_text(self->_.return_.return_comment,
                                        output);

    fprintf(output, "\n");
}

void
statement_free_return(struct statement *self)
{
    self->_.return_.toreturn->free(self->_.return_.toreturn);
    free(self->_.return_.return_comment);
    free(self);
}


struct statement*
statement_new_assert(struct expression *condition,
                     char *assert_comment)
{
    struct statement* statement = malloc(sizeof(struct statement));
    statement->type = STAT_ASSERT;
    statement->_.assert.condition = condition;
    statement->_.assert.assert_comment = assert_comment;
    statement->output_latex = statement_output_latex_assert;
    statement->free = statement_free_assert;
    return statement;
}

void
statement_output_latex_assert(const struct statement *self,
                              const struct definitions *defs,
                              FILE *output)
{
    fprintf(output, "$\\ASSERT~");

    self->_.assert.condition->output_latex(self->_.assert.condition,
                                           defs,
                                           output);

    fprintf(output, "$");

    statement_output_latex_comment_text(self->_.assert.assert_comment, output);

    fprintf(output, "\n");
}

void
statement_free_assert(struct statement *self)
{
    self->_.assert.condition->free(self->_.assert.condition);
    free(self->_.assert.assert_comment);
    free(self);
}


struct statement*
statement_new_write(io_t type,
                    struct expression *value,
                    struct expression *to_write,
                    char *comment)
{
    if ((to_write->type == EXP_INTEGER) && (to_write->_.integer == 0)) {
        fprintf(stderr,
                "*** Error: writing value to 0 %s probably isn't what you want\n",
                type == IO_BYTES ? "bytes" : "bits");
        exit(1);
        return NULL;
    } else {
        struct statement *statement = malloc(sizeof(struct statement));
        statement->type = STAT_WRITE;
        statement->_.write.type = type;
        statement->_.write.value = value;
        statement->_.write.to_write = to_write;
        statement->_.write.comment = comment;
        statement->output_latex = statement_output_latex_write;
        statement->free = statement_free_write;
        return statement;
    }
}

void
statement_output_latex_write(const struct statement *self,
                             const struct definitions *defs,
                             FILE *output)
{
    io_t type = self->_.write.type;
    const struct expression *value = self->_.write.value;
    const struct expression *to_write = self->_.write.to_write;
    char *comment = self->_.write.comment;

    fprintf(output, "$");

    value->output_latex(value, defs, output);

    fprintf(output, " \\rightarrow ");
    statement_output_latex_write_args(type, to_write, defs, output);
    fprintf(output, "$");
    statement_output_latex_comment_text(comment, output);
    fprintf(output, "\n");
}

void
statement_free_write(struct statement *self)
{
    struct expression *value = self->_.write.value;
    struct expression *to_write = self->_.write.to_write;
    char *comment = self->_.write.comment;

    value->free(value);
    to_write->free(to_write);
    free(comment);
    free(self);
}


struct statement*
statement_new_write_unary(long long stop_bit,
                          struct expression *value,
                          char *comment)
{
    if ((stop_bit == 0) || (stop_bit == 1)) {
        struct statement *statement = malloc(sizeof(struct statement));
        statement->type = STAT_WRITE_UNARY;
        statement->_.write_unary.stop_bit = stop_bit;
        statement->_.write_unary.value = value;
        statement->_.write_unary.comment = comment;
        statement->output_latex = statement_output_latex_write_unary;
        statement->free = statement_free_write_unary;
        return statement;
    } else {
        fprintf(stderr, "unary stop bit must be 0 or 1\n");
        exit(1);
    }
}

void
statement_output_latex_write_unary(const struct statement *self,
                                   const struct definitions *defs,
                                   FILE *output)
{
    int stop_bit = self->_.write_unary.stop_bit;
    const struct expression *value = self->_.write_unary.value;
    const char *comment = self->_.write_unary.comment;

    fprintf(output, "$");

    value->output_latex(value, defs, output);

    fprintf(output, " \\rightarrow ");

    statement_output_latex_write_args_unary(stop_bit, output);

    fprintf(output, "$");

    statement_output_latex_comment_text(comment, output);

    fprintf(output, "\n");
}

void
statement_free_write_unary(struct statement *self)
{
    struct expression *value = self->_.write_unary.value;
    char *comment = self->_.write_unary.comment;

    value->free(value);
    free(comment);
    free(self);
}


struct statement*
statement_new_skip(struct expression *expression,
                   io_t type,
                   char *skip_comment)
{
    struct statement *statement = malloc(sizeof(struct statement));
    statement->type = STAT_SKIP;
    statement->_.skip.to_skip = expression;
    statement->_.skip.type = type;
    statement->_.skip.skip_comment = skip_comment;
    statement->output_latex = statement_output_latex_skip;
    statement->free = statement_free_skip;
    return statement;
}

void
statement_output_latex_skip(const struct statement *self,
                            const struct definitions *defs,
                            FILE *output)
{
    const struct expression *to_skip = self->_.skip.to_skip;
    char *comment = self->_.skip.skip_comment;
    fprintf(output, "$\\SKIP~");

    to_skip->output_latex(to_skip, defs, output);

    switch (self->_.skip.type) {
    case IO_UNSIGNED:
    case IO_SIGNED:
        if ((to_skip->type == EXP_INTEGER) && (to_skip->_.integer == 1)) {
            fprintf(output, "~\\textrm{bit}");
        } else {
            fprintf(output, "~\\textrm{bits}");
        }
        break;
    case IO_BYTES:
        if ((to_skip->type == EXP_INTEGER) && (to_skip->_.integer == 1)) {
            fprintf(output, "~\\textrm{byte}");
        } else {
            fprintf(output, "~\\textrm{bytes}");
        }
        break;
    }

    fprintf(output, "$");
    statement_output_latex_comment_text(comment, output);
    fprintf(output, "\n");
}

void
statement_free_skip(struct statement *self)
{
    self->_.skip.to_skip->free(self->_.skip.to_skip);
    free(self->_.skip.skip_comment);
    free(self);
}
