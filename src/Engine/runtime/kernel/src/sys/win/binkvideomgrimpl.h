
// This file contains the definitions for the PC version of the VideoMgr implementation.

#ifndef __BINKVIDEOMGRIMPL_H__
#define __BINKVIDEOMGRIMPL_H__

#ifndef __VIDEOMGR_H__
#include "videomgr.h"
#endif

#ifndef __RENDERSTRUCT_H__
#include "renderstruct.h"
#endif

#ifndef __DTXMGR_H__
#include "dtxmgr.h"
#endif

#ifndef __DE_WORLD_H__
#include "de_world.h"
#endif

#ifndef __RENDER_H__
#include "render.h"
#endif

// nolf2src: the engine loads Binkw32.dll at run time and uses nothing of
// RAD's SDK but these entry points, the first fields of the BINK structure
// and a few flag values, so they are declared here rather than taken from
// bink.h (BINK 1.x, as Binkw32.dll exports it: __stdcall, "_BinkOpen@8").
#define RADEXPLINK __stdcall

typedef unsigned char	u8;
typedef unsigned int	u32;
typedef signed int		s32;

typedef struct BINK
{
	u32 Width;			// width of the video
	u32 Height;			// height of the video
	u32 Frames;			// number of frames
	u32 FrameNum;		// frame about to be displayed (1 based)
	// the rest is Binkw32.dll's own
} BINK, *HBINK;

// BinkOpen flags
#define BINKFILEHANDLE		0x00800000L
#define BINKFROMMEMORY		0x04000000L

// BinkCopyToBuffer flags
#define BINKCOPY2XHI		0x20000000L

typedef void *BINKSNDOPEN;
typedef BINKSNDOPEN (RADEXPLINK *BINKSNDSYSOPEN)(u32 param);

typedef u8 (RADEXPLINK *BinkSoundFn)(BINKSNDSYSOPEN open, u32 param);
typedef BINKSNDOPEN (RADEXPLINK *BinkMilesFn)(u32 param);
typedef BINKSNDOPEN (RADEXPLINK *BinkDSndFn)(u32 param);
typedef HBINK (RADEXPLINK *BinkOpenFn)(const char* name,u32 flags);
typedef void (RADEXPLINK *BinkCloseFn)(HBINK bnk);
typedef u32 (RADEXPLINK *BinkWaitFn)(HBINK bnk);
typedef void (RADEXPLINK *BinkToBufferFn)(HBINK bnk,void* buf,u32 left,u32 top,u32 Pitch,u32 destheight,u32 Flags);
typedef u32 (RADEXPLINK *BinkDoFrameFn)(HBINK bnk);
typedef void (RADEXPLINK *BinkNextFrameFn)(HBINK bnk);
typedef s32 (RADEXPLINK *BinkIsSoftCursorFn)(void* lpSurface, HCURSOR hCur);
typedef s32 (RADEXPLINK *BinkCheckCursorFn)(HWND hWnd, s32 x, s32 y, s32 w, s32 h);
typedef s32 (RADEXPLINK *BinkRestoreCursorFn)(s32 checkcount);
typedef s32 (RADEXPLINK *BinkDX8SurfaceTypeFn)(void* lpD3Ds);

class BinkVideoInst;

// -------------------------------------------------------------------------------- //
// BinkVideoMgr.
// -------------------------------------------------------------------------------- //
class BinkVideoMgr : public VideoMgr
{
public:
                
						BinkVideoMgr();
						~BinkVideoMgr();

    LTRESULT			Init();

    virtual LTRESULT	CreateScreenVideo(const char *pFilename, uint32 flags, VideoInst* &pVideo);

public:

	//video flags
    uint32						m_VideoFlags;

	//Bink interface
    BinkSoundFn                 m_BinkSoundFn;
    BinkDSndFn                  m_BinkDSndFn;
    BinkOpenFn                  m_BinkOpen;
    BinkCloseFn                 m_BinkClose;
    BinkWaitFn                  m_BinkWait;
    BinkToBufferFn              m_BinkToBuffer;
    BinkDoFrameFn               m_BinkDoFrame;
    BinkNextFrameFn             m_BinkNextFrame;
    BinkIsSoftCursorFn          m_BinkIsSoftCursorFn;
    BinkCheckCursorFn           m_BinkCheckCursorFn;
    BinkRestoreCursorFn         m_BinkRestoreCursorFn;
	BinkDX8SurfaceTypeFn		m_BinkDX8SurfaceTypeFn;
    HINSTANCE                   m_hBinkDLL;
};


// -------------------------------------------------------------------------------- //
// BinkVideoInst.
// -------------------------------------------------------------------------------- //
class BinkVideoInst : public VideoInst
{
public:

					    BinkVideoInst(BinkVideoMgr *pMgr);
					    ~BinkVideoInst();
    
    LTRESULT			InitBaseVideo(const char *pFilename, uint32 flags);
    LTRESULT			InitScreen();
    void				Term();

    void				OnRenderInit();
    void				OnRenderTerm();

    virtual LTRESULT	Update();
    virtual LTRESULT	DrawVideo();
    virtual LTRESULT	GetVideoStatus();
    virtual void		Release();

    bool				IsAtLastFrame();
    LTRESULT			UpdateOnScreen();

private:

	//fills in our texture with black
	bool				ClearSurface();

	//handle to the actual bink video
	HBINK				m_bnk;

	//pointer to the manager that created us
    BinkVideoMgr		*m_pMgr;
    
    // The on-screen rendering surface
    LPDIRECT3DTEXTURE8  m_pTexture;

	//flags for the video
    uint32				m_Flags;

	//the bink format that corresponds to our surface type
    uint32				m_BufferFormat;

	//the dimensions of the surface that we have allocated
	uint32				m_nTextureWidth;
	uint32				m_nTextureHeight;
};




#endif
