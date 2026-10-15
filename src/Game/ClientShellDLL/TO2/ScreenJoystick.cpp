// ----------------------------------------------------------------------- //
//
// MODULE  : ScreenJoystick.cpp
//
// PURPOSE : Interface screen for joystick/gamepad settings
//
// (c) 1999-2001 Monolith Productions, Inc.  All Rights Reserved
//
// ----------------------------------------------------------------------- //

#include "stdafx.h"
#include "ScreenJoystick.h"
#include "ScreenMgr.h"
#include "ScreenCommands.h"
#include "GameSettings.h"
#include "InterfaceMgr.h"
#ifdef NOLF2SRC_MODERN
// MODERN.md M-G62: the controller's default buttons
#include "../modern/xinput/clientpad.h"
#endif

namespace
{
	int kGap = 200;
	int kWidth = 200;
#ifdef NOLF2SRC_MODERN
	void PadRestoreCallBack(LTBOOL bReturn, void *pData)
	{
		CScreenJoystick *pThisScreen = (CScreenJoystick *)pData;
		if (pThisScreen)
			pThisScreen->ConfirmPadRestore(bReturn);
	}

	int PadPercent(char const* pVar, float fDefault)
	{
		return (int)(100.0f * GetConsoleFloat(pVar, fDefault) + 0.5f);
	}
#endif
}


//////////////////////////////////////////////////////////////////////
// Construction/Destruction
//////////////////////////////////////////////////////////////////////

CScreenJoystick::CScreenJoystick()
{
	memset(m_nAxis,0,sizeof(m_nAxis));
	memset(m_nPOV,0,sizeof(m_nPOV));
#ifdef NOLF2SRC_MODERN
	m_nPadLookSpeed = 100;
	m_bPadInvert = LTFALSE;
	m_nPadLookDeadZone = 15;
	m_nPadMoveDeadZone = 20;
#endif

}

CScreenJoystick::~CScreenJoystick()
{

}

// Build the screen
LTBOOL CScreenJoystick::Build()
{
#ifdef NOLF2SRC_MODERN
	// MODERN.md M-G62: the controller's screen. Its axes are not bound
	// (the client reads the sticks, M-G47), so instead of the retail axis
	// assignments: the right stick's speed and direction, both sticks'
	// dead zones, and its default buttons back. The buttons themselves are
	// bound in Configure controls, like keys.
	CreateTitle(IDS_MODERN_PAD_TITLE);

	kGap = g_pLayoutMgr->GetScreenCustomInt(SCREEN_ID_JOYSTICK,"ColumnWidth");
	kWidth = 200;

	CLTGUISlider *pSlider = AddSlider(IDS_MODERN_PAD_LOOKSPEED, IDS_HELP_MODERN_PAD_LOOKSPEED, kGap, kWidth, -1, &m_nPadLookSpeed);
	pSlider->SetSliderRange(25, 300);
	pSlider->SetSliderIncrement(25);
	pSlider->SetNumericDisplay(LTTRUE);

	char szYes[16];
	char szNo[16];
	FormatString(IDS_YES,szYes,sizeof(szYes));
	FormatString(IDS_NO,szNo,sizeof(szNo));
	CLTGUIToggle *pToggle = AddToggle(IDS_MODERN_PAD_INVERT, IDS_HELP_MODERN_PAD_INVERT, kGap, &m_bPadInvert);
	pToggle->SetOnString(szYes);
	pToggle->SetOffString(szNo);

	pSlider = AddSlider(IDS_MODERN_PAD_LOOKDEADZONE, IDS_HELP_MODERN_PAD_LOOKDEADZONE, kGap, kWidth, -1, &m_nPadLookDeadZone);
	pSlider->SetSliderRange(0, 50);
	pSlider->SetSliderIncrement(5);
	pSlider->SetNumericDisplay(LTTRUE);

	pSlider = AddSlider(IDS_MODERN_PAD_MOVEDEADZONE, IDS_HELP_MODERN_PAD_MOVEDEADZONE, kGap, kWidth, -1, &m_nPadMoveDeadZone);
	pSlider->SetSliderRange(0, 50);
	pSlider->SetSliderIncrement(5);
	pSlider->SetNumericDisplay(LTTRUE);

	AddTextItem(IDS_MODERN_PAD_RESTORE, CMD_RESET_DEFAULTS, IDS_HELP_MODERN_PAD_RESTORE);
#else
	CreateTitle(IDS_TITLE_JOYSTICK);
	
	kGap = g_pLayoutMgr->GetScreenCustomInt(SCREEN_ID_JOYSTICK,"ColumnWidth");
	uint8 nLarge = g_pLayoutMgr->GetScreenCustomInt(SCREEN_ID_JOYSTICK,"HeaderFontSize");

	
	CLTGUICycleCtrl *pCtrl = AddCycle(IDS_JOYSTICK_AXIS, NULL, kGap, NULL, kDefaultPos, LTTRUE );
	pCtrl->AddString(LoadTempString(IDS_JOYSTICK_ACTION));
	pCtrl->SetFont(NULL,nLarge);
	m_nextPos.y += 8;

	for (int axis = 0; axis < g_pProfileMgr->GetNumAxis(); axis++)
	{
		CDeviceAxisData *pAxisData = g_pProfileMgr->GetAxisData(axis);
		if (!pAxisData || !strlen(pAxisData->m_sName)) continue;

		CLTGUICycleCtrl *pCtrl = AddCycle(pAxisData->m_sName, IDS_HELP_AXIS, kGap, &m_nAxis[axis] );
		pCtrl->SetParam1(axis);
		pCtrl->AddString(LoadTempString(IDS_JOYSTICK_AXISNONE));

		switch (pAxisData->m_nType)
		{
			case CONTROLTYPE_XAXIS:
			case CONTROLTYPE_RXAXIS:
			case CONTROLTYPE_ZAXIS:
				pCtrl->AddString(LoadTempString(IDS_JOYSTICK_TURN));
				pCtrl->AddString(LoadTempString(IDS_JOYSTICK_STRAFE));
				break;
			case CONTROLTYPE_YAXIS:
			case CONTROLTYPE_RYAXIS:
			case CONTROLTYPE_RZAXIS:
				pCtrl->AddString(LoadTempString(IDS_JOYSTICK_LOOK));
				pCtrl->AddString(LoadTempString(IDS_JOYSTICK_MOVE));
				pCtrl->AddString(LoadTempString(IDS_JOYSTICK_INVERT));
				break;
		}

//		pCtrl->NotifyOnChange(CMD_UPDATE,this);
	}

	for (int POV = 0; POV < g_pProfileMgr->GetNumPOV(); POV++)
	{
		CDevicePOVData *pPOVData = g_pProfileMgr->GetPOVData(POV);
		if (!pPOVData || !strlen(pPOVData->m_sName)) continue;

		CLTGUICycleCtrl *pCtrl = AddCycle(pPOVData->m_sName, IDS_HELP_POV, kGap, &m_nPOV[POV] );
		pCtrl->SetParam1(POV);
		pCtrl->AddString(LoadTempString(IDS_JOYSTICK_AXISNONE));

		pCtrl->AddString(LoadTempString(IDS_POV_LOOK));
		pCtrl->AddString(LoadTempString(IDS_POV_MOVE));
	}
#endif


	// Make sure to call the base class
	if (! CBaseScreen::Build()) return LTFALSE;

	UseBack(LTTRUE,LTTRUE);
	return LTTRUE;

}

