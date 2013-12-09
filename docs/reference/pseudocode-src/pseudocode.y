%{
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <getopt.h>
#include <errno.h>
#include "variable.h"
#include "statement.h"
#include "expression.h"
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


typedef enum {
    OUT_LATEX
} output_format_t;

void yyerror(char *s);
int yylex(void);
unsigned lineno = 1;

extern FILE *yyin;
FILE *input_file = NULL;
FILE *output_file = NULL;
output_format_t output_format = OUT_LATEX;

struct pseudocode {
    struct code_io *input;
    struct code_io *output;
    struct definitions definitions;
    struct statlist *statlist;
};


struct pseudocode*
new_pseudocode(struct code_io *input,
               struct code_io *output,
               struct vardef *vardef,
               struct funcdef *funcdef,
               struct statlist *statlist);

void
output_pseudocode_latex(const struct pseudocode *code, FILE *output);

void
free_pseudocode(struct pseudocode *code);

%}

%left AND OR
%left CMP_EQ CMP_NE CMP_LT CMP_LTE CMP_GT CMP_GTE
%left PLUS DASH STAR SLASH PERCENT
%left NOT
%left CARAT

%token INPUT OUTPUT VAR FUNC BREAK FRAC CEIL FLOOR SUM
%token INFINITY PI
%token LOG SIN COS TAN
%token <string> STRING
%token <identifier> IDENTIFIER
%token <integer> INTEGER
%token <float_> FLOAT
%token <comment> COMMENT
%token ASSIGN_IN ASSIGN_OUT OPEN_BRACKET CLOSE_BRACKET
%token READ WRITE UNARY SKIP UNSIGNED SIGNED BYTES
%token OPEN_PAREN CLOSE_PAREN OPEN_CURLYBRACE CLOSE_CURLYBRACE PIPE
%token DO WHILE FOR TO DOWNTO
%token IF ELIF ELSE SWITCH CASE DEFAULT
%token CMP_EQ CMP_NE CMP_LT CMP_LTE CMP_GT CMP_GTE AND OR NOT
%token PLUS DASH STAR SLASH PERCENT
%token RETURN COMMA EOS ASSERT

%type <code> pseudocode
%type <code_io> input
%type <code_io> output
%type <vardef> vardef
%type <funcdef> funcdef
%type <statlist> statlist
%type <statement> statement
%type <elselist> elselist
%type <caselist> caselist
%type <variable> variable
%type <variablelist> variablelist
%type <expression> expression
%type <expressionlist> expressionlist
%type <subscript> subscript
%type <intlist> intlist
%type <comment> comment

%union {
    char *string;
    char *identifier;
    long long integer;
    char *float_;
    char *comment;
    struct pseudocode *code;
    struct code_io *code_io;
    struct vardef *vardef;
    struct funcdef *funcdef;
    struct statlist *statlist;
    struct statement *statement;
    struct elselist *elselist;
    struct caselist *caselist;
    struct variable *variable;
    struct variablelist *variablelist;
    struct expression *expression;
    struct expressionlist *expressionlist;
    struct intlist *intlist;
    struct subscript *subscript;
}

%%

pseudocode: input output vardef funcdef statlist {
    struct pseudocode *code = new_pseudocode($1, $2, $3, $4, $5);
    switch (output_format) {
    case OUT_LATEX:
        output_pseudocode_latex(code, output_file);
        break;
    }
    free_pseudocode(code);
 }
 ;

input: INPUT STRING EOS                {
    $$ = new_code_io(PSEUDOCODE_INPUT, $2, NULL);
 }
 | INPUT variablelist EOS              {
    $$ = new_code_io(PSEUDOCODE_INPUT, NULL, $2);
 }
 | INPUT STRING COMMA variablelist EOS {
    $$ = new_code_io(PSEUDOCODE_INPUT, $2, $4);
 }
 ;

output: OUTPUT STRING EOS                {
    $$ = new_code_io(PSEUDOCODE_OUTPUT, $2, NULL);
 }
 | OUTPUT variablelist EOS              {
    $$ = new_code_io(PSEUDOCODE_OUTPUT, NULL, $2);
 }
 | OUTPUT STRING COMMA variablelist EOS {
    $$ = new_code_io(PSEUDOCODE_OUTPUT, $2, $4);
 }
 ;

vardef:                               {$$ = NULL;}
 | VAR IDENTIFIER STRING EOS vardef   {$$ = vardef_new($2, $3, $5);}
 ;

