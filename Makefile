export PYTHON = python

all:
	$(PYTHON) setup.py build

install:
	$(PYTHON) setup.py install
	cd docs && $(MAKE) install

clean:
	rm -rfv build
	rm -fv audiotools/*.pyc
	cd docs && $(MAKE) clean
	cd pyconstruct && $(MAKE) clean

distclean: clean
	cd docs && $(MAKE) distclean

construct:
	cd pyconstruct && $(MAKE)

construct_install:
	cd pyconstruct && $(MAKE) install

