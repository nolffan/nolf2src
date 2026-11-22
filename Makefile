# No One Lives Forever 2, built from source.
#
#   make          build the game into out/nolf2-legacy-release/ (and its -private / -public .tar.gz)
#   make test     scripted playtest of out/nolf2-legacy-release/: main menu, new game, play
#   make debug    the same game with symbols and debug logging, in out/nolf2-legacy-debug/
#   make modern   the game with NOLF2SRC_MODERN, in out/nolf2-modern-release/
#   make progress how much of the build is byte-identical to the retail game;
#                 fails if a function recorded as identical stops matching
#   make ci       the CI build and check, without the retail game
#   make help     everything else
#
# Needs only docker on the host, the submodules (`git submodule update
# --init`): the build's scripts and checks, ext/tools/ (shared with the NOLF
# and Contract J.A.C.K. projects; ext/tools/README.md), the compilers,
# ext/toolchains/ (ext/toolchains/README.md), ext/lithtools/, whose lithrez
# packs assets/ into the game's archives (build/lithrez.sh) -- and your own
# images, in isos/ (or NOLF2_ISOS=<dir>): the two discs of the European
# release and the 1.3 update's installer, from which `make retail`, which
# every build runs first, installs the retail game once, and the CD of the
# LithTech Jupiter SDK, whose source ServerDir.dll is built from (`make
# sdk`, the same way; build/discs.py). `make progress` also needs the
# multiplayer demo's installer there (`make demo`). `make modern` also needs
# the ext/ffmpeg submodule (FFmpeg, pinned to a release), which its Bink
# player is built on (build/ext.sh). Every step runs in a throwaway
# container of the image docker/Dockerfile describes, with this checkout
# mounted at /repo, as you.

IMAGE     ?= nolf2src-build
CONTAINER ?= nolf2src-build
# Parallel compile jobs inside the build (build/build.mk); empty: one per CPU
JOBS ?=
# The game directory `make test` plays: the release build's, or a variant's
# (make test TEST_GAME=out/nolf2-modern-release; build/variant.sh)
TEST_GAME ?= out/nolf2-legacy-release
TEST_NAME = $(if $(filter out/nolf2-legacy-release,$(TEST_GAME:%/=%)),test,test-$(notdir $(TEST_GAME:%/=%)))

# Your images, if they are not in isos/: NOLF2_ISOS=<directory> (mounted
# read-only). NODISCS=1: build without the retail game and the SDK, any
# variant (`make ci`; build/all.sh): into out/<name>-nodiscs/, which does not
# play, and out/<name>-public.tar.gz, which installs from your disc images.
# NOLF2_MAC_DIR=<directory>: the Mac release, for development only (make
# shell mounts it).
NOLF2_ISOS ?=
NOLF2_MAC_DIR ?=
NODISCS ?=
ISO_MOUNT := $(if $(NOLF2_ISOS),-v $(abspath $(NOLF2_ISOS)):/isos:ro -e NOLF2_ISOS=/isos)
MAC_MOUNT := $(if $(NOLF2_MAC_DIR),-v $(abspath $(NOLF2_MAC_DIR)):/mac:ro -e NOLF2_MAC_DIR=/mac)

DOCKER_RUN = docker run --rm --init --name $(CONTAINER) \
	-u $(shell id -u):$(shell id -g) -e HOME=/tmp/home $(if $(JOBS),-e NOLF2SRC_JOBS=$(JOBS)) \
	$(if $(NOLF2_ARCHIVES),-e NOLF2_ARCHIVES="$(NOLF2_ARCHIVES)") \
	$(if $(filter 1,$(NODISCS)),-e NOLF2_NODISCS=1) \
	-v $(CURDIR):/repo -w /repo $(ISO_MOUNT) $(IMAGE)

TOOLCHAIN_FILES = ext/toolchains/msvc-6.00-8966/BIN/cl.exe ext/toolchains/msvc-6.00-9782/Common/MSDev98/Bin/RC.EXE \
	ext/toolchains/dxsdk-8.1/include/d3d8.h

.PHONY: all game debug modern modern-debug image retail sdk demo retail-ranges art art-check serverdir ci progress-ci check-tools check-lithtools check-ext check-toolchain test progress progress-update shell clean distclean help

all: game