funcdef:                              {$$ = NULL;}
 | FUNC IDENTIFIER STRING EOS funcdef {
    $$ = funcdef_new($2, $3, NULL, $5);
 }
 | FUNC IDENTIFIER STRING STRING EOS funcdef {
    $$ = funcdef_new($2, $3, $4, $6);
 }
 ;

statlist: statement   {$$ = statlist_new($1, NULL);}
 | statement statlist {$$ = statlist_new($1, $2);}
 ;

statement: EOS {
    $$ = statement_new_blankline();
 }
 |COMMENT EOS {
    $$ = statement_new_comment($1);
 }
 | BREAK comment EOS {
    $$ = statement_new_break($2);
 }
 | variablelist ASSIGN_IN expression comment EOS {
    $$ = statement_new_assign_in($1, $3, $4);
 }
 | IDENTIFIER OPEN_PAREN CLOSE_PAREN comment EOS {
    $$ = statement_new_functioncall($1, NULL, NULL, $4);
 }
 | IDENTIFIER OPEN_PAREN expressionlist CLOSE_PAREN comment EOS {
    $$ = statement_new_functioncall($1, $3, NULL, $5);
 }
 | variablelist ASSIGN_IN IDENTIFIER OPEN_PAREN CLOSE_PAREN comment EOS {
    $$ = statement_new_functioncall($3, NULL, $1, $6);
 }
 | variablelist ASSIGN_IN IDENTIFIER OPEN_PAREN expressionlist CLOSE_PAREN comment EOS {
    $$ = statement_new_functioncall($3, $5, $1, $7);
 }
 | IF expression comment OPEN_CURLYBRACE statlist CLOSE_CURLYBRACE elselist {
    $$ = statement_new_if($2, $5, $3, $7);
 }
 | SWITCH expression comment OPEN_CURLYBRACE caselist CLOSE_CURLYBRACE {
    $$ = statement_new_switch($2, $3, $5);
 }
 | WHILE expression comment OPEN_CURLYBRACE statlist CLOSE_CURLYBRACE {
    $$ = statement_new_while($2, $3, $5);
 }
 | DO comment OPEN_CURLYBRACE statlist CLOSE_CURLYBRACE WHILE expression comment EOS  {
    $$ = statement_new_do_while($7, $8, $4, $2);
 }
 | FOR variable ASSIGN_IN expression TO expression comment OPEN_CURLYBRACE statlist CLOSE_CURLYBRACE {
    $$ = statement_new_for(FOR_TO, $2, $4, $6, $7, $9);
 }
 | FOR variable ASSIGN_IN expression DOWNTO expression comment OPEN_CURLYBRACE statlist CLOSE_CURLYBRACE {
    $$ = statement_new_for(FOR_DOWNTO, $2, $4, $6, $7, $9);
 }
 | expression ASSIGN_OUT WRITE expression UNSIGNED comment EOS {
     $$ = statement_new_write(IO_UNSIGNED, $1, $4, $6);
 }
 | expression ASSIGN_OUT WRITE expression SIGNED comment EOS {
     $$ = statement_new_write(IO_SIGNED, $1, $4, $6);
 }
 | expression ASSIGN_OUT WRITE expression BYTES comment EOS {
     $$ = statement_new_write(IO_BYTES, $1, $4, $6);
 }
 | expression ASSIGN_OUT WRITE UNARY INTEGER comment EOS {
     $$ = statement_new_write_unary($5, $1, $6);
 }
 | IDENTIFIER OPEN_PAREN CLOSE_PAREN ASSIGN_OUT WRITE expression UNSIGNED comment EOS {
     $$ = statement_new_functioncall_write($1, NULL, IO_UNSIGNED, $6, $8);
 }
 | IDENTIFIER OPEN_PAREN expressionlist CLOSE_PAREN ASSIGN_OUT WRITE expression UNSIGNED comment EOS {
     $$ = statement_new_functioncall_write($1, $3, IO_UNSIGNED, $7, $9);
 }
 | IDENTIFIER OPEN_PAREN CLOSE_PAREN ASSIGN_OUT WRITE expression SIGNED comment EOS {
     $$ = statement_new_functioncall_write($1, NULL, IO_SIGNED, $6, $8);
 }
 | IDENTIFIER OPEN_PAREN expressionlist CLOSE_PAREN ASSIGN_OUT WRITE expression SIGNED comment EOS {
     $$ = statement_new_functioncall_write($1, $3, IO_SIGNED, $7, $9);
 }
 | IDENTIFIER OPEN_PAREN CLOSE_PAREN ASSIGN_OUT WRITE expression BYTES comment EOS {
     $$ = statement_new_functioncall_write($1, NULL, IO_BYTES, $6, $8);
 }
 | IDENTIFIER OPEN_PAREN expressionlist CLOSE_PAREN ASSIGN_OUT WRITE expression BYTES comment EOS {
     $$ = statement_new_functioncall_write($1, $3, IO_BYTES, $7, $9);
 }
 | IDENTIFIER OPEN_PAREN CLOSE_PAREN ASSIGN_OUT WRITE UNARY INTEGER comment EOS {
     $$ = statement_new_functioncall_write_unary($1, NULL, $7, $8);
 }
 | IDENTIFIER OPEN_PAREN expressionlist CLOSE_PAREN ASSIGN_OUT WRITE UNARY INTEGER comment EOS {
     $$ = statement_new_functioncall_write_unary($1, $3, $8, $9);
 }
 | SKIP expression comment EOS  {
    $$ = statement_new_skip($2, IO_UNSIGNED, $3);
 }
 | SKIP expression BYTES comment EOS {
    $$ = statement_new_skip($2, IO_BYTES, $4);
 }
 | RETURN expressionlist comment EOS {
    $$ = statement_new_return($2, $3);
 }
 | ASSERT expression comment EOS {
    $$ = statement_new_assert($2, $3);
 }
 ;

