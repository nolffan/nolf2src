// nolf2src: stand-ins for what Lithtech.exe's link needs of the UI files
// that do not compile yet (docs/engine/PLAN.md, "skeleton").

#include "bdefs.h"

// cuifontmanager.cpp (the font classes: NOLF2's cuifont.h and
// iltfontmanager.h differ from Jupiter's)
class CUIFontManager;
CUIFontManager* __impl_ptr_CUIFontManager_Default__ = LTNULL;
