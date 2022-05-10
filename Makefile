
repo=localhost
user=pypiadmin
password=pypiadmin

install:
	pip install --extra-index-url http://$(repo):8036 --trusted-host $(repo) -U --pre -r test_requirements.txt

.PHONY: build
build:
	shellfoundry install

download:
	pip download --extra-index-url http://$(repo):8036 --trusted-host $(repo) --pre -r src/requirements.txt -d dist/downloads
