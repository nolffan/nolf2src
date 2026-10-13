// counter.cpp: the engine's performance-counter module, linked into the
// sound driver. Only the global divisor's initializer is in the retail image
// (0x10001120, data at 0x1000d0b0): the driver calls none of the counter
// functions, so the linker (/OPT:REF) drops them. They were compiled all the
// same -- the 64-bit division and multiplication helpers they call
// (msvcrt.lib's ulldiv, lldiv and llmul, 0x1000a220..) stay in the image,
// pulled in and kept though nothing calls them -- so they are written here,
// as Monolith's later revision of this file has them; their code cannot be
// checked against the retail image.

#include <windows.h>
#include "ltbasedefs.h"
#include "counter.h"

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

unsigned long cnt_NumTicksPerSecond()
{
	LARGE_INTEGER perSec;

	QueryPerformanceFrequency(&perSec);
	return (unsigned long)(perSec.QuadPart / g_CountDiv);
}

CounterFinal::CounterFinal(unsigned long startMode)
{
	if(startMode == CSTART_MICRO)
		StartMicro();
	else if(startMode == CSTART_MILLI)
		StartMS();
}

void CounterFinal::StartMS()
{
	LARGE_INTEGER *pInt;

	pInt = (LARGE_INTEGER*)m_Data;
	QueryPerformanceCounter(pInt);
}

unsigned long CounterFinal::EndMS()
{
	LARGE_INTEGER curCount, *pInCount, perSec;
	LONGLONG timeElapsed;

	pInCount = (LARGE_INTEGER*)m_Data;
	QueryPerformanceCounter(&curCount);

	QueryPerformanceFrequency(&perSec);
	timeElapsed = curCount.QuadPart - pInCount->QuadPart;
	return (unsigned long)((timeElapsed*(LONGLONG)1000) / perSec.QuadPart);
}

unsigned long CounterFinal::CountMS()
{
	return EndMS();
}

void CounterFinal::StartMicro()
{
	LARGE_INTEGER *pInt;

	pInt = (LARGE_INTEGER*)m_Data;
	QueryPerformanceCounter(pInt);
}

unsigned long CounterFinal::EndMicro()
{
	LARGE_INTEGER curCount, *pInCount;

	pInCount = (LARGE_INTEGER*)m_Data;
	QueryPerformanceCounter(&curCount);

	return (unsigned long)((curCount.QuadPart - pInCount->QuadPart) / g_CountDiv);
}

unsigned long CounterFinal::CountMicro()
{
	return EndMicro();
}

void cnt_StartCounterFinal(CounterFinal &cCounter)
{
	cCounter.StartMicro();
}

unsigned long cnt_EndCounterFinal(CounterFinal &cCounter)
{
	return cCounter.EndMicro();
}
