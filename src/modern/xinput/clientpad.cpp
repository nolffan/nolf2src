// ----------------------------------------------------------------------- //
//
// MODULE  : clientpad.cpp
//
// PURPOSE : The modern build's controller, the client's half.  See
//           clientpad.h.  #included once, by GameClientShell.cpp, in a
//           NOLF2SRC_MODERN block (CShell.dll's project files are the
//           retail ones, so a modern source of its own would have no
//           place in them).
//
//           The pad is read once a frame (Pad_Update), while the game's
//           window is the foreground one, through padread.h -- the reader
//           the engine's ##gamepad device uses, so the test pad
//           (NOLF2SRC_PADTEST) drives both.
//
//           Look (M-G47): the right stick past a radial dead zone
//           (PadLookDeadZone), the rest of its travel rescaled to 0..1 and
//           raised to PadLookCurve (fine aim near the centre), is a turn
//           rate: 180 degrees a second across, 120 up and down, times
//           PadLookSpeed and the frame time.  PlayerMgr adds it to the
//           mouse's turn, so it slows with the zoom as the mouse does;
//           PadInvertY turns its up and down over (the mouse's own invert
//           and mouse look setting do not apply to it).
//
//           Movement (M-G47): the left stick past PadMoveDeadZone is a
//           direction and a deflection.  The direction sets the movement
//           flags (by octant: what the animations and the server see) and
//           the acceleration; the deflection the speed: past three-quarters
//           it runs (the Run command held turns that over, as Shift does
//           the keyboard's run; RunLock is not used with the stick), below
//           it walks at a share of the walking speed, never less than a
//           third.  On the snowmobile the stick is the throttle and brake
//           (up, down) and the steering (left, right).
//
//           Keys (M-G61): outside play -- the menus, the screens, a popup,
//           the in-game menus, a paused game, a movie -- the d-pad or the
//           left stick is the arrow keys (repeating while held), A is
//           Enter, B and Start are Escape; in play Start is Escape (the
//           menu), and A, in a cut-scene or once dead, is Space (skips the
//           cut-scene; goes on to the mission-failure screen).  They go
//           through the client shell's own OnKeyDown / OnKeyUp, as the
//           engine delivers a key.  Not while the Controls screen waits for
//           a control to bind.
//
//           Decisions (M-G61): while a dialogue decision is up, the d-pad
//           moves a highlight over its choices, A takes the highlighted
//           one and B declines (Escape); the engine's bindings do not see
//           those buttons meanwhile (PadHoldButtons, M-E20).
//
//           Modern build only (NOLF2SRC_MODERN).
//
// ----------------------------------------------------------------------- //

#include "GameClientShell.h"
#include "InterfaceMgr.h"
#include "PlayerMgr.h"
#include "HUDMgr.h"
#include "HUDDecision.h"
#include "ProfileMgr.h"
#include "CommandIDs.h"
#include "SharedMovement.h"
#include "VarTrack.h"
#include "ClientUtilities.h"
#include "padread.h"
#include "clientpad.h"

#include <math.h>

extern HWND g_hMainWnd;		// GameClientShell.cpp

namespace
{
	VarTrack	s_vtLookSpeed;
	VarTrack	s_vtLookCurve;
	VarTrack	s_vtLookDeadZone;
	VarTrack	s_vtMoveDeadZone;
	VarTrack	s_vtInvertY;
	bool		s_bVarsInitted;

	const float	c_fYawRate		= 3.14159265f;			// 180 degrees a second
	const float	c_fPitchRate	= 3.14159265f * 2 / 3;	// 120
	const float	c_fRunAt		= 0.75f;				// of the stick's travel past the dead zone
	const float	c_fMinWalk		= 1.0f / 3;
	const float	c_fOctant		= 0.3827f;				// sin(22.5 degrees)
	const float	c_fRepeatDelay	= 0.4f;					// menu keys: the first repeat, then every
	const float	c_fRepeatRate	= 0.12f;

	// The buttons a decision takes from the bindings while it is up.
	const WORD	c_wDecisionButtons = PAD_A | PAD_B | PAD_DPAD;

	PadState	s_Pad;
	bool		s_bPad;									// connected, and the game has the foreground
	float		s_fFrameTime;
	float		s_fMoveX, s_fMoveY, s_fMoveMag;			// past the dead zone; 0 when not moving
	float		s_fLookX, s_fLookY;
	bool		s_bCapture;
	int			s_nHold = -1;							// PadHoldButtons as last written

	// The arrow key held, and its repeat timer.
	WORD		s_wPrevButtons;
	int			s_nHeldKey;
	float		s_fHeldTime;
	float		s_fNextRepeat;

