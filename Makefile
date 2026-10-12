# No One Lives Forever 2, built from source.
#
#   make          build the game into out/nolf2-legacy-release/ (and out/nolf2-legacy-release.tar.gz)
#   make test     scripted playtest of out/nolf2-legacy-release/
#   make debug    the same game with symbols and debug logging, in out/nolf2-legacy-debug/
#   make modern   the game with NOLF2SRC_MODERN, in out/nolf2-modern-release/
#   make progress how much of the build is byte-identical to the retail game;
#                 fails if a function recorded as identical stops matching
#   make help     everything else
#
# Needs only docker on the host and the two submodules (`git submodule update
# --init`): the compilers, toolchains/ (toolchains/README.md), and rez/, which
# fetches the redump images of the European discs from archive.org and
# installs the game from them with the 1.3 update (rez/README.md; `make
# retail`, which every build runs first, does it once). Every step runs in a
# throwaway container of the image docker/Dockerfile describes, with this
# checkout mounted at /repo, as you.

IMAGE     ?= nolf2src-build
CONTAINER ?= nolf2src-build
TEST_LEVELS ?=
# Parallel compile jobs inside the build (build/build.mk); empty: one per CPU
JOBS ?=

DOCKER_RUN = docker run --rm --init --name $(CONTAINER) \
	-u $(shell id -u):$(shell id -g) -e HOME=/tmp/home $(if $(JOBS),-e NOLF2SRC_JOBS=$(JOBS)) \
	-v $(CURDIR):/repo -w /repo $(IMAGE)

TOOLCHAIN_FILES = toolchains/msvc-6.00-8966/BIN/cl.exe toolchains/msvc-6.00-9782/Common/MSDev98/Bin/RC.EXE \
	toolchains/dxsdk-8.1/include/d3d8.h

.PHONY: all game debug modern modern-debug image retail check-rez check-toolchain test progress progress-update shell clean distclean help

all: game

help:
	@echo "make            build everything into out/nolf2-legacy-release/ and out/nolf2-legacy-release.tar.gz"
	@echo "make debug      the game with symbols and NOLF2SRC_DEBUG logging, in out/nolf2-legacy-debug/"
	@echo "make modern     the game with NOLF2SRC_MODERN, in out/nolf2-modern-release/"
	@echo "make modern-debug  both, in out/nolf2-modern-debug/"
	@echo "                (none of these is ever scored; build/variant.sh)"
	@echo "make test       scripted playtest of out/nolf2-legacy-release/ (TEST_LEVELS), under Xvfb"
	@echo "make progress   score the build against the retail binaries; fails if a"
	@echo "                function recorded in progress/identical.txt stops matching"
	@echo "make progress-update  record the score in progress/ and README.md"
	@echo "make retail     fetch the two disc images and install the retail game and its"
	@echo "                1.3 update from them (rez/, once; every build runs it), and check it"
	@echo "make shell      a shell in the build container (build/*.sh, tools/ work there)"
	@echo "make image      (re)build the docker image $(IMAGE)"
	@echo "make clean      remove out/ and every build output in the source tree"
	@echo "make distclean  clean, and remove the docker image too"
	@echo
	@echo "Variables: TEST_LEVELS=\"$(TEST_LEVELS)\", JOBS=<n> (parallel compiles; default one per CPU)"
	@echo "           COMPLETE=1, COVERED=1, ACCEPT_LOSSES=1 (progress/README.md)"

game: check-toolchain retail
	$(DOCKER_RUN) bash build/all.sh

debug modern modern-debug: check-toolchain retail
	$(DOCKER_RUN) bash build/variant.sh $@

image:
	@docker build -q -t $(IMAGE) docker/ >/dev/null || \
	  { echo "error: could not build the docker image (docker/Dockerfile)" >&2; exit 1; }
	@echo "== docker image $(IMAGE) ready"

# The retail game the build takes its data from (build/retail.sh): installed
# by rez/ the first time, checked against rez/games.sha256 every time.
retail: check-rez image
	@$(DOCKER_RUN) bash -c 'source build/retail.sh && retail_install && retail_verify'

check-rez:
	@[ -f rez/install-games.sh ] || { echo "error: rez/ is empty -- the disc images and their installer are the rez/ submodule: run git submodule update --init (see rez/README.md)" >&2; exit 1; }

check-toolchain:
	@for f in $(TOOLCHAIN_FILES); do \
	  [ -f "$$f" ] || { echo "error: $$f is missing -- the compilers are the toolchains/ submodule: run git submodule update --init (see toolchains/README.md)" >&2; exit 1; }; \
	done

test: image
	@[ -f out/nolf2-legacy-release/Lithtech.exe ] || { echo "error: no out/nolf2-legacy-release/ -- run make first" >&2; exit 1; }
	$(DOCKER_RUN) env PLAYTEST_NAME=test-menu bash tools/playtest.sh out/nolf2-legacy-release - 60

progress: retail
	$(DOCKER_RUN) env COMPLETE=$(COMPLETE) COVERED=$(COVERED) bash build/progress.sh check

progress-update: retail
	$(DOCKER_RUN) env ACCEPT_LOSSES=$(ACCEPT_LOSSES) bash build/progress.sh update

shell: image
	docker run --rm -it --init --name $(CONTAINER)-shell \
	  -u $(shell id -u):$(shell id -g) -e HOME=/tmp/home \
	  -v $(CURDIR):/repo -w /repo $(IMAGE) bash

clean:
	rm -rf out .wine .build
	find src -depth -type d \( -name built -o -name Built \) -exec rm -rf {} +
	rm -f src/Game/ObjectDLL/ObjectShared/AnimationLex.o src/Game/ObjectDLL/ObjectShared/AnimationParse.o \
	  src/Game/ObjectDLL/ObjectShared/AnimationLexSymbols.h

distclean: clean
	-docker rmi $(IMAGE)
