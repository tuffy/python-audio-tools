from container import Container


def drill(obj, root = "", levels = -1):
    if levels == 0:
        yield root, obj
        return
    levels -= 1
    if isinstance(obj, Container):
        for k, v in obj:
            r = "%s.%s" % (root, k)
            if levels:
                for r2, v2 in drill(v, r, levels):
                    yield r2, v2
            else:
                yield r, v
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            r = "%s[%d]" % (root, i)
            if levels:
                for r2, v2 in drill(item, r, levels):
                    yield r2, v2
            else:
                yield r, item
    else:
        yield root, obj


if __name__ == "__main__":
    from construct import *
    
    c = Struct("foo",
        Byte("a"),
        Struct("b",
            Byte("c"),
            UBInt16("d"),
        ),
        Byte("e"),
        Array(4,
            Struct("f", 
                Byte("x"),
                Byte("y"),
            ),
        ),
        Byte("g"),
    )
    o = c.parse("acddexyxyxyxyg")
    
    for lvl in range(4):
        for path, value in drill(o, levels = lvl):
            print path, value
        print "---"
    
    output = """ 
     Container:
        a = 97
        b = Container:
            c = 99
            d = 25700
        e = 101
        f = [
            Container:
                x = 120
                y = 121
            Container:
                x = 120
                y = 121
            Container:
                x = 120
                y = 121
            Container:
                x = 120
                y = 121
        ]
        g = 103
    ---
    .a 97
    .b Container:
        c = 99
        d = 25700
    .e 101
    .f [
        Container:
            x = 120
            y = 121
        Container:
            x = 120
            y = 121
        Container:
            x = 120
            y = 121
        Container:
            x = 120
            y = 121
    ]
    .g 103
    ---
    .a 97
    .b.c 99
    .b.d 25700
    .e 101
    .f[0] Container:
        x = 120
        y = 121
    .f[1] Container:
        x = 120
        y = 121
    .f[2] Container:
        x = 120
        y = 121
    .f[3] Container:
        x = 120
        y = 121
    .g 103
    ---
    .a 97
    .b.c 99
    .b.d 25700
    .e 101
    .f[0].x 120
    .f[0].y 121
    .f[1].x 120
    .f[1].y 121
    .f[2].x 120
    .f[2].y 121
    .f[3].x 120
    .f[3].y 121
    .g 103
    ---
    """





