	struct PadDefault
	{
		int			nCommand;
		const char*	pButton;
	};

	// M-G60: the controller's default layout. Start is not bound: it is
	// Escape, the menu. Not the in-game menus' other commands either:
	// Back opens the menu bar on Mission, and the d-pad's left and right go
	// from one menu to the next.
	const PadDefault s_PadDefaults[] =
	{
		{ COMMAND_ID_FIRING,		"Right Trigger" },
		{ COMMAND_ID_ZOOM_IN,		"Left Trigger" },
		{ COMMAND_ID_JUMP,			"A Button" },
		{ COMMAND_ID_DUCK,			"B Button" },
		{ COMMAND_ID_ACTIVATE,		"X Button" },
		{ COMMAND_ID_RELOAD,		"Y Button" },
		{ COMMAND_ID_NEXT_WEAPON,	"Right Bumper" },
		{ COMMAND_ID_PREV_WEAPON,	"Left Bumper" },
		{ COMMAND_ID_MISSION,		"Back" },
		{ COMMAND_ID_RUN,			"Left Stick Click" },
		{ COMMAND_ID_CENTERVIEW,	"Right Stick Click" },
		{ COMMAND_ID_NEXT_AMMO,		"D-Pad Up" },
		{ COMMAND_ID_HOLSTER,		"D-Pad Down" },
		{ COMMAND_ID_FLASHLIGHT,	"D-Pad Left" },
		{ COMMAND_ID_MOVE_BODY,		"D-Pad Right" },
	};

	void InitVars()
	{
		if (s_bVarsInitted)
			return;

		s_vtLookSpeed.Init(g_pLTClient, "PadLookSpeed", LTNULL, 1.0f);
		s_vtLookCurve.Init(g_pLTClient, "PadLookCurve", LTNULL, 2.0f);
		s_vtLookDeadZone.Init(g_pLTClient, "PadLookDeadZone", LTNULL, 0.15f);
		s_vtMoveDeadZone.Init(g_pLTClient, "PadMoveDeadZone", LTNULL, 0.2f);
		s_vtInvertY.Init(g_pLTClient, "PadInvertY", LTNULL, 0.0f);
		s_bVarsInitted = true;
	}

	// A stick, -32768..32767 a side (y up positive), past a radial dead
	// zone: its direction kept, its length rescaled from the dead zone's
	// edge to 1.  Returns the length.
	float Stick(SHORT nX, SHORT nY, float fDeadZone, float* pX, float* pY)
	{
		float fX = nX / 32767.0f, fY = nY / 32767.0f;
		float fLen = (float)sqrt(fX * fX + fY * fY);
		float fScaled;

		if (fDeadZone < 0.0f) fDeadZone = 0.0f;
		if (fDeadZone > 0.9f) fDeadZone = 0.9f;

		if (fLen <= fDeadZone)
		{
			*pX = *pY = 0.0f;
			return 0.0f;
		}

		fScaled = (fLen - fDeadZone) / (1.0f - fDeadZone);
		if (fScaled > 1.0f)
			fScaled = 1.0f;

		*pX = fX / fLen * fScaled;
		*pY = fY / fLen * fScaled;
		return fScaled;
	}

	// A key, as the engine delivers one: through IClientShell, where the
	// two are public.
	void PressKey(int nKey)
	{
		IClientShell* pShell = g_pGameClientShell;

		pShell->OnKeyDown(nKey, 1);
		pShell->OnKeyUp(nKey);
	}

	bool InPlay()
	{
		return g_pInterfaceMgr && g_pInterfaceMgr->GetGameState() == GS_PLAYING;
	}

	// The arrow key the d-pad (or, bStick, the left stick) holds, or 0.
	int Direction(bool bStick)
	{
		float fX, fY;

		if (s_Pad.wButtons & PAD_DPAD_UP)		return VK_UP;
		if (s_Pad.wButtons & PAD_DPAD_DOWN)		return VK_DOWN;
		if (s_Pad.wButtons & PAD_DPAD_LEFT)		return VK_LEFT;
		if (s_Pad.wButtons & PAD_DPAD_RIGHT)	return VK_RIGHT;

		if (!bStick || Stick(s_Pad.sThumbLX, s_Pad.sThumbLY, 0.5f, &fX, &fY) <= 0.0f)
			return 0;

		if (fabs(fY) >= fabs(fX))
			return fY > 0.0f ? VK_UP : VK_DOWN;

		return fX > 0.0f ? VK_RIGHT : VK_LEFT;
	}