uint32 CScreenJoystick::OnCommand(uint32 dwCommand, uint32 dwParam1, uint32 dwParam2)
{
	switch(dwCommand)
	{
	case CMD_UPDATE:
		{
			UpdateData();

		
			break;
		}
#ifdef NOLF2SRC_MODERN
	case CMD_RESET_DEFAULTS:
		{
			// M-G62: the controller's default buttons back
			MBCreate mb;
			mb.eType = LTMB_YESNO;
			mb.pFn = PadRestoreCallBack;
			mb.pData = this;
			g_pInterfaceMgr->ShowMessageBox(IDS_MODERN_PAD_CONFIRMRESTORE,&mb);
			break;
		}
#endif
	default:
		return CBaseScreen::OnCommand(dwCommand,dwParam1,dwParam2);

	}
	return 1;
};



#ifdef NOLF2SRC_MODERN
// M-G62: the controller's column of the bindings back to its defaults; the
// keyboard's and the mouse's are left as they are
void CScreenJoystick::ConfirmPadRestore(LTBOOL bConfirm)
{
	if (!bConfirm) return;

	CUserProfile *pProfile = g_pProfileMgr->GetCurrentProfile();
	pProfile->SetBindings();
	Pad_DefaultBindings(pProfile, true);
	pProfile->ApplyBindings();
	pProfile->Save();
}

#endif
// Change in focus
void CScreenJoystick::OnFocus(LTBOOL bFocus)
{
	CUserProfile *pProfile = g_pProfileMgr->GetCurrentProfile();
#ifdef NOLF2SRC_MODERN
	// M-G62: the controller's console variables (clientpad.cpp)
	if (bFocus)
	{
		m_nPadLookSpeed = PadPercent("PadLookSpeed", 1.0f);
		m_bPadInvert = (GetConsoleInt("PadInvertY", 0) != 0);
		m_nPadLookDeadZone = PadPercent("PadLookDeadZone", 0.15f);
		m_nPadMoveDeadZone = PadPercent("PadMoveDeadZone", 0.2f);

		UpdateData(LTFALSE);
	}
	else
	{
		UpdateData();

		WriteConsoleFloat("PadLookSpeed", (LTFLOAT)m_nPadLookSpeed / 100.0f);
		WriteConsoleInt("PadInvertY", m_bPadInvert ? 1 : 0);
		WriteConsoleFloat("PadLookDeadZone", (LTFLOAT)m_nPadLookDeadZone / 100.0f);
		WriteConsoleFloat("PadMoveDeadZone", (LTFLOAT)m_nPadMoveDeadZone / 100.0f);
	}
	CBaseScreen::OnFocus(bFocus);
	return;
#endif
	if (bFocus)
	{
		pProfile->SetJoystick();
		for (int axis = 0; axis < g_pProfileMgr->GetNumAxis(); axis++)
		{
			m_nAxis[axis] = pProfile->m_nAxis[axis];
		}
		for (int POV = 0; POV < g_pProfileMgr->GetNumPOV(); POV++)
		{
			m_nPOV[POV] = pProfile->m_nPOV[POV];
		}

	
        UpdateData(LTFALSE);
	}
	else
	{
		UpdateData();

		for (int axis = 0; axis < g_pProfileMgr->GetNumAxis(); axis++)
		{
			pProfile->m_nAxis[axis] = m_nAxis[axis];
		};
		for (int POV = 0; POV < g_pProfileMgr->GetNumPOV(); POV++)
		{
			pProfile->m_nPOV[POV] = m_nPOV[POV];
		};

		pProfile->ApplyJoystick();
		pProfile->Save();
	}
	CBaseScreen::OnFocus(bFocus);
}