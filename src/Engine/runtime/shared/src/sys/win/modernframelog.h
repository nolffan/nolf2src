#ifndef __MODERNFRAMELOG_H__
#define __MODERNFRAMELOG_H__

#ifdef NOLF2SRC_MODERN

// MODERN.md M-E58: FrameTimeLog, the frame's time by what it was spent on.
// A section adds the time from its constructor to its destructor to its
// part of the frame, on the main thread, while the log is on (one test of
// a flag while it is off). Sections nest: the shell's update holds the
// network, the server, the objects, the drawing and the present, the
// drawing holds the projected shadows (M-E69), and the log takes those out
// of what holds them (clientmgr.cpp). Here rather than in clientmgr.h so
// that the renderer can time its own parts.
enum
{
	MFL_VIDEO,
	MFL_SOUND,
	MFL_INPUT,
	MFL_SHELL,
	MFL_NET,
	MFL_SERVER,
	MFL_OBJECTS,
	MFL_RENDER,
	MFL_PRESENT,
	MFL_LIMIT,
	MFL_SHADOWS,
	MFL_COUNT
};

// MODERN.md M-E70: V-sync in a window under Wine is a cap, not a wait: the
// renderer presents at once and sets this to the monitor's refresh rate,
// which the frame limiter (clientmgr.cpp) then holds the game to; 0 when
// it does not apply.
extern uint32	g_nModernVSyncCapHz;

extern bool		g_bModernFrameLog;
extern DWORD	g_dwModernFrameLogThread;
extern __int64	g_aModernFrameTicks[MFL_COUNT];

class CModernFrameSection
{
public:
	CModernFrameSection(int nSection)
	{
		m_nSection = -1;
		if (g_bModernFrameLog && GetCurrentThreadId() == g_dwModernFrameLogThread)
		{
			m_nSection = nSection;
			QueryPerformanceCounter(&m_Start);
		}
	}

	~CModernFrameSection()
	{
		if (m_nSection >= 0)
		{
			LARGE_INTEGER End;
			QueryPerformanceCounter(&End);
			g_aModernFrameTicks[m_nSection] += End.QuadPart - m_Start.QuadPart;
		}
	}

private:
	int				m_nSection;
	LARGE_INTEGER	m_Start;
};

#endif

#endif  // __MODERNFRAMELOG_H__
