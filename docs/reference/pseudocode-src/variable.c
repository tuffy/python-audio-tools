#include <stdlib.h>
#include <string.h>
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

struct vardef*
vardef_new(char *identifier, char *label, struct vardef *next)
{
    struct vardef *var = malloc(sizeof(struct vardef));
    var->identifier = identifier;
    var->label = label;
    var->next = next;
    return var;
}

void
vardef_free(struct vardef *var)
{
    if (var != NULL) {
        free(var->identifier);
        free(var->label);
        vardef_free(var->next);
        free(var);
    }
}


struct variablelist*
variablelist_new(struct variable *variable, struct variablelist *next)
{
    struct variablelist *variablelist = malloc(sizeof(struct variablelist));
    variablelist->variable = variable;
    variablelist->next = next;
    variablelist->output_latex = variablelist_output_latex;
    variablelist->len = variablelist_len;
    variablelist->free = variablelist_free;
    return variablelist;
}

void
variablelist_output_latex(const struct variablelist *self,
                          const struct definitions *defs,
                          FILE *output)
{
    if (self->len(self) == 1) {
        struct variable *variable = self->variable;
        variable->output_latex(variable, defs, output);
    } else {
        /*divide arguments into columns if there are too many*/
        const unsigned args = self->len(self);
        const unsigned total_columns =
            (args / ITEMS_PER_COLUMN) +
            ((args % ITEMS_PER_COLUMN) ? 1 : 0);
        unsigned i;

        fputs("\\left.\\begin{tabular}{", output);
        for (i = 0; i < total_columns; i++) {
            fputs("r", output);
        }
        fputs("}", output);

        while (self != NULL) {
            for (i = 0; i < total_columns; i++) {
                if (self != NULL) {
                    const struct variable *variable = self->variable;
                    fputs("$", output);
                    variable->output_latex(variable, defs, output);
                    fputs("$", output);

                    self = self->next;
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

        fprintf(output, "\\end{tabular}\\right\\rbrace");
    }
}

unsigned
variablelist_len(const struct variablelist *self)
{
    const struct variablelist *v;
    unsigned count = 0;
    for (v = self; v != NULL; v = v->next) {
        count++;
    }
    return count;
}

void
variablelist_free(struct variablelist *self)
{
    self->variable->free(self->variable);
    if (self->next != NULL) {
        self->next->free(self->next);
    }
    free(self);
}


struct variable*
variable_new(char *identifier, struct subscript* subscript)
{
    struct variable *variable = malloc(sizeof(struct variable));
    variable->identifier = identifier;
    variable->subscript = subscript;
    variable->output_latex = variable_output_latex;
    variable->free = variable_free;
    return variable;
}

void
variable_output_latex(const struct variable *self,
                      const struct definitions *defs,
                      FILE *output)
{
    const char *identifier = self->identifier;
    const struct vardef *var;
    unsigned variable_id;

    /*see if variable is in list of labels
      and output its LaTeX variable ID if so*/
    for (var = defs->variables, variable_id = 0;
         var != NULL;
         var = var->next, variable_id++) {
        if (strcmp(identifier, var->identifier) == 0) {
            fprintf(output, "\\");
            escape_latex_variable(output, variable_id);
            break;
        }
    }
    if (var == NULL) {
        /*see if variable has a predefined replacement of some sort*/
        if (strcmp(identifier, "alpha") == 0) {
            fputs("\\alpha", output);
        } else if (strcmp(identifier, "beta") == 0) {
            fputs("\\beta", output);
        } else if (strcmp(identifier, "kappa") == 0) {
            fputs("\\kappa", output);
        } else {
            escape_latex_identifier(output, identifier);
        }
    }

    if (self->subscript != NULL) {
        const struct subscript* subscript;

        fprintf(output, "_{");
        for (subscript = self->subscript;
             subscript != NULL;
             subscript = subscript->next) {
            subscript->expression->output_latex(subscript->expression,
                                                defs,
                                                output);
            if (subscript->next != NULL) {
                fprintf(output, "~");
            }
        }
        fprintf(output, "}");
    }
}

void
variable_free(struct variable *self)
{
    free(self->identifier);
    subscript_free(self->subscript);
    free(self);
}

struct subscript*
subscript_new(struct expression *expression, struct subscript* next)
{
    struct subscript *subscript = malloc(sizeof(struct subscript));
    subscript->expression = expression;
    subscript->next = next;
    return subscript;
}

void
subscript_free(struct subscript* subscript)
{
    if (subscript != NULL) {
        subscript->expression->free(subscript->expression);
        subscript_free(subscript->next);
        free(subscript);
    }
}
