from construct import *


class AstNode(Container):
    def __init__(self, nodetype, **kw):
        Container.__init__(self)
        self.nodetype = nodetype
        for k, v in sorted(kw.iteritems()):
            setattr(self, k, v)
    
    def accept(self, visitor):
        return getattr(visitor, "visit_%s" % (self.nodetype,))(self)


class AstTransformator(Adapter):
    def _decode(self, obj, context):
        return self.to_ast(obj, context)
    def _encode(self, obj, context):
        return self.to_cst(obj, context)








