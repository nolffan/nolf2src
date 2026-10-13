// nolf2src: stand-ins for what Lithtech.exe's link needs of the client
// files that do not compile yet (docs/engine/PLAN.md, "skeleton"): each
// does nothing and fails. Delete a block when its file builds.

#include "bdefs.h"
#include "clientde_impl.h"
#include "winconsole_impl.h"
#include "interface_helpers.h"
#include "renderstruct.h"


// clientde_impl.cpp (ltrendererstats.h: Jupiter's ILTClient::GetRendererStats)

void CreateLTClient()
{
}

void ci_Term()
{
}


// sys/win/winclientde_impl.cpp (ltgraphicscaps.h: Jupiter's graphics caps)

CisSurface g_ScreenSurface;
RenderStruct *g_pCisRenderStruct = LTNULL;
GenericColor g_TransparentColor, g_SolidColor;
PFormat g_ScreenFormat;
uint32 g_nScreenPixelBytes;

bool cis_RendererIsHere(RenderStruct *pStruct)
{
	return false;
}

bool cis_RendererGoingAway()
{
	return false;
}

CisSurface* cis_InternalCreateSurface(uint32 width, uint32 height)
{
	return LTNULL;
}


// sys/win/winconsole_impl.cpp (the renderer's headers)

CConsole g_Console;

CConsole::CConsole()
{
}

CConsole::~CConsole()
{
}

bool CConsole::Init(const LTRect *pRect, CommandHandler handler, RenderStruct *pStruct, CConIterator *pCompletionIterator)
{
	return false;
}

bool CConsole::InitBare()
{
	return false;
}

void CConsole::Term(bool bDeleteTextLines)
{
}

LTRESULT CConsole::LoadBackground()
{
	return LT_ERROR;
}

void CConsole::Draw()
{
}

void CConsole::DrawSmall(int nLines)
{
}

void CConsole::DrawTextLine(const char *pText, const LTRect *pRect, COLORREF textColor)
{
}

void CConsole::OnKeyPress(uint32 key)
{
}

void CConsole::PrintString(CONCOLOR theColor, int filterLevel, const char *pMsg)
{
}

void CConsole::vPrintf(CONCOLOR theColor, int filterLevel, const char *pMsg, va_list vaArgs)
{
}

void CConsole::CycleCommands(int iCount)
{
}

void CConsole::SetCompletionIterator(CConIterator *pIterator)
{
}

bool CConIterator::First(const char *pValue)
{
	return false;
}

bool CConIterator::Last(const char *pValue)
{
	return false;
}

bool CConIterator::Next(const char *pValue)
{
	return false;
}

bool CConIterator::Prev(const char *pValue)
{
	return false;
}

CConHistory::CConHistory(int iListSize)
{
}

CConHistory::~CConHistory()
{
}

void CConHistory::Add(const char *pString, bool bUnique)
{
}

bool CConHistory::Begin()
{
	return false;
}

bool CConHistory::End()
{
	return false;
}

bool CConHistory::NextItem()
{
	return false;
}

bool CConHistory::PrevItem()
{
	return false;
}

int CConHistory::Remove(const char *pString)
{
	return 0;
}

void CConHistory::Remove(int iIndex)
{
}

const char* CConHistory::Get() const
{
	return LTNULL;
}

CConCommandBox::CConCommandBox()
{
}


// memorywatch.cpp (not in the retail engine; clientmgr.cpp and
// soundbuffer.cpp still call it)

unsigned long g_dwSoundMemory;

void mw_ResetWatches()
{
}
