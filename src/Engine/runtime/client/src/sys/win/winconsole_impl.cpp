//------------------------------------------------------------------
//	FILE	  : console_impl.cpp
//	PURPOSE	  : Implementation for the console.
//	CREATED	  : November 4 1999
// ------------------------------------------------------------------ //

#include "bdefs.h"

#include "winconsole_impl.h"
#include "consolecommands.h"
#include "dsys_interface.h"
#include "streamsim.h"
#include "load_pcx.h"
#include "resource.h"
#include "sysclientde_impl.h"
#include "clientmgr.h"
#include "clientde_impl.h"
#include "iltclient.h"
#include "renderstruct.h"
#include "iltfontmanager.h"
#include "ilttexinterface.h"
#include "debuggeometry.h"

//------------------------------------------------------------------
//------------------------------------------------------------------
// Holders and their headers.
//------------------------------------------------------------------
//------------------------------------------------------------------

//a IClientFormatMgr interface
#include "client_formatmgr.h"
static IClientFormatMgr *format_mgr;
define_holder(IClientFormatMgr, format_mgr);

//the ILTClient game interface
#include "iltclient.h"
static ILTClient *ilt_client;
define_holder(ILTClient, ilt_client);

static ILTDrawPrim* g_pILTDrawPrim;
define_holder_to_instance(ILTDrawPrim, g_pILTDrawPrim, Internal);
static ILTTexInterface* g_ITexInterface;
define_holder(ILTTexInterface, g_ITexInterface);
static ILTFontManager*  g_IFontManager;
define_holder(ILTFontManager, g_IFontManager);

#include "iclientshell.h"
static IClientShell *i_client_shell;
define_holder(IClientShell, i_client_shell);

// Constants
#define SEPERATOR_CHARACTERS " .()\""
#define SCROLL_INDICATOR_UP " \\/  \\/  \\/  \\/  \\/  \\/  \\/  \\/  \\/  \\/  \\/  \\/  \\/  \\/  \\/  \\/  \\/  \\/  \\/  \\/  \\/  \\/  \\/  \\/  \\/  \\/  \\/  \\/  \\/  \\/  \\/  \\/  \\/  \\/  \\/  \\/  \\/  \\/  \\/  \\/  \\/  \\/  \\/  \\/  \\/  \\/  \\/  \\/ "

extern int32 g_CV_TraceConsole;
extern char* g_CV_Console_FontTexFile;
	
// The global console variable	
CConsole g_Console;

// Default empty iterator
CConIterator g_ConEmptyIterator;

// Convenience functions...
inline bool IsKeyDown( uint16 vkKey )
{
#ifdef NOLF2SRC_MODERN
	// MODERN.md M-E5: the key asked about (Jupiter's tested Ctrl whatever
	// the key, so Shift+Tab was Tab)
	return ((GetAsyncKeyState( vkKey ) & 0x8000) != 0);
#else
	return ((GetAsyncKeyState( VK_CONTROL ) & 0x8000) != 0);
#endif
}

inline ConsoleState *GetConsoleState()
{
	return &g_ClientConsoleState;
}

// Console Variables
#ifdef NOLF2SRC_MODERN
extern char* g_CV_ConsoleFont;
extern int32 g_CV_ConsoleFontSize;
#endif
extern int32 g_CV_ConsoleHistoryLen;
extern int32 g_CV_ConsoleBufferLen;
extern float g_CV_ConsoleAlpha;
extern int32 g_CV_ConsoleLeft;
extern int32 g_CV_ConsoleTop;
extern int32 g_CV_ConsoleRight;
extern int32 g_CV_ConsoleBottom;

// ------------------------------------------------------------------ //
// CConIterator functionality
// ------------------------------------------------------------------ //
bool CConIterator::First( const char *pValue )
{
	// Go to the beginning
	if ( !Begin() )
		return false;

	// Jump out on an empty string
	if ( (!pValue) || (!*pValue) )
		return true;

	// Check for the first one being the one we're looking for
	const char *pCur = Get();
	if ( !pCur )
		return false;

	if ( strnicmp( pValue, pCur, strlen( pValue ) ) == 0 )
		return true;

	// Find the first value
	return Next( pValue );
}

bool CConIterator::Last( const char *pValue )
{
	// Go to the ending
	if ( !End() )
		return false;

	// Jump out on an empty string
	if ( (!pValue) || (!*pValue) )
		return true;

	// Check for the last one being the one we're looking for
	const char *pCur = Get();
	if ( !pCur )
		return false;

	if ( strnicmp( pValue, pCur, strlen( pValue ) ) == 0 )
		return true;

	// Find the first value
	return Prev( pValue );
}

bool CConIterator::Next( const char *pValue )
{
	if ( !pValue )
		return NextItem();

	int iLength = strlen( pValue );

	bool bFound = false;

	while ( !bFound )
	{
		if ( !NextItem() )
			break;

		const char *pCur = Get();
		if ( !pCur )
			break;

		bFound = strnicmp( pValue, pCur, iLength ) == 0;
	}

	return bFound;
}

bool CConIterator::Prev( const char *pValue )
{
	if ( !pValue )
		return PrevItem();

	int iLength = strlen( pValue );

	bool bFound = false;

	while ( !bFound )
	{
		if ( !PrevItem() )
			break;

		const char *pCur = Get();
		if ( !pCur )
			break;

		bFound = strnicmp( pValue, pCur, iLength ) == 0;
	}

	return bFound;
}

// ------------------------------------------------------------------ //
// CConCommandBox functionality
// ------------------------------------------------------------------ //
CConCommandBox::CConCommandBox()
{
	m_TextColor = CONRGB( 180, 180, 255 );
	
	m_BackColor = CONRGB( 30, 30, 30 );
	m_BorderColor = CONRGB( 255, 255, 255 );

	m_pConsole = LTNULL;
	
	m_FlashTime = 500;

	Clear();
}

void CConCommandBox::Term()
{
	SetConsole( LTNULL );
}

void CConCommandBox::Clear()
{
	m_CurCommand[0] = 0;
	m_iCurLength = 0;
	MoveCursor(0);
}

void CConCommandBox::SetCommand( const char *pCommand )
{ 
	if ( !pCommand )
		Clear();
	else
	{
		// Copy the string
		LTStrCpy( m_CurCommand, pCommand, MAX_CONSOLE_TEXTLEN );
		m_iCurLength = strlen( m_CurCommand );
		// Move to the end of the string
		MoveCursor( m_iCurLength );
	}
}