	// The key held this frame: true once when it goes down, then again
	// after c_fRepeatDelay and every c_fRepeatRate while it is held.
	bool Repeat(int nKey)
	{
		if (nKey != s_nHeldKey)
		{
			s_nHeldKey    = nKey;
			s_fHeldTime   = 0.0f;
			s_fNextRepeat = c_fRepeatDelay;
			return nKey != 0;
		}

		if (!nKey)
			return false;

		s_fHeldTime += s_fFrameTime;

		if (s_fHeldTime >= s_fNextRepeat)
		{
			s_fNextRepeat += c_fRepeatRate;
			return true;
		}

		return false;
	}

	void SetHold(WORD wButtons)
	{
		if (s_nHold != (int)wButtons)
		{
			s_nHold = (int)wButtons;
			WriteConsoleInt("PadHoldButtons", s_nHold);
		}
	}

	// In play: Start, A in a cut-scene or once dead, a decision's choices.
	void UpdatePlay(WORD wPressed)
	{
		bool bDecision = g_pDecision && g_pDecision->IsVisible() && s_bPad;
		int  nKey;

		SetHold(bDecision ? c_wDecisionButtons : 0);

		if (bDecision)
		{
			// a highlight from the start, so that A takes the first choice
			g_pDecision->PadMove(0);

			nKey = Direction(false);

			if (Repeat(nKey))
			{
				if (nKey == VK_UP)
					g_pDecision->PadMove(-1);
				else if (nKey == VK_DOWN)
					g_pDecision->PadMove(1);
			}

			if (wPressed & PAD_A)
				g_pDecision->PadChoose();
			else if (wPressed & PAD_B)
				PressKey(VK_ESCAPE);		// declines it (CInterfaceMgr::OnKeyDown)

			return;
		}

		s_nHeldKey = 0;

		if (wPressed & PAD_START)
			PressKey(VK_ESCAPE);

		// A skips a cut-scene, and goes on from the death screen: both take
		// Space (any key, for the second), and A's own binding (Jump) is a
		// command, not a key.
		if ((wPressed & PAD_A) && g_pPlayerMgr &&
			(g_pPlayerMgr->IsUsingExternalCamera() || g_pPlayerMgr->IsPlayerDead()))
		{
			PressKey(VK_SPACE);
		}
	}

	// Outside play: the keys of the menus and screens.
	void UpdateMenus(WORD wPressed)
	{
		int nKey;

		SetHold(0);

		if (s_bCapture)
		{
			s_nHeldKey = 0;
			return;
		}

		if (wPressed & PAD_A)
			PressKey(VK_RETURN);

		if (wPressed & (PAD_B | PAD_START))
			PressKey(VK_ESCAPE);

		nKey = Direction(true);

		if (Repeat(nKey))
			PressKey(nKey);
	}

	int FindCommand(int nCommandID)
	{
		int c;

		for (c = 0; c < g_kNumCommands; c++)
		{
			if (GetCommandData(c)->nCommandID == nCommandID)
				return c;
		}

		return -1;
	}
}

void Pad_Update(float fFrameTime)
{
	WORD wPressed;

	InitVars();

	s_fFrameTime = fFrameTime;

	s_bPad = PadRead_Available() && GetForegroundWindow() == g_hMainWnd && PadRead_State(&s_Pad);

	if (!s_bPad)
		memset(&s_Pad, 0, sizeof(s_Pad));

	wPressed       = s_Pad.wButtons & ~s_wPrevButtons;
	s_wPrevButtons = s_Pad.wButtons;

	if (InPlay())
	{
		s_fMoveMag = Stick(s_Pad.sThumbLX, s_Pad.sThumbLY, s_vtMoveDeadZone.GetFloat(0.2f), &s_fMoveX, &s_fMoveY);
		Stick(s_Pad.sThumbRX, s_Pad.sThumbRY, s_vtLookDeadZone.GetFloat(0.15f), &s_fLookX, &s_fLookY);
		UpdatePlay(wPressed);
	}
	else
	{
		s_fMoveX = s_fMoveY = s_fMoveMag = 0.0f;
		s_fLookX = s_fLookY = 0.0f;
		UpdateMenus(wPressed);
	}
}

void Pad_Term()
{
	PadRead_Term();
}

void Pad_GetLook(float* pYaw, float* pPitch)
{
	float fLen = (float)sqrt(s_fLookX * s_fLookX + s_fLookY * s_fLookY);
	float fScale, fCurve;

	*pYaw = *pPitch = 0.0f;

	if (fLen <= 0.0f)
		return;

	// The curve on the length, so that the direction stays the stick's.
	fCurve = s_vtLookCurve.GetFloat(2.0f);
	if (fCurve < 1.0f)
		fCurve = 1.0f;

	fScale = (float)pow(fLen, fCurve) / fLen * s_vtLookSpeed.GetFloat(1.0f) * s_fFrameTime;

	*pYaw = s_fLookX * fScale * c_fYawRate;

	// The stick's up is the camera's pitch up (negative) unless inverted.
	if (s_vtInvertY.GetFloat(0.0f) != 0.0f)
		*pPitch = s_fLookY * fScale * c_fPitchRate;
	else
		*pPitch = -s_fLookY * fScale * c_fPitchRate;
}

