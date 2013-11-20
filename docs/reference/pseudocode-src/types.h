#ifndef PSEUDOCODE_TYPES
#define PSEUDOCODE_TYPES

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

typedef enum {
    IO_UNSIGNED,
    IO_SIGNED,
    IO_BYTES
} io_t;

struct vardef {
    char *identifier;
    char *label;
    struct vardef *next;
};

struct funcdef {
    char *identifier;
    char *description;
    char *address;
    struct funcdef *next;
};

struct definitions {
    struct vardef *variables;
    struct funcdef *functions;
};

struct expression;

struct subscript {
    struct expression* expression;
    struct subscript* next;
};

struct variable {
    char *identifier;
    struct subscript* subscript;
    void (*output_latex)(const struct variable *self,
                         const struct definitions *defs,
                         FILE *output);
    void (*free)(struct variable *self);
};

struct variablelist {
    struct variable *variable;
    struct variablelist *next;
    void (*output_latex)(const struct variablelist *self,
                         const struct definitions *defs,
                         FILE *output);
    unsigned (*len)(const struct variablelist *self);
    void (*free)(struct variablelist *self);
};

typedef enum {
    EXP_INFINITY,
    EXP_VARIABLE,
    EXP_INTEGER,
    EXP_FLOAT,
    EXP_BYTES,
    EXP_WRAPPED,
    EXP_FRACTION,
    EXP_COMPARISON,
    EXP_BOOLEAN,
    EXP_NOT,
    EXP_MATH,
    EXP_POW,
    EXP_LOG,
    EXP_SUM,
    EXP_READ,
    EXP_READ_UNARY
} expression_t;

typedef enum {
    WRAP_PARENTHESIZED,
    WRAP_CEILING,
    WRAP_FLOOR,
    WRAP_ABS,
    WRAP_UMINUS
} wrap_type_t;

typedef enum {
    MATH_ADD,
    MATH_SUBTRACT,
    MATH_MULTIPLY,
    MATH_DIVIDE,
    MATH_MOD
} math_op_t;

typedef enum {
    CMP_OP_EQ,
    CMP_OP_NE,
    CMP_OP_LT,
    CMP_OP_LTE,
    CMP_OP_GT,
    CMP_OP_GTE
} cmp_op_t;

typedef enum {
    BOOL_AND,
    BOOL_OR
} bool_op_t;

struct expression {
    expression_t type;
    union {
        struct variable *variable;
        int integer;
        char *float_;
        struct intlist *bytes;
        struct {
            wrap_type_t wrapper;
            struct expression *sub;
        } wrapped;
        struct {
            struct expression *numerator;
            struct expression *denominator;
        } fraction;
        struct {
            cmp_op_t operator;
            struct expression *sub1;
            struct expression *sub2;
        } comparison;
        struct {
            bool_op_t operator;
            struct expression *sub1;
            struct expression *sub2;
        } boolean;
        struct expression *not;
        struct {
            math_op_t operator;
            struct expression *sub1;
            struct expression *sub2;
        } math;
        struct {
            struct expression *base;
            struct expression *power;
        } pow;
        struct {
            struct expression *subscript;
            struct expression *expression;
        } log;
        struct {
            struct variable *variable;
            struct expression *from;
            struct expression *to;
            struct expression *func;
        } sum;
        struct {
            io_t type;
            struct expression *to_read;
        } read;
        int read_unary;
    } _;
    void (*output_latex)(const struct expression *self,
                         const struct definitions *defs,
                         FILE *output);
    int (*is_tall)(const struct expression *self);
    void (*free)(struct expression *self);
};

struct expressionlist {
    struct expression *expression;
    struct expressionlist *next;
    unsigned (*len)(const struct expressionlist *self);
    void (*free)(struct expressionlist *self);
};

typedef enum {
    STAT_BLANKLINE,
    STAT_COMMENT,
    STAT_ASSIGN_IN,
    STAT_FUNCTIONCALL,
    STAT_IF,
    STAT_SWITCH,
    STAT_WRITE,
    STAT_WRITE_UNARY,
    STAT_SKIP,
    STAT_WHILE,
    STAT_DO_WHILE,
    STAT_FOR,
    STAT_RETURN,
    STAT_ASSERT
} statement_t;

typedef enum {
    FOR_TO,
    FOR_DOWNTO
} for_direction_t;

struct statement {
    statement_t type;
    union {
        char *comment;
        struct {
            struct variablelist *variablelist;
            struct expression *expression;
            char *comment;
        } assign_in;
        struct {
            char *identifier;
            struct expressionlist *input_args;
            struct variablelist *output_args;
            char *functioncall_comment;
        } functioncall;
        struct {
            struct expression *condition;
            struct statlist *then;
            char *then_comment;
            struct elselist *elselist;
        } if_;
        struct {
            struct expression *condition;
            char *comment;
            struct caselist *cases;
        } switch_;
        struct {
            struct expression *condition;
            char *condition_comment;
            struct statlist *statements;
        } while_;
        struct {
            struct expression *condition;
            char *condition_comment;
            struct statlist *statements;
            char *statements_comment;
        } do_while;
        struct {
            for_direction_t direction;
            struct variable *variable;
            struct expression *start;
            struct expression *finish;
            char *for_comment;
            struct statlist *statements;
        } for_;
        struct {
            io_t type;
            struct expression *value;
            struct expression *to_write;
            char *comment;
        } write;
        struct {
            int stop_bit;
            struct expression *value;
            char *comment;
        } write_unary;
        struct {
            struct expression *to_skip;
            io_t type;
            char *skip_comment;
        } skip;
        struct {
            struct expressionlist *toreturn;
            char *return_comment;
        } return_;
        struct {
            struct expression *condition;
            char *assert_comment;
        } assert;
    } _;

    void (*output_latex)(const struct statement *self,
                         const struct definitions *defs,
                         FILE *output);
    void (*free)(struct statement *self);
};

struct statlist {
    struct statement *statement;
    struct statlist *next;
    void (*output_latex)(const struct statlist *self,
                         const struct definitions *defs,
                         FILE *output);
    void (*free)(struct statlist *self);
};

struct elselist {
    /*if condition is NULL, this is a final "else" block
      and one can assume "next" is also NULL
      otherwise, it's an "elif" block
      and "next" may or may not be NULL*/
    struct expression *condition;
    char *comment;
    struct statlist *else_;
    struct elselist *next;
    void (*output_latex)(const struct elselist *self,
                         const struct definitions *defs,
                         FILE *output);
    void (*free)(struct elselist *self);
};

struct caselist {
    /*if condition is NULL, this is a "default" switch block
      and one can assume "next" is also NULL
      otherwise, it's a "case" switch block
      and "next" may or may not be NULL*/
    struct expression *condition;
    char *comment;
    struct statlist *case_;
    struct caselist *next;
    void (*output_latex)(const struct caselist *self,
                         const struct definitions *defs,
                         FILE *output);
    void (*free)(struct caselist *self);
};

struct intlist {
    int integer;
    struct intlist *next;
};

#endif