void CConCommandBox::DeleteChar( int iOffset )
{
	// Find the position
	int iPosition = m_iCursorPos + iOffset;

	// Restrict to the contents of the string
	if ( (iPosition < 0) || (iPosition >= m_iCurLength) )
		return;

	// Delete the character
	strcpy( &m_CurCommand[iPosition], &m_CurCommand[iPosition + 1] );
	m_iCurLength--;
}

void CConCommandBox::DeleteWord( int iOffset )
{
	bool bSeperator = (iOffset < 0);
	for ( int iLoop = 0; iLoop < 2; iLoop++)
	{
		// Skip over the next set of seperators or characters
		while ( ((m_iCursorPos + iOffset) >= 0) && ((m_iCursorPos + iOffset) < m_iCurLength) &&
			((strchr( SEPERATOR_CHARACTERS, m_CurCommand[m_iCursorPos + iOffset] ) == 0) ^ bSeperator) )
		{
			DeleteChar( iOffset );
			m_iCursorPos += iOffset;
		}
		bSeperator = !bSeperator;
	}
}

void CConCommandBox::AddChar( char key )
{
	// Don't add past the end of the string
	if ( m_iCursorPos >= (MAX_CONSOLE_TEXTLEN - 1) )
		return;

	// Don't allow the string to get too big
	if ( m_iCurLength >= (MAX_CONSOLE_TEXTLEN - 1) )
	{
		m_iCurLength--;
		m_CurCommand[m_iCurLength] = 0;
	}

	// Make room if necessary
	if ( m_iCursorPos < m_iCurLength )
		memmove( &m_CurCommand[m_iCursorPos + 1], &m_CurCommand[m_iCursorPos], (m_iCurLength - m_iCursorPos) + 1 );
	// Otherwise make sure it's terminated
	else
		m_CurCommand[m_iCurLength + 1] = 0;

	// Put the character in the string
	m_CurCommand[m_iCursorPos] = key;

	// Update the length
	m_iCurLength++;
}

void CConCommandBox::MoveCursor(int iOffset)
{
	m_iCursorPos = max(min(m_iCursorPos + iOffset, m_iCurLength), 0);
}

void CConCommandBox::MoveWord( int iOffset )
{
	bool bSeperator = (iOffset < 0);
	for ( int iLoop = 0; iLoop < 2; iLoop++)
	{
		// Skip over the next set of seperators or characters
		while ( ((m_iCursorPos + iOffset) >= 0) && ((m_iCursorPos + iOffset) <= m_iCurLength) &&
			((strchr( SEPERATOR_CHARACTERS, m_CurCommand[m_iCursorPos + iOffset] ) == 0) ^ bSeperator) )
			m_iCursorPos += iOffset;
		bSeperator = !bSeperator;
	}
	// Make sure we end up on a non-seperator
	while ( ((m_iCursorPos + iOffset) >= 0) && ((m_iCursorPos + iOffset) <= m_iCurLength) &&
		(strchr( SEPERATOR_CHARACTERS, m_CurCommand[m_iCursorPos] ) != 0) )
		m_iCursorPos += iOffset;
}

char CConCommandBox::TranslateKey(uint32 key) const
{
	char aResult[2];
	uint8 aKeyState[256];
	if ( !GetKeyboardState( aKeyState ) )
		return 0;

	switch ( ToAscii( key, 0, aKeyState, (LPWORD)aResult, 0 ) )
	{
		// No translation available
		case 0 : 
			return 0;
		// 1 character translated
		case 1 :
			return aResult[0];
		// 2 characters required for translation
		case 2 : 
			return aResult[1];
		// Documentation says this should never happen...
		default :
			return 0;
	}
}

void CConCommandBox::OnKeyPress(uint32 key)
{
	switch ( key )
	{
		case VK_ESCAPE :
			Clear();
			break;
		case VK_LEFT :
			if ( IsKeyDown( VK_CONTROL ) )
				// Ctrl+Left = word left
				MoveWord( -1 );
			else
				MoveCursor( -1 );
			break;
		case VK_RIGHT :
			if ( IsKeyDown( VK_CONTROL ) )
				// Ctrl+Right = word right
				MoveWord( 1 );
			else
				MoveCursor( 1 );
			break;
		case VK_HOME :
			MoveCursor( -m_iCursorPos );
			break;
		case VK_END :
			if ( IsKeyDown( VK_CONTROL ) )
				// Ctrl+End = delete the rest of the buffer
				AddChar( 0 );
			else
				MoveCursor( m_iCurLength );
			break;
		case VK_BACK : 
			if ( IsKeyDown( VK_CONTROL ) )
				// Ctrl+Backspace = delete the next word
				DeleteWord( -1 );
			else
			{
				DeleteChar( -1 );
				MoveCursor( -1 );
			}
			break;
		case VK_DELETE :
			if ( IsKeyDown( VK_CONTROL ) )
				// Ctrl+Delete = delete the next word
				DeleteWord( 0 );
			else
				DeleteChar( 0 );
			break;
		default :
			char chChar = TranslateKey( key );
			if (chChar)
			{
				AddChar( chChar );
				MoveCursor( 1 );
			}
			break;
	}
}

// ------------------------------------------------------------------ //
// CConHistory functionality
// ------------------------------------------------------------------ //
CConHistory::CConHistory( int iListSize ) :
	m_pLines(LTNULL),
	m_iIndex(0),
	m_iListSize(0),
	m_iListStart(0),
	m_iListEnd(0)
{
	Resize( iListSize );
}

CConHistory::~CConHistory()
{
	Resize( 0 );
}

bool CConHistory::Begin()
{
	m_iIndex = m_iListStart;
	return m_iIndex != m_iListEnd;
}

bool CConHistory::End()
{
	m_iIndex = m_iListEnd;
	return PrevItem();
}

bool CConHistory::NextItem()
{
	if ( m_iIndex == m_iListEnd )
		return false;
	m_iIndex++;
	if ( m_iIndex >= m_iListSize )
		m_iIndex = 0;
	return m_iIndex != m_iListEnd;
}

bool CConHistory::PrevItem()
{
	if ( m_iIndex == m_iListStart )
		return false;
	m_iIndex--;
	if ( m_iIndex < 0 )
		m_iIndex = m_iListSize - 1;
	return true;
}

int CConHistory::Remove( const char *pString )
{
	// You haven't removed any yet...
	int iResult = 0;
	// Begin at the beginning
	int iCurEntry = m_iListStart;
	// Continue until the ending
	while ( iCurEntry != m_iListEnd )
	{
		// Is this the droid you're looking for?
		if ( strnicmp( pString, m_pLines[iCurEntry].m_Text, MAX_CONSOLE_TEXTLEN ) == 0 )
		{
			// Remove this entry
			Remove( iCurEntry );
			// Count it
			++iResult;
		}
		else
			// Move along
			iCurEntry = ( iCurEntry + 1 ) % m_iListSize;
	}

	// Tell the interested parties what happened
	return iResult;
}

