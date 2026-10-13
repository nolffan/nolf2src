# build/build.mk -- every compile and link of the game, as one Makefile.
#
# Monolith's Visual C++ 6 workspace (src/Game/TO2.dsw) as Developer Studio
# would build it: tools/dsp2mk.py reads the workspace and the project files
# and writes the rules (.build/projects.mk) -- every compile with the flags
# its project's configuration gives it (the shipped one, "Final"; the
# libraries' "Release" where they have no "Final"), one source per compile,
# every library and link, the custom build steps (flex and bison). `make -j`
# then runs the compiles of every binary at once, and a rebuild redoes only
# what changed: an object is rebuilt when its source, a header it includes
# (tools/mkdeps.py finds them: VC6 cannot list them), or its command line
# changes (the line is kept in <object>.cmd), a binary when any of its inputs
# does.
#
# It is run from the root of the tree being built, never from a checkout:
# build/compile.sh runs it in out/release-tree/ (src/ without its variant
# blocks, build/env.sh) and build/variant.sh in out/build-<variant>/, as
#
#   make -f build/build.mk -j<N> [target...]
#
# Targets: all (the default: the projects below); a project by its workspace
# name (ClientShellDLL, Object, ClientFxDLL, ClientRes, ServerRes, Launcher,
# ServerApp, ServerDir, ltmsg, Lithtech, server, and the libraries they
# depend on); any single output.
#
# The compilers see the tree's src/ as drive S: and toolchains/ as T:, so
# they see the same paths wherever the tree is: VC6's output for NOLF's game
# DLLs depended on the path. (Monolith's own build ran in
# \proj\to2\source\, as the project files' custom build steps show; Wine
# names a working directory by its physical path, so giving the compilers
# that path would need src/ to be physically in such a directory.)
#
# From the environment (build/variant.sh sets them; empty for the release
# build, whose command lines are then exactly the project files' ones):
#   NOLF2SRC_CFLAGS   appended to every compile (/D NOLF2SRC_MODERN, /Z7 ...)
#   NOLF2SRC_LDFLAGS  put first on every link
#   NOLF2SRC_RCFLAGS  put first on every resource compile

ROOT := $(CURDIR)
SHELL := /bin/bash
.SUFFIXES:
.DELETE_ON_ERROR:
MAKEFLAGS += --no-builtin-rules --no-builtin-variables
.DEFAULT_GOAL := all

ifeq ($(wildcard $(ROOT)/src/Game/TO2.dsw),)
$(error run build/build.mk from the root of a tree, as build/compile.sh does)
endif

empty :=
space := $(empty) $(empty)
comma := ,
tab := $(empty)	$(empty)
define nl


endef
# one shell word per make word, quoted: Windows paths keep their backslashes
q = $(foreach w,$(1),'$(subst ','\'',$(w))')

NOLF2SRC_CFLAGS  ?=
NOLF2SRC_LDFLAGS ?=
NOLF2SRC_RCFLAGS ?=

# The projects the game is built from (and, through the workspace, every
# library they depend on), and the launcher (Launcher, NOLF2.exe).
PROJECTS_WANTED := ClientShellDLL Object ClientFxDLL ClientRes ServerRes ServerApp Launcher

# ServerDir.dll, of which Monolith's release has only the headers and the
# import library: src/Game/Libs/ServerDir/ServerDir.dsw (written for this
# project) builds it from the LithTech Jupiter SDK's source -- WONAPI and
# CServerDir_Titan, which tools/jupitersrc.py copies into src/Game/Libs/ from
# rez/ (build/all.sh does, first).
SERVERDIR_WANTED := ServerDir

# The engine's sound driver, SndDrv.dll, of which Monolith's release has
# nothing: src/Engine/snddrv/snddrv.dsw (written for this project) builds it
# from its reconstruction, with the ltmem library it links
# (src/libs/ltmem/) and EAX's GUIDs (eaxguid), which the retail Rich header
# says cl 12.00.8168 compiled: CL_eaxguid.
SNDDRV_WANTED := snddrv

# ltmsg.dll, the engine's message strings, which Monolith's release lacks:
# src/Engine/ltmsg/ltmsg.dsw (written for this project) builds it from a
# reconstructed resource script.
LTMSG_WANTED := ltmsg

