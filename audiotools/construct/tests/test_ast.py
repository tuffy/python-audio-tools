import unittest

from construct import *
from construct.text import *

class NodeAdapter(Adapter):
    def __init__(self, factory, subcon):
        Adapter.__init__(self, subcon)
        self.factory = factory
    def _decode(self, obj, context):
        return self.factory(obj)


#===============================================================================
# AST nodes
#===============================================================================
class Node(Container):
    def __init__(self, name, **kw):
        Container.__init__(self)
        self.name = name
        for k, v in kw.iteritems():
            setattr(self, k, v)
    
    def accept(self, visitor):
        return getattr(visitor, "visit_%s" % self.name)(self)

def binop_node(obj):
    lhs, rhs = obj
    if rhs is None:
        return lhs
    else:
        op, rhs = rhs
        return Node("binop", lhs=lhs, op=op, rhs=rhs)

def literal_node(value):
    return Node("literal", value = value)


#===============================================================================
# concrete grammar
#===============================================================================
ws = Whitespace()
term = IndexingAdapter(
    Sequence("term",
        ws, 
        Select("term", 
            NodeAdapter(literal_node, DecNumber("number")), 
            IndexingAdapter(
                Sequence("subexpr", 
                    Literal("("), 
                    LazyBound("expr", lambda: expr), 
                    Literal(")")
                ),
                index = 0
            ),
        ),
        ws,
    ),
    index = 0
)

def OptSeq(name, *args):
    return Optional(Sequence(name, *args))

expr1 = NodeAdapter(binop_node, 
    Sequence("expr1", 
        term,
        OptSeq("rhs",
            CharOf("op", "*/"), 
            LazyBound("rhs", lambda: expr1)
        ),
    )
)

expr2 = NodeAdapter(binop_node, 
    Sequence("expr2", 
        expr1, 
        OptSeq("rhs",
            CharOf("op", "+-"), 
            LazyBound("rhs", lambda: expr2)
        ),
    )
)

expr = expr2


#===============================================================================
# evaluation visitor
#===============================================================================
class EvalVisitor(object):
    def visit_literal(self, obj):
        return obj.value
    def visit_binop(self, obj):
        lhs = obj.lhs.accept(self)
        op = obj.op
        rhs = obj.rhs.accept(self)
        if op == "+":
            return lhs + rhs
        elif op == "-":
            return lhs - rhs
        elif op == "*":
            return lhs * rhs
        elif op == "/":
            return lhs / rhs
        else:
            raise ValueError("invalid op", op)

ev = EvalVisitor()

class TestSomethingSomething(unittest.TestCase):

    def test_that_one_thing(self):
        node = expr.parse("2*3+4")
        self.assertEqual(node.name, "binop")
        self.assertEqual(node.op, "+")
        self.assertEqual(node.rhs.name, "literal")
        self.assertEqual(node.rhs.value, 4)
        self.assertEqual(node.lhs.name, "binop")
        self.assertEqual(node.lhs.op, "*")
        self.assertEqual(node.lhs.rhs.name, "literal")
        self.assertEqual(node.lhs.rhs.value, 3)
        self.assertEqual(node.lhs.lhs.name, "literal")
        self.assertEqual(node.lhs.lhs.value, 2)

    def test_that_other_thing(self):
        node = expr.parse("2*(3+4)")
        self.assertEqual(node.name, "binop")
        self.assertEqual(node.op, "*")
        self.assertEqual(node.rhs.name, "binop")
        self.assertEqual(node.rhs.op, "+")
        self.assertEqual(node.rhs.rhs.name, "literal")
        self.assertEqual(node.rhs.rhs.value, 4)
        self.assertEqual(node.rhs.lhs.name, "literal")
        self.assertEqual(node.rhs.lhs.value, 3)
        self.assertEqual(node.lhs.name, "literal")
        self.assertEqual(node.lhs.value, 2)
