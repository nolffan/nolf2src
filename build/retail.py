# NOLF2's retail game, for tools/retailextract.py and tools/mkinstall.py
# (their defaults are NOLF2's; this sets what differs from them).
#
# The 1.3 update's data ships with the release: assets/ holds what its
# Update_v1x3.rez carries besides the game DLLs (assets/rez/, packed into
# nolf2src.rez by build/all.sh with lithtools' lithrez) and the shipped
# settings and default profile it installs (assets/game/). So the game
# directory takes nothing from the update -- the retail install's
# Update_v1x3.rez stays the source of the 1.3 game DLLs the scoring compares
# against (REFERENCE_REZ, unchanged) -- and the install scripts ask only for
# the discs.

# the archives of the retail install the game directory takes (the discs')
REZ = ["Engine.REZ", "GAME.REZ", "GAME2.REZ", "GAMEDLL.REZ", "SOUND.REZ"]

# autoexec.cfg.retail and Default.prf.retail come from assets/game/
RETAIL_COPIES = []

INSTALL_UPDATE = None
