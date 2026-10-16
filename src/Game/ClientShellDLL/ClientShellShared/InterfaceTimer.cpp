// ----------------------------------------------------------------------- //
//
// MODULE  : InterfaceTimer.cpp
//
// PURPOSE : Implementation of InterfaceTimer class
//
// CREATED : 10/18/99
//
// (c) 1999-2001 Monolith Productions, Inc.  All Rights Reserved
//
// ----------------------------------------------------------------------- //

#include "stdafx.h"
#include <stdio.h>
#include "InterfaceTimer.h"
#include "GameClientShell.h"
#include "iltclient.h"
#include "InterfaceResMgr.h"

static void BuildTimeString(char* aBuffer, int nTime);

CInterfaceTimer::CInterfaceTimer() 
{
	m_fTime		= 0.0f;
#ifdef NOLF2SRC_MODERN
	m_fTimeLeft	= 0.0f;	// MODERN.md M-G85
#endif
	m_bPause	= LTFALSE;
	m_pTimeStr	= LTNULL;
	m_nBaseSize = 0;
	m_nTeamId	= INVALID_TEAM;
	m_nColor	= argbWhite;
}

CInterfaceTimer::~CInterfaceTimer() 
{ 
	if (m_pTimeStr) 
		g_pFontManager->DestroyPolyString(m_pTimeStr); 
}


// ----------------------------------------------------------------------- //
//
//	ROUTINE:	CInterfaceTimer::Draw()
//
//	PURPOSE:	Handle drawing the stats
//
// ----------------------------------------------------------------------- //

void CInterfaceTimer::Draw()
{

	// RETAIL: reconstructed from the retail 1.3 CShell.dll (0x100eb260): the
	// time left is counted from the game time on every draw, paused or not.
#ifdef NOLF2SRC_MODERN
	// MODERN.md M-G85: not while the timer is paused.
	if( !m_bPause )
		m_fTimeLeft = m_fTime - g_pLTClient->GetGameTime( );
	float fTimeLeft = m_fTimeLeft;
#else
	float fTimeLeft = m_fTime - g_pLTClient->GetGameTime( );
#endif

	// Update/Draw the timer if there is anytime left...
	if( fTimeLeft <= 0.0f )
		return;

	// Draw the string to the surface...

	int nMinutes = int(fTimeLeft) / 60;
	int nSeconds = fTimeLeft > 60.0 ? int(fTimeLeft) % 60 : int(fTimeLeft);

	char aBuffer[8];
	char aMinutes[8];
	char aSeconds[8];
	BuildTimeString(aMinutes, nMinutes);
	BuildTimeString(aSeconds, nSeconds);
	uint8 nFont = 0;
	LTVector vColor;

	sprintf(aBuffer, "%s:%s", aMinutes, aSeconds);
	
 	if (!m_pTimeStr)
 	{
		switch( m_nTeamId )
		{
			// Team1.
			case 0:
				nFont = (uint8)g_pLayoutMgr->GetInt("Miscellaneous","Team1TimerFont");
				m_nBaseSize = (uint8)g_pLayoutMgr->GetInt("Miscellaneous","Team1TimerSize");
				m_BasePos = g_pLayoutMgr->GetPoint("Miscellaneous","Team1TimerPos");
				vColor = g_pLayoutMgr->GetVector("Miscellaneous","Team1TimerColor");
				break;
			// Team2.
			case 1:
				nFont = (uint8)g_pLayoutMgr->GetInt("Miscellaneous","Team2TimerFont");
				m_nBaseSize = (uint8)g_pLayoutMgr->GetInt("Miscellaneous","Team2TimerSize");
				m_BasePos = g_pLayoutMgr->GetPoint("Miscellaneous","Team2TimerPos");
				vColor = g_pLayoutMgr->GetVector("Miscellaneous","Team2TimerColor");
				break;
			// Unspecified.
			default:
				nFont = (uint8)g_pLayoutMgr->GetInt("Miscellaneous","TimerFont");
				m_nBaseSize = (uint8)g_pLayoutMgr->GetInt("Miscellaneous","TimerSize");
				m_BasePos = g_pLayoutMgr->GetPoint("Miscellaneous","TimerPos");
				vColor = g_pLayoutMgr->GetVector("Miscellaneous","TimerColor");
				break;
		}

		if (m_nBaseSize == 0) 
			m_nBaseSize = 24;

		if (m_BasePos.x == 0)
			m_BasePos = LTIntPt(320,40);

		CUIFont* pFont = g_pInterfaceResMgr->GetFont(nFont);
		m_pTimeStr = g_pFontManager->CreateFormattedPolyString(pFont, aBuffer);
		m_pTimeStr->SetAlignmentH(CUI_HALIGN_CENTER);

		m_nColor = SET_ARGB( 0xFF, ( uint8 )vColor.x, ( uint8 )vColor.y, ( uint8 )vColor.z );
 	}
 	else
 	{
		m_pTimeStr->SetText(aBuffer);
 	}

	uint8 nSize = (uint8)((LTFLOAT)m_nBaseSize * g_pInterfaceResMgr->GetXRatio());
	m_pTimeStr->SetCharScreenHeight(nSize);

	// Position the text
	float x = (float)m_BasePos.x * g_pInterfaceResMgr->GetXRatio();
	float y = (float)m_BasePos.y * g_pInterfaceResMgr->GetYRatio();
#ifdef NOLF2SRC_MODERN
	x += (float)g_pInterfaceResMgr->GetHUDXOffset(m_BasePos.x);	// MODERN.md M-G2
#endif

	m_pTimeStr->SetPosition( x+2.0f, y+2.0f);
	m_pTimeStr->SetColor(argbBlack);
	m_pTimeStr->Render();
	
	m_pTimeStr->SetPosition( x, y );
	m_pTimeStr->SetColor(m_nColor);
	m_pTimeStr->Render();
}

#ifdef NOLF2SRC_MODERN
// MODERN.md M-G85: the server sends the game time the timer ends at, which
// for a paused timer is the time left counted from when it was sent. Take
// the time left then; Draw counts it down only while the timer runs.
void CInterfaceTimer::SetTime(LTFLOAT fTime, bool bPause)
{
	m_fTime		= fTime;
	m_fTimeLeft	= fTime - g_pLTClient->GetGameTime( );
	m_bPause	= bPause;
}

#endif
static void BuildTimeString(char* aBuffer, int nTime)
{
	if (nTime > 9)
	{
		sprintf(aBuffer, "%d", nTime);
	}
	else
	{
		sprintf(aBuffer, "0%d", nTime);
	}
}