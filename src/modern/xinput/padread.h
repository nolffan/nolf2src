// ----------------------------------------------------------------------- //
//
// MODULE  : padread.h
//
// PURPOSE : The modern build's controller (MODERN.md M-E20, M-G47):
//           reading the pad, for the two modules that do -- Lithtech.exe's
//           ##gamepad input device (gamepad_device.h, included by the
//           engine's input.cpp: the buttons the bindings see) and
//           CShell.dll (clientpad.cpp: the sticks, and the keys the menus
//           take, which must not depend on what a button is bound to).
//           Each includes this once and has its own copy of the state.
//
//           The first connected XInput pad (slot 0..3), from whichever of
//           xinput1_4 / 1_3 / 9_1_0 loads, looked up at run time: VC6 and
//           the DirectX 8.1 SDK predate XInput, so its two types are
//           declared here. Only the connected slot is read in the frame.
//           Asking about an empty slot can take milliseconds on Windows
//           (Microsoft's XInput guide: do not ask about empty slots every
//           frame), and the slots were looked through in the frame once a
//           second, a hitch every second for a player with no pad
//           (MODERN.md M-E59); now a thread of the module's own looks for a
//           pad once a second while none is connected, and the frame reads
//           only the slot it found. A pad plugged in is found within a
//           second, as before. PadRead_Term stops the thread (CShell.dll's
//           must stop before the DLL is unloaded; Lithtech.exe's ends with
//           the process).
//
//           The test pad: with NOLF2SRC_PADTEST naming a file, XInput is
//           not used and the pad in slot 0 is that file's one line,
//           "<buttons> <lx> <ly> <rx> <ry> <lt> <rt>" in XInput's units
//           (XINPUT_GAMEPAD's wButtons; the sticks -32768..32767, y up
//           positive; the triggers 0..255), read again every 15 ms; no file
//           (or one that does not parse) is no pad connected. Slots 1..3
//           are always empty. It goes through the same scan as XInput, so
//           the playtest's hot-plug (tools/playtest.sh's `pad` command,
//           which writes the file) tests it; NOLF2SRC_PADTEST_STALL=<ms>
//           makes asking about an empty slot take that long, as on Windows.
//
//           Modern build only (NOLF2SRC_MODERN): nothing of the release
//           build includes it.
//
// ----------------------------------------------------------------------- //

#ifndef __NOLF2SRC_PADREAD_H__
#define __NOLF2SRC_PADREAD_H__

#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// XINPUT_GAMEPAD
struct PadState
{
	WORD	wButtons;
	BYTE	bLeftTrigger;
	BYTE	bRightTrigger;
	SHORT	sThumbLX;
	SHORT	sThumbLY;
	SHORT	sThumbRX;
	SHORT	sThumbRY;
};

// XINPUT_GAMEPAD's button bits
enum
{
	PAD_DPAD_UP				= 0x0001,
	PAD_DPAD_DOWN			= 0x0002,
	PAD_DPAD_LEFT			= 0x0004,
	PAD_DPAD_RIGHT			= 0x0008,
	PAD_START				= 0x0010,
	PAD_BACK				= 0x0020,
	PAD_LEFT_THUMB			= 0x0040,
	PAD_RIGHT_THUMB			= 0x0080,
	PAD_LEFT_SHOULDER		= 0x0100,
	PAD_RIGHT_SHOULDER		= 0x0200,
	PAD_A					= 0x1000,
	PAD_B					= 0x2000,
	PAD_X					= 0x4000,
	PAD_Y					= 0x8000,
	PAD_DPAD				= 0x000F,
	PAD_TRIGGER_THRESHOLD	= 30		// XINPUT_GAMEPAD_TRIGGER_THRESHOLD
};

namespace
{
	struct PadXInputState				// XINPUT_STATE
	{
		DWORD		dwPacketNumber;
		PadState	Gamepad;
	};

	typedef DWORD (WINAPI* PadXInputGetState)(DWORD dwUserIndex, PadXInputState* pState);

