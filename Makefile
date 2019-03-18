
# Get package version from setup.py:VERSION
VERSION=$(shell python3 -c \
'import setup; \
print(setup.VERSION); \
')

.PHONY: clean

wheel:
	python3 setup.py bdist_wheel


test:
	pytest -v tests


docker-build: wheel
	python3 setup.py bdist_wheel
	docker build -t "solitude:$(VERSION)-dev" .
	@echo Docker image built!
	@echo Run tests: docker run --rm -it "solitude:$(VERSION)-dev" pytest -v tests


clean:
	rm -rf dist
	rm -rf build
