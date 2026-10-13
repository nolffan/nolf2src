
#include "bdefs.h"
#include "videomgr.h"

#include "binkvideomgrimpl.h"

extern int32 g_CV_VideoDebug;

void VideoMgr::UpdateVideos()
{
	uint32 nRunning = 0;
	for(MPOS pos=m_Videos; pos; ) 
	{
		VideoInst *pVideo = m_Videos.GetNext(pos);

		pVideo->Update();
			
		if(pVideo->GetVideoStatus() == LT_OK)
			++nRunning;
	}

	if( g_CV_VideoDebug ) 
	{
		dsi_ConsolePrint("%d videos, %d active", m_Videos.GetSize(), nRunning);
	}
}


void VideoMgr::OnRenderInit()
{
	MPOS pos;

	for( pos = m_Videos; pos; )
		m_Videos.GetNext(pos)->OnRenderInit();
}


void VideoMgr::OnRenderTerm()
{
	MPOS pos;

	for( pos = m_Videos; pos; )
		m_Videos.GetNext(pos)->OnRenderTerm();
}




// -------------------------------------------------------------------------------- //
// The starting point...
//
//	Create the appropriate videomgr 
//
// 
//
// -------------------------------------------------------------------------------- //
VideoMgr* CreateVideoMgr( const char *pszName )
{
	bool want_bink    = (stricmp( pszName, "BINK" ) == 0);

	// load bink

	if( want_bink ) 
	{
		// load bink //

		// Note: Bink can play Smacker files.
		VideoMgr* pVidMgr;
		LT_MEM_TRACK_ALLOC(pVidMgr = new BinkVideoMgr(),LT_MEM_TYPE_MISC);
		if( pVidMgr )
		{
			if(((BinkVideoMgr*)pVidMgr)->Init() == LT_OK)
			{
				//success, give them back the video manager
				return pVidMgr;
			}

			//we failed to initialize
			delete pVidMgr;
			pVidMgr = NULL;
		}

	}
  
	return LTNULL;
}


