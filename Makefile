PROJECT_VERSION=$(shell python setup.py --version)

run:
	python -m seiko_converter -i "./data/seiko_qt2100_A10S_timestamped.raw" -g --csv -d
	python -m seiko_converter -i "./data/seiko_qt2100_A10S.raw" -g --csv -d
	python -m seiko_converter -i "./data/seiko_qt2100_B1S_1.raw" -g --csv -d
	python -m seiko_converter -i "./data/seiko_qt2100_B1S_2.raw" -g --csv -d
	#python -m seiko_converter -i "./data/seiko_qt2100_999999.raw" -g --csv -d

clean:
	@rm *.csv *.pdf

# Tests
tests:
	pytest tests

coverage:
	pytest --cov=seiko_converter --cov-report term-missing -vv
	@-coverage-badge -f -o images/coverage.svg

docstring_coverage:
	interrogate -v seiko_converter/ \
	    -e seiko_converter/__init__.py \
	    --badge-style flat --generate-badge images/

# development & release cycle
fullrelease:
	fullrelease

install:
	@# Replacement for python setup.py develop which doesn't support extra_require keyword.
	@# Install a project in editable mode.
	pip install -e .[dev]

uninstall:
	pip seiko_converter uninstall

sdist:
	@echo Building the distribution package...
	python setup.py sdist

upload: clean sdist
	python setup.py bdist_wheel
	twine upload dist/* -r pypi

check_setups:
	pyroma .

check_code:
	prospector seiko_converter/
	check-manifest

archive:
	# Create upstream src archive
	git archive HEAD --prefix='seiko-converter-$(PROJECT_VERSION).orig/' | gzip > ../seiko-converter-$(PROJECT_VERSION).orig.tar.gz
