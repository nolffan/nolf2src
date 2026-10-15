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
//           The first connected XInput pad (slot 0..3; an empty slot is
//           slow to ask about, so the slots are looked through at most once
//           a second while none is connected), from whichever of
//           xinput1_4 / 1_3 / 9_1_0 loads, looked up at run time: VC6 and
//           the DirectX 8.1 SDK predate XInput, so its two types are
//           declared here.
//
//           The test pad: with NOLF2SRC_PADTEST naming a file, XInput is
//           not used and the pad's state is that file's one line,
//           "<buttons> <lx> <ly> <rx> <ry> <lt> <rt>" in XInput's units
//           (XINPUT_GAMEPAD's wButtons; the sticks -32768..32767, y up
//           positive; the triggers 0..255), read again every 15 ms; no file
//           (or one that does not parse) is no pad connected.
//           tools/playtest.sh's `pad` command writes it.
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
	PadXInputGetState	s_pPadGetState;
	int					s_nPadSlot = -1;		// the slot being read, -1: none
	DWORD				s_dwPadLastScan;
	bool				s_bPadScanned;

	const char*			s_pPadTestFile;			// NOLF2SRC_PADTEST
	bool				s_bPadTestRead;
	DWORD				s_dwPadTestRead;
	bool				s_bPadTestPad;
	PadState			s_PadTestState;

	// Can there be a pad at all: XInput loads, or the test pad is on.
	// Decided once.
	bool PadRead_Available()
	{
		static const char* const dlls[] = { "xinput1_4.dll", "xinput1_3.dll", "xinput9_1_0.dll" };
		int i;

		if (s_nPadAvailable >= 0)
			return s_nPadAvailable != 0;

		s_pPadTestFile = getenv("NOLF2SRC_PADTEST");

		if (s_pPadTestFile && !*s_pPadTestFile)
			s_pPadTestFile = NULL;

		if (s_pPadTestFile)
		{
			s_nPadAvailable = 1;
			return true;
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
		return s_nPadAvailable != 0;
	}

	// The test pad's state, read again at most every 15 ms (a file's time
	// is only to the second, so it is not asked).
	bool PadRead_Test(PadState* pPad)
	{
		DWORD dwNow = GetTickCount();

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

		*pPad = s_PadTestState;
		return s_bPadTestPad;
	}

	// The pad's state; false (and everything released) when none is
	// connected.
	bool PadRead_State(PadState* pPad)
	{
		PadXInputState state;
		DWORD          dwNow;
		int            i;

		memset(pPad, 0, sizeof(*pPad));

		if (!PadRead_Available())
			return false;

		if (s_pPadTestFile)
		{
			if (!PadRead_Test(pPad))
			{
				memset(pPad, 0, sizeof(*pPad));
				return false;
			}
			return true;
		}

		if (s_nPadSlot >= 0)
		{
			if (s_pPadGetState(s_nPadSlot, &state) == ERROR_SUCCESS)
			{
				*pPad = state.Gamepad;
				return true;
			}

			s_nPadSlot = -1;
		}

		dwNow = GetTickCount();

		if (s_bPadScanned && dwNow - s_dwPadLastScan < 1000)
			return false;

		s_bPadScanned   = true;
		s_dwPadLastScan = dwNow;

		for (i = 0; i < 4; i++)
		{
			if (s_pPadGetState(i, &state) == ERROR_SUCCESS)
			{
				s_nPadSlot = i;
				*pPad      = state.Gamepad;
				return true;
			}
		}

		return false;
	}
}

#endif // __NOLF2SRC_PADREAD_H__