# The engine, Lithtech.exe and server.dll, of which Monolith's release has
# only the SDK headers: src/Engine/runtime/winbuild/Engine.dsw (written for
# this project) builds them from the LithTech Jupiter engine source
# (src/Engine/runtime/), with the libraries they link: the renderer
# (D3DRender), the UI (Lib_UI), the sound driver loader (Lib_ILTSound),
# RezMgr (src/Engine/libs/rezmgr/), and ltmem, Lib_StdLith and Lib_Lith,
# whose rules the workspaces above already give (dsp2mk.py --have).
ENGINE_WANTED := Lithtech server

# ---------------------------------------------------------------------------
# Wine and the toolchains
export WINEDEBUG := -all
export WINEDLLOVERRIDES := mscoree,mshtml=
WINE := wine
PFX := $(ROOT)/.wine/drives

# The retail binaries' Rich headers name C++ build 8966 (VC6 SP5) and linker
# 6.00.8447: msvc-6.00-8966 is that compiler, with SP5's headers, CRT and MFC
# libraries, and the linker and librarian it ships. The SP5 tree has no
# resource compiler; RC.EXE is SP6's. The DirectX 8.1 SDK comes before VC's
# own directories, where its setup puts it.
TC      := $(ROOT)/toolchains
VC8966  := $(TC)/msvc-6.00-8966
VC9782  := $(TC)/msvc-6.00-9782
DXSDK   := $(TC)/dxsdk-8.1
CL      := $(VC8966)/BIN/cl.exe
LINK    := $(VC8966)/BIN/link.exe
LIBEXE  := $(VC8966)/BIN/lib.exe
RC      := $(VC9782)/Common/MSDev98/Bin/RC.EXE
CL_eaxguid := $(TC)/msvc-6.00-8168/BIN/cl.exe

# Windows paths: src/ is S:, toolchains/ T:, the rest Z:
wz = z:$(subst /,\,$(1))
ws = $(if $(filter $(ROOT)/src $(ROOT)/src/%,$(1)),s:$(subst /,\,$(patsubst $(ROOT)/src%,%,$(1))),$(if $(filter $(TC) $(TC)/%,$(1)),t:$(subst /,\,$(patsubst $(TC)%,%,$(1))),$(call wz,$(1))))

# The environment of a tool run. src/nolf2src/ (nolf2src_debug.h) is on
# every compiler's include path, last.
ENV_GAME := WINEPREFIX=$(PFX) WINEPATH='$(call ws,$(VC8966))\BIN;$(call ws,$(VC9782))\Common\MSDev98\Bin' \
    INCLUDE='$(call ws,$(DXSDK))\include;$(call ws,$(VC8966))\INCLUDE;$(call ws,$(VC8966))\MFC\INCLUDE;$(call ws,$(ROOT)/src/nolf2src)' \
    LIB='$(call ws,$(DXSDK))\lib;$(call ws,$(VC8966))\LIB;$(call ws,$(VC8966))\MFC\LIB'

# The prefix: made the first time, then only checked; every tool run waits
# for it (an order-only prerequisite, so it causes no rebuild).
$(PFX)/.ready:
	@echo "   WINE prefix $(@D)"
	@mkdir -p $(@D) && export WINEPREFIX=$(@D) && { $(WINE) wineboot -i >/dev/null 2>&1; \
	  for v in TEMP TMP; do $(WINE) reg add 'HKCU\Environment' /v $$v /t REG_SZ /d 'C:\windows\temp' /f >/dev/null 2>&1; done; \
	  wineserver -w; } && test -f $(@D)/system.reg && touch $@
.PHONY: wine-drives FORCE
wine-drives: $(PFX)/.ready
	@ln -sfn $(ROOT)/src $(PFX)/dosdevices/s:
	@ln -sfn $(TC) $(PFX)/dosdevices/t:

# ---------------------------------------------------------------------------
# The machinery
#
# Every output's command is a variable, cmd_<output>, that the rule runs and
# keeps in <output>.cmd. An output whose command differs from the kept one
# is rebuilt (FORCE): a changed flag, a file added to a link.
cmd_changed = $(call str_ne,$(strip $(cmd_$(1))),$(strip $(file <$(1).cmd)),FORCE)
str_ne = $(if $(subst x$(1),,x$(2))$(subst x$(2),,x$(1)),$(3))

OBJECTS :=
DEPSPEC :=
TOOLS :=

