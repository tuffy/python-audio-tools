# which Python interpreter to use
PYTHON = python

# which Python test coverage utility to use
COVERAGE = coverage

all: .FORCE
	$(PYTHON) setup.py build

install: .FORCE
	$(PYTHON) setup.py install
	cd docs && $(MAKE) install

probe: .FORCE
	$(PYTHON) setup.py build_ext --dry-run

check: .FORCE
	cd test && $(PYTHON) test.py

check_coverage: .FORCE
	cd test && $(COVERAGE) run test.py

coverage_report: .FORCE
	cd test && $(COVERAGE) report -m

clean: .FORCE
	rm -rfv build
	rm -fv audiotools/*.pyc

distclean: clean
	cd docs && $(MAKE) clean

.FORCE:

