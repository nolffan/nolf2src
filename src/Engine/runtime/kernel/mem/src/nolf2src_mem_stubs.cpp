// nolf2src: stand-ins for what the link needs of the memory library that
// src/libs/ltmem/ does not have yet (docs/engine/PLAN.md, "skeleton").
// LTMemConsole, the "Mem" console command, is retail's ltmem.cpp's
// ("mem commands not available"); it is here, not in ltmem.cpp, because
// SndDrv.dll links that object as retail's does.

#include "bdefs.h"

void LTMemConsole(int argc, char *argv[])
{
}
