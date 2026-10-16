// ----------------------------------------------------------------------- //
//
// MODULE  : InterfaceTimer.h
//
// PURPOSE : Definition of InterfaceTimer class
//
// CREATED : 10/18/99
//
// (c) 1999 Monolith Productions, Inc.  All Rights Reserved
//
// ----------------------------------------------------------------------- //

#ifndef __INTERFACE_TIMER_H__
#define __INTERFACE_TIMER_H__

#include "ltbasedefs.h"
#include "iltfontmanager.h"
#include "TeamMgr.h"

extern ILTFontManager*	g_pFontManager;

class CInterfaceTimer
{
	public:

		CInterfaceTimer();
		~CInterfaceTimer();

		void		SetTeamId( uint8 nTeamId ) { m_nTeamId = nTeamId; }
		uint8		GetTeamId( ) const { return m_nTeamId; }

		void		Draw();

		// RETAIL: reconstructed from the retail 1.3 CShell.dll (0x1005c484,
		// 0x10063f4e): the timer has no m_fTimeLeft, and SetTime only
		// stores; the source release also kept the time left while paused.
#ifdef NOLF2SRC_MODERN
		// MODERN.md M-G85: the time left is taken when the timer is set,
		// and kept while it is paused.
		void        SetTime(LTFLOAT fTime, bool bPause);
#else
		void        SetTime(LTFLOAT fTime, bool bPause) { m_fTime = fTime; m_bPause = bPause; }
#endif
		float		GetTime() const { return m_fTime; }

	private:

		// Server game time when timer runs out.
		float					m_fTime;
#ifdef NOLF2SRC_MODERN
		float					m_fTimeLeft;	// M-G85: the time left, kept while paused
#endif
		bool					m_bPause;
		uint8					m_nTeamId;

		CUIFormattedPolyString	*m_pTimeStr;

		LTIntPt			m_BasePos;
		uint8			m_nBaseSize;
		uint32			m_nColor;
};

#endif  // __INTERFACE_TIMER_H__