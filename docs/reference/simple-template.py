#!/usr/bin/python

class Template:
    def __init__(self, replacements):
        import re

        self.__replacements__ = replacements
        self.__template__ = re.compile(r'<<([a-z]+?):(.+?)>>')

    def process_string(self, s):
        return self.__template__.sub(self.process_command, s)

    def process_command(self, match):
        command = match.group(1)
        argument = match.group(2)
        if (command == "const"):
            return (self.__replacements__[argument]
                    if argument in self.__replacements__ else "")
        elif (command == "file"):
            return self.process_string(open(argument, "rb").read().strip())
        else:
            print >>sys.stderr,"*** Unknown command \"%s\"" % (command)
            sys.exit(1)


if (__name__ == "__main__"):
    import sys
    import optparse

    parser = optparse.OptionParser()

    parser.add_option("-D",
                      action="append",
                      dest="const",
                      help="constant definition")

    (options, args) = parser.parse_args()

    template = Template(dict([arg.split("=", 1) for arg in options.const])
                        if options.const is not None else {})
    sys.stdout.write(template.process_string(open(args[0], "rb").read()))