void CConHistory::Remove( int iIndex )
{
	// Go over the list...
	for ( int iCurEntry = iIndex; iCurEntry != m_iListEnd; iCurEntry = (iCurEntry + 1) % m_iListSize )
	{
		// Who's next?
		int iNextEntry = (iCurEntry + 1) % m_iListSize;
		// Clean cup, move down..
		LTStrCpy( m_pLines[iCurEntry].m_Text, m_pLines[iNextEntry].m_Text, MAX_CONSOLE_TEXTLEN );
	}
	// Adjust the end
	m_iListEnd = ((m_iListEnd > 0) ? m_iListEnd : m_iListSize) - 1;
}


void CConHistory::Add( const char *pString, bool bUnique )
{
	// Make sure the list exists
	if ( !m_iListSize )
		return;
	// Make sure it's a unique entry in the history
	if ( bUnique )
		Remove( pString );
	// Copy the string
	LTStrCpy( m_pLines[m_iListEnd].m_Text, pString, MAX_CONSOLE_TEXTLEN );
	// Move the end of the list
	m_iListEnd++;
	if ( m_iListEnd >= m_iListSize )
		m_iListEnd = 0;
	// Move the beginning of the list if necessary
	if ( m_iListStart == m_iListEnd )
	{
		m_iListStart++;
		if ( m_iListStart >= m_iListSize )
			m_iListStart = 0;
	}
}

// Resize the history list
bool CConHistory::Resize( int iSize )
{
	// Jump out if it's already the right size
	if ( m_iListSize == (iSize + 1) )
		return true;

	CConTextLine *pNewList = LTNULL;

	// Allocate a new buffer
	if ( iSize )
	{
		iSize++;
		LT_MEM_TRACK_ALLOC(pNewList = new CConTextLine[iSize],LT_MEM_TYPE_CONSOLE);
		if ( !pNewList )
			return false;

		// Move over the old lines
		if ( End() )
		{
			int iIndex = iSize - 1;
			do
			{
				const char *pLine = Get();
				if ( !pLine )
					break;
				LTStrCpy( pNewList[iIndex].m_Text, pLine, MAX_CONSOLE_TEXTLEN );
			} while ( (--iIndex) && (PrevItem()) );
			m_iListStart = iIndex + 1;
			m_iListEnd = 0;
		}
		else
			m_iListStart = m_iListEnd = 0;
	}
	else
		m_iListStart = m_iListEnd = 0;

	// Get rid of the old lines
	if ( m_iListSize )
		delete [] m_pLines;

	// Update the list buffer variables
	m_iListSize = iSize;
	m_pLines = pNewList;

	return true;
}

const char *CConHistory::Get() const 
{ 
	if ( (m_iIndex < 0) || (m_iIndex >= m_iListSize) || (m_iIndex == m_iListEnd) )
		return LTNULL;

	return &(m_pLines[m_iIndex].m_Text[0]); 
}

int CConHistory::GetIndex() const
{
	int iResult = m_iIndex - m_iListStart;
	if ( iResult < 0 )
		iResult += m_iListSize;
	return iResult;
}

bool CConHistory::MoveTo( int iIndex )
{
	// Guard against the obvious
	if ( iIndex < 0 )
		return false;

	bool bResult = false;

	iIndex += m_iListStart;
	// Handle the new index being before the bottom of the list or the list not wrapping
	if ( (iIndex < m_iListSize) || (m_iListEnd > m_iListStart) )
		bResult = (iIndex < m_iListEnd) || (m_iListEnd < m_iListStart);
	// Handle the new index being after the bottom of the list
	else
	{
		iIndex -= m_iListSize;
		bResult = iIndex < m_iListEnd;
	}
	if ( bResult )
		m_iIndex = iIndex;
	return bResult;
}

// ------------------------------------------------------------------ //
// CConsole functionality
// ------------------------------------------------------------------ //

CConsole::CConsole()
{
	m_pFontBitmapData = LTNULL;

	m_hWnd = 0;
	m_CommandHandler = LTNULL;
	m_FilterLevel = 1;
	
	m_BackColor = CONRGB( 0, 0, 0 );
	m_BorderColor = CONRGB( 255, 255, 255 );

	m_FontHeight = 1;
	
	m_pStruct = LTNULL;
	m_ErrorLogFn = LTNULL;
	m_hBackground = LTNULL;
	m_fBackgroundAlpha = 1.0f;
	m_bBackgroundOptimized = false;

	m_pCompletionIterator = &g_ConEmptyIterator;

	m_bInitialized = true;
	m_bInitTerminate = false;

	m_Tex = NULL;
	m_Font = NULL;

#ifdef NOLF2SRC_MODERN
	m_pModernStr = LTNULL;
	m_nModernFontSize = 0;
	m_nModernLineHeight = 0;
#endif
}

CConsole::~CConsole()
{ 
	Term( true ); 

	m_bInitialized = false;
}

bool CConsole::Init(const LTRect *pRect, CommandHandler handler, RenderStruct *pStruct, CConIterator *pCompletionIterator )
{
	HWND hWnd = (HWND)dsi_GetMainWindow();

	if ( m_bInitTerminate )
		Term( false );
	m_bInitTerminate = true;

	if (!InitFont()) {
		Term(true);
		return false; }

	m_hWnd = hWnd;
	// Note : This has no effect now that the window position is in a console variable
	m_ScrRect = *pRect;
	m_CommandHandler = handler;
	m_pStruct = pStruct;

	m_iScrollOffset = 0;

	if ( !m_TextLines.GetSize() )
		ResizeTextLines( 200 );

	// Setup the command box.
	GetCommandBox()->SetConsole( this );

	if ( !m_cHistory.GetSize() )
		m_cHistory.Resize( 20 );

	if ( pCompletionIterator )
		SetCompletionIterator( pCompletionIterator );

	// Read in the variable states
	CheckVariables();

	return true;
}

bool CConsole::InitBare()
{
	if ( !m_TextLines.GetSize() )
		ResizeTextLines( 200 );
	return true;
}

