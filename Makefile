# The same steps CI runs, for use on your own machine.
#
#   conda activate fenicsx-0.11
#   make kernel     once, so the notebooks find this environment
#   make test
#
# The online environment, Codespaces and Binder alike, is the image built by
#
#   make image      the environment of the installation instructions
#   make binder     that image plus the repository, as mybinder.org builds it
#
# both of which need docker and neither of which needs the conda environment.

NOTEBOOKS := $(wildcard linear-elasticity/*.ipynb)

IMAGE := ghcr.io/cmaurini/m2-fracture-2026:env-0.11

.PHONY: kernel test run check image binder clean

kernel:
	python -m ipykernel install --user --name fenicsx-0.11 --display-name "FEniCSx 0.11"

test: run check

run:
	jupyter nbconvert --to notebook --execute --output-dir executed $(NOTEBOOKS)

check:
	python tools/check_notebooks.py executed/*.ipynb

image:
	docker build -f docker/Dockerfile -t $(IMAGE) .
	docker run --rm -v "$(PWD):/work" -w /work $(IMAGE) python tools/check_environment.py

# --memory=2g is what a mybinder.org session gets, and --user-id 1000 is the
# uid it builds with: left to itself repo2docker takes the uid of whoever runs
# it, and a uid clash in the image would go unseen here.
binder: image
	jupyter-repo2docker --no-run --user-id 1000 --user-name jovyan \
	  --image-name m2fr-binder .
	docker run --rm --memory=2g m2fr-binder \
	  bash -c "jupyter nbconvert --to notebook --execute --output-dir executed $(NOTEBOOKS) \
	           && python tools/check_notebooks.py executed/*.ipynb"

clean:
	rm -rf executed linear-elasticity/.ipynb_checkpoints utils/__pycache__
	find linear-elasticity/output -type f ! -name .gitkeep -delete
