# The same steps CI runs, for use on your own machine.
#
#   conda activate fenicsx-0.11
#   make kernel     once, so the notebooks find this environment
#   make test

NOTEBOOKS := $(wildcard linear-elasticity/*.ipynb)

.PHONY: kernel test run check clean

kernel:
	python -m ipykernel install --user --name fenicsx-0.11 --display-name "FEniCSx 0.11"

test: run check

run:
	jupyter nbconvert --to notebook --execute --output-dir executed $(NOTEBOOKS)

check:
	python tools/check_notebooks.py executed/*.ipynb

clean:
	rm -rf executed linear-elasticity/.ipynb_checkpoints utils/__pycache__
	find linear-elasticity/output -type f ! -name .gitkeep -delete