	int					s_nPadAvailable = -1;	// -1: not decided yet
	PadXInputGetState	s_pPadGetState;			// XInput's, or the test pad's
	volatile LONG		s_lPadSlot = -1;		// the connected slot, -1: none
	HANDLE				s_hPadScanThread;
	HANDLE				s_hPadScanStop;
	DWORD				s_dwPadLastScan;		// without the thread: the frame scans
	bool				s_bPadScanned;

	const char*			s_pPadTestFile;			// NOLF2SRC_PADTEST
	DWORD				s_dwPadTestStall;		// NOLF2SRC_PADTEST_STALL
	CRITICAL_SECTION	s_PadTestLock;
	bool				s_bPadTestRead;
	DWORD				s_dwPadTestRead;
	bool				s_bPadTestPad;
	PadState			s_PadTestState;

	// The test pad, as XInputGetState: slot 0 is the file's state, read
	// again at most every 15 ms (a file's time is only to the second, so it
	// is not asked); both threads ask, so under a lock.
	DWORD WINAPI PadRead_TestGetState(DWORD dwUserIndex, PadXInputState* pState)
	{
		bool bPad = false;

		memset(pState, 0, sizeof(*pState));

		if (dwUserIndex == 0)
		{
			DWORD dwNow = GetTickCount();

			EnterCriticalSection(&s_PadTestLock);
			if (!s_bPadTestRead || dwNow - s_dwPadTestRead >= 15)
			{
				FILE* pFile = fopen(s_pPadTestFile, "r");
				int   n[7];

				s_bPadTestRead  = true;
				s_dwPadTestRead = dwNow;
				s_bPadTestPad   = false;

				if (pFile)
				{
					if (fscanf(pFile, "%i %i %i %i %i %i %i",
					           &n[0], &n[1], &n[2], &n[3], &n[4], &n[5], &n[6]) == 7)
					{
						s_PadTestState.wButtons      = (WORD)n[0];
						s_PadTestState.sThumbLX      = (SHORT)n[1];
						s_PadTestState.sThumbLY      = (SHORT)n[2];
						s_PadTestState.sThumbRX      = (SHORT)n[3];
						s_PadTestState.sThumbRY      = (SHORT)n[4];
						s_PadTestState.bLeftTrigger  = (BYTE)n[5];
						s_PadTestState.bRightTrigger = (BYTE)n[6];
						s_bPadTestPad = true;
					}

					fclose(pFile);
				}
			}
			bPad = s_bPadTestPad;
			if (bPad)
				pState->Gamepad = s_PadTestState;
			LeaveCriticalSection(&s_PadTestLock);
		}

		if (bPad)
			return ERROR_SUCCESS;

		if (s_dwPadTestStall)
			Sleep(s_dwPadTestStall);
		return ERROR_DEVICE_NOT_CONNECTED;
	}

	// Look through the slots for a connected pad; the first found is the
	// one read.
	void PadRead_Scan()
	{
		PadXInputState state;
		int            i;

		for (i = 0; i < 4; i++)
		{
			if (s_pPadGetState(i, &state) == ERROR_SUCCESS)
			{
				InterlockedExchange((LONG*)&s_lPadSlot, i);
				return;
			}
		}
	}

	// The scan, once a second while no pad is connected (only the frame
	// clears the slot, when the pad there is gone, so the two never set it
	// at once). The thread holds a reference to the module it runs in, so
	// that a DLL unloaded without PadRead_Term stays mapped under it.
	DWORD WINAPI PadRead_ScanThread(LPVOID pModule)
	{
		do
		{
			if (s_lPadSlot < 0)
				PadRead_Scan();
		}
		while (WaitForSingleObject(s_hPadScanStop, 1000) == WAIT_TIMEOUT);

		if (pModule)
			FreeLibraryAndExitThread((HMODULE)pModule, 0);
		return 0;
	}