bool Pad_GetMove(float* pRight, float* pForward)
{
	if (s_fMoveMag <= 0.0f)
		return false;

	*pRight   = s_fMoveX;
	*pForward = s_fMoveY;
	return true;
}

void Pad_MoveFlags(uint32* pdwFlags, bool bCanRun)
{
	bool bRun;

	if (s_fMoveMag <= 0.0f)
		return;

	if (s_fMoveY >  c_fOctant * s_fMoveMag) *pdwFlags |= BC_CFLG_FORWARD;
	if (s_fMoveY < -c_fOctant * s_fMoveMag) *pdwFlags |= BC_CFLG_REVERSE;
	if (s_fMoveX >  c_fOctant * s_fMoveMag) *pdwFlags |= BC_CFLG_STRAFE_RIGHT;
	if (s_fMoveX < -c_fOctant * s_fMoveMag) *pdwFlags |= BC_CFLG_STRAFE_LEFT;

	// The deflection decides walking and running, not RunLock; Run held
	// turns it over.
	bRun = s_fMoveMag >= c_fRunAt;
	if (g_pLTClient->IsCommandOn(COMMAND_ID_RUN))
		bRun = !bRun;

	if (bRun && bCanRun)
		*pdwFlags |= BC_CFLG_RUN;
	else
		*pdwFlags &= ~BC_CFLG_RUN;
}

void Pad_VehicleFlags(uint32* pdwFlags)
{
	if (s_fMoveMag <= 0.0f)
		return;

	// Forward and reverse as the snowmobile has them: reverse wins.
	if (s_fMoveY < -c_fOctant * s_fMoveMag)
	{
		*pdwFlags |= BC_CFLG_REVERSE;
		*pdwFlags &= ~BC_CFLG_FORWARD;
	}
	else if (s_fMoveY > c_fOctant * s_fMoveMag)
	{
		*pdwFlags |= BC_CFLG_FORWARD;
	}

	if (s_fMoveX >  c_fOctant * s_fMoveMag) *pdwFlags |= BC_CFLG_RIGHT;
	if (s_fMoveX < -c_fOctant * s_fMoveMag) *pdwFlags |= BC_CFLG_LEFT;
}

float Pad_SpeedScale()
{
	float fScale;

	if (s_fMoveMag <= 0.0f || s_fMoveMag >= c_fRunAt)
		return 1.0f;

	fScale = s_fMoveMag / c_fRunAt;
	return fScale < c_fMinWalk ? c_fMinWalk : fScale;
}

void Pad_SetCapture(bool bCapture)
{
	s_bCapture = bCapture;
}

void Pad_DefaultBindings(CUserProfile* pProfile, bool bReplace)
{
	const int nPad = 2;		// the profile's third column: the joystick or gamepad
	int i, c;

	if (bReplace)
	{
		for (c = 0; c < g_kNumCommands; c++)
		{
			CBindingData* pData = pProfile->FindBinding(c);

			if (pData)
			{
				pData->strRealName[nPad][0]    = '\0';
				pData->strTriggerName[nPad][0] = '\0';
				pData->nDeviceObjectId[nPad]   = 0;
			}
		}
	}

	for (i = 0; i < (int)(sizeof(s_PadDefaults) / sizeof(s_PadDefaults[0])); i++)
	{
		CBindingData* pData;
		bool bTaken = false;

		c = FindCommand(s_PadDefaults[i].nCommand);
		pData = c >= 0 ? pProfile->FindBinding(c) : LTNULL;

		// not over a binding the player made
		if (!pData || (pData->strRealName[nPad][0] && pData->strRealName[nPad][0] != ' '))
			continue;

		for (c = 0; c < g_kNumCommands && !bTaken; c++)
		{
			CBindingData* pOther = pProfile->FindBinding(c);
			bTaken = pOther && !stricmp(pOther->strRealName[nPad], s_PadDefaults[i].pButton);
		}

		if (bTaken)
			continue;

		SAFE_STRCPY(pData->strRealName[nPad], s_PadDefaults[i].pButton);
		SAFE_STRCPY(pData->strTriggerName[nPad], s_PadDefaults[i].pButton);
		pData->nDeviceObjectId[nPad] = 0;
	}
}
