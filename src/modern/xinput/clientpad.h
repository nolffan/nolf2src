// ----------------------------------------------------------------------- //
//
// MODULE  : clientpad.h
//
// PURPOSE : The modern build's controller, the client's half (MODERN.md
//           M-G47, M-G60, M-G61, M-G62).  The engine's ##gamepad device
//           (gamepad_device.h, M-E20) gives the pad's buttons to the
//           bindings like any key's; this reads the pad itself for what must
//           not depend on them: the sticks (analog look and movement, the
//           vehicles), the keys the menus and screens take, A in a
//           cut-scene and on the death screen, and the choices of a
//           dialogue decision.  The retail files call into these from
//           NOLF2SRC_MODERN blocks; clientpad.cpp, the implementation, is
//           compiled as part of GameClientShell.cpp.
//
//           Modern build only (NOLF2SRC_MODERN).
//
// ----------------------------------------------------------------------- //

#ifndef __NOLF2SRC_CLIENTPAD_H__
#define __NOLF2SRC_CLIENTPAD_H__

class CUserProfile;

// CGameClientShell::Update, every frame, menus too: read the pad, and the
// menus' keys and A's
void	Pad_Update(float fFrameTime);

// M-E59: CGameClientShell::OnEngineTerm: stop looking for a pad (the
// thread that does must end before the DLL is unloaded)
void	Pad_Term();

// M-G47: the right stick, as this frame's turn (yaw) and look (pitch) in
// radians; 0 outside play
void	Pad_GetLook(float* pYaw, float* pPitch);

// M-G47: the left stick: the movement flags by its direction, and running
// past three-quarters (bCanRun: not ducking or leaning)
void	Pad_MoveFlags(uint32* pdwFlags, bool bCanRun);

// M-G47: the left stick past its dead zone, -1..1 (forward positive); false
// when it is not pushed
bool	Pad_GetMove(float* pRight, float* pForward);

// M-G47: the share of the walking speed the stick asks for (1 when it is
// not pushed, or pushed to run)
float	Pad_SpeedScale();

// M-G47: on the snowmobile, the stick's throttle, brake and steering
void	Pad_VehicleFlags(uint32* pdwFlags);

// M-G61: the Controls screen is waiting for a control to bind; the pad's
// menu keys stop meanwhile
void	Pad_SetCapture(bool bCapture);

// M-G60: give the profile's controller column the default layout, leaving
// a command the player has bound on the controller, and a button already
// bound, alone (bReplace: the column cleared first, Restore controller
// defaults)
void	Pad_DefaultBindings(CUserProfile* pProfile, bool bReplace);

#endif // __NOLF2SRC_CLIENTPAD_H__
