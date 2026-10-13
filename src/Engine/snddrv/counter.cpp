// counter.cpp: the engine's performance-counter module, linked into the
// sound driver. Of it only the global divisor and its initializer are in the
// retail image (0x10001120, data at 0x1000d0b0); the driver calls none of the
// module's functions, so the linker (/OPT:REF) keeps nothing else, and
// nothing else is written here.

#include <windows.h>
#include "ltbasedefs.h"

static unsigned __int64 g_CountDiv = 1;

// The high-resolution counter's divisor: always 1 (counts are not scaled to
// microseconds).
class CountDivSetter
{
public:
	CountDivSetter()
	{
		LARGE_INTEGER perSec;

		QueryPerformanceFrequency(&perSec);
		g_CountDiv = 1;
	}
};
static CountDivSetter __g_CountDivSetter;