# $(call compile,<object>,<working dir>,<source as spelled>,<env>,<exe>,<flags>,<prefix>)
# One compile: `<exe> <flags> <source> $(NOLF2SRC_CFLAGS)` in <working dir>
# (the variant flags last: /Oy- must follow the /O2 that implies /Oy).
define compile
OBJECTS += $(1)
cmd_$(1) := cd $(2) && $(4) $(WINE) $(5) $(call q,$(6) $(3) $(NOLF2SRC_CFLAGS))
DEPSPEC += $(subst $(space),|,$(1)$(tab)$(2)$(tab)$(3)$(tab)$(strip $(6)))
$(1): $$(call cmd_changed,$(1)) | $(7)
endef

# $(call tool,<output>,<prerequisites>,<command>): any other build step
define tool
cmd_$(1) := $(3)
$(1): $$(call cmd_changed,$(1)) $(2)
TOOLS += $(1)
endef

# $(call rcfile,<res>,<project dir>,<rc as spelled>,<rc in the tree>,<flags>)
# The script's directory is a prerequisite as a whole: the bitmaps, icons
# and text files it includes.
define rcfile
$(call tool,$(1),$(4) $(filter-out %/Built %/built,$(wildcard $(dir $(4))*)) | wine-drives,\
    cd $(2) && $(ENV_GAME) $(WINE) $(RC) $(NOLF2SRC_RCFLAGS) $(call q,$(5) $(3)))
endef

# $(call library,<lib>,<project dir>,<flags>,<objects>,<objects as the project dir sees them>)
define library
$(call tool,$(1),$(4) | wine-drives,\
    cd $(2) && { printf '%s\n' $(call q,$(3) $(subst /,\,$(5))) > $(1:%=$(ROOT)/%).rsp; } && \
    $(ENV_GAME) $(WINE) $(LIBEXE) '@$(call ws,$(ROOT)/$(1)).rsp')
endef

# $(call binary,<dll or exe>,<project dir>,<flags>,<prerequisites>,<inputs as the project dir sees them>,
#   <the libraries' precompiled-header objects, as the project dir sees them>)
# Through a response file, as Developer Studio links; with a map beside it.
# Compiled with /Z7 (the debug builds), the libraries' precompiled-header
# objects are linked too: the others refer to the type information in them
# (LNK1211 without).
Z7 := $(findstring /Z7,$(NOLF2SRC_CFLAGS))
define binary
$(call tool,$(1),$(4) | wine-drives,\
    cd $(2) && { printf '%s\n' $(call q,$(NOLF2SRC_LDFLAGS) $(3) /map:$(call ws,$(ROOT)/$(basename $(1))).map $(subst /,\,$(5) $(if $(Z7),$(6)))) > $(1:%=$(ROOT)/%).rsp; } && \
    $(ENV_GAME) $(WINE) $(LINK) '@$(call ws,$(ROOT)/$(1)).rsp')
endef

# $(call custom,<outputs>,<input>,<project dir>,<commands>): a source's
# custom build step (flex, bison), its commands run by cmd.exe
define custom
$(1) &: $(2) | wine-drives
	@echo "   GEN  $(1)"
	@cd $(3) && $(ENV_GAME) $(WINE) cmd /c $(call q,$(4)) >/dev/null
	@# (bison names its output in lower case, and the step's own
	@# `ren AnimationParse.o AnimationParse.o` that fixes it on Windows changes
	@# no case under Wine: give each output the name the step gives it)
	@for o in $(1); do [ -f "$$$$o" ] || { f=$$$$(find "$$$$(dirname $$$$o)" -maxdepth 1 -iname "$$$$(basename $$$$o)" | head -1); \
	  [ -n "$$$$f" ] && mv "$$$$f" "$$$$o"; }; test -f "$$$$o" || { echo "error: $$$$o was not made" >&2; exit 1; }; done
endef

# ---------------------------------------------------------------------------
# The projects (tools/dsp2mk.py)

DEPDIR := $(ROOT)/.build
$(shell mkdir -p $(DEPDIR))
PROJECTS :=
DSP_OK := $(shell python3 tools/dsp2mk.py src/Game/TO2.dsw Final $(DEPDIR)/projects.mk $(PROJECTS_WANTED) 2>$(DEPDIR)/dsp2mk.log && echo ok)
ifneq ($(DSP_OK),ok)
$(error tools/dsp2mk.py failed: $(file <$(DEPDIR)/dsp2mk.log))
endif
include $(DEPDIR)/projects.mk