elselist: {$$ = NULL;}
 | ELSE comment OPEN_CURLYBRACE statlist CLOSE_CURLYBRACE {
   $$ = elselist_new(NULL, $2, $4, NULL);
 }
 | ELIF expression comment OPEN_CURLYBRACE statlist CLOSE_CURLYBRACE elselist {
   $$ = elselist_new($2, $3, $5, $7);
 }
 ;

caselist: {$$ = NULL;}
 | DEFAULT comment OPEN_CURLYBRACE statlist CLOSE_CURLYBRACE {
    $$ = caselist_new(NULL, $2, $4, NULL);
 }
 | CASE expression comment OPEN_CURLYBRACE statlist CLOSE_CURLYBRACE caselist {
    $$ = caselist_new($2, $3, $5, $7);
 }
 ;

comment: {$$ = NULL;}
 | COMMENT {$$ = $1;}
 ;

variable: IDENTIFIER     {$$ = variable_new($1, NULL);}
 | IDENTIFIER subscript  {$$ = variable_new($1, $2);}
 ;

variablelist: variable         {$$ = variablelist_new($1, NULL);}
 | variable COMMA variablelist {$$ = variablelist_new($1, $3);}
 ;

subscript: OPEN_BRACKET expression CLOSE_BRACKET {
    $$ = subscript_new($2, NULL);}
 | OPEN_BRACKET expression CLOSE_BRACKET subscript {
    $$ = subscript_new($2, $4);}
 ;