void CConsole::Term(bool bDeleteTextLines)
{
#ifdef NOLF2SRC_MODERN
	ModernFreeFont();
#endif
	FreeBackground();

	if ( bDeleteTextLines )
	{
		GDeleteAndRemoveElements( m_TextLines );
		m_cHistory.Resize( 0 );
	}

	TermFont();
	GetCommandBox()->Term();
	
	m_hWnd = 0;
	m_CommandHandler = LTNULL;
	m_pStruct = LTNULL;

	if (g_IFontManager && m_Font)	{ 
		CDebugGeometry& dgPerf = getDebugGeometry(); dgPerf.clear();	// Make sure all the debug text (shares this font) is destroyed...
		g_IFontManager->DestroyFont(m_Font); m_Font = 0; }
	if (m_Tex)						{ g_ITexInterface->ReleaseTextureHandle(m_Tex); m_Tex = 0; }

	m_bInitTerminate = false;
}

void CConsole::FreeBackground()
{
	if ( !m_hBackground )
		return;

	cis_DeleteSurface( m_hBackground );
	m_hBackground = LTNULL;
}


bool CConsole::InitFont()
{
	m_FontHeight = 9;

	for (uint32 i = 0; i < NUM_CONSOLE_CHARACTERS; ++i)
		m_CharWidths[i] = (uint16)7;

	return true;
}

void CConsole::TermFont()
{
	if (m_pFontBitmapData) {
		delete m_pFontBitmapData;
		m_pFontBitmapData = LTNULL; }

	if (m_Font) {
		g_IFontManager->DestroyFont(m_Font);
		m_Font = NULL;
	}
}

bool CConsole::ResizeHistory( int iNewSize )
{
	if ( m_cHistory.GetSize() == iNewSize )
		return true;

	bool bResult = m_cHistory.Resize( iNewSize );
	return bResult;
}

bool CConsole::ResizeTextLines( uint32 nNewSize )
{
	// Jump out if the number of lines hasn't changed
	if ( m_TextLines.GetSize() == nNewSize )
		return true;

	CConTextLine	*pLine;

	while ( m_TextLines.GetSize() < nNewSize )
	{
		LT_MEM_TRACK_ALLOC(pLine = new CConTextLine,LT_MEM_TYPE_CONSOLE);
		
		memset( pLine, 0, sizeof(CConTextLine) );
		m_TextLines.AddHead( pLine );
	}

	while ( m_TextLines.GetSize() > nNewSize )
		delete m_TextLines.RemoveHead();

	return true;
}

void CConsole::FinishCommand()
{
	EndNav();

	char *pCurCommand = (char *)(GetCommandBox()->GetCommand());
	if (pCurCommand[0] == 0)
		return;

#ifdef NOLF2SRC_MODERN
	// MODERN.md M-E5: the line echoed after a prompt, run, and answered
	// where the handler is silent; back to the newest output
	Printf( GetCommandBox()->GetTextColor(), 0, "> %s", pCurCommand );

	m_cHistory.Add( pCurCommand );

	// The line is run from a copy: a command can print, or close the
	// console, while it runs
	char aCommand[MAX_CONSOLE_TEXTLEN + 1];
	LTStrCpy( aCommand, pCurCommand, sizeof(aCommand) );
	GetCommandBox()->Clear();
	m_iScrollOffset = 0;

	c_ModernTypedCommand( aCommand );
#else
	PrintString( GetCommandBox()->GetTextColor(), 0, pCurCommand );

	m_cHistory.Add( pCurCommand );

	if ( m_CommandHandler )
		m_CommandHandler( pCurCommand );

	GetCommandBox()->Clear();
#endif
}

void CConsole::CheckVariables()
{
	// Read from the console's variables
	SetBackgroundAlpha( g_CV_ConsoleAlpha );
	// Note : This makes sure the console buffer always has at least 10 lines in it..
	ResizeTextLines( (uint32)LTMAX( g_CV_ConsoleBufferLen , 10 ) );
	m_cHistory.Resize( (uint32)LTMAX( g_CV_ConsoleHistoryLen, 5 ) );
	// Update the window rectangle
	LTRect cRect;
	cRect.top = g_CV_ConsoleTop;
	cRect.left = g_CV_ConsoleLeft;
	cRect.bottom = g_CV_ConsoleBottom;
	cRect.right = g_CV_ConsoleRight;
	SetRect( cRect );
}

void CConsole::CycleCommands(int iCount)
{
	if (!iCount)
		return;

	bool bForward = iCount > 0;
	iCount = abs( iCount );

	// Pull up the first entry in the history list
	if ( GetState() != STATE_HISTORY )
	{
		// Go to the first match in the history list
		bool bMatch;
		if ( bForward )
			bMatch = m_cHistory.First( GetCommandBox()->GetCommand() );
		else
			bMatch = m_cHistory.Last( GetCommandBox()->GetCommand() );

		if ( !bMatch )
			return;
	
		StartNav( STATE_HISTORY );
		iCount--;
	}

	bool bContinue = true;
	// Pull up the next entry in the history list
	while ( iCount && bContinue )
	{
		if ( bForward )
			bContinue = m_cHistory.Next( m_aNavCommand );
		else
			bContinue = m_cHistory.Prev( m_aNavCommand );
		iCount--;
	}

	if ( !bContinue )
	{
		// End navigation mode
		GetCommandBox()->SetCommand( m_aNavCommand );
		EndNav();
	}
	else
		GetCommandBox()->SetCommand( m_cHistory.Get() );
}

void CConsole::SetCompletionIterator(CConIterator *pIterator)
{
	if ( !pIterator )
		m_pCompletionIterator = &g_ConEmptyIterator;
	else
		m_pCompletionIterator = pIterator;
}

void CConsole::NextCommand()
{
	// Start the iterator if we're not navigating yet
	if ( GetState() != STATE_COMPLETE )
	{
		// Find the first match
		if ( !GetCompletionIterator()->First( GetCommandBox()->GetCommand() ) )
			return;
	
		// Go into navigation mode
		StartNav( STATE_COMPLETE );
	}
	// Otherwise find the next one
	else if ( !GetCompletionIterator()->Next( m_aNavCommand ) )
	{
		// Start over if we get to the end
		GetCommandBox()->SetCommand( m_aNavCommand );
		EndNav();
		return;
	}

	// Show the new item
	GetCommandBox()->SetCommand( GetCompletionIterator()->Get() );
}

void CConsole::PrevCommand()
{
	// Start the iterator if we're not navigating yet
	if ( GetState() != STATE_COMPLETE )
	{
		// Find the first match
		if ( !GetCompletionIterator()->Last( GetCommandBox()->GetCommand() ) )
			return;
	
		// Go into navigation mode
		StartNav( STATE_COMPLETE );
	}
	// Otherwise find the previous one
	else if ( !GetCompletionIterator()->Prev( m_aNavCommand ) )
	{
		// Start over if we get to the beginning
		GetCommandBox()->SetCommand( m_aNavCommand );
		EndNav();
		return;
	}

	// Show the new item
	GetCommandBox()->SetCommand( GetCompletionIterator()->Get() );
}

