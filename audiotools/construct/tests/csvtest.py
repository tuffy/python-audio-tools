from construct import *
from construct.text import *


class LineSplitAdapter(Adapter):
   def _decode(self, obj, context):
       return obj.split('\t')
   def _encode(self, obj, context):
       return '\t'.join(obj)+'\n'

sectionrow = Struct('sectionrow',
    QuotedString('sectionname', start_quote='[', end_quote=']'),
    Line('restofline'),
    Literal('\n'),
)

fieldsrow = Struct('fieldsrow',
    Literal('FIELDS\t'),
    LineSplitAdapter(
        Line('items')
    ),
    Literal('\n'),
)

data = Struct('data',
    OptionalGreedyRange(
        Struct('data',
            Literal('DATA\t'),
            LineSplitAdapter(
                Line('items')
            ),
            Literal('\n'),
        )
    )
)

section = Struct('section',
    sectionrow,
    fieldsrow,
    data,
    Literal('\n')
)

sections = Struct('sections',
    GreedyRange(section)
)


if __name__ == "__main__":
    import psyco
    psyco.full()
    numdatarows = 2000
    
    tsvstring = (
    '[ENGINEBAY]'+'\t'*80 + '\n' + 
    'FIELDS'+('\tTIMESTAMP\tVOLTAGE\tCURRENT\tTEMPERATURE'*20) + '\n' + 
    ('DATA'+('\t12:13:14.15\t1.2345\t2.3456\t345.67'*20) +
    '\n')*numdatarows + '\n' + 
    '[CARGOBAY]'+'\t'*80 + '\n' + 
    'FIELDS'+('\tTIMESTAMP\tVOLTAGE\tCURRENT\tTEMPERATURE'*20) + '\n' + 
    ('DATA'+('\t12:13:14.15\t1.2345\t2.3456\t345.67'*20) +
    '\n')*numdatarows + '\n' + 
    '[FRONTWHEELWELL]'+'\t'*80 + '\n' + 
    'FIELDS'+('\tTIMESTAMP\tVOLTAGE\tCURRENT\tTEMPERATURE'*20) + '\n' + 
    ('DATA'+('\t12:13:14.15\t1.2345\t2.3456\t345.67'*20) +
    '\n')*numdatarows + '\n' + 
    '[REARWHEELWELL]'+'\t'*80 + '\n' + 
    'FIELDS'+('\tTIMESTAMP\tVOLTAGE\tCURRENT\tTEMPERATURE'*20) + '\n' +
    ('DATA'+('\t12:13:14.15\t1.2345\t2.3456\t345.67'*20) + '\n') * numdatarows + '\n'
    )
    
    #print len(tsvstring)
    
    import time
    t = time.time()
    x = sections.parse(tsvstring)
    print time.time() - t
    # 43.2030000687 / 3.10899996758 with psyco (x13)
    
    t = time.time()
    s = sections.build(x)
    print time.time() - t
    # 39.625 / 2.65700006485 with psyco (x14)
    
    print s == tsvstring
    # True









