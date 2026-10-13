// winsync.h: Win32 synchronisation objects wrapped in classes, as the sound
// driver's streaming thread uses them. The shapes are fixed by the retail
// code: a critical section and an event each own one handle-sized member
// (the CRITICAL_SECTION itself, the HANDLE), a scoped lock keeps a pointer
// to the section it entered, and an event is created manual-reset and
// unsignalled.

#ifndef __WINSYNC_H__
#define __WINSYNC_H__

// A critical section, initialised for the lifetime of the object.
class CWinSync_CS
{
public:
	CWinSync_CS()		{ InitializeCriticalSection(&GetCS()); }
	~CWinSync_CS()		{ DeleteCriticalSection(&GetCS()); }

	void Enter()		{ EnterCriticalSection(&GetCS()); }
	void Leave()		{ LeaveCriticalSection(&GetCS()); }

	CRITICAL_SECTION& GetCS() const { return m_CS; }

private:
	mutable CRITICAL_SECTION m_CS;
};

// Holds a critical section for the scope of the object.
class CWinSync_CSAuto
{
public:
	CWinSync_CSAuto(const CWinSync_CS& cCS) : m_pCS(&cCS.GetCS())
	{
		EnterCriticalSection(m_pCS);
	}
	~CWinSync_CSAuto()
	{
		LeaveCriticalSection(m_pCS);
	}

private:
	CRITICAL_SECTION* m_pCS;
};

// A manual-reset event, created unsignalled.
class CWinSync_Event
{
public:
	CWinSync_Event()	{ m_hEvent = CreateEvent(NULL, TRUE, FALSE, NULL); }
	~CWinSync_Event()	{ CloseHandle(m_hEvent); }

	HANDLE GetEvent() const	{ return m_hEvent; }
	void Set()				{ SetEvent(GetEvent()); }
	bool Clear()			{ return ResetEvent(GetEvent()) == TRUE; }
	bool IsSet()			{ return WaitForSingleObject(m_hEvent, 0) == WAIT_OBJECT_0; }

private:
	HANDLE m_hEvent;
};

#endif // __WINSYNC_H__