void CConsole::MatchCommands()
{
	// Display a list of what matches
	bool bContinue = GetCompletionIterator()->First( GetCommandBox()->GetCommand() );
	if ( bContinue )
		Printf( GetCommandBox()->GetTextColor(), 0, ">%s*>", GetCommandBox()->GetCommand() );
	while ( bContinue )
	{
		char *pString = (char *)GetCompletionIterator()->Get();
		if ( !pString )
			break;
		PrintString( GetCommandBox()->GetTextColor(), 0, pString );
		bContinue = GetCompletionIterator()->Next( GetCommandBox()->GetCommand() );
	}
}

void CConsole::StartNav( EConState eState )
{
	// Jump out if we're already navigating
	if ( GetState() == eState )
		return;

	// Make a copy of whatever's in the command buffer
	LTStrCpy( m_aNavCommand, GetCommandBox()->GetCommand(), MAX_CONSOLE_TEXTLEN );

	// Change our state
	SetState( eState );
}

void CConsole::EndNav()
{
	// Jump out if we're not navigating
	if ( GetState() == STATE_NORMAL )
		return;

	// Change our state
	SetState( STATE_NORMAL );
}

LTRESULT CConsole::LoadBackground()
{
	ILTStream *pStream;
	LoadedBitmap bitmap;
	LTRESULT dResult;
	
	FreeBackground();

	dResult = LT_ERROR;
	if ( (pStream = streamsim_Open("console.pcx", "rb")) == LTNULL )
		return dResult;

	if ( pcx_Create2(pStream, &bitmap) )
	{
		m_hBackground = cis_CreateSurfaceFromPcx( &bitmap );

		m_bBackgroundOptimized = ilt_client->OptimizeSurface(m_hBackground, RGB(0,0,0)) != 0;
		SetBackgroundAlpha( m_fBackgroundAlpha );

		dResult = LT_OK;
	}

	pStream->Release();

	return dResult;
}

void CConsole::SetBackgroundAlpha( float fValue )
{
	if ( !m_hBackground )
		return;

	m_fBackgroundAlpha = fValue; 

	if ( m_bBackgroundOptimized != LT_OK )
		m_bBackgroundOptimized = ilt_client->OptimizeSurface(m_hBackground, RGB(0,0,0)) != 0;

	ilt_client->SetSurfaceAlpha( m_hBackground, fValue );
}

int CConsole::Scroll( int iOffset )
{
	m_iScrollOffset = min( max( m_iScrollOffset + iOffset, 0 ), (int)(m_TextLines.GetSize() - m_nTextLines + 1));
	return m_iScrollOffset;
}

inline bool CConsole::GetTextLineBox(uint32 iLine, LTRect *pRect, bool bScreen)
{
	LTRect cRect;
	if (bScreen)
		cRect = m_ScrRect;
	else
		CalcRect( cRect );
	pRect->top = cRect.top + (iLine * m_FontHeight) + CONSOLE_TOP_BORDER;
	pRect->bottom = cRect.top + ((iLine+1) * m_FontHeight) + 1;
	pRect->left = cRect.left + CONSOLE_LEFT_BORDER;
	pRect->right = cRect.right - 1;

	if ( ((pRect->bottom - pRect->top) > 0) && ((pRect->right - pRect->left) > 0) )
		return true;
	else
		return false;
}


void CConsole::SetRect( const LTRect &cRect )
{
	// Jump out if it hasn't changed
	// Note: Taken out, because the screen extents may have changed... -JE
//	if ((m_Rect.left == cRect.left) && (m_Rect.top == cRect.top) && (m_Rect.right == cRect.right) && (m_Rect.bottom == cRect.bottom)) return;

	m_Rect = cRect;
	LTRect TempRect;

	CalcRect( TempRect );
	m_nTextLines = (TempRect.bottom - TempRect.top) / m_FontHeight;
	m_nTextLines -= 2;	// Leave 1 for the command box.

	LTRect cCommandRect;
	GetTextLineBox( m_nTextLines, &cCommandRect);
	GetCommandBox()->SetRect( cCommandRect );
}

void CConsole::CalcRect( LTRect &cRect )
{
	// Just default to the rendering rectangle if we don't have a rendering structure yet
	if ( !GetRenderStruct() )
	{
		cRect = m_Rect;
		return;
	}

	// Get the new rectangle based on the screen width and height for negative values
	if ( m_Rect.top == -1 )
		cRect.top = 0;
	else if ( m_Rect.top < 0 )
		cRect.top = (int)GetRenderStruct()->m_Height / (-m_Rect.top);
	else
		cRect.top = m_Rect.top;

	if ( m_Rect.left == -1 )
		cRect.left = 0;
	else if ( m_Rect.left < 0 )
		cRect.left = (int)GetRenderStruct()->m_Width / (-m_Rect.left);
	else
		cRect.left = m_Rect.left;

	if ( m_Rect.right == -1 )
		cRect.right = (int)GetRenderStruct()->m_Width;
	else if ( m_Rect.right < 0 )
		cRect.right = (int)GetRenderStruct()->m_Width - ((int)GetRenderStruct()->m_Width / (-m_Rect.right));
	else
		cRect.right = m_Rect.right;

	if ( m_Rect.bottom == -1 )
		cRect.bottom = (int)GetRenderStruct()->m_Height;
	else if ( m_Rect.bottom < 0 )
		cRect.bottom = (int)GetRenderStruct()->m_Height - ((int)GetRenderStruct()->m_Height / (-m_Rect.bottom));
	else
		cRect.bottom = m_Rect.bottom;

	// Clip the rectangle to the screen
	cRect.right = min( cRect.right, (int)GetRenderStruct()->m_Width - 3);
	cRect.bottom = min( cRect.bottom, (int)GetRenderStruct()->m_Height );
	// Restrict the rectangle to a minimum size
	cRect.right = max( cRect.right, 160 );
	cRect.bottom = max( cRect.bottom, m_FullFontHeight * 4 );
	cRect.left = min( cRect.left, cRect.right - 160 );
	cRect.top = min( cRect.top, cRect.bottom - (m_FullFontHeight * 4) );
}

#ifndef RGBA_GETA
#define RGBA_GETA(color)			((uint8)( color               >> 24))
#define RGBA_GETR(color)			((uint8)((color & 0x00FF0000) >> 16))
#define RGBA_GETG(color)			((uint8)((color & 0x0000FF00) >> 8 ))
#define RGBA_GETB(color)			((uint8)((color & 0x000000FF)      ))
#endif

