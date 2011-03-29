import os


basepath = os.path.abspath("..")

def scan(path, failures):
    if os.path.isdir(path):
        for subpath in os.listdir(path):
            scan(os.path.join(path, subpath), failures)
    elif os.path.isfile(path) and path.endswith(".py"):
        dirname, name = os.path.split(path)
        os.chdir(dirname)
        errorcode = os.system("python %s > %s 2> %s" % (name, os.devnull, os.devnull))
        if errorcode != 0:
            failures.append((path, errorcode))

failures = []
print "testing packages"

scan(os.path.join(basepath, "formats"), failures)
scan(os.path.join(basepath, "protocols"), failures)

if not failures:
    print "success"
else:
    print "%d errors:" % (len(failures),)
    for fn, ec in failures:
        print "     %s" % (fn,)


