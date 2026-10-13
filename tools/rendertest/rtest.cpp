// tools/rendertest/rtest.cpp: a test harness for the renderer, never part of
// the game. Linked with Lithtech.exe's objects (its WinMain wins with
// /FORCE:MULTIPLE; build.sh), it fills a RenderStruct with its own engine
// callbacks (console variables kept in a table, prints to rtest.log), lists
// the modes, initializes the renderer windowed at the first mode's size (Xvfb
// has only its screen's), and clears and blits a surface for a while.
#include "bdefs.h"
#include "renderstruct.h"
#include <stdio.h>
#include <stdarg.h>

void rdll_RenderDLLSetup(RenderStruct *pStruct);
RMode* rdll_GetSupportedModes();

static FILE *g_Log;
static void Log(const char *fmt, ...)
{
	va_list v; va_start(v, fmt); vfprintf(g_Log, fmt, v); va_end(v);
	fputc('\n', g_Log); fflush(g_Log);
}

struct FakeParam { char name[64]; float f; char s[32]; };
static FakeParam g_Params[512];
static int g_nParams;

static FakeParam* FindParam(const char *pName)
{
	for (int i = 0; i < g_nParams; i++)
		if (stricmp(pName, g_Params[i].name) == 0) return &g_Params[i];
	return NULL;
}
static void SetParam(const char *pName, const char *pVal)
{
	FakeParam *p = FindParam(pName);
	if (!p && g_nParams < 512) { p = &g_Params[g_nParams++]; strncpy(p->name, pName, 63); }
	if (!p) return;
	strncpy(p->s, pVal, 31); p->f = (float)atof(pVal);
}

static HLTPARAM T_GetParameter(char *pName) { return FindParam(pName); }
static float T_GetFloat(HLTPARAM h) { return h ? ((FakeParam*)h)->f : 0.0f; }
static char* T_GetString(HLTPARAM h) { return h ? ((FakeParam*)h)->s : NULL; }
static void T_RunConsoleString(char *p)
{
	char name[64], val[64];
	if (sscanf(p, "%63s %63s", name, val) == 2 && !FindParam(name)) SetParam(name, val);
}
static void T_ConsolePrint(char *pMsg, ...)
{
	char buf[512]; va_list v; va_start(v, pMsg); _vsnprintf(buf, sizeof(buf), pMsg, v); va_end(v);
	Log("ConsolePrint: %s", buf);
}
static uint32 g_Frame;
static uint32 T_IncObjectFrameCode() { return ++g_Frame; }
static uint32 T_GetObjectFrameCode() { return g_Frame; }
static uint16 T_IncTex() { static uint16 n; return ++n; }

static LRESULT CALLBACK WndProc(HWND h, UINT m, WPARAM w, LPARAM l) { return DefWindowProc(h, m, w, l); }