void CConsole::PrintString(CONCOLOR theColor, int filterLevel, const char *pMsg)
{
	// Protect agains error messages that happen after the destructor has been called
	if (!m_bInitialized)
		return;

	//	Send the info we're using for output to the client shell so the 
	//	game code can do whatever it wants with it.
	if (i_client_shell != NULL) {
		CConsolePrintData	PrintData;

		//	turn the CONCOLOR into an LTRGB
		PrintData.m_Color.r	= RGBA_GETR (theColor);
		PrintData.m_Color.g	= RGBA_GETG (theColor);
		PrintData.m_Color.b	= RGBA_GETB (theColor);
		PrintData.m_Color.a	= RGBA_GETA (theColor);

		PrintData.m_pMessage		= pMsg;
		PrintData.m_nFilterLevel	= filterLevel;

		i_client_shell->OnConsolePrint (&PrintData);

		//	the client shell might have changed any of the data we sent it\
		//	so reset our parameters
		if (PrintData.m_pMessage == NULL)
			return;

		filterLevel	= PrintData.m_nFilterLevel;
		pMsg		= PrintData.m_pMessage;
		theColor	= CONRGB (PrintData.m_Color.r, PrintData.m_Color.g,
							  PrintData.m_Color.b);
	}

	if ( filterLevel > m_FilterLevel ) return; 

	CConTextLine*	pLine;

	m_CS.Enter();
			
	if ( m_ErrorLogFn )
		m_ErrorLogFn( pMsg );

	if ( g_CV_TraceConsole )
	{
		OutputDebugString( pMsg );
		OutputDebugString( "\n" );
	}
			
	if ( m_TextLines.GetSize() > 0 )
	{
		int iLength;
		const char *pNewLine;

		do
		{
			// Search for a newline character
			pNewLine = strchr( pMsg, '\n' );
			if ( pNewLine && (pNewLine[1]) )
				iLength = pNewLine - pMsg;
			else
			{
				pNewLine = LTNULL;
				iLength = MAX_CONSOLE_TEXTLEN - 1;
			}

			// Get the head of the text list
			pLine = m_TextLines.GetHead();
			// Make sure the list doesn't get too long
			m_TextLines.RemoveAt( pLine );

			// Copy the message
			pLine->m_Color = theColor;
			LTStrCpy( pLine->m_Text, pMsg, iLength );

			// Remove the newline character
			if ( pNewLine )
			{
				pLine->m_Text[iLength] = 0;
				pMsg = &pNewLine[1];
			}

			// Add it to the end of the list
			m_TextLines.AddTail( pLine );

		} while ( pNewLine );
	}
		
	m_CS.Leave();
}

void CConsole::vPrintf(CONCOLOR theColor, int filterLevel, const char *pMsg, va_list vaArgs)
{
	if ( FilterAction( filterLevel ) )
		return;

	char str[500];
	LTVSNPrintF(str, sizeof(str), pMsg, vaArgs);
	PrintString(theColor, filterLevel, str);
}

void CConsole::Printf(CONCOLOR theColor, int filterLevel, const char *pMsg, ...)
{
	va_list vaArgs;
	va_start(vaArgs, pMsg);
	vPrintf(theColor, filterLevel, pMsg, vaArgs);
	va_end(vaArgs);
}

void CConsole::OnKeyPress(uint32 key)
{
	switch (key)
	{
		case VK_RETURN :
			FinishCommand();
			break;
		case VK_UP : 
			if ( IsKeyDown( VK_CONTROL ) )
				Scroll( 1 );
			else
				CycleCommands( -1 );
			break;
		case VK_DOWN :
			if ( IsKeyDown( VK_CONTROL ) )
				Scroll( -1 );
			else
				CycleCommands( 1 );
			break;
		case VK_TAB :
#ifdef NOLF2SRC_MODERN
			// MODERN.md M-E5: completes the name typed, as far as the names
			// that start with it agree, and lists them when there are several
			ModernComplete();
			break;
#endif
			if ( IsKeyDown( VK_CONTROL ) )
				MatchCommands();
			else if ( IsKeyDown( VK_SHIFT ) )
				PrevCommand();
			else
				NextCommand();
			break;
		case VK_PRIOR :
			if ( IsKeyDown( VK_CONTROL ) )
				Scroll( (int)m_TextLines.GetSize() );
			else
				Scroll( (int)m_nTextLines );
			break;
		case VK_NEXT :
			if ( IsKeyDown( VK_CONTROL ) )
				Scroll( -GetScrollOffset() );
			else
				Scroll( -(int)m_nTextLines );
			break;
		default :
			GetCommandBox()->OnKeyPress( key );
			break;
	}
}


#ifdef NOLF2SRC_MODERN

// ------------------------------------------------------------------ //
// MODERN.md M-E5: the console drawn and completing names again.
//
// The release build keeps the console's text, history and command line
// but none of its drawing: Jupiter's drew a bitmap font from a texture that
// NOLF2 does not ship (console\console_font.dtx) through D3D9 calls. This
// draws through the engine's own font manager instead, a TrueType face
// (ConsoleFont, or a fixed-pitch face found installed) at a size for the
// screen
// (ConsoleFontSize, or a 45th of its height), so it reads the same at
// 640x480 and at 4K, over a dark translucent band (the rectangle of
// ConsoleLeft, ConsoleTop, ConsoleRight and ConsoleBottom: the top half of
// the screen by default). FlipScreen calls it, the last thing drawn in a
// frame.
// ------------------------------------------------------------------ //

#define MODERN_CONSOLE_MINSIZE		12
#define MODERN_CONSOLE_MAXSIZE		80		// the font's letter sizes are 8-bit
#define MODERN_CONSOLE_MAXMATCHES	512

static int CALLBACK ModernFontFound( const LOGFONT *pFont, const TEXTMETRIC *pMetric, DWORD nType, LPARAM lParam )
{
	*(bool *)lParam = true;
	return 0;
}

// The first fixed-pitch face of a few that is installed (Windows has the
// first three, Wine finds Linux's own through fontconfig); GDI would put a
// proportional face in place of one that is missing
static const char *ModernConsoleFace()
{
	static const char *s_aFaces[] = { "Consolas", "Lucida Console", "Courier New",
		"Liberation Mono", "DejaVu Sans Mono", "Courier" };
	const int nFaces = sizeof(s_aFaces) / sizeof(s_aFaces[0]);
	const char *pFace = s_aFaces[2];

	HDC hDC = GetDC( NULL );
	if ( !hDC )
		return pFace;

	for ( int i = 0; i < nFaces; i++ )
	{
		bool bFound = false;
		EnumFontFamilies( hDC, s_aFaces[i], (FONTENUMPROC)ModernFontFound, (LPARAM)&bFound );
		if ( bFound )
		{
			pFace = s_aFaces[i];
			break;
		}
	}

	ReleaseDC( NULL, hDC );
	return pFace;
}