expression: variable  {$$ = expression_new_variable($1);}
 | INTEGER            {$$ = expression_new_integer($1);}
 | FLOAT              {$$ = expression_new_float($1);}
 | INFINITY           {$$ = expression_new_constant(CONST_INFINITY);}
 | PI                 {$$ = expression_new_constant(CONST_PI);}
 | OPEN_BRACKET intlist CLOSE_BRACKET {$$ = expression_new_bytes($2);}
 | OPEN_PAREN expression CLOSE_PAREN {
     $$ = expression_new_wrapped(WRAP_PARENTHESIZED, $2);}
 | OPEN_CURLYBRACE expression CLOSE_CURLYBRACE {$$ = $2;}
 | CEIL OPEN_PAREN expression CLOSE_PAREN {
     $$ = expression_new_wrapped(WRAP_CEILING, $3);
 }
 | FLOOR OPEN_PAREN expression CLOSE_PAREN {
     $$ = expression_new_wrapped(WRAP_FLOOR, $3);
 }
 | PIPE expression PIPE {
     $$ = expression_new_wrapped(WRAP_ABS, $2);
 }
 | DASH expression {
     $$ = expression_new_wrapped(WRAP_UMINUS, $2);
 }
 | SIN OPEN_PAREN expression CLOSE_PAREN {
     $$ = expression_new_function(FUNC_SIN, $3);
 }
 | COS OPEN_PAREN expression CLOSE_PAREN {
     $$ = expression_new_function(FUNC_COS, $3);
 }
 | TAN OPEN_PAREN expression CLOSE_PAREN {
     $$ = expression_new_function(FUNC_TAN, $3);
 }
 | FRAC OPEN_PAREN expression COMMA expression CLOSE_PAREN {
     $$ = expression_new_fraction($3, $5);
 }
 | SUM variable ASSIGN_IN expression TO expression OPEN_CURLYBRACE expression CLOSE_CURLYBRACE {
     $$ = expression_new_sum($2, $4, $6, $8);
 }
 | expression CMP_EQ expression {
     $$ = expression_new_comparison(CMP_OP_EQ, $1, $3);}
 | expression CMP_NE expression {
     $$ = expression_new_comparison(CMP_OP_NE, $1, $3);}
 | expression CMP_LT expression {
     $$ = expression_new_comparison(CMP_OP_LT, $1, $3);}
 | expression CMP_LTE expression {
     $$ = expression_new_comparison(CMP_OP_LTE, $1, $3);}
 | expression CMP_GT expression {
     $$ = expression_new_comparison(CMP_OP_GT, $1, $3);}
 | expression CMP_GTE expression {
     $$ = expression_new_comparison(CMP_OP_GTE, $1, $3);}
 | expression AND expression {
     $$ = expression_new_boolean(BOOL_AND, $1, $3);
 }
 | expression OR expression {
     $$ = expression_new_boolean(BOOL_OR, $1, $3);
 }
 | NOT expression {
     $$ = expression_new_not($2);
 }
 | expression PLUS expression    {
     $$ = expression_new_math(MATH_ADD, $1, $3);}
 | expression DASH expression    {
     $$ = expression_new_math(MATH_SUBTRACT, $1, $3);}
 | expression STAR expression    {
     $$ = expression_new_math(MATH_MULTIPLY, $1, $3);}
 | expression SLASH expression    {
     $$ = expression_new_math(MATH_DIVIDE, $1, $3);}
 | expression PERCENT expression {
     $$ = expression_new_math(MATH_MOD, $1, $3);
 }
 | expression CARAT expression    {
     $$ = expression_new_pow($1, $3);
 }
 | LOG OPEN_PAREN expression COMMA expression CLOSE_PAREN {
     $$ = expression_new_log($3, $5);
 }
 | READ expression UNSIGNED      {$$ = expression_new_read(IO_UNSIGNED, $2);}
 | READ expression SIGNED        {$$ = expression_new_read(IO_SIGNED, $2);}
 | READ expression BYTES         {$$ = expression_new_read(IO_BYTES, $2);}
 | READ UNARY INTEGER            {$$ = expression_new_read_unary($3);}
 ;

expressionlist: expression         {$$ = expressionlist_new($1, NULL);}
 | expression COMMA expressionlist {$$ = expressionlist_new($1, $3);}
 ;

intlist: INTEGER  {$$ = intlist_new($1, NULL);}
 | INTEGER COMMA intlist {$$ = intlist_new($1, $3);}
 ;

%%

int main(int argc, char *argv[])
{
    char *input_filename = NULL;
    char *output_filename = NULL;
    output_format_t output_format = OUT_LATEX;

    char c;
    const static struct option long_opts[] = {
        {"help",   no_argument,       NULL, 'h'},
        {"output", required_argument, NULL, 'o'},
        {"format", required_argument, NULL, 'f'},
        {NULL,     no_argument,       NULL, 0}
    };
    const static char* short_opts = "-ho:f:";

    while ((c = getopt_long(argc, argv, short_opts, long_opts, NULL)) != -1) {
        switch (c) {
        case 1:
            if (input_filename == NULL) {
                input_filename = optarg;
            } else {
                fprintf(stderr, "*** Error: only one input file allowed\n");
                return 1;
            }
            break;
        case 'o':
            if (output_filename == NULL) {
                output_filename = optarg;
            } else {
                fprintf(stderr, "*** Error: only one output file allowed\n");
                return 1;
            }
            break;
        case 'f':
            if (strcmp(optarg, "latex") == 0) {
                output_format = OUT_LATEX;
            } else {
                fprintf(stderr, "*** Error: invalid output format \"%s\"\n",
                        optarg);
                fprintf(stderr, "choose from: \"%s\"", "latex");
                return 1;
            }
            break;
        case 'h':  /*fallthrough*/
        case ':':
        case '?':
            printf("*** Usage: pseudocode [options] <input.pfl>\n");
            printf("-o, --output=<filename>    output filename\n");
            printf("-f, --format=<format>      output format\n");
            return 0;
        default:
            break;
        }
    }

    if (input_filename == NULL) {
        fprintf(stderr, "*** Error: input filename is required\n");
    } else {
        if ((input_file = fopen(input_filename, "r")) == NULL) {
            fprintf(stderr, "*** Error: %s: %s",
                    input_filename,
                    strerror(errno));
            return 2;
        }

        yyin = input_file;
    }

    if (output_filename == NULL) {
        output_file = stdout;
    } else {
        if ((output_file = fopen(output_filename, "w")) == NULL) {
            fprintf(stderr, "*** Error: %s: %s",
                    output_filename,
                    strerror(errno));
            return 3;
        }
    }

    yyparse();

    fclose(input_file);
    fclose(output_file);

    return 0;
}

