all: clean format sdist
	ls -lah dist

wheel:
	pipx run build --wheel .

whl_file = $(shell ls dist/*.whl)

install: clean wheel
	pip3 install $(whl_file) --user

format:
	pre-commit run --all-files

clean:
	rm -rf build
	rm -rf *.egg-info
	rm -rf dist
	pip3 uninstall sgr-agent-core UNKNOWN -y
