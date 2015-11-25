# which Python interpreter to use
PYTHON = python

# which Python test coverage utility to use
COVERAGE = coverage

all:
	$(PYTHON) setup.py build

install:
	$(PYTHON) setup.py install
	cd docs && $(MAKE) install

probe:
	$(PYTHON) setup.py build_ext --dry-run

check:
	cd test && $(PYTHON) test.py

check_coverage:
	cd test && $(COVERAGE) run test.py

coverage_report:
	cd test && $(COVERAGE) report -m

clean:
	rm -rfv build
	rm -fv audiotools/*.pyc

distclean: clean
	cd docs && $(MAKE) clean
