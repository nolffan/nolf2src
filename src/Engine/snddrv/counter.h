// counter.h: the engine's performance counters, as the sound driver sees
// them in the Final build: CounterFinal and its helpers are real, the
// profiling helpers (CountAdder) compile to nothing.

#ifndef __COUNTER_H__
#define __COUNTER_H__

#include "ltbasetypes.h"

// A counter can be started by its constructor.
#define CSTART_NONE			0
#define CSTART_MILLI		1
#define CSTART_MICRO		2

class CounterFinal
{
public:
					CounterFinal(unsigned long startMode=CSTART_NONE);

	// milliseconds
	void			StartMS();
	unsigned long	EndMS();
	unsigned long	CountMS();

	// microseconds
	void			StartMicro();
	unsigned long	EndMicro();
	unsigned long	CountMicro();

	unsigned long m_Data[2];
};

unsigned long cnt_NumTicksPerSecond();
void cnt_StartCounterFinal(CounterFinal &cCounter);
unsigned long cnt_EndCounterFinal(CounterFinal &cCounter);

#ifdef _FINAL

// Adds the time spent in a scope to a count: nothing in the Final build,
// but still an object with a destructor where it is declared (Thread_Func's
// exception states count them: 0x10003221).
class CountAdder
{
public:
	CountAdder(uint32 *pNum) {}
	~CountAdder() {}
};

#endif // _FINAL

#endif // __COUNTER_H__
