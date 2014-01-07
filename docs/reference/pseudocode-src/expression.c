#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include "expression.h"

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
expressionlist_new(struct expression *expression, struct expressionlist *next)
{
    struct expressionlist *expressionlist =
        malloc(sizeof(struct expressionlist));
    expressionlist->expression = expression;
    expressionlist->next = next;
    expressionlist->output_latex = expressionlist_output_latex;
    expressionlist->len = expressionlist_len;
    expressionlist->is_tall = expressionlist_is_tall;
    expressionlist->free = expressionlist_free;
    return expressionlist;
}

void
expressionlist_output_latex(const struct expressionlist *self,
                            const struct definitions *defs,
                            FILE *output)
{
    const unsigned args = self->len(self);
    if (args == 1) {
        /*just one item in list*/
        self->expression->output_latex(self->expression, defs, output);
    } else {
        /*multiple items in expression list*/
        /*divide items into columns if there are too many*/
        const unsigned total_columns =
            (args / ITEMS_PER_COLUMN) +
            ((args % ITEMS_PER_COLUMN) ? 1 : 0);
        unsigned i;

        fputs("\\left\\lbrace\\begin{tabular}{", output);
        for (i = 0; i < total_columns; i++) {
            fputs("l", output);
        }
        fputs("}", output);

        while (self != NULL) {
            for (i = 0; i < total_columns; i++) {
                if (self != NULL) {
                    const struct expression *expression = self->expression;
                    fputs("$", output);
                    expression->output_latex(expression, defs, output);
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
        fputs("\\end{tabular}\\right.", output);
    }
}

unsigned
expressionlist_len(const struct expressionlist *self)
{
    const struct expressionlist *e;
    unsigned count = 0;

    for (e = self; e != NULL; e = e->next) {
        count++;
    }

    return count;
}

int
expressionlist_is_tall(const struct expressionlist *self)
{
    int exp_is_tall = self->expression->is_tall(self->expression);

    if (self->next == NULL) {
        return exp_is_tall;
    } else {
        return exp_is_tall || self->next->is_tall(self->next);
    }
}

void
expressionlist_free(struct expressionlist *self)
{
    self->expression->free(self->expression);
    if (self->next != NULL) {
        self->next->free(self->next);
    }
    free(self);
}

int
expression_is_tall(const struct expression *self)
{
    return 1;
}

int
expression_isnt_tall(const struct expression *self)
{
    return 0;
}


struct expression*
expression_new_constant(const_t constant)
{
    struct expression *expression = malloc(sizeof(struct expression));
    expression->type = EXP_CONSTANT;
    expression->_.constant = constant;
    expression->output_latex = expression_output_latex_constant;
    expression->is_tall = expression_isnt_tall;
    expression->free = expression_free_constant;
    return expression;
}

void
expression_output_latex_constant(const struct expression *self,
                                 const struct definitions *defs,
                                 FILE *output)
{
    switch (self->_.constant) {
    case CONST_INFINITY:
        fputs("\\infty", output);
        break;
    case CONST_PI:
        fputs("\\pi", output);
        break;
    case CONST_TRUE:
        fputs("\\TRUE", output);
        break;
    case CONST_FALSE:
        fputs("\\FALSE", output);
        break;
    case CONST_EMPTY_LIST:
        fputs("\\texttt{[]}", output);
        break;
    }
}

void
expression_free_constant(struct expression *self)
{
    free(self);
}


struct expression*
expression_new_variable(struct variable *variable)
{
    struct expression *expression = malloc(sizeof(struct expression));
    expression->type = EXP_VARIABLE;
    expression->_.variable = variable;
    expression->output_latex = expression_output_latex_variable;
    expression->is_tall = expression_isnt_tall;
    expression->free = expression_free_variable;
    return expression;
}

void
expression_output_latex_variable(const struct expression *self,
                                 const struct definitions *defs,
                                 FILE *output)
{
    struct variable *variable = self->_.variable;
    variable->output_latex(variable, defs, output);
}

void
expression_free_variable(struct expression *self)
{
    struct variable *variable = self->_.variable;
    variable->free(variable);
    free(self);
}


struct expression*
expression_new_integer(int_type_t integer)
{
    struct expression *expression = malloc(sizeof(struct expression));
    expression->type = EXP_INTEGER;
    expression->_.integer = integer;
    expression->output_latex = expression_output_latex_integer;
    expression->is_tall = expression_isnt_tall;
    expression->free = expression_free_integer;
    return expression;
}

void
expression_output_latex_integer(const struct expression *self,
                                const struct definitions *defs,
                                FILE *output)
{
    fprintf(output, int_type_format, self->_.integer);
}

void
expression_free_integer(struct expression *self)
{
    free(self);
}


struct expression*
expression_new_float(float_type_t float_)
{
    struct expression *expression = malloc(sizeof(struct expression));
    expression->type = EXP_FLOAT;
    expression->_.float_ = float_;
    expression->output_latex = expression_output_latex_float;
    expression->is_tall = expression_isnt_tall;
    expression->free = expression_free_float;
    return expression;

}

void
expression_output_latex_float(const struct expression *self,
                              const struct definitions *defs,
                              FILE *output)
{
    const float_type_t float_ = self->_.float_;
    fprintf(output, float_type_format, float_);
    fputs(float_, output);
}

void
expression_free_float(struct expression *self)
{
    float_type_t float_ = self->_.float_;
    free(float_);
    free(self);
}


struct expression*
expression_new_intlist(struct intlist *intlist)
{
    struct expression *expression = malloc(sizeof(struct expression));
    expression->type = EXP_INTLIST;
    expression->_.intlist = intlist;
    expression->output_latex = expression_output_latex_intlist;
    expression->is_tall = expression_isnt_tall;
    expression->free = expression_free_intlist;
    return expression;
}

void
expression_output_latex_intlist(const struct expression *self,
                                const struct definitions *defs,
                                FILE *output)
{
    const struct intlist *intlist;

    fputs("[", output);
    for (intlist = self->_.intlist; intlist != NULL; intlist = intlist->next) {
        const int_type_t integer = intlist->integer;
        fprintf(output, int_type_format, integer);
        if (intlist->next != NULL) {
            fputs(", ", output);
        }
    }
    fputs("]", output);
}

void
expression_free_intlist(struct expression *self)
{
    intlist_free(self->_.intlist);
    free(self);
}

struct expression*
expression_new_floatlist(struct floatlist *floatlist)
{
    struct expression *expression = malloc(sizeof(struct expression));
    expression->type = EXP_FLOATLIST;
    expression->_.floatlist = floatlist;
    expression->output_latex = expression_output_latex_floatlist;
    expression->is_tall = expression_isnt_tall;
    expression->free = expression_free_floatlist;
    return expression;
}

void
expression_output_latex_floatlist(const struct expression *self,
                                  const struct definitions *defs,
                                  FILE *output)
{
    const struct floatlist *floatlist;

    fputs("[", output);
    for (floatlist = self->_.floatlist;
         floatlist != NULL;
         floatlist = floatlist->next) {
        const float_type_t float_ = floatlist->float_;
        fprintf(output, float_type_format, float_);
        if (floatlist->next != NULL) {
            fputs(", ", output);
        }
    }
    fputs("]", output);
}

void
expression_free_floatlist(struct expression *self)
{
    floatlist_free(self->_.floatlist);
    free(self);
}


struct expression*
expression_new_bytes(struct intlist *intlist)
{
    struct expression *expression;
    struct intlist *i;
    /*ensure all bytes are in the proper range*/
    for (i = intlist; i != NULL; i = i->next) {
        if ((i->integer < 0) || (i->integer > 255)) {
            fprintf(stderr,
                    "*** Error: byte value "
                    int_type_format
                    " is out of range [0-255]\n",
                    i->integer);
            exit(1);
        }
    }

    expression = malloc(sizeof(struct expression));
    expression->type = EXP_BYTES;
    expression->_.bytes = intlist;
    expression->output_latex = expression_output_latex_bytes;
    expression->is_tall = expression_isnt_tall;
    expression->free = expression_free_bytes;
    return expression;
}

void
expression_output_latex_bytes(const struct expression *self,
                              const struct definitions *defs,
                              FILE *output)
{
    const struct intlist *bytes = self->_.bytes;
    const struct intlist *b;
    int printable = 1;
    for (b = bytes; b != NULL; b = b->next) {
        if (!isalnum((char)b->integer)) {
            printable = 0;
            break;
        }
    }

    fprintf(output, "\\texttt{");
    if (printable) {
        fprintf(output, "\"");
        for (b = bytes; b != NULL; b = b->next) {
            fputc(b->integer, output);
        }
        fprintf(output, "\"");
    } else {
        fprintf(output, "[");
        for (b = bytes; b != NULL; b = b->next) {
            fprintf(output, int_type_format, b->integer);
            if (b->next != NULL) {
                fprintf(output, ", ");
            }
        }
        fprintf(output, "]");
    }
    fprintf(output, "}");
}

void
expression_free_bytes(struct expression *self)
{
    intlist_free(self->_.bytes);
    free(self);
}


struct expression*
expression_new_wrapped(wrap_type_t wrapper, struct expression *sub)
{
    struct expression *expression = malloc(sizeof(struct expression));
    expression->type = EXP_WRAPPED;
    expression->_.wrapped.wrapper = wrapper;
    expression->_.wrapped.sub = sub;
    expression->output_latex = expression_output_latex_wrapped;
    expression->is_tall = expression_is_tall_wrapped;
    expression->free = expression_free_wrapped;
    return expression;
}

void
expression_output_latex_wrapped(const struct expression *self,
                                const struct definitions *defs,
                                FILE *output)
{
    wrap_type_t wrapper = self->_.wrapped.wrapper;
    const struct expression *sub = self->_.wrapped.sub;
    switch (wrapper) {
    case WRAP_PARENTHESIZED:
        if (sub->is_tall(sub)) {
            fprintf(output, "\\left( ");
            sub->output_latex(sub, defs, output);
            fprintf(output, "\\right) ");
        } else {
            fprintf(output, "(");
            sub->output_latex(sub, defs, output);
            fprintf(output, ")");
        }
        break;
    case WRAP_CEILING:
        if (sub->is_tall(sub)) {
            fprintf(output, "\\left\\lceil ");
            sub->output_latex(sub, defs, output);
            fprintf(output, "\\right\\rceil ");
        } else {
            fprintf(output, "\\lceil ");
            sub->output_latex(sub, defs, output);
            fprintf(output, "\\rceil ");
        }
        break;
    case WRAP_FLOOR:
        if (sub->is_tall(sub)) {
            fprintf(output, "\\left\\lfloor ");
            sub->output_latex(sub, defs, output);
            fprintf(output, "\\right\\rfloor ");
        } else {
            fprintf(output, "\\lfloor ");
            sub->output_latex(sub, defs, output);
            fprintf(output, "\\rfloor ");
        }
        break;
    case WRAP_ABS:
        if (sub->is_tall(sub)) {
            fprintf(output, "\\left|");
            sub->output_latex(sub, defs, output);
            fprintf(output, "\\right|");
        } else {
            fprintf(output, "|");
            sub->output_latex(sub, defs, output);
            fprintf(output, "|");
        }
        break;
    case WRAP_UMINUS:
        fprintf(output, "-");
        sub->output_latex(sub, defs, output);
        break;
    }
}

int
expression_is_tall_wrapped(const struct expression *self)
{
    const struct expression *sub = self->_.wrapped.sub;
    return sub->is_tall(sub);
}

void
expression_free_wrapped(struct expression *self)
{
    struct expression *sub = self->_.wrapped.sub;
    sub->free(sub);
    free(self);
}

struct expression*
expression_new_function(func_type_t function, struct expression *arg)
{
    struct expression *expression = malloc(sizeof(struct expression));
    expression->type = EXP_FUNCTION;
    expression->_.function.function = function;
    expression->_.function.arg = arg;
    expression->output_latex = expression_output_latex_function;
    expression->is_tall = expression_is_tall_function;
    expression->free = expression_free_function;
    return expression;
}

void
expression_output_latex_function(const struct expression *self,
                                 const struct definitions *defs,
                                 FILE *output)
{
    const func_type_t function = self->_.function.function;
    const struct expression *arg = self->_.function.arg;

    switch (function) {
    case FUNC_SIN:
        fputs("\\sin", output);
        break;
    case FUNC_COS:
        fputs("\\cos", output);
        break;
    case FUNC_TAN:
        fputs("\\tan", output);
        break;
    }
    if (arg->is_tall(arg)) {
        fputs("\\left(", output);
        arg->output_latex(arg, defs, output);
        fputs("\\right)", output);
    } else {
        fputs("(", output);
        arg->output_latex(arg, defs, output);
        fputs(")", output);
    }
}

int
expression_is_tall_function(const struct expression *self)
{
    const struct expression *arg = self->_.function.arg;
    return arg->is_tall(arg);
}

void
expression_free_function(struct expression *self)
{
    struct expression *arg = self->_.function.arg;
    arg->free(arg);
    free(self);
}


struct expression*
expression_new_fraction(struct expression *numerator,
                        struct expression *denominator)
{
    struct expression *expression = malloc(sizeof(struct expression));
    expression->type = EXP_FRACTION;
    expression->_.fraction.numerator = numerator;
    expression->_.fraction.denominator = denominator;
    expression->output_latex = expression_output_latex_fraction;
    expression->is_tall = expression_is_tall;
    expression->free = expression_free_fraction;
    return expression;
}

void
expression_output_latex_fraction(const struct expression *self,
                                 const struct definitions *defs,
                                 FILE *output)
{
    const struct expression *numerator = self->_.fraction.numerator;
    const struct expression *denominator = self->_.fraction.denominator;

    fprintf(output, "\\frac{");
    numerator->output_latex(numerator, defs, output);
    fprintf(output, "}{");
    denominator->output_latex(denominator, defs, output);
    fprintf(output, "}");
}

void
expression_free_fraction(struct expression *self)
{
    struct expression *numerator = self->_.fraction.numerator;
    struct expression *denominator = self->_.fraction.denominator;
    numerator->free(numerator);
    denominator->free(denominator);
    free(self);
}


struct expression*
expression_new_comparison(
    cmp_op_t operator, struct expression *sub1, struct expression *sub2)
{
    struct expression *expression = malloc(sizeof(struct expression));
    expression->type = EXP_COMPARISON;
    expression->_.comparison.operator = operator;
    expression->_.comparison.sub1 = sub1;
    expression->_.comparison.sub2 = sub2;
    expression->output_latex = expression_output_latex_comparison;
    expression->is_tall = expression_is_tall_comparison;
    expression->free = expression_free_comparison;
    return expression;
}

void
expression_output_latex_comparison(const struct expression *self,
                                   const struct definitions *defs,
                                   FILE *output)
{
    const struct expression *sub1 = self->_.comparison.sub1;
    const struct expression *sub2 = self->_.comparison.sub2;

    sub1->output_latex(sub1, defs, output);

    switch (self->_.comparison.operator) {
    case CMP_OP_EQ:
        fprintf(output, " = ");
        break;
    case CMP_OP_NE:
        fprintf(output, " \\neq ");
        break;
    case CMP_OP_LT:
        fprintf(output, " < ");
        break;
    case CMP_OP_LTE:
        fprintf(output, " \\leq ");
        break;
    case CMP_OP_GT:
        fprintf(output, " > ");
        break;
    case CMP_OP_GTE:
        fprintf(output, " \\geq ");
        break;
    }

    sub2->output_latex(sub2, defs, output);
}

int
expression_is_tall_comparison(const struct expression *self)
{
    const struct expression *sub1 = self->_.comparison.sub1;
    const struct expression *sub2 = self->_.comparison.sub2;

    return (sub1->is_tall(sub1) || sub2->is_tall(sub2));
}

void
expression_free_comparison(struct expression *self)
{
    struct expression *sub1 = self->_.comparison.sub1;
    struct expression *sub2 = self->_.comparison.sub2;

    sub1->free(sub1);
    sub2->free(sub2);
    free(self);
}


struct expression*
expression_new_boolean(bool_op_t operator,
                       struct expression *sub1,
                       struct expression *sub2)
{
    struct expression *expression = malloc(sizeof(struct expression));
    expression->type = EXP_BOOLEAN;
    expression->_.boolean.operator = operator;
    expression->_.boolean.sub1 = sub1;
    expression->_.boolean.sub2 = sub2;
    expression->output_latex = expression_output_latex_boolean;
    expression->is_tall = expression_is_tall_boolean;
    expression->free = expression_free_boolean;
    return expression;
}

void
expression_output_latex_boolean(const struct expression *self,
                                const struct definitions *defs,
                                FILE *output)
{
    const bool_op_t operator = self->_.boolean.operator;
    const struct expression *sub1 = self->_.boolean.sub1;
    const struct expression *sub2 = self->_.boolean.sub2;

    sub1->output_latex(sub1, defs, output);
    switch (operator) {
    case BOOL_AND:
        fprintf(output, "~\\AND~");
        break;
    case BOOL_OR:
        fprintf(output, "~\\OR~");
        break;
    }
    sub2->output_latex(sub2, defs, output);
}

int
expression_is_tall_boolean(const struct expression *self)
{
    const struct expression *sub1 = self->_.boolean.sub1;
    const struct expression *sub2 = self->_.boolean.sub2;

    return (sub1->is_tall(sub1) || sub2->is_tall(sub2));
}

void
expression_free_boolean(struct expression *self)
{
    struct expression *sub1 = self->_.boolean.sub1;
    struct expression *sub2 = self->_.boolean.sub2;

    sub1->free(sub1);
    sub2->free(sub2);
    free(self);
}


struct expression*
expression_new_not(struct expression *not)
{
    struct expression *expression = malloc(sizeof(struct expression));
    expression->type = EXP_NOT;
    expression->_.not = not;
    expression->output_latex = expression_output_latex_not;
    expression->is_tall = expression_is_tall_not;
    expression->free = expression_free_not;
    return expression;
}

void
expression_output_latex_not(const struct expression *self,
                            const struct definitions *defs,
                            FILE *output)
{
    const struct expression *not = self->_.not;

    fprintf(output, "\\NOT~");
    not->output_latex(not, defs, output);
}

int
expression_is_tall_not(const struct expression *self)
{
    const struct expression *not = self->_.not;
    return not->is_tall(not);
}

void
expression_free_not(struct expression *self)
{
    struct expression *not = self->_.not;
    not->free(not);
    free(self);
}


struct expression*
expression_new_math(math_op_t operator,
                    struct expression *sub1,
                    struct expression *sub2)
{
    struct expression *expression = malloc(sizeof(struct expression));
    expression->type = EXP_MATH;
    expression->_.math.operator = operator;
    expression->_.math.sub1 = sub1;
    expression->_.math.sub2 = sub2;
    expression->output_latex = expression_output_latex_math;
    expression->is_tall = expression_is_tall_math;
    expression->free = expression_free_math;
    return expression;
}

void
expression_output_latex_math(const struct expression *self,
                             const struct definitions *defs,
                             FILE *output)
{
    const struct expression *sub1 = self->_.math.sub1;
    const struct expression *sub2 = self->_.math.sub2;

    sub1->output_latex(sub1, defs, output);

    switch (self->_.math.operator) {
    case MATH_ADD:
        fprintf(output, " + ");
        break;
    case MATH_SUBTRACT:
        fprintf(output, " - ");
        break;
    case MATH_MULTIPLY:
        fprintf(output, " \\times ");
        break;
    case MATH_DIVIDE:
        fprintf(output, " \\div ");
        break;
    case MATH_MOD:
        fprintf(output, " \\bmod ");
        break;
    case MATH_XOR:
        fprintf(output, "~\\XOR~");
        break;
    }
    sub2->output_latex(sub2, defs, output);
}

int
expression_is_tall_math(const struct expression *self)
{
    const struct expression *sub1 = self->_.math.sub1;
    const struct expression *sub2 = self->_.math.sub2;

    return (sub1->is_tall(sub1) || sub2->is_tall(sub2));
}

void
expression_free_math(struct expression *self)
{
    struct expression *sub1 = self->_.math.sub1;
    struct expression *sub2 = self->_.math.sub2;
    sub1->free(sub1);
    sub2->free(sub2);
    free(self);
}


struct expression*
expression_new_pow(struct expression *sub1,
                   struct expression *sub2)
{
    struct expression *expression = malloc(sizeof(struct expression));
    expression->type = EXP_POW;
    expression->_.pow.base = sub1;
    expression->_.pow.power = sub2;
    expression->output_latex = expression_output_latex_pow;
    expression->is_tall = expression_is_tall_pow;
    expression->free = expression_free_pow;
    return expression;
}

void
expression_output_latex_pow(const struct expression *self,
                            const struct definitions *defs,
                            FILE *output)
{
    const struct expression *base = self->_.pow.base;
    const struct expression *power = self->_.pow.power;

    base->output_latex(base, defs, output);
    fprintf(output, " ^ {");
    power->output_latex(power, defs, output);
    fprintf(output, "}");
}

int
expression_is_tall_pow(const struct expression *self)
{
    const struct expression *base = self->_.pow.base;

    return base->is_tall(base);
}

void
expression_free_pow(struct expression *self)
{
    struct expression *base = self->_.pow.base;
    struct expression *power = self->_.pow.power;

    base->free(base);
    power->free(power);
    free(self);
}


struct expression*
expression_new_log(struct expression *subscript,
                   struct expression *expression)
{
    struct expression *log = malloc(sizeof(struct expression));
    log->type = EXP_LOG;
    log->_.log.subscript = subscript;
    log->_.log.expression = expression;
    log->output_latex = expression_output_latex_log;
    log->is_tall = expression_is_tall_log;
    log->free = expression_free_log;
    return log;
}

void
expression_output_latex_log(const struct expression *self,
                            const struct definitions *defs,
                            FILE *output)
{
    const struct expression *subscript = self->_.log.subscript;
    const struct expression *expression = self->_.log.expression;

    if ((subscript->type == EXP_VARIABLE) &&
        (strcmp(subscript->_.variable->identifier, "e") == 0) &&
        (subscript->_.variable->subscript == NULL)) {
        /*natural logarithm*/
        fprintf(output, "\\ln ");
    } else {
        fprintf(output, "\\log_{");
        subscript->output_latex(subscript, defs, output);
        fprintf(output, "} ");
    }

    expression->output_latex(expression, defs, output);
}

int
expression_is_tall_log(const struct expression *self)
{
    const struct expression *expression = self->_.log.expression;
    return expression->is_tall(expression);
}

void
expression_free_log(struct expression *self)
{
    struct expression *subscript = self->_.log.subscript;
    struct expression *expression = self->_.log.expression;
    subscript->free(subscript);
    expression->free(expression);
    free(self);
}


struct expression*
expression_new_sum(struct variable *variable,
                   struct expression *from,
                   struct expression *to,
                   struct expression *func)
{
    struct expression *expression = malloc(sizeof(struct expression));
    expression->type = EXP_SUM;
    expression->_.sum.variable = variable;
    expression->_.sum.from = from;
    expression->_.sum.to = to;
    expression->_.sum.func = func;
    expression->output_latex = expression_output_latex_sum;
    expression->is_tall = expression_is_tall;
    expression->free = expression_free_sum;
    return expression;
}

void
expression_output_latex_sum(const struct expression *self,
                            const struct definitions *defs,
                            FILE *output)
{
    const struct variable *variable = self->_.sum.variable;
    const struct expression *from = self->_.sum.from;
    const struct expression *to = self->_.sum.to;
    const struct expression *func = self->_.sum.func;

    fprintf(output, "\\displaystyle \\sum_{");
    variable->output_latex(variable, defs, output);
    fprintf(output, " = ");
    from->output_latex(from, defs, output);
    fprintf(output, "}^{");
    to->output_latex(to, defs, output);
    fprintf(output, "} ");
    func->output_latex(func, defs, output);
}

void
expression_free_sum(struct expression *self)
{
    struct variable *variable = self->_.sum.variable;
    struct expression *from = self->_.sum.from;
    struct expression *to = self->_.sum.to;
    struct expression *func = self->_.sum.func;

    variable->free(variable);
    from->free(from);
    to->free(to);
    func->free(func);
    free(self);
}


struct expression*
expression_new_sqrt(struct expression *root,
                    struct expression *value)
{
    struct expression *expression = malloc(sizeof(struct expression));
    expression->type = EXP_SQRT;
    expression->_.sqrt.root = root;
    expression->_.sqrt.value = value;
    expression->output_latex = expression_output_latex_sqrt;
    expression->is_tall = expression_is_tall_sqrt;
    expression->free = expression_free_sqrt;
    return expression;
}

void
expression_output_latex_sqrt(const struct expression *self,
                             const struct definitions *defs,
                             FILE *output)
{
    const struct expression *root = self->_.sqrt.root;
    const struct expression *value = self->_.sqrt.value;
    const int is_sqrt2 = ((root->type == EXP_INTEGER) &&
                          (root->_.integer == 2));

    fputs("\\sqrt", output);
    if (!is_sqrt2) {
        fputs("[", output);
        root->output_latex(root, defs, output);
        fputs("]", output);
    }
    fputs("{", output);
    value->output_latex(value, defs, output);
    fputs("}", output);
}

int
expression_is_tall_sqrt(const struct expression *self)
{
    const struct expression *value = self->_.sqrt.value;
    return value->is_tall(value);
}

void
expression_free_sqrt(struct expression *self)
{
    struct expression *root = self->_.sqrt.root;
    struct expression *value = self->_.sqrt.value;
    root->free(root);
    value->free(value);
    free(self);
}


struct expression*
expression_new_read(io_t type, struct expression *to_read)
{
    struct expression *expression = malloc(sizeof(struct expression));
    expression->type = EXP_READ;
    expression->_.read.type = type;
    expression->_.read.to_read = to_read;
    expression->output_latex = expression_output_latex_read;
    expression->is_tall = expression_is_tall_read;
    expression->free = expression_free_read;
    return expression;
}

void
expression_output_latex_read(const struct expression *self,
                             const struct definitions *defs,
                             FILE *output)
{
    const struct expression *to_read = self->_.read.to_read;
    const int singular = ((to_read->type == EXP_INTEGER) &&
                          (to_read->_.integer == 1));
    fprintf(output, "{\\textnormal{\\READ~$");
    to_read->output_latex(to_read, defs, output);
    switch (self->_.read.type) {
    case IO_UNSIGNED:
        fprintf(output, "$~{\\textrm{unsigned %s}}", singular ? "bit" : "bits");
        break;
    case IO_SIGNED:
        fprintf(output, "$~{\\textrm{signed bits}}");
        break;
    case IO_BYTES:
        fprintf(output, "$~{\\textrm{%s}}", singular ?  "byte" : "bytes");
        break;
    }
    fprintf(output, "}}");
}

int
expression_is_tall_read(const struct expression *self)
{
    const struct expression *to_read = self->_.read.to_read;
    return to_read->is_tall(to_read);
}

void
expression_free_read(struct expression *self)
{
    struct expression *to_read = self->_.read.to_read;
    to_read->free(to_read);
    free(self);
}


struct expression*
expression_new_read_unary(int stop_bit)
{
    if ((stop_bit == 0) || (stop_bit == 1)) {
        struct expression *expression = malloc(sizeof(struct expression));
        expression->type = EXP_READ_UNARY;
        expression->_.read_unary = stop_bit;
        expression->output_latex = expression_output_latex_read_unary;
        expression->is_tall = expression_isnt_tall;
        expression->free = expression_free_read_unary;
        return expression;
    } else {
        fprintf(stderr, "unary stop bit must be 0 or 1\n");
        exit(1);
    }
}

void
expression_output_latex_read_unary(const struct expression *self,
                                   const struct definitions *defs,
                                   FILE *output)
{
    fprintf(output, "{\\RUNARY~\\textrm{with stop bit %d}}",
            self->_.read_unary);
}

void
expression_free_read_unary(struct expression *self)
{
    free(self);
}


struct intlist*
intlist_new(int_type_t integer, struct intlist *next)
{
    struct intlist *intlist = malloc(sizeof(struct intlist));
    intlist->integer = integer;
    intlist->next = next;
    return intlist;
}

void
intlist_free(struct intlist *intlist)
{
    if (intlist != NULL) {
        intlist_free(intlist->next);
        free(intlist);
    }
}


struct floatlist*
floatlist_new(float_type_t float_, struct floatlist *next)
{
    struct floatlist *floatlist = malloc(sizeof(struct floatlist));
    floatlist->float_ = float_;
    floatlist->next = next;
    return floatlist;
}

void
floatlist_free(struct floatlist *floatlist)
{
    if (floatlist != NULL) {
        floatlist_free(floatlist->next);
        free(floatlist->float_);
        free(floatlist);
    }
}
