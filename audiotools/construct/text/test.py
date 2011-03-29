from construct import *
from construct.text import *



#===============================================================================
# AST transfomations
#===============================================================================
class NumberTransformator(AstTransformator):
    def to_ast(self, obj, context):
        return AstNode("number", value = obj)

class StringTransformator(AstTransformator):
    def to_ast(self, obj, context):
        return AstNode("string", value = obj)

class SymbolTransformator(AstTransformator):
    keywords = set([
        "if", "for", "while", "else", "def", "import", "in", "and", "or",
        "not", "as", "from", "return", "const", "var",
    ])
    def to_ast(self, obj, context):
        if obj in self.keywords:
            return AstNode("error", 
                message = "reserved word used as a symbol", 
                args = [obj]
            )
        else:
            return AstNode("symbol", name = obj)

class CommentTransformator(AstTransformator):
    def to_ast(self, obj, context):
        return AstNode("comment", text = obj)

class CallTransformator(AstTransformator):
    def to_ast(self, obj, context):
        symbol, args, lastarg = obj
        args.append(lastarg)
        return AstNode("call", name = symbol, args = args)

class ExprTransformator(AstTransformator):
    def to_ast(self, obj, context):
        lhs, rhs = obj
        if rhs is None:
            return lhs
        else:
            op, rhs = rhs
            return AstNode("expr", lhs = lhs, op = op, rhs = rhs)

class VardefTransformator(AstTransformator):
    def to_ast(self, obj, context):
        args, lastarg = obj
        vars = []
        for name, type, init in args:
            args.append((name, type, init))
        name, type, init = lastarg
        vars.append((name, type, init))
        return AstNode("vardef", vars = vars)

class AsgnTransformator(AstTransformator):
    def to_ast(self, obj, context):
        name, expr = obj
        return AstNode("asgnstmt", name = name, expr = expr)

class IfTransformator(AstTransformator):
    def to_ast(self, obj, context):
        return AstNode("ifstmt", 
            cond = obj.cond, 
            thencode = obj.thencode, 
            elsecode = obj.elsecode
        )

class WhileTransformator(AstTransformator):
    def to_ast(self, obj, context):
        return AstNode("whilestmt", cond = obj.cond, code = obj.code) 

class BlockTransformator(AstTransformator):
    def to_ast(self, obj, context):
        return AstNode("block", statements = obj)

class RootTransformator(AstTransformator):
    def to_ast(self, obj, context):
        return AstNode("root", statements = obj)


#===============================================================================
# macros
#===============================================================================
def OptSeq(name, *subcons):
    return Optional(Sequence(name, *subcons))

def SeqOfOne(name, *subcons):
    return IndexingAdapter(Sequence(name, *subcons), index = 0)

def OptSeqOfOne(name, *subcons):
    return Optional(SeqOfOne(name, *subcons))

def Expr(name):
    return LazyBound(name, lambda: expr2)


#===============================================================================
# grammar
#===============================================================================
ws = Whitespace(" \t\r\n")
rws = Whitespace(" \t\r\n", optional = False)

number = NumberTransformator(
    Select("num", 
        FloatNumber("flt"), 
        SeqOfOne("hex",
            Literal("0x"),
            HexNumber("value"),
        ),
        DecNumber("dec"),
    )
)

symbol = SymbolTransformator(Identifier("symbol"))

call = CallTransformator(
    Sequence("call",
        symbol,
        ws,
        Literal("("),
        OptionalGreedyRange(
            SeqOfOne("args",
                Expr("expr"),
                Literal(","),
            )
        ),
        Optional(Expr("expr")),
        Literal(")"),
    )
)

comment = CommentTransformator(
    SeqOfOne("comment",
        Literal("/*"),
        StringUpto("text", "*/"),
        Literal("*/"),
    )
)

term = SeqOfOne("term",
    ws,
    Select("term",
        number,
        call,
        symbol,
        SeqOfOne("subexpr",
            Literal("("),
            Expr("subexpr"),
            Literal(")"),
        )
    ),
    ws,
)

expr1 = ExprTransformator(
    Sequence("expr1",
        term,
        OptSeq("rhs",
            CharOf("op", "*/"),
            LazyBound("expr1", lambda: expr1),
        )
    )
)
expr2 = ExprTransformator(
    Sequence("expr2",
        expr1,
        OptSeq("rhs",
            CharOf("op", "+-"),
            LazyBound("expr2", lambda: expr2),
        )
    )
)

asgnstmt = AsgnTransformator(
    Sequence("asgnstmt",
        symbol,
        ws,
        Literal("="),
        Expr("expr"),
        Literal(";"),
    )
)

vardef_elem = Sequence("vardef_elem",
    Identifier("name"),
    ws,
    Literal("as"),
    ws,
    Identifier("type"),
    OptSeqOfOne("init",
        ws,
        Literal("="),
        Expr("expr"),
    )
)
vardef = VardefTransformator(
    Sequence("vardef",
        Literal("var"),
        rws,
        OptionalGreedyRange(
            SeqOfOne("names",
                ws,
                vardef_elem,
                ws,
                Literal(","),
            )
        ),
        ws,
        vardef_elem,
        ws,
        Literal(";"),
    )
)

stmt = SeqOfOne("stmt",
    ws,
    Select("stmt",
        comment,
        LazyBound("if", lambda: ifstmt),
        LazyBound("while", lambda: whilestmt),
        asgnstmt,
        vardef,
        SeqOfOne("expr",
            Expr("expr"), 
            Literal(";")
        ),
    ),
    ws,
)
        
def Block(name):
    return BlockTransformator(
        Select(name,
            SeqOfOne("multi",
                ws,
                Literal("{"),
                OptionalGreedyRange(stmt),
                Literal("}"),
                ws,
            ),
            Sequence("single", stmt),
        )
    )

ifstmt = IfTransformator(
    Struct("ifstmt", 
        Literal("if"),
        ws,
        Literal("("),
        Expr("cond"),
        Literal(")"),
        Block("thencode"),
        Optional(
            SeqOfOne("elsecode",
                Literal("else"),
                Block("code"),
            )
        ),
    )
)

whilestmt = WhileTransformator(
    Struct("whilestmt", 
        Literal("while"),
        ws,
        Literal("("),
        Expr("cond"),
        Literal(")"),
        Block("code"),
    )
)

root = RootTransformator(
    OptionalGreedyRange(stmt)
)

test = """var x as int, y as int;"""

print vardef.parse(test)






