int WINAPI WinMain(HINSTANCE hInst, HINSTANCE, LPSTR, int)
{
	g_Log = fopen("rtest.log", "w");
	Log("rtest start");
	SetParam("windowed", "1");
	SetParam("OptimizeSurfaces", "1");

	WNDCLASS wc; memset(&wc, 0, sizeof(wc));
	wc.lpfnWndProc = WndProc; wc.hInstance = hInst; wc.lpszClassName = "LithTech";
	wc.hbrBackground = (HBRUSH)GetStockObject(BLACK_BRUSH);
	RegisterClass(&wc);
	HWND hWnd = CreateWindow("LithTech", "LithTech", WS_OVERLAPPEDWINDOW, 0, 0, 640, 480, NULL, NULL, hInst, NULL);
	ShowWindow(hWnd, SW_SHOW);
	Log("window %p", hWnd);

	RenderStruct rs;
	memset(&rs, 0, sizeof(rs));
	rs.GetParameter = T_GetParameter;
	rs.GetParameterValueFloat = T_GetFloat;
	rs.GetParameterValueString = T_GetString;
	rs.RunConsoleString = T_RunConsoleString;
	rs.ConsolePrint = T_ConsolePrint;
	rs.IncObjectFrameCode = T_IncObjectFrameCode;
	rs.GetObjectFrameCode = T_GetObjectFrameCode;
	rs.IncCurTextureFrameCode = T_IncTex;

	RMode *pModes = rdll_GetSupportedModes();
	int nModes = 0;
	for (RMode *p = pModes; p; p = p->m_pNext)
	{
		if (nModes < 8) Log("mode %dx%dx%d hwtnl %d '%s' '%s'", p->m_Width, p->m_Height, p->m_BitDepth, p->m_bHWTnL, p->m_InternalName, p->m_Description);
		nModes++;
	}
	Log("%d modes", nModes);

	uint32 nW = 640, nH = 480;
	if (pModes) { nW = pModes->m_Width; nH = pModes->m_Height; }	// Xvfb has only its screen size
	rdll_RenderDLLSetup(&rs);
	rs.m_Width = nW; rs.m_Height = nH;

	RenderStructInit init; memset(&init, 0, sizeof(init));
	init.m_hWnd = hWnd;
	init.m_Mode.m_Width = nW; init.m_Mode.m_Height = nH; init.m_Mode.m_BitDepth = 32; init.m_Mode.m_bHWTnL = false;
	int r = rs.Init(&init);
	Log("Init returned %d (version %d), device %p", r, init.m_RendererVersion, rs.GetD3DDevice ? rs.GetD3DDevice() : NULL);
	if (r != RENDER_OK) { fclose(g_Log); return 1; }
	rs.m_bInitted = 1;

	// a surface, as the console and the interface use them
	{ FakeParam *p = FindParam("OptimizeSurfaces"); Log("%d params; OptimizeSurfaces %s", g_nParams, p ? p->s : "(none)"); }
	HLTBUFFER hSurf = rs.CreateSurface(64, 64);
	Log("CreateSurface %p", hSurf);
	if (hSurf)
	{
		uint32 pitch = 0;
		uint8 *pData = (uint8*)rs.LockSurface(hSurf, pitch);
		Log("LockSurface %p pitch %d", pData, pitch);
		if (pData)
		{
			for (int y = 0; y < 64; y++) memset(pData + y*pitch, (y*4) & 0xff, 64*4 > pitch ? pitch : 64*4);
			rs.UnlockSurface(hSurf);
		}
		bool bOpt = rs.OptimizeSurface(hSurf, OPTIMIZE_NO_TRANSPARENCY);
		Log("OptimizeSurface %d", bOpt);
	}

	for (int i = 0; i < 300; i++)
	{
		MSG msg;
		while (PeekMessage(&msg, NULL, 0, 0, PM_REMOVE)) { TranslateMessage(&msg); DispatchMessage(&msg); }
		bool b3d = rs.Start3D();
		LTRGBColor c; c.rgb.r = (uint8)(i*3); c.rgb.g = 64; c.rgb.b = 160; c.rgb.a = 0;
		rs.Clear(NULL, CLEARSCREEN_SCREEN | CLEARSCREEN_RENDER, c);
		if (hSurf && rs.StartOptimized2D())
		{
			LTRect src(0, 0, 64, 64), dst(100 + i, 100, 164 + i, 164);
			BlitRequest req;
			req.m_hBuffer = hSurf; req.m_BlitOptions = 0;
			req.m_pSrcRect = &src; req.m_pDestRect = &dst; req.m_Alpha = 1.0f;
			rs.BlitToScreen(&req);
			rs.EndOptimized2D();
		}
		rs.End3D();
		rs.SwapBuffers(0);
		if (i == 0) Log("first frame done (Start3D %d)", b3d);
		Sleep(30);
	}
	Log("frames done");
	if (hSurf) rs.DeleteSurface(hSurf);
	rs.Term(true);
	Log("Term done");
	fclose(g_Log);
	return 0;
}
