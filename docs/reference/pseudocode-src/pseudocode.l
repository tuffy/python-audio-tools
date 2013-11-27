%{
#include "pseudocode.tab.h"

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

extern unsigned lineno;

char*
extract_string(const char *token)
{
   /*grab everything but the first and last characters
     and un-escape any necessay characters*/
   char *string = calloc(strlen(token) - 2 + 1, sizeof(char));
   char *output = string;
   char c;

   token++;  /*skip initial " character*/

   while ((c = token[0]) != '"') {  /*continue until final " character*/
       if (c != '\\') {
           output[0] = c;
           output++;
           token++;
       } else {
           const char escape = token[1];
           output[0] = escape;
           output++;
           token += 2;
       }
   }

   return string;
}

char*
extract_comment(const char *token)
{
   /*cut off first 2 and last 2 characters*/
   /*FIXME - strip out leading and trailing whitespace*/
   const size_t token_len = strlen(token);
   char *comment = calloc(token_len - 4 + 1, sizeof(char));
   strncpy(comment, token + 2, token_len - 4);
   return comment;
}
%}

%%

"INPUT"                 {return INPUT;}
"OUTPUT"                {return OUTPUT;}
"VAR"                   {return VAR;}
"FUNC"                  {return FUNC;}
"break"                 {return BREAK;}
"infinity"              {return INFINITY;}
"pi"                    {return PI;}
"read"                  {return READ;}
"write"                 {return WRITE;}
"skip"                  {return SKIP;}
"unary"                 {return UNARY;}
"unsigned"              {return UNSIGNED;}
"signed"                {return SIGNED;}
"bytes"                 {return BYTES;}
"frac"                  {return FRAC;}
"ceil"                  {return CEIL;}
"floor"                 {return FLOOR;}
"sum"                   {return SUM;}
"log"                   {return LOG;}
"sin"                   {return SIN;}
"cos"                   {return COS;}
"tan"                   {return TAN;}
"<-"                    {return ASSIGN_IN;}
"->"                    {return ASSIGN_OUT;}
"["                     {return OPEN_BRACKET;}
"]"                     {return CLOSE_BRACKET;}
"("                     {return OPEN_PAREN;}
")"                     {return CLOSE_PAREN;}
"{"                     {return OPEN_CURLYBRACE;}
"}"                     {return CLOSE_CURLYBRACE;}
"|"                     {return PIPE;}
"do"                    {return DO;}
"if"                    {return IF;}
"elif"                  {return ELIF;}
"else"                  {return ELSE;}
"switch"                {return SWITCH;}
"case"                  {return CASE;}
"default"               {return DEFAULT;}
"while"                 {return WHILE;}
"for"                   {return FOR;}
"to"                    {return TO;}
"downto"                {return DOWNTO;}
"=="                    {return CMP_EQ;}
"!="                    {return CMP_NE;}
"<"                     {return CMP_LT;}
"<="                    {return CMP_LTE;}
">"                     {return CMP_GT;}
">="                    {return CMP_GTE;}
"and"                   {return AND;}
"or"                    {return OR;}
"not"                   {return NOT;}
"+"                     {return PLUS;}
"-"                     {return DASH;}
"*"                     {return STAR;}
"/"                     {return SLASH;}
"%"                     {return PERCENT;}
"^"                     {return CARAT;}
","                     {return COMMA;}
"return"                {return RETURN;}
"assert"                {return ASSERT;}
\"(\\.|[^"])*\"         {yylval.string = extract_string(yytext);
                         return STRING;}
[a-zA-Z_][a-zA-Z0-9_]*  {yylval.identifier = strdup(yytext);
                         return IDENTIFIER;}
[0-9]+                  {yylval.integer = atoi(yytext);
                         return INTEGER;}
-?[0-9]+\.[0-9]+       {yylval.float_ = strdup(yytext);
                         return FLOAT;}
\/\*([^*]|\*+[^/*])*\*+\/ {yylval.comment = extract_comment(yytext);
                           return COMMENT;}
\n                      {lineno++;}
";"                     {return EOS;}
[ \t]                   { }
#.*                     { }
.                       {printf("mystery char %s\n", yytext);}

%%