help:
	@echo "make            build everything into out/nolf2-legacy-release/ and its .tar.gz archives"
	@echo "make debug      the game with symbols and NOLF2SRC_DEBUG logging, in out/nolf2-legacy-debug/"
	@echo "make modern     the game with NOLF2SRC_MODERN, in out/nolf2-modern-release/"
	@echo "make modern-debug  both, in out/nolf2-modern-debug/"
	@echo "                (none of these is ever scored; build/variant.sh)"
	@echo "make test       scripted playtest of out/nolf2-legacy-release/ under Xvfb: the main menu,"
	@echo "               a new game, the first level (ext/tools/playtest-newgame.txt; out/play/test/)"
	@echo "make test TEST_GAME=out/nolf2-modern-release   the same on a variant's game directory"
	@echo "               (out/play/test-<its name>/)"
	@echo "make progress   score the build against the retail binaries; fails if a"
	@echo "                function recorded in progress/identical.txt stops matching"
	@echo "make progress-update  record the score in progress/ (and its README.md table), and"
	@echo "                the hashes make progress-ci checks against in progress/hashes/"
	@echo "make progress-ci  the check without the retail game: the build against"
	@echo "                progress/hashes/ (finds no new matches)"
	@echo "make ci         what CI runs: make NODISCS=1 (the legacy release build without"
	@echo "                the retail game: no game data), then make progress-ci"
	@echo "make retail     install the retail game and its 1.3 update from your two disc"
	@echo "                images and the update's installer in isos/ (once; every build"
	@echo "                runs it), and check it"
	@echo "make sdk        install the Jupiter SDK's WONAPI source from your image of its CD"
	@echo "                in isos/ (once; every build runs it), and check it"
	@echo "make demo       install the multiplayer demo's engine from its installer in isos/"
	@echo "                (once; make progress runs it)"
	@echo "make retail-ranges  write build/retail-ranges.txt from the retail game: its PE"
	@echo "                files and zeroed DLLs (for NODISCS=1 and the install scripts)"
	@echo "make art        write the retail art our binaries are compiled with into"
	@echo "                assets/art/ again, from the retail binaries"
	@echo "make art-check  check that assets/art/ is the retail art (every build with"
	@echo "                the retail game also does this)"
	@echo "make serverdir  write assets/serverdir/ again from the last make: the"
	@echo "                ServerDir.dll a build without the SDK uses (every build with"
	@echo "                the SDK checks it)"
	@echo "make shell      a shell in the build container (build/*.sh, ext/tools/ work there)"
	@echo "make image      (re)build the docker image $(IMAGE)"
	@echo "make clean      remove out/ and every build output in the source tree"
	@echo "make distclean  clean, and remove the docker image too"
	@echo
	@echo "Variables: JOBS=<n> (parallel compiles; default one per CPU)"
	@echo "           NOLF2_ARCHIVES=\"private public\" (the archives build/package.sh writes)"
	@echo "           NOLF2_ISOS=<dir> (your images, if not in isos/), NODISCS=1 (without"
	@echo "           them: out/<name>-nodiscs/, which does not play, and out/<name>-public.tar.gz)"
	@echo "           IMAGE_BUILD=0 (use the docker image as it is, as CI does)"
	@echo "           COMPLETE=1, COVERED=1, ACCEPT_LOSSES=1 (progress/README.md)"

game: check-toolchain check-lithtools retail sdk
	$(DOCKER_RUN) bash build/all.sh

debug: check-toolchain check-lithtools retail sdk
	$(DOCKER_RUN) bash build/variant.sh $@

# the modern build also builds its Bink player on FFmpeg from ext/
# (build/ext.sh)
modern modern-debug: check-toolchain check-lithtools check-ext retail sdk
	$(DOCKER_RUN) bash build/variant.sh $@

# IMAGE_BUILD=0: use $(IMAGE) as it is (CI builds it with a layer cache
# first, .github/workflows/ci.yml).
IMAGE_BUILD ?= 1
image:
ifeq ($(IMAGE_BUILD),0)
	@docker image inspect $(IMAGE) >/dev/null 2>&1 || \
	  { echo "error: IMAGE_BUILD=0, but there is no docker image $(IMAGE)" >&2; exit 1; }
else
	@docker build -q -t $(IMAGE) docker/ >/dev/null || \
	  { echo "error: could not build the docker image (docker/Dockerfile)" >&2; exit 1; }
endif
	@echo "== docker image $(IMAGE) ready"

# The retail game the build takes its data from (build/retail.sh): installed
# from your images (isos/, or NOLF2_ISOS) by build/discs.py the first time,
# checked against build/retail-files.txt every time. Nothing with NODISCS=1.
retail: check-tools image
ifeq ($(NODISCS),1)
	@echo "== NODISCS=1: no retail game (the build has no game data; its art is assets/art/)"
else
	@$(DOCKER_RUN) bash -c 'source build/retail.sh && retail_install && retail_verify'
endif

# The Jupiter SDK's WONAPI source (build/jupiter.sh): installed from your
# image of its CD the first time, checked against build/sdk-files.txt every
# time. Nothing with NODISCS=1 (the build uses assets/serverdir/).
sdk: check-tools image
ifeq ($(NODISCS),1)
	@echo "== NODISCS=1: no Jupiter SDK (ServerDir.dll is assets/serverdir/'s)"
else
	@$(DOCKER_RUN) bash -c 'source build/jupiter.sh && jupiter_install && jupiter_verify'
endif

# The multiplayer demo's engine, which make progress reads (build/progress.sh):
# installed from its installer the first time (build/demo-files.txt)
demo: check-tools image
	@$(DOCKER_RUN) bash -c 'cmp -s out/retail/nolf2-mpdemo/.retail-files build/demo-files.txt || \
	  { echo "== installing the engine of the multiplayer demo from its installer (build/discs.py, once)"; \
	    python3 build/discs.py install demo out/retail/nolf2-mpdemo; }'