void yyerror(char *s)
{
    fprintf(stderr, "*** Line %u: %s\n", lineno, s);
    exit(1);
}

struct pseudocode*
new_pseudocode(struct code_io *input,
               struct code_io *output,
               struct vardef *vardef,
               struct funcdef *funcdef,
               struct statlist *statlist)
{
    struct pseudocode *code;
    struct vardef *var;
    struct funcdef *func;

    /*ensure variables aren't defined more than once*/
    for (var = vardef; var != NULL; var = var->next) {
        struct vardef *var2;
        for (var2 = vardef; var2 != var; var2 = var2->next) {
            if (strcmp(var->identifier, var2->identifier) == 0) {
                fprintf(stderr,
                        "*** Error: variable \"%s\" defined more than once\n",
                        var2->identifier);
                exit(1);
            }
        }
    }

    /*ensure functions aren't defined more than once*/
    for (func = funcdef; func != NULL; func = func->next) {
        struct funcdef *func2;
        for (func2 = funcdef; func2 != func; func2 = func2->next) {
            if (strcmp(func->identifier, func2->identifier) == 0) {
                fprintf(stderr,
                        "*** Error: function \"%s\" defined more than once\n",
                        func2->identifier);
                exit(1);
            }
        }
    }

    code = malloc(sizeof(struct pseudocode));
    code->input = input;
    code->output = output;
    code->definitions.variables = vardef;
    code->definitions.functions = funcdef;
    code->statlist = statlist;
    return code;
}

void
free_pseudocode(struct pseudocode *code)
{
    code->input->free(code->input);
    code->output->free(code->output);
    vardef_free(code->definitions.variables);
    funcdef_free(code->definitions.functions);
    code->statlist->free(code->statlist);
    free(code);
}

void
output_pseudocode_latex(const struct pseudocode *code, FILE *output)
{
    struct vardef *vardef;
    unsigned variable_id;

    fprintf(output, "\\begin{algorithm}[H]\n");
    fprintf(output, "\\DontPrintSemicolon\n");
    /*setup keywords*/
    /*FIXME - only output keywords which are used*/
    fprintf(output, "\\SetKw{KwDownTo}{downto}\n");
    fprintf(output, "\\SetKw{READ}{read}\n");
    fprintf(output, "\\SetKw{RUNARY}{read unary}\n");
    fprintf(output, "\\SetKw{WRITE}{write}\n");
    fprintf(output, "\\SetKw{WUNARY}{write unary}\n");
    fprintf(output, "\\SetKw{SKIP}{skip}\n");
    fprintf(output, "\\SetKw{ASSERT}{assert}\n");
    fprintf(output, "\\SetKw{AND}{and}\n");
    fprintf(output, "\\SetKw{OR}{or}\n");
    fprintf(output, "\\SetKw{NOT}{not}\n");
    fprintf(output, "\\SetKw{BREAK}{break}\n");
    fprintf(output, "\\SetKwRepeat{Repeat}{repeat}{while}\n");

    /*setup variables*/
    /*FIXME - only output variables which are used*/
    for (vardef = code->definitions.variables, variable_id = 0;
         vardef != NULL;
         vardef = vardef->next, variable_id++) {
        fprintf(output, "\\SetKwData{");
        escape_latex_variable(output, variable_id);
        fprintf(output, "}{");
        escape_latex_curly_brackets(output, vardef->label);
        fprintf(output, "}\n");
    }

    code->input->output_latex(code->input,
                              &(code->definitions),
                              output);
    code->output->output_latex(code->output,
                              &(code->definitions),
                              output);
    fprintf(output, "\\BlankLine\n");
    code->statlist->output_latex(code->statlist,
                                 &(code->definitions),
                                 output);
    fprintf(output, "\\end{algorithm}\n");
}
