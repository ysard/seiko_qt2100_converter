PROJECT_VERSION=$(shell python setup.py --version)
PACKAGE_NAME=seiko_converter

run:
	python -m $(PACKAGE_NAME) -i "./test_data/seiko_qt2100_A10S_timestamped.raw" -g --csv -d
	python -m $(PACKAGE_NAME) -i "./test_data/seiko_qt2100_A10S.raw" -g --csv -d
	python -m $(PACKAGE_NAME) -i "./test_data/seiko_qt2100_B1S_1.raw" -g --csv -d
	python -m $(PACKAGE_NAME) -i "./test_data/seiko_qt2100_B1S_2.raw" -g --csv -d
	#python -m $(PACKAGE_NAME) -i "./test_data/seiko_qt2100_999999.raw" -g --csv -d

clean:
	@-rm -rf $(PACKAGE_NAME).egg-info/
	@rm *.csv *.pdf

# Tests
tests:
	pytest tests

coverage:
	pytest --cov=$(PACKAGE_NAME) --cov-report term-missing -vv
	@-coverage-badge -f -o images/coverage.svg

docstring_coverage:
	interrogate -v $(PACKAGE_NAME)/ \
	    -e $(PACKAGE_NAME)/__init__.py \
	    --badge-style flat --generate-badge images/

# development & release cycle
fullrelease:
	fullrelease

install:
	@# Replacement for python setup.py develop which doesn't support extra_require keyword.
	@# Install a project in editable mode.
	pip install -e .[dev]

uninstall:
	pip $(PACKAGE_NAME) uninstall

sdist:
	@echo Building the distribution package...
	python setup.py sdist

upload: clean sdist
	python setup.py bdist_wheel
	twine upload dist/* -r pypi

check_setups:
	pyroma .

check_code:
	prospector $(PACKAGE_NAME)/
	check-manifest

archive:
	# Create upstream src archive
	git archive HEAD --prefix='seiko-converter-$(PROJECT_VERSION).orig/' | gzip > ../seiko-converter-$(PROJECT_VERSION).orig.tar.gz

debianize: archive
	dpkg-buildpackage -us -uc -b -d

debcheck:
	lintian -EvIL +pedantic ../seiko-converter_*.deb