	void PadRead_StartScan()
	{
		MEMORY_BASIC_INFORMATION info;
		HMODULE hModule = NULL;
		DWORD   dwThread;

		// This module, if it is a DLL: a reference for the thread
		if (VirtualQuery((LPCVOID)PadRead_ScanThread, &info, sizeof(info)) &&
			(HMODULE)info.AllocationBase != GetModuleHandle(NULL))
		{
			char szPath[MAX_PATH];

			if (GetModuleFileName((HMODULE)info.AllocationBase, szPath, sizeof(szPath)))
				hModule = LoadLibrary(szPath);
		}

		s_hPadScanStop = CreateEvent(NULL, TRUE, FALSE, NULL);
		if (s_hPadScanStop)
			s_hPadScanThread = CreateThread(NULL, 0, PadRead_ScanThread, (LPVOID)hModule, 0, &dwThread);

		if (!s_hPadScanThread)
		{
			// No thread: the frame scans, once a second
			if (s_hPadScanStop)
				CloseHandle(s_hPadScanStop);
			s_hPadScanStop = NULL;
			if (hModule)
				FreeLibrary(hModule);
		}
	}

	// Can there be a pad at all: XInput loads, or the test pad is on.
	// Decided once.
	bool PadRead_Available()
	{
		static const char* const dlls[] = { "xinput1_4.dll", "xinput1_3.dll", "xinput9_1_0.dll" };
		const char* pStall;
		int i;

		if (s_nPadAvailable >= 0)
			return s_nPadAvailable != 0;

		s_pPadTestFile = getenv("NOLF2SRC_PADTEST");

		if (s_pPadTestFile && !*s_pPadTestFile)
			s_pPadTestFile = NULL;

		if (s_pPadTestFile)
		{
			pStall = getenv("NOLF2SRC_PADTEST_STALL");
			s_dwPadTestStall = pStall ? (DWORD)atoi(pStall) : 0;
			InitializeCriticalSection(&s_PadTestLock);
			s_pPadGetState = PadRead_TestGetState;
		}

		for (i = 0; i < 3 && !s_pPadGetState; i++)
		{
			HMODULE hXInput = LoadLibrary(dlls[i]);

			if (hXInput)
			{
				s_pPadGetState = (PadXInputGetState)GetProcAddress(hXInput, "XInputGetState");

				if (!s_pPadGetState)
					FreeLibrary(hXInput);
			}
		}

		s_nPadAvailable = s_pPadGetState ? 1 : 0;
		if (s_nPadAvailable)
			PadRead_StartScan();
		return s_nPadAvailable != 0;
	}

	// The pad's state; false (and everything released) when none is
	// connected.
	bool PadRead_State(PadState* pPad)
	{
		PadXInputState state;
		LONG           nSlot;
		DWORD          dwNow;

		memset(pPad, 0, sizeof(*pPad));

		if (!PadRead_Available())
			return false;

		nSlot = s_lPadSlot;
		if (nSlot >= 0)
		{
			if (s_pPadGetState(nSlot, &state) == ERROR_SUCCESS)
			{
				*pPad = state.Gamepad;
				return true;
			}

			// Gone: the scan looks for one again
			InterlockedExchange((LONG*)&s_lPadSlot, -1);
		}

		if (s_hPadScanThread)
			return false;

		dwNow = GetTickCount();

		if (s_bPadScanned && dwNow - s_dwPadLastScan < 1000)
			return false;

		s_bPadScanned   = true;
		s_dwPadLastScan = dwNow;

		PadRead_Scan();
		nSlot = s_lPadSlot;
		if (nSlot >= 0 && s_pPadGetState(nSlot, &state) == ERROR_SUCCESS)
		{
			*pPad = state.Gamepad;
			return true;
		}
		return false;
	}

	// Stop the scan's thread (and wait for it, two seconds at most).
	void PadRead_Term()
	{
		if (s_hPadScanThread)
		{
			SetEvent(s_hPadScanStop);
			WaitForSingleObject(s_hPadScanThread, 2000);
			CloseHandle(s_hPadScanThread);
			CloseHandle(s_hPadScanStop);
			s_hPadScanThread = NULL;
			s_hPadScanStop   = NULL;
		}
	}
}

#endif // __NOLF2SRC_PADREAD_H__