# build/retail-ranges.txt, written again from the retail game
# (build/retailextract.py ranges): only needed when what the build takes
# out of the retail game changes; every build with it checks the list
retail-ranges: check-tools retail
	$(DOCKER_RUN) bash -c 'source build/retail.sh && python3 build/retailextract.py ranges write "$$(retail_dir)"'

# The retail art our binaries are compiled with, committed in assets/art/:
# written again from the retail binaries' resources, or checked against
# them (build/retailextract.py art; every build with the retail game checks
# it)
art: check-tools retail
	$(DOCKER_RUN) bash -c 'source build/retail.sh && python3 build/retailextract.py art write "$$(retail_dir)"'

art-check: check-tools retail
	$(DOCKER_RUN) bash -c 'source build/retail.sh && python3 build/retailextract.py art check "$$(retail_dir)"'

# assets/serverdir/, the ServerDir.dll (and its link map) that a build
# without the SDK uses, written again from the last make
# (build/serverdir.py; every build with the SDK checks it)
serverdir: check-tools image
	$(DOCKER_RUN) python3 build/serverdir.py write

check-tools:
	@[ -f ext/tools/retailextract.py ] || { echo "error: ext/tools/ is empty -- the build's scripts and checks are the ext/tools/ submodule: run git submodule update --init (see ext/tools/README.md)" >&2; exit 1; }

check-lithtools:
	@[ -f ext/lithtools/tools/lithrez/CMakeLists.txt ] || { echo "error: ext/lithtools/ is empty -- lithrez, which packs assets/ into nolf2src.rez, is the lithtools submodule's: run git submodule update --init lithtools" >&2; exit 1; }

check-ext:
	@[ -f ext/ffmpeg/LICENSE.md ] || { echo "error: ext/ffmpeg is empty -- the modern build's Bink player is built on the ext/ffmpeg submodule: run git submodule update --init ext/ffmpeg" >&2; exit 1; }

check-toolchain: check-tools
	@for f in $(TOOLCHAIN_FILES); do \
	  [ -f "$$f" ] || { echo "error: $$f is missing -- the compilers are the ext/toolchains/ submodule: run git submodule update --init (see ext/toolchains/README.md)" >&2; exit 1; }; \
	done

test: check-tools image
	@[ -f $(TEST_GAME)/Lithtech.exe ] || { echo "error: no $(TEST_GAME)/ -- build it first (make, or make debug/modern/modern-debug)" >&2; exit 1; }
	@[ ! -f $(TEST_GAME)/NOT-PLAYABLE.txt ] || { cat $(TEST_GAME)/NOT-PLAYABLE.txt >&2; exit 1; }
	$(DOCKER_RUN) env PLAYTEST_NAME=$(TEST_NAME) PLAYTEST_SCRIPT=ext/tools/playtest-newgame.txt bash ext/tools/playtest.sh $(TEST_GAME) - 5

# what ext/tools/evidence.py cannot ask git for in the container (the build
# image has no git)
EVIDENCE_ENV = EVIDENCE_REVISION=$(shell git rev-parse HEAD 2>/dev/null) \
	EVIDENCE_MODIFIED=$(shell git status --porcelain --untracked-files=no 2>/dev/null | wc -l) \
	EVIDENCE_SUBMODULES="$(shell git submodule status 2>/dev/null | sed 's/^ *//' | tr '\n' ';')"

progress: retail demo
	$(DOCKER_RUN) env COMPLETE=$(COMPLETE) COVERED=$(COVERED) $(EVIDENCE_ENV) bash build/progress.sh check

progress-update: retail demo
	$(DOCKER_RUN) env ACCEPT_LOSSES=$(ACCEPT_LOSSES) $(EVIDENCE_ENV) bash build/progress.sh update

# Without the retail game: the build against progress/hashes/ (build/progress.sh ci)
progress-ci: check-tools image
	$(DOCKER_RUN) bash build/progress.sh ci

# What CI runs (.github/workflows/ci.yml): the legacy release build without
# the retail game, then the check without it
ci:
	$(MAKE) --no-print-directory NODISCS=1 game
	$(MAKE) --no-print-directory progress-ci

shell: image
	docker run --rm -it --init --name $(CONTAINER)-shell \
	  -u $(shell id -u):$(shell id -g) -e HOME=/tmp/home \
	  -v $(CURDIR):/repo -w /repo $(ISO_MOUNT) $(MAC_MOUNT) $(IMAGE) bash

# (out/retail/, the installed retail game and SDK, goes too: the next build
# installs them again from your images)
clean:
	rm -rf out .wine .build
	rm -f src/Engine/runtime/winbuild/lithtech/res/lithtech.ico
	find src -depth -type d \( -name built -o -name Built \) -exec rm -rf {} +
	rm -f src/Game/ObjectDLL/ObjectShared/AnimationLex.o src/Game/ObjectDLL/ObjectShared/AnimationParse.o \
	  src/Game/ObjectDLL/ObjectShared/AnimationLexSymbols.h

distclean: clean
	-docker rmi $(IMAGE)
