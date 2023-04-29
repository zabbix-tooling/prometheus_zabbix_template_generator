SHELL=/bin/bash

.PHONY: all deps clean prune docker_build docker_inspect docker_publish docker_check run

VERSION = $(shell git describe --abbrev=0 --tags)

FORCE_UPGRADE_MARKER ?= $(shell date "+%Y-%m-%d")

IMAGE_REPO = zabbix-tooling
IMAGE_NAME = prometheus_zabbix_template_generator

scriptDir=${shell case "$$(uname)" in MING*) echo Scripts;; *) echo bin;; esac}
venv = . venv/${scriptDir}/activate
pythonVersion = 3.11
python = python${pythonVersion}

## public

all: deps

deps: ${venv}

${venv}: Makefile pyproject.toml
	@which ${python} >/dev/null 2>&1 || { echo "Missing requirement: ${python}" >&2; exit 1; }
	[ -f venv/${scriptDir}/python ] && venv/${scriptDir}/python --version | cut -d' ' -f2 | grep -q ^${pythonVersion} || ${MAKE} --no-print-directory prune >&2
	${python} -m venv venv || { echo "Missing requirement: ${python}-venv - check ${cliDocumentation} for installation procedure" >&2; exit 1; }
	${venv} && pip3 install --use-pep51 -e .
	touch ${venv}

clean:
	rm -rf __pycache__

prune: clean
	rm -rf venv

docker_build:
	@echo "the FORCE_UPGRADE_MARKER variable forces a upgrade every day, current value is : ${FORCE_UPGRADE_MARKER}"
	docker build --build-arg FORCE_UPGRADE_MARKER="${FORCE_UPGRADE_MARKER}" -t ${IMAGE_NAME}:${VERSION} -f Dockerfile .
	docker images ${IMAGE_NAME}:${VERSION} --format='DOCKER IMAGESIZE: {{.Size}}'


docker_check: 
	docker run -t --network host --hostname "test-manual" \
		${IMAGE_NAME}:${VERSION} make check

docker_publish: docker_build
	@echo "publishing version ${VERSION}"
	docker tag ${IMAGE_NAME}:${VERSION} ${IMAGE_REPO}/${IMAGE_NAME}:${VERSION}
	docker push ${IMAGE_REPO}/${IMAGE_NAME}:${VERSION}
	docker tag ${IMAGE_NAME}:${VERSION} ${IMAGE_REPO}/${IMAGE_NAME}:latest
	docker push ${IMAGE_REPO}/${IMAGE_NAME}:latest

test: deps
	${venv} && PYTHONPATH=${PWD} pytest

run: deps
	@echo "use 'export INI_FILE=...; make -e run' to use other profiles'"
	mkdir -p logs
	${venv} && PYTHONPATH=prometheus_zabbix_template_generator ./prom2zabbix.py -c ${INI_FILE}

check: lint type-check test
.PHONY: check

lint: deps
	${venv} && python3 -m flake8 ./prom2zabbix.py prometheus_zabbix_template_generator
.PHONY: lint

type-check: deps
	${venv} && python3 -m mypy ./prom2zabbix.py prometheus_zabbix_template_generator
.PHONY: lint
