# The same steps CI runs, for use on your own machine.
#
#   conda activate fenicsx-0.11
#   make test

NOTEBOOKS := $(wildcard linear-elasticity/*.ipynb)

.PHONY: test run check clean

test: run check

run:
	jupyter nbconvert --to notebook --execute --output-dir executed $(NOTEBOOKS)

check:
	python tools/check_notebooks.py executed/*.ipynb

clean:
	rm -rf executed linear-elasticity/.ipynb_checkpoints
	find linear-elasticity/output -type f ! -name .gitkeep -delete