ifeq ($(wildcard $(ROOT)/src/Game/Libs/WONAPI/WONAPI.dsp),)
$(error src/Game/Libs/WONAPI/ is missing -- the Jupiter SDK's source is put there by tools/jupitersrc.py (build/all.sh runs it))
endif
DSP_OK := $(shell python3 tools/dsp2mk.py src/Game/Libs/ServerDir/ServerDir.dsw Final $(DEPDIR)/serverdir.mk $(SERVERDIR_WANTED) 2>$(DEPDIR)/dsp2mk-serverdir.log && echo ok)
ifneq ($(DSP_OK),ok)
$(error tools/dsp2mk.py failed: $(file <$(DEPDIR)/dsp2mk-serverdir.log))
endif
include $(DEPDIR)/serverdir.mk

DSP_OK := $(shell python3 tools/dsp2mk.py src/Engine/snddrv/snddrv.dsw Final $(DEPDIR)/snddrv.mk $(SNDDRV_WANTED) 2>$(DEPDIR)/dsp2mk-snddrv.log && echo ok)
ifneq ($(DSP_OK),ok)
$(error tools/dsp2mk.py failed: $(file <$(DEPDIR)/dsp2mk-snddrv.log))
endif
include $(DEPDIR)/snddrv.mk

DSP_OK := $(shell python3 tools/dsp2mk.py src/Engine/ltmsg/ltmsg.dsw Final $(DEPDIR)/ltmsg.mk $(LTMSG_WANTED) 2>$(DEPDIR)/dsp2mk-ltmsg.log && echo ok)
ifneq ($(DSP_OK),ok)
$(error tools/dsp2mk.py failed: $(file <$(DEPDIR)/dsp2mk-ltmsg.log))
endif
include $(DEPDIR)/ltmsg.mk

DSP_OK := $(shell python3 tools/dsp2mk.py --have "$(PROJECTS)" src/Engine/runtime/winbuild/Engine.dsw Final $(DEPDIR)/engine.mk $(ENGINE_WANTED) 2>$(DEPDIR)/dsp2mk-engine.log && echo ok)
ifneq ($(DSP_OK),ok)
$(error tools/dsp2mk.py failed: $(file <$(DEPDIR)/dsp2mk-engine.log))
endif
include $(DEPDIR)/engine.mk

.PHONY: all game
all game: $(PROJECTS_WANTED) $(SERVERDIR_WANTED) $(SNDDRV_WANTED) $(LTMSG_WANTED) $(ENGINE_WANTED)

# ---------------------------------------------------------------------------
# The rules all compiles and tools share

dups := $(strip $(foreach o,$(sort $(OBJECTS)),$(if $(word 2,$(filter $(o),$(OBJECTS))),$(o))))
ifneq ($(dups),)
$(error two sources compile to one object: $(dups))
endif

# Under Wine, a compile that uses a precompiled header now and then dies
# with C1001 (an internal compiler error) or C1060 ("out of heap space")
# while other compiles run; the same compile run again succeeds, and gives
# the same object. Those two are retried, up to three tries in all (said so
# in the log); any other error fails the build at once.
$(OBJECTS):
	@echo "   CC   $@"
	@mkdir -p $(@D) && rm -f $@
	@for try in 1 2 3; do \
	  out=$$( { $(cmd_$@); } 2>&1 ); rc=$$?; \
	  if [ $$rc = 0 ] || [ $$try = 3 ] || ! grep -qE 'error C10(01|60)' <<< "$$out"; then printf '%s\n' "$$out"; break; fi; \
	  echo "   CC   $@: $$(grep -oE 'error C10(01|60)' <<< "$$out" | head -1), compiling it again"; rm -f $@; \
	done; exit $$rc
	@test -f $@ || { echo "error: $@ was not built" >&2; exit 1; }
	@printf '%s\n' '$(subst ','\'',$(cmd_$@))' > $@.cmd

$(TOOLS):
	@echo "   GEN  $@"
	@mkdir -p $(@D) && rm -f $@
	@$(cmd_$@)
	@test -f $@ || { echo "error: $@ was not built" >&2; exit 1; }
	@printf '%s\n' '$(subst ','\'',$(cmd_$@))' > $@.cmd

FORCE:

# Header dependencies (tools/mkdeps.py), brought up to date on every run
$(file >$(DEPDIR)/deps.spec,$(subst |, ,$(subst $(space),$(nl),$(DEPSPEC))))
DEPS_OK := $(shell python3 tools/mkdeps.py $(DEPDIR)/deps.spec $(DEPDIR)/deps.mk && echo ok)
ifneq ($(DEPS_OK),ok)
$(error tools/mkdeps.py failed)
endif
include $(DEPDIR)/deps.mk
