from construct.text import *


ws = Whitespace(" \t\r\n")

term = Select("term",
    DecNumber("dec"),
    Identifier("symbol"),
    IndexingAdapter(
        Sequence("expr",
            Literal("("),
            ws,
            LazyBound("expr", lambda: expr),
            ws,
            Literal(")"),
        ),
        0
    ),
)

expr1 = Select("expr1",
    Sequence("node", 
        term,
        ws,
        CharOf("binop", "*/"),
        ws,
        LazyBound("rhs", lambda: expr1),
    ),
    term,
)

expr2 = Select("expr2",
    Sequence("node", 
        expr1,
        ws,
        CharOf("binop", "+-"),
        ws,
        LazyBound("rhs", lambda: expr2),
    ),
    expr1,
)

expr = expr2

def eval2(node):
    if type(node) is int:
        return node
    lhs = eval2(node[0])
    op = node[1]
    rhs = eval2(node[2])
    if op == "+":
        return lhs + rhs
    elif op == "-":
        return lhs - rhs
    elif op == "*":
        return lhs * rhs
    elif op == "/":
        return lhs / rhs
    assert False

print expr.parse("(1 + 2)*3")
print eval2(expr.parse("(1 + 2)*3"))
print expr.build([[1, "+", 2], "*", 3])














