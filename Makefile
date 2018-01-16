#
# Simple Makefile to build and install the wheel
# Ralph Schmieder, rschmied@cisco.com 2018
#

PYTHON := python3
WHEEL  := dist/.built

.PHONY: all clean wheel
all: $(WHEEL)

check-env:
ifndef VIRTUAL_ENV
	$(error venv undefined)
endif

SOURCES := ${shell find virltester -name '*.py'}

$(WHEEL): $(SOURCES) | check-env
	@echo "### building wheel"
	$(PYTHON) setup.py bdist_wheel --universal && touch $(WHEEL)

wheel: $(WHEEL)

clean:
	@echo "### cleaning up"
	find . -name '*.egg-info' -maxdepth 1 -exec rm -rf {} \;
	find . -name 'build' -maxdepth 1 -exec rm -rf {} \;
	rm -f dist/*.whl $(WHEEL)

install: $(WHEEL)
	@echo "### installing the latest wheel"
	$(eval TMP := ${shell ls -t dist/*.whl | head -1})
	$(PYTHON) -mpip install --upgrade $(TMP)
