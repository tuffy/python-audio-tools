import sys
from construct import *
from construct.text import *


# some tests require doing bad things...
import warnings
warnings.filterwarnings("ignore", category = DeprecationWarning)


# declarative to the bitter end!
tests = [
    #
    # lib
    #
    [int_to_bin, (19, 5), "\x01\x00\x00\x01\x01", None],
    [int_to_bin, (-13, 5), "\x01\x00\x00\x01\x01", None],
    [bin_to_int, ("\x01\x00\x00\x01\x01", False), 19, None],
    [bin_to_int, ("\x01\x00\x00\x01\x01", True), -13, None],
    [swap_bytes, ("aaaabbbbcccc", 4), "ccccbbbbaaaa", None],
    [encode_bin, "ab", "\x00\x01\x01\x00\x00\x00\x00\x01\x00\x01\x01\x00\x00\x00\x01\x00", None],
    [decode_bin, "\x00\x01\x01\x00\x00\x00\x00\x01\x00\x01\x01\x00\x00\x00\x01\x00", "ab", None],
    
    #
    # constructs
    #
    [StaticField("staticfield", 2).parse, "ab", "ab", None],
    [StaticField("staticfield", 2).build, "ab", "ab", None],
    [StaticField("staticfield", 2).parse, "a", None, FieldError],
    [StaticField("staticfield", 2).build, "a", None, FieldError],
    
    [FormatField("formatfield", "<", "L").parse, "\x12\x34\x56\x78", 0x78563412, None],
    [FormatField("formatfield", "<", "L").parse, "\x12\x34\x56", None, FieldError],
    [FormatField("formatfield", "<", "L").build, 0x78563412, "\x12\x34\x56\x78", None],
    [FormatField("formatfield", "<", "L").build, 9e9999, None, FieldError],
    
    [MetaField("metafield", lambda ctx: 3).parse, "abc", "abc", None],
    [MetaField("metafield", lambda ctx: 3).parse, "ab", None, FieldError],
    [MetaField("metafield", lambda ctx: 3).build, "abc", "abc", None],
    [MetaField("metafield", lambda ctx: 3).build, "ab", None, FieldError],
    
    [MetaArray(lambda ctx: 3, UBInt8("metaarray")).parse, "\x01\x02\x03", [1,2,3], None],
    [MetaArray(lambda ctx: 3, UBInt8("metaarray")).parse, "\x01\x02", None, ArrayError],
    [MetaArray(lambda ctx: 3, UBInt8("metaarray")).build, [1,2,3], "\x01\x02\x03", None],
    [MetaArray(lambda ctx: 3, UBInt8("metaarray")).build, [1,2], None, ArrayError],
    
    [Range(3, 5, UBInt8("range")).parse, "\x01\x02\x03", [1,2,3], None],
    [Range(3, 5, UBInt8("range")).parse, "\x01\x02\x03\x04", [1,2,3,4], None],
    [Range(3, 5, UBInt8("range")).parse, "\x01\x02\x03\x04\x05", [1,2,3,4,5], None],
    [Range(3, 5, UBInt8("range")).parse, "\x01\x02", None, RangeError],
    [Range(3, 5, UBInt8("range")).build, [1,2,3], "\x01\x02\x03", None],
    [Range(3, 5, UBInt8("range")).build, [1,2,3,4], "\x01\x02\x03\x04", None],
    [Range(3, 5, UBInt8("range")).build, [1,2,3,4,5], "\x01\x02\x03\x04\x05", None],
    [Range(3, 5, UBInt8("range")).build, [1,2], None, RangeError],
    [Range(3, 5, UBInt8("range")).build, [1,2,3,4,5,6], None, RangeError],
    
    [RepeatUntil(lambda obj, ctx: obj == 9, UBInt8("repeatuntil")).parse, "\x02\x03\x09", [2,3,9], None],
    [RepeatUntil(lambda obj, ctx: obj == 9, UBInt8("repeatuntil")).parse, "\x02\x03\x08", None, ArrayError],
    [RepeatUntil(lambda obj, ctx: obj == 9, UBInt8("repeatuntil")).build, [2,3,9], "\x02\x03\x09", None],
    [RepeatUntil(lambda obj, ctx: obj == 9, UBInt8("repeatuntil")).build, [2,3,8], None, ArrayError],
    
    [Struct("struct", UBInt8("a"), UBInt16("b")).parse, "\x01\x00\x02", Container(a=1,b=2), None],
    [Struct("struct", UBInt8("a"), UBInt16("b"), Struct("foo", UBInt8("c"), UBInt8("d"))).parse, "\x01\x00\x02\x03\x04", Container(a=1,b=2,foo=Container(c=3,d=4)), None],
    [Struct("struct", UBInt8("a"), UBInt16("b"), Embedded(Struct("foo", UBInt8("c"), UBInt8("d")))).parse, "\x01\x00\x02\x03\x04", Container(a=1,b=2,c=3,d=4), None],
    [Struct("struct", UBInt8("a"), UBInt16("b")).build, Container(a=1,b=2), "\x01\x00\x02", None],
    [Struct("struct", UBInt8("a"), UBInt16("b"), Struct("foo", UBInt8("c"), UBInt8("d"))).build, Container(a=1,b=2,foo=Container(c=3,d=4)), "\x01\x00\x02\x03\x04", None],
    [Struct("struct", UBInt8("a"), UBInt16("b"), Embedded(Struct("foo", UBInt8("c"), UBInt8("d")))).build, Container(a=1,b=2,c=3,d=4), "\x01\x00\x02\x03\x04", None],
    
    [Sequence("sequence", UBInt8("a"), UBInt16("b")).parse, "\x01\x00\x02", [1,2], None],
    [Sequence("sequence", UBInt8("a"), UBInt16("b"), Sequence("foo", UBInt8("c"), UBInt8("d"))).parse, "\x01\x00\x02\x03\x04", [1,2,[3,4]], None],
    [Sequence("sequence", UBInt8("a"), UBInt16("b"), Embedded(Sequence("foo", UBInt8("c"), UBInt8("d")))).parse, "\x01\x00\x02\x03\x04", [1,2,3,4], None],
    [Sequence("sequence", UBInt8("a"), UBInt16("b")).build, [1,2], "\x01\x00\x02", None],
    [Sequence("sequence", UBInt8("a"), UBInt16("b"), Sequence("foo", UBInt8("c"), UBInt8("d"))).build, [1,2,[3,4]], "\x01\x00\x02\x03\x04", None],
    [Sequence("sequence", UBInt8("a"), UBInt16("b"), Embedded(Sequence("foo", UBInt8("c"), UBInt8("d")))).build, [1,2,3,4], "\x01\x00\x02\x03\x04", None],
    
    [Switch("switch", lambda ctx: 5, {1:UBInt8("x"), 5:UBInt16("y")}).parse, "\x00\x02", 2, None],
    [Switch("switch", lambda ctx: 6, {1:UBInt8("x"), 5:UBInt16("y")}).parse, "\x00\x02", None, SwitchError],
    [Switch("switch", lambda ctx: 6, {1:UBInt8("x"), 5:UBInt16("y")}, default = UBInt8("x")).parse, "\x00\x02", 0, None],
    [Switch("switch", lambda ctx: 5, {1:UBInt8("x"), 5:UBInt16("y")}, include_key = True).parse, "\x00\x02", (5, 2), None],
    [Switch("switch", lambda ctx: 5, {1:UBInt8("x"), 5:UBInt16("y")}).build, 2, "\x00\x02", None],
    [Switch("switch", lambda ctx: 6, {1:UBInt8("x"), 5:UBInt16("y")}).build, 9, None, SwitchError],
    [Switch("switch", lambda ctx: 6, {1:UBInt8("x"), 5:UBInt16("y")}, default = UBInt8("x")).build, 9, "\x09", None],
    [Switch("switch", lambda ctx: 5, {1:UBInt8("x"), 5:UBInt16("y")}, include_key = True).build, ((5, 2),), "\x00\x02", None],
    [Switch("switch", lambda ctx: 5, {1:UBInt8("x"), 5:UBInt16("y")}, include_key = True).build, ((89, 2),), None, SwitchError],
    
    [Select("select", UBInt32("a"), UBInt16("b"), UBInt8("c")).parse, "\x07", 7, None],
    [Select("select", UBInt32("a"), UBInt16("b")).parse, "\x07", None, SelectError],
    [Select("select", UBInt32("a"), UBInt16("b"), UBInt8("c"), include_name = True).parse, "\x07", ("c", 7), None],
    [Select("select", UBInt32("a"), UBInt16("b"), UBInt8("c")).build, 7, "\x00\x00\x00\x07", None],
    [Select("select", UBInt32("a"), UBInt16("b"), UBInt8("c"), include_name = True).build, (("c", 7),), "\x07", None],
    [Select("select", UBInt32("a"), UBInt16("b"), UBInt8("c"), include_name = True).build, (("d", 7),), None, SelectError],
    
    [Peek(UBInt8("peek")).parse, "\x01", 1, None],
    [Peek(UBInt8("peek")).parse, "", None, None],
    [Peek(UBInt8("peek")).build, 1, "", None],
    [Peek(UBInt8("peek"), perform_build = True).build, 1, "\x01", None],
    [Struct("peek", Peek(UBInt8("a")), UBInt16("b")).parse, "\x01\x02", Container(a=1,b=0x102), None],
    [Struct("peek", Peek(UBInt8("a")), UBInt16("b")).build, Container(a=1,b=0x102), "\x01\x02", None],
    
    [Value("value", lambda ctx: "moo").parse, "", "moo", None],
    [Value("value", lambda ctx: "moo").build, None, "", None],
    
    [Anchor("anchor").parse, "", 0, None],
    [Anchor("anchor").build, None, "", None],
    
    [LazyBound("lazybound", lambda: UBInt8("foo")).parse, "\x02", 2, None],
    [LazyBound("lazybound", lambda: UBInt8("foo")).build, 2, "\x02", None],
    
    [Pass.parse, "", None, None],
    [Pass.build, None, "", None],

    [Terminator.parse, "", None, None],
    [Terminator.parse, "x", None, TerminatorError],
    [Terminator.build, None, "", None],
    
    [Pointer(lambda ctx: 2, UBInt8("pointer")).parse, "\x00\x00\x07", 7, None],
    [Pointer(lambda ctx: 2, UBInt8("pointer")).build, 7, "\x00\x00\x07", None],
    
    [OnDemand(UBInt8("ondemand")).parse("\x08").read, (), 8, None],
    [Struct("ondemand", UBInt8("a"), OnDemand(UBInt8("b")), UBInt8("c")).parse, 
        "\x07\x08\x09", Container(a=7,b=LazyContainer(None, None, None, None),c=9), None],
    [Struct("ondemand", UBInt8("a"), OnDemand(UBInt8("b"), advance_stream = False), UBInt8("c")).parse, 
        "\x07\x09", Container(a=7,b=LazyContainer(None, None, None, None),c=9), None],
    
    [OnDemand(UBInt8("ondemand")).build, 8, "\x08", None],
    [Struct("ondemand", UBInt8("a"), OnDemand(UBInt8("b")), UBInt8("c")).build, 
        Container(a=7,b=8,c=9), "\x07\x08\x09", None],
    [Struct("ondemand", UBInt8("a"), OnDemand(UBInt8("b"), force_build = False), UBInt8("c")).build, 
        Container(a=7,b=LazyContainer(None, None, None, None),c=9), "\x07\x00\x09", None],
    [Struct("ondemand", UBInt8("a"), OnDemand(UBInt8("b"), force_build = False, advance_stream = False), UBInt8("c")).build, 
        Container(a=7,b=LazyContainer(None, None, None, None),c=9), "\x07\x09", None],
    
    [Struct("reconfig", Reconfig("foo", UBInt8("bar"))).parse, "\x01", Container(foo=1), None],
    [Struct("reconfig", Reconfig("foo", UBInt8("bar"))).build, Container(foo=1), "\x01", None],
    
    [Buffered(UBInt8("buffered"), lambda x:x, lambda x:x, lambda x:x).parse, 
        "\x07", 7, None],
    [Buffered(GreedyRange(UBInt8("buffered")), lambda x:x, lambda x:x, lambda x:x).parse, 
        "\x07", None, SizeofError],
    [Buffered(UBInt8("buffered"), lambda x:x, lambda x:x, lambda x:x).build, 
        7, "\x07", None],
    [Buffered(GreedyRange(UBInt8("buffered")), lambda x:x, lambda x:x, lambda x:x).build, 
        [7], None, SizeofError],
    
    [Restream(UBInt8("restream"), lambda x:x, lambda x:x, lambda x:x).parse,
        "\x07", 7, None],
    [Restream(GreedyRepeater(UBInt8("restream")), lambda x:x, lambda x:x, lambda x:x).parse,
        "\x07", [7], None],
    [Restream(UBInt8("restream"), lambda x:x, lambda x:x, lambda x:x).parse,
        "\x07", 7, None],
    [Restream(GreedyRepeater(UBInt8("restream")), lambda x:x, lambda x:x, lambda x:x).parse,
        "\x07", [7], None],
    
    #
    # adapters
    #
    [BitIntegerAdapter(Field("bitintegeradapter", 8), 8).parse, "\x01" * 8, 255, None],
    [BitIntegerAdapter(Field("bitintegeradapter", 8), 8, signed = True).parse, "\x01" * 8, -1, None],
    [BitIntegerAdapter(Field("bitintegeradapter", 8), 8, swapped = True, bytesize = 4).parse, 
        "\x01" * 4 + "\x00" * 4, 0x0f, None],
    [BitIntegerAdapter(Field("bitintegeradapter", 8), 8).build, 255, "\x01" * 8, None],
    [BitIntegerAdapter(Field("bitintegeradapter", 8), 8).build, -1, None, BitIntegerError],
    [BitIntegerAdapter(Field("bitintegeradapter", 8), 8, signed = True).build, -1, "\x01" * 8, None],
    [BitIntegerAdapter(Field("bitintegeradapter", 8), 8, swapped = True, bytesize = 4).build, 
        0x0f, "\x01" * 4 + "\x00" * 4, None],
    
    [MappingAdapter(UBInt8("mappingadapter"), {2:"x",3:"y"}, {"x":2,"y":3}).parse,
        "\x03", "y", None],
    [MappingAdapter(UBInt8("mappingadapter"), {2:"x",3:"y"}, {"x":2,"y":3}).parse,
        "\x04", None, MappingError],
    [MappingAdapter(UBInt8("mappingadapter"), {2:"x",3:"y"}, {"x":2,"y":3}, decdefault="foo").parse,
        "\x04", "foo", None],
    [MappingAdapter(UBInt8("mappingadapter"), {2:"x",3:"y"}, {"x":2,"y":3}, decdefault=Pass).parse,
        "\x04", 4, None],
    [MappingAdapter(UBInt8("mappingadapter"), {2:"x",3:"y"}, {"x":2,"y":3}).build,
        "y", "\x03", None],
    [MappingAdapter(UBInt8("mappingadapter"), {2:"x",3:"y"}, {"x":2,"y":3}).build,
        "z", None, MappingError],
    [MappingAdapter(UBInt8("mappingadapter"), {2:"x",3:"y"}, {"x":2,"y":3}, encdefault=17).build,
        "foo", "\x11", None],
    [MappingAdapter(UBInt8("mappingadapter"), {2:"x",3:"y"}, {"x":2,"y":3}, encdefault=Pass).build,
        4, "\x04", None],
        
    [FlagsAdapter(UBInt8("flagsadapter"), {"a":1,"b":2,"c":4,"d":8,"e":16,"f":32,"g":64,"h":128}).parse, 
        "\x81", Container(a=True, b=False,c=False,d=False,e=False,f=False,g=False,h=True), None],
    [FlagsAdapter(UBInt8("flagsadapter"), {"a":1,"b":2,"c":4,"d":8,"e":16,"f":32,"g":64,"h":128}).build, 
        Container(a=True, b=False,c=False,d=False,e=False,f=False,g=False,h=True), "\x81", None],
    
    [IndexingAdapter(Array(3, UBInt8("indexingadapter")), 2).parse, "\x11\x22\x33", 0x33, None],
    [IndexingAdapter(Array(3, UBInt8("indexingadapter")), 2)._encode, (0x33, {}), [None, None, 0x33], None],
    
    [SlicingAdapter(Array(3, UBInt8("indexingadapter")), 1, 3).parse, "\x11\x22\x33", [0x22, 0x33], None],
    [SlicingAdapter(Array(3, UBInt8("indexingadapter")), 1, 3)._encode, ([0x22, 0x33], {}), [None, 0x22, 0x33], None],
    
    [PaddingAdapter(Field("paddingadapter", 4)).parse, "abcd", "abcd", None],
    [PaddingAdapter(Field("paddingadapter", 4), strict = True).parse, "abcd", None, PaddingError],
    [PaddingAdapter(Field("paddingadapter", 4), strict = True).parse, "\x00\x00\x00\x00", "\x00\x00\x00\x00", None],
    [PaddingAdapter(Field("paddingadapter", 4)).build, "abcd", "\x00\x00\x00\x00", None],
    
    [LengthValueAdapter(Sequence("lengthvalueadapter", UBInt8("length"), Field("value", lambda ctx: ctx.length))).parse,
        "\x05abcde", "abcde", None],
    [LengthValueAdapter(Sequence("lengthvalueadapter", UBInt8("length"), Field("value", lambda ctx: ctx.length))).build,
        "abcde", "\x05abcde", None],
        
    [TunnelAdapter(PascalString("data", encoding = "zlib"), GreedyRange(UBInt16("elements"))).parse, 
        "\rx\x9cc`f\x18\x16\x10\x00u\xf8\x01-", [3] * 100, None],
    [TunnelAdapter(PascalString("data", encoding = "zlib"), GreedyRange(UBInt16("elements"))).build, 
        [3] * 100, "\rx\x9cc`f\x18\x16\x10\x00u\xf8\x01-", None],
    
    [Const(Field("const", 2), "MZ").parse, "MZ", "MZ", None],
    [Const(Field("const", 2), "MZ").parse, "MS", None, ConstError],
    [Const(Field("const", 2), "MZ").build, "MZ", "MZ", None],
    [Const(Field("const", 2), "MZ").build, "MS", None, ConstError],
    [Const(Field("const", 2), "MZ").build, None, "MZ", None],
    
    [ExprAdapter(UBInt8("expradapter"), 
        encoder = lambda obj, ctx: obj / 7, 
        decoder = lambda obj, ctx: obj * 7).parse, 
        "\x06", 42, None],
    [ExprAdapter(UBInt8("expradapter"), 
        encoder = lambda obj, ctx: obj / 7, 
        decoder = lambda obj, ctx: obj * 7).build, 
        42, "\x06", None],
    
    [HexDumpAdapter(Field("hexdumpadapter", 6)).parse, "abcdef", "abcdef", None],
    [HexDumpAdapter(Field("hexdumpadapter", 6)).parse("abcdef").__pretty_str__, 
        (),  "\n    0000   61 62 63 64 65 66                                 abcdef", 
        None],
    [HexDumpAdapter(Field("hexdumpadapter", 6)).build, "abcdef", "abcdef", None],
    
    [OneOf(UBInt8("oneof"), [7,8,9]).parse, "\x08", 8, None],
    [OneOf(UBInt8("oneof"), [7,8,9]).parse, "\x06", None, ValidationError],
    [OneOf(UBInt8("oneof"), [7,8,9]).build, 8, "\x08", None],
    [OneOf(UBInt8("oneof"), [7,8,9]).build, 6, None, ValidationError],
    
    [NoneOf(UBInt8("noneof"), [7,8,9]).parse, "\x06", 6, None],
    [NoneOf(UBInt8("noneof"), [7,8,9]).parse, "\x08", None, ValidationError],
    [NoneOf(UBInt8("noneof"), [7,8,9]).build, 6, "\x06", None],
    [NoneOf(UBInt8("noneof"), [7,8,9]).build, 8, None, ValidationError],
    
    #
    # text
    #
    [QuotedString("foo", start_quote = "{", end_quote = "}", esc_char = "-").parse,
        "{hello-} world}", "hello} world", None],
    [QuotedString("foo", start_quote = "{", end_quote = "}", esc_char = None).parse,
        "{hello-} world}", "hello-", None],
    [QuotedString("foo", start_quote = "{", end_quote = "}", esc_char = None, allow_eof = True).parse,
        "{hello world", "hello world", None],
    [QuotedString("foo", start_quote = "{", end_quote = "}", esc_char = None, allow_eof = False).parse,
        "{hello world", None, FieldError],
    [QuotedString("foo", start_quote = "{", end_quote = "}", esc_char = "-").build,
        "hello} world", "{hello-} world}", None],
    [QuotedString("foo", start_quote = "{", end_quote = "}", esc_char = None).build,
        "hello}", None, QuotedStringError],
    
    [Whitespace().parse, "  \t\t ", None, None],
    [Whitespace(optional = False).parse, "X", None, RangeError],
    [Whitespace().build, None, " ", None],
    
    [Identifier("identifier").parse, "ab_c8 XXX", "ab_c8", None],
    [Identifier("identifier").parse, "_c8 XXX", "_c8", None],
    [Identifier("identifier").parse, "2c8 XXX", None, ValidationError],
    [Identifier("identifier").build, "ab_c8", "ab_c8", None],
    [Identifier("identifier").build, "_c8", "_c8", None],
    [Identifier("identifier").build, "2c8", None, ValidationError],
    
    [TextualIntAdapter(Field("textintadapter", 3)).parse, "234", 234, None],
    [TextualIntAdapter(Field("textintadapter", 3), radix = 16).parse, "234", 0x234, None],
    [TextualIntAdapter(Field("textintadapter", 3)).build, 234, "234", None],
    [TextualIntAdapter(Field("textintadapter", 3), radix = 16).build, 0x234, "234", None],
    # [TextualIntAdapter(Field("textintadapter", 3)).build, 23, "023", None],
    
    [StringUpto("stringupto", "XY").parse, "helloX", "hello", None],
    [StringUpto("stringupto", "XY").parse, "helloY", "hello", None],
    [StringUpto("stringupto", "XY").build, "helloX", "hello", None],
    
    #
    # macros
    #
    [Aligned(UBInt8("aligned")).parse, "\x01\x00\x00\x00", 1, None],
    [Aligned(UBInt8("aligned")).build, 1, "\x01\x00\x00\x00", None],
    [Struct("aligned", Aligned(UBInt8("a")), UBInt8("b")).parse, 
        "\x01\x00\x00\x00\x02", Container(a=1,b=2), None],
    [Struct("aligned", Aligned(UBInt8("a")), UBInt8("b")).build, 
        Container(a=1,b=2), "\x01\x00\x00\x00\x02", None],
    
    [Bitwise(Field("bitwise", 8)).parse, "\xff", "\x01" * 8, None],
    [Bitwise(Field("bitwise", lambda ctx: 8)).parse, "\xff", "\x01" * 8, None],
    [Bitwise(Field("bitwise", 8)).build, "\x01" * 8, "\xff", None],
    [Bitwise(Field("bitwise", lambda ctx: 8)).build, "\x01" * 8, "\xff", None],
    
    [Union("union", 
        UBInt32("a"), 
        Struct("b", UBInt16("a"), UBInt16("b")), 
        BitStruct("c", Padding(4), Octet("a"), Padding(4)), 
        Struct("d", UBInt8("a"), UBInt8("b"), UBInt8("c"), UBInt8("d")),
        Embedded(Struct("q", UBInt8("e"))),
        ).parse,
        "\x11\x22\x33\x44",
        Container(a=0x11223344, 
            b=Container(a=0x1122, b=0x3344), 
            c=Container(a=0x12),
            d=Container(a=0x11, b=0x22, c=0x33, d=0x44),
            e=0x11,
        ),
        None],
    [Union("union", 
        UBInt32("a"), 
        Struct("b", UBInt16("a"), UBInt16("b")), 
        BitStruct("c", Padding(4), Octet("a"), Padding(4)), 
        Struct("d", UBInt8("a"), UBInt8("b"), UBInt8("c"), UBInt8("d")), 
        Embedded(Struct("q", UBInt8("e"))),
        ).build,
        Container(a=0x11223344, 
            b=Container(a=0x1122, b=0x3344), 
            c=Container(a=0x12),
            d=Container(a=0x11, b=0x22, c=0x33, d=0x44),
            e=0x11,
        ),
        "\x11\x22\x33\x44",
        None],
    
    [Flag("flag").parse, "\x01", True, None],
    [Flag("flag", truth = 0, falsehood = 1).parse, "\x00", True, None],
    [Flag("flag").build, True, "\x01", None],
    [Flag("flag", truth = 0, falsehood = 1).build, True, "\x00", None],
    
    [Enum(UBInt8("enum"),q=3,r=4,t=5).parse, "\x04", "r", None],
    [Enum(UBInt8("enum"),q=3,r=4,t=5).parse, "\x07", None, MappingError],
    [Enum(UBInt8("enum"),q=3,r=4,t=5, _default_ = "spam").parse, "\x07", "spam", None],
    [Enum(UBInt8("enum"),q=3,r=4,t=5, _default_ =Pass).parse, "\x07", 7, None],
    [Enum(UBInt8("enum"),q=3,r=4,t=5).build, "r", "\x04", None],
    [Enum(UBInt8("enum"),q=3,r=4,t=5).build, "spam", None, MappingError],
    [Enum(UBInt8("enum"),q=3,r=4,t=5, _default_ = 9).build, "spam", "\x09", None],
    [Enum(UBInt8("enum"),q=3,r=4,t=5, _default_ =Pass).build, 9, "\x09", None],
    
    [String("string", 6).parse, "hellow", "hellow", None],
    [String("string", 8, encoding = "utf8").parse, "hello\xe1\x88\xb4", u"hello\u1234", None],
    [String("string", 7, padchar = "\x00", paddir = "right").parse, "hello\x00\x00", "hello", None],
    [String("string", 7, padchar = "\x00", paddir = "left").parse, "\x00\x00hello", "hello", None],
    [String("string", 7, padchar = "\x00", paddir = "center").parse, "\x00hello\x00", "hello", None],
    [String("string", 6).build, "hellow", "hellow", None],
    [String("string", 8, encoding = "utf8").build, u"hello\u1234", "hello\xe1\x88\xb4", None],
    [String("string", 7, padchar = "\x00", paddir = "right").build, "hello", "hello\x00\x00", None],
    [String("string", 7, padchar = "\x00", paddir = "left").build, "hello", "\x00\x00hello", None],
    [String("string", 7, padchar = "\x00", paddir = "center").build, "hello", "\x00hello\x00", None],
    
    [PascalString("pascalstring").parse, "\x05helloXXX", "hello", None],
    [PascalString("pascalstring").build, "hello", "\x05hello", None],
    
    [CString("cstring").parse, "hello\x00", "hello", None],
    [CString("cstring").build, "hello", "hello\x00", None],
    
    [PrefixedArray(UBInt8("array"), UBInt8("count")).parse, "\x03\x01\x01\x01", [1,1,1], None],
    [PrefixedArray(UBInt8("array"), UBInt8("count")).parse, "\x03\x01\x01", None, ArrayError],
    [PrefixedArray(UBInt8("array"), UBInt8("count")).build, [1,1,1], "\x03\x01\x01\x01", None],
    
    [IfThenElse("ifthenelse", lambda ctx: True, UBInt8("then"), UBInt16("else")).parse, 
        "\x01", 1, None],
    [IfThenElse("ifthenelse", lambda ctx: False, UBInt8("then"), UBInt16("else")).parse, 
        "\x00\x01", 1, None],
    [IfThenElse("ifthenelse", lambda ctx: True, UBInt8("then"), UBInt16("else")).build, 
        1, "\x01", None],
    [IfThenElse("ifthenelse", lambda ctx: False, UBInt8("then"), UBInt16("else")).build, 
        1, "\x00\x01", None],
    
    [Magic("MZ").parse, "MZ", "MZ", None],
    [Magic("MZ").parse, "ELF", None, ConstError],
    [Magic("MZ").build, None, "MZ", None],
]


def run_tests(tests):
    errors = []
    for func, args, res, exctype in tests:
        if type(args) is not tuple:
            args = (args,)
        try:
            r = func(*args)
        except:
            t, ex, tb = sys.exc_info()
            if exctype is None:
                errors.append("[%s]: unexpected exception %r" % (func, ex))
                continue
            if t is not exctype:
                errors.append("[%s]: raised %r, expected %r" % (func, t, exctype))
                continue
        else:
            if exctype is not None:
                errors.append("[%s]: expected exception %r" % (func, exctype))
                continue
            if r != res:
                errors.append("[%s]: returned %r, expected %r" % (func, r, res))
                continue
    return errors


def run_all():
    errors = run_tests(tests)
    if not errors:
        print "success"
    else:
        print "errors:"
        for e in errors:
            print "   ", e

if __name__ == "__main__":
    run_all()


