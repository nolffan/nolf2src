// ltmemstats.cpp: the "mem" console command (LTMemConsole), which the
// engine's client and server console tables name. Without the engine's
// heap (ltmem.cpp) and without allocation tracking (LTMEMTRACK in ltmem.h),
// all it can say is that the commands are not available: the help, mark,
// dump, log and statistics commands of later LithTech versions are compiled
// only with tracking, and retail Lithtech.exe (0x4c14c0) and server.dll
// (0x10048a10) have this function alone in the object. Not linked by
// SndDrv.dll, which never references it.

#include "ltmem.h"

// From the engine (dsys_interface.h; bdefs.h names it dsi_ConsolePrint).
extern void dsi_PrintToConsole(const char *pMsg, ...);
#define dsi_ConsolePrint dsi_PrintToConsole

// true if lt mem system is initialized
extern bool g_bLTMemInitialized;

// console command handler for "mem" console command
void LTMemConsole(int argc, char *argv[])
{
	// if the ltmem system is not being used then just display message and exit
	if (!g_bLTMemInitialized)
	{
		dsi_ConsolePrint("mem commands not available (ltmem system is not turned on in ltmem.cpp in this build)\n");
		return;
	}

#ifndef LTMEMTRACK
	dsi_ConsolePrint("mem commands not available (tracking in ltmem.h is not turned on in this build)\n");
	return;
#endif
}
