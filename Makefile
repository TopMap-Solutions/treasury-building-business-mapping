PLUGIN=treasury_mapper
VERSION=0.2.3
DIST=dist/$(PLUGIN)-$(VERSION).zip

.PHONY: test test-core test-qgis package clean

test: test-core test-qgis

test-core:
	python3 -m unittest discover -s tests/unit -v

test-qgis:
	mkdir -p /tmp/treasury-qgis-config
	QT_QPA_PLATFORM=offscreen XDG_CONFIG_HOME=/tmp/treasury-qgis-config python3 -m unittest discover -s tests/qgis -v

package: test
	mkdir -p dist
	rm -f dist/$(PLUGIN)-*.zip
	zip -rq $(DIST) $(PLUGIN) -x '*/__pycache__/*' '*.pyc'

clean:
	rm -rf dist