bool CConsole::ModernMakeFont( uint32 nScreenHeight )
{
	uint32 nSize = (g_CV_ConsoleFontSize > 0) ? (uint32)g_CV_ConsoleFontSize : nScreenHeight / 45;
	nSize = LTCLAMP( nSize, MODERN_CONSOLE_MINSIZE, MODERN_CONSOLE_MAXSIZE );

	// Made already (or tried, and failed: not again every frame)
	if ( m_nModernFontSize == nSize )
		return m_pModernStr != LTNULL;

	ModernFreeFont();
	m_nModernFontSize = nSize;

	if ( !g_IFontManager )
		return false;

	const char *pFace = (g_CV_ConsoleFont && g_CV_ConsoleFont[0]) ? g_CV_ConsoleFont : ModernConsoleFace();
	m_Font = g_IFontManager->CreateFont( "", pFace, nSize );
	if ( !m_Font )
		return false;

	m_pModernStr = g_IFontManager->CreatePolyString( m_Font, LTNULL, 0.0f, 0.0f );
	if ( !m_pModernStr )
	{
		g_IFontManager->DestroyFont( m_Font );
		m_Font = LTNULL;
		return false;
	}

	m_nModernLineHeight = nSize + (nSize / 5) + 1;
	m_FontHeight = (uint16)m_nModernLineHeight;
	return true;
}

void CConsole::ModernFreeFont()
{
	if ( g_IFontManager )
	{
		if ( m_pModernStr )
			g_IFontManager->DestroyPolyString( m_pModernStr );
		if ( m_Font )
			g_IFontManager->DestroyFont( m_Font );
	}

	m_pModernStr = LTNULL;
	m_Font = LTNULL;
	m_nModernFontSize = 0;
}

float CConsole::ModernTextWidth( const char *pText, int nChars )
{
	char aText[MAX_CONSOLE_TEXTLEN + 4];
	float fWidth = 0.0f;

	if ( nChars < 0 )
		nChars = strlen( pText );
	nChars = LTMIN( nChars, MAX_CONSOLE_TEXTLEN + 3 );
	memcpy( aText, pText, nChars );
	aText[nChars] = 0;

	if ( !nChars || !m_pModernStr )
		return 0.0f;

	float fHeight = 0.0f;
	m_pModernStr->SetText( aText );
	m_pModernStr->GetDims( &fWidth, &fHeight );
	return fWidth;
}

void CConsole::ModernDrawText( const char *pText, float x, float y, CONCOLOR theColor, const LTRect &cClip )
{
	// A line keeps a message's last newline (PrintString), and a tab or any
	// character the font lacks would draw as its first letter: spaces for
	// those, the line ends at a newline
	char aText[MAX_CONSOLE_TEXTLEN + 4];
	int nLength = 0;
	while ( pText[nLength] && (pText[nLength] != '\n') && (pText[nLength] != '\r') &&
		(nLength < MAX_CONSOLE_TEXTLEN + 3) )
	{
		uint8 nChar = (uint8)pText[nLength];
		aText[nLength] = ((nChar < ' ') || (nChar > '~')) ? ' ' : (char)nChar;
		nLength++;
	}
	aText[nLength] = 0;
	if ( !nLength )
		return;

	m_pModernStr->SetText( aText );
	m_pModernStr->SetPosition( x, y );
	m_pModernStr->SetColor( theColor | 0xFF000000 );

	CUIRECT cClipRect( (float)cClip.left, (float)cClip.top,
		(float)(cClip.right - cClip.left), (float)(cClip.bottom - cClip.top) );
	m_pModernStr->RenderClipped( &cClipRect );
}

// A dark band, mostly opaque, and a line along its bottom
void CConsole::ModernDrawBackground( const LTRect &cRect )
{
	g_pILTDrawPrim->SetTransformType( DRAWPRIM_TRANSFORM_SCREEN );
	g_pILTDrawPrim->SetZBufferMode( DRAWPRIM_NOZ );
	g_pILTDrawPrim->SetClipMode( DRAWPRIM_NOCLIP );
	g_pILTDrawPrim->SetFillMode( DRAWPRIM_FILL );
	g_pILTDrawPrim->SetCullMode( DRAWPRIM_CULL_NONE );
	g_pILTDrawPrim->SetTexture( LTNULL );
	g_pILTDrawPrim->SetColorOp( DRAWPRIM_NOCOLOROP );
	g_pILTDrawPrim->SetAlphaTestMode( DRAWPRIM_NOALPHATEST );
	g_pILTDrawPrim->SetAlphaBlendMode( DRAWPRIM_BLEND_MOD_SRCALPHA );

	float fEdge = (float)LTMAX( 2, (int)(m_nModernLineHeight / 12) );
	float aTop[2], aBottom[2];
	uint8 aAlpha[2], aShade[2];

	aTop[0] = (float)cRect.top;			aBottom[0] = (float)cRect.bottom - fEdge;
	aTop[1] = aBottom[0];				aBottom[1] = (float)cRect.bottom;
	aAlpha[0] = 216;					aShade[0] = 0;
	aAlpha[1] = 255;					aShade[1] = 120;

	for ( int i = 0; i < 2; i++ )
	{
		LT_POLYF4 cPoly;
		cPoly.rgba.r = aShade[i];
		cPoly.rgba.g = aShade[i];
		cPoly.rgba.b = (uint8)LTMIN( 255, aShade[i] + aShade[i] / 2 );
		cPoly.rgba.a = aAlpha[i];
		cPoly.verts[0].x = (float)cRect.left;	cPoly.verts[0].y = aTop[i];		cPoly.verts[0].z = SCREEN_NEAR_Z;
		cPoly.verts[1].x = (float)cRect.right;	cPoly.verts[1].y = aTop[i];		cPoly.verts[1].z = SCREEN_NEAR_Z;
		cPoly.verts[2].x = (float)cRect.right;	cPoly.verts[2].y = aBottom[i];	cPoly.verts[2].z = SCREEN_NEAR_Z;
		cPoly.verts[3].x = (float)cRect.left;	cPoly.verts[3].y = aBottom[i];	cPoly.verts[3].z = SCREEN_NEAR_Z;
		g_pILTDrawPrim->DrawPrim( &cPoly, 1 );
	}
}

