// ltmem.cpp: the LithTech memory interface (Engine/sdk/inc/ltmem.h) in its
// plain form, without the engine's own heap: allocation and release go
// straight to the C runtime. The sound driver links it as a library after
// msacm32.lib (retail 0x1000a0c0..0x1000a21b, below the MSACM32 import
// thunks): the initializers of the math constants ltbasedefs.h brings in,
// the global initializer object's registration, and LTMemAlloc and
// LTMemFree. Compiled without __declspec(dllimport) on the runtime (the
// calls go through import thunks), as a static library project is.

#include <stdlib.h>
#include "ltmem.h"

// true if lt mem system is initialized (never, in this form; ltmemstats.cpp
// reads it)
bool g_bLTMemInitialized = false;

// Initializes the memory system before anything else runs, and terminates
// it after everything else.
class CLTMemInitialize
{
public:
	CLTMemInitialize();
	~CLTMemInitialize();
} g_LTMemInitialize;

CLTMemInitialize::CLTMemInitialize()
{
	LTMemInit();
}

CLTMemInitialize::~CLTMemInitialize()
{
	LTMemTerm();
}

// Nothing to set up or tear down without the engine's heap: the global
// object's constructor compiles to nothing, its destructor to a bare `ret`
// (0x1000a1f0) that the initializer registers with atexit (0x1000a1e0).
void LTMemInit()
{
}

void LTMemTerm()
{
}

void* LTMemAlloc(uint32 nSize)
{
	return malloc(nSize);
}

void LTMemFree(void* pMem)
{
	free(pMem);
}
