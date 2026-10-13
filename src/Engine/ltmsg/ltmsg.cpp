// ltmsg.cpp -- ltmsg.dll, the LithTech engine's message strings.
//
// Written for nolf2src (Monolith did not release the engine's source).
// The DLL is its resources (ltmsg.rc): Lithtech.exe loads it and formats
// its errors from the string table by number. It has no code of its own --
// not even a DllMain: the retail DLL's is the C runtime's default one
// (msvcrt.lib's, which turns off the thread notifications), linked after
// the CRT's startup code. So this file only has to exist, compiled as C++,
// as the DLL's one object.

#include <windows.h>