void CConsole::Draw()
{
	RenderStruct *pStruct = GetRenderStruct();
	if ( !pStruct || !pStruct->m_bInitted || !g_pILTDrawPrim )
		return;

	if ( !ModernMakeFont( pStruct->m_Height ) )
		return;

	// The buffer and history sizes and the rectangle, from their variables
	CheckVariables();

	LTRect cRect;
	CalcRect( cRect );
	if ( m_Rect.right == -1 )
		cRect.right = (int)pStruct->m_Width;	// CalcRect keeps 3 pixels off the edge

	int nLine = (int)m_nModernLineHeight;
	int nMargin = nLine / 2;

	ModernDrawBackground( cRect );

	LTRect cText;
	cText.left = cRect.left + nMargin;
	cText.right = cRect.right - nMargin;
	cText.top = cRect.top;
	cText.bottom = cRect.bottom;

	// The command line along the bottom, scrolled sideways if the caret
	// would be past the right edge, and its blinking caret
	const char *pCommand = GetCommandBox()->GetCommand();
	float fY = (float)(cRect.bottom - nMargin - nLine);
	float fPrompt = ModernTextWidth( "> ", -1 );
	float fCaret = fPrompt + ModernTextWidth( pCommand, GetCommandBox()->GetCursorPos() );
	float fRoom = (float)(cText.right - cText.left) - ModernTextWidth( "__", -1 );
	float fX = (float)cText.left - LTMAX( 0.0f, fCaret - fRoom );

	char aCommand[MAX_CONSOLE_TEXTLEN + 4];
	LTSNPrintF( aCommand, sizeof(aCommand), "> %s", pCommand );
	ModernDrawText( aCommand, fX, fY, GetCommandBox()->GetTextColor(), cText );
	if ( (timeGetTime() / 400) & 1 )
		ModernDrawText( "_", fX + fCaret, fY, CONRGB( 255, 255, 255 ), cText );

	// The text above it, newest at the bottom
	m_CS.Enter();

	int iRows = (int)(fY - (float)(cRect.top + nMargin)) / nLine;
	m_nTextLines = (uint32)LTMAX( iRows, 1 );

	GPOS pos = m_TextLines.GetTail();
	int iCount = m_iScrollOffset;
	while ( pos && iCount )
	{
		m_TextLines.GetPrev( pos );
		iCount--;
	}

	float fRowY = fY - (float)nLine;

	// Scrolled back: say there is more below
	if ( m_iScrollOffset && (iRows > 0) )
	{
		ModernDrawText( SCROLL_INDICATOR_UP, (float)cText.left, fRowY, CONRGB( 192, 192, 255 ), cText );
		fRowY -= (float)nLine;
		iRows--;
	}

	while ( pos && (iRows > 0) )
	{
		CConTextLine *pLine = m_TextLines.GetPrev( pos );
		ModernDrawText( pLine->m_Text, (float)cText.left, fRowY, pLine->m_Color, cText );
		fRowY -= (float)nLine;
		iRows--;
	}

	m_CS.Leave();
}

void CConsole::ModernOnOpen()
{
	EndNav();
	GetCommandBox()->Clear();
	m_iScrollOffset = 0;
}

// The names Tab can complete: gathered, then sorted
struct ModernMatches
{
	const char	*m_aNames[MODERN_CONSOLE_MAXMATCHES];
	int			m_nNames;
};

static void ModernAddMatch( const char *pName, void *pUser )
{
	ModernMatches *pMatches = (ModernMatches *)pUser;
	if ( pMatches->m_nNames < MODERN_CONSOLE_MAXMATCHES )
		pMatches->m_aNames[pMatches->m_nNames++] = pName;
}

static int ModernCompareNames( const void *pA, const void *pB )
{
	return stricmp( *(const char **)pA, *(const char **)pB );
}

void CConsole::ModernComplete()
{
	EndNav();

	// Only a first word, with the caret at its end
	const char *pCommand = GetCommandBox()->GetCommand();
	int nLength = strlen( pCommand );
	if ( !nLength || strchr( pCommand, ' ' ) || (GetCommandBox()->GetCursorPos() != nLength) )
		return;

	// "+Name value" saves a variable: complete the name after the sign
	const char *pPrefix = pCommand;
	char aSign[2] = { 0, 0 };
	if ( (pPrefix[0] == '+') || (pPrefix[0] == '-') )
	{
		aSign[0] = pPrefix[0];
		++pPrefix;
	}

	static ModernMatches s_cMatches;
	s_cMatches.m_nNames = 0;
	c_ModernEnumNames( pPrefix, ModernAddMatch, &s_cMatches );
	if ( !s_cMatches.m_nNames )
		return;

	// Sorted, each name once
	qsort( s_cMatches.m_aNames, s_cMatches.m_nNames, sizeof(const char *), ModernCompareNames );
	int nNames = 1;
	int i;
	for ( i = 1; i < s_cMatches.m_nNames; i++ )
	{
		if ( stricmp( s_cMatches.m_aNames[i], s_cMatches.m_aNames[nNames - 1] ) != 0 )
			s_cMatches.m_aNames[nNames++] = s_cMatches.m_aNames[i];
	}

	char aNew[MAX_CONSOLE_TEXTLEN];
	if ( nNames == 1 )
	{
		LTSNPrintF( aNew, sizeof(aNew), "%s%s ", aSign, s_cMatches.m_aNames[0] );
		GetCommandBox()->SetCommand( aNew );
		return;
	}

	// As far as they all agree
	int nCommon = strlen( s_cMatches.m_aNames[0] );
	for ( i = 1; i < nNames; i++ )
	{
		while ( nCommon && strnicmp( s_cMatches.m_aNames[0], s_cMatches.m_aNames[i], nCommon ) != 0 )
			nCommon--;
	}
	if ( nCommon > (int)strlen( pPrefix ) )
	{
		LTSNPrintF( aNew, sizeof(aNew), "%s%.*s", aSign, nCommon, s_cMatches.m_aNames[0] );
		GetCommandBox()->SetCommand( aNew );
	}

	// And the list, several to a line
	char aLine[MAX_CONSOLE_TEXTLEN];
	int nLine = 0;
	aLine[0] = 0;
	for ( i = 0; i < nNames; i++ )
	{
		const char *pName = s_cMatches.m_aNames[i];
		int nName = strlen( pName );
		if ( nLine && ((nLine + 2 + nName) > 76) )
		{
			PrintString( GetCommandBox()->GetTextColor(), 0, aLine );
			nLine = 0;
			aLine[0] = 0;
		}
		LTSNPrintF( &aLine[nLine], sizeof(aLine) - nLine, nLine ? "  %s" : "%s", pName );
		nLine = strlen( aLine );
	}
	if ( nLine )
		PrintString( GetCommandBox()->GetTextColor(), 0, aLine );
}

#endif // NOLF2SRC_MODERN



