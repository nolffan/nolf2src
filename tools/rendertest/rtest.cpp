// tools/rendertest/rtest.cpp: a test harness for the renderer, never part of
// the game. Linked with Lithtech.exe's objects (its WinMain wins with
// /FORCE:MULTIPLE; build.sh), it fills a RenderStruct with its own engine
// callbacks (console variables kept in a table, prints to rtest.log), lists
// the modes, initializes the renderer windowed at the first mode's size (Xvfb
// has only its screen's), and for a while clears, blits a surface (plain and
// optimized), and draws through ILTDrawPrim (gouraud quads, and a quad with a
// bound 64x64 checkerboard texture).
#include "bdefs.h"
#include "renderstruct.h"
#include "iltdrawprim.h"
#include "dtxmgr.h"
#include "de_world.h"
#include <stdio.h>
#include <stdarg.h>

void rdll_RenderDLLSetup(RenderStruct *pStruct);
extern RenderStruct g_Render;
RMode* rdll_GetSupportedModes();

static ILTDrawPrim *g_pDrawPrim;
define_holder_to_instance(ILTDrawPrim, g_pDrawPrim, Internal);

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
static TextureData* T_GetTexture(SharedTexture *p) { return p ? (TextureData*)p->m_pEngineData : NULL; }
static uint16 T_IncTex() { static uint16 n; return ++n; }

static LRESULT CALLBACK WndProc(HWND h, UINT m, WPARAM w, LPARAM l) { return DefWindowProc(h, m, w, l); }

int WINAPI WinMain(HINSTANCE hInst, HINSTANCE, LPSTR, int)
{
	g_Log = fopen("rtest.log", "w");
	Log("rtest start");
	SetParam("windowed", "1");
	SetParam("OptimizeSurfaces", "1");
	SetParam("32BitTextures", "1");	// the checkerboard is uploaded as it is: no 16-bit conversion here

	WNDCLASS wc; memset(&wc, 0, sizeof(wc));
	wc.lpfnWndProc = WndProc; wc.hInstance = hInst; wc.lpszClassName = "LithTech";
	wc.hbrBackground = (HBRUSH)GetStockObject(BLACK_BRUSH);
	RegisterClass(&wc);
	HWND hWnd = CreateWindow("LithTech", "LithTech", WS_OVERLAPPEDWINDOW, 0, 0, 640, 480, NULL, NULL, hInst, NULL);
	ShowWindow(hWnd, SW_SHOW);
	Log("window %p", hWnd);

	// the engine's own RenderStruct (render.cpp): CD3DDrawPrim and the rest of
	// the engine reach the renderer through it
	RenderStruct &rs = g_Render;
	memset(&rs, 0, sizeof(rs));
	rs.GetParameter = T_GetParameter;
	rs.GetParameterValueFloat = T_GetFloat;
	rs.GetParameterValueString = T_GetString;
	rs.RunConsoleString = T_RunConsoleString;
	rs.ConsolePrint = T_ConsolePrint;
	rs.IncObjectFrameCode = T_IncObjectFrameCode;
	rs.GetObjectFrameCode = T_GetObjectFrameCode;
	rs.IncCurTextureFrameCode = T_IncTex;
	rs.GetTexture = T_GetTexture;

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
	Log("ILTDrawPrim %p", g_pDrawPrim);
	Log("Init returned %d (version %d), device %p", r, init.m_RendererVersion, rs.GetD3DDevice ? rs.GetD3DDevice() : NULL);
	if (r != RENDER_OK) { fclose(g_Log); return 1; }
	rs.m_bInitted = 1;

	// a texture, as the engine binds them: a 64x64 ARGB checkerboard
	SharedTexture tex;
	PFormat fmt; fmt.Init(BPP_32, 0xFF000000, 0x00FF0000, 0x0000FF00, 0x000000FF);
	tex.SetTextureInfo(64, 64, fmt);
	TextureData *pTD = dtx_Alloc(BPP_32, 64, 64, 1, NULL, NULL);
	Log("dtx_Alloc %p", pTD);
	if (pTD)
	{
		pTD->m_PFormat = fmt;
		pTD->m_Header.m_Extra[2] = BPP_32;	// as CSysTexInterface::CreateTextureFromData sets it
		pTD->m_pSharedTexture = &tex;
		tex.m_pEngineData = pTD;
		TextureMipData &mip = pTD->m_Mips[0];
		for (uint32 y = 0; y < 64; y++)
			for (uint32 x = 0; x < 64; x++)
				((uint32*)(mip.m_Data + y * mip.m_Pitch))[x] = (((x / 8) ^ (y / 8)) & 1) ? 0xFFFFC000 : 0xFF2040FF;
		rs.BindTexture(&tex, false);
		Log("BindTexture: render data %p", tex.m_pRenderData);
	}

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
		if (g_pDrawPrim)
		{
			// a few gouraud quads through ILTDrawPrim, as the interface draws
			g_pDrawPrim->BeginDrawPrim();
			g_pDrawPrim->SetTransformType(DRAWPRIM_TRANSFORM_SCREEN);
			g_pDrawPrim->SetColorOp(DRAWPRIM_NOCOLOROP);
			g_pDrawPrim->SetAlphaBlendMode(DRAWPRIM_BLEND_MOD_SRCALPHA);
			g_pDrawPrim->SetZBufferMode(DRAWPRIM_NOZ);
			g_pDrawPrim->SetAlphaTestMode(DRAWPRIM_NOALPHATEST);
			g_pDrawPrim->SetTexture(NULL);
			for (int q = 0; q < 3; q++)
			{
				LT_POLYG4 quad;
				float x0 = 300.0f + q * 120.0f, y0 = 300.0f;
				float xs[4] = { x0, x0 + 100.0f, x0 + 100.0f, x0 };
				float ys[4] = { y0, y0, y0 + 100.0f, y0 + 100.0f };
				for (int v = 0; v < 4; v++)
				{
					quad.verts[v].x = xs[v]; quad.verts[v].y = ys[v]; quad.verts[v].z = 0.0f;
					quad.verts[v].rgba.r = (uint8)(v == 0 || q == 0 ? 255 : 0);
					quad.verts[v].rgba.g = (uint8)(v == 1 || q == 1 ? 255 : 0);
					quad.verts[v].rgba.b = (uint8)(v == 2 || q == 2 ? 255 : 0);
					quad.verts[v].rgba.a = 255;
				}
				LTRESULT res = g_pDrawPrim->DrawPrim(&quad, 1);
				if (i == 0 && q == 0) Log("DrawPrim returned %d", res);
			}
			if (tex.m_pRenderData)
			{
				LT_POLYGT4 tq;
				float xs[4] = { 700.0f, 900.0f, 900.0f, 700.0f };
				float ys[4] = { 100.0f, 100.0f, 300.0f, 300.0f };
				float us[4] = { 0.0f, 1.0f, 1.0f, 0.0f };
				float vs[4] = { 0.0f, 0.0f, 1.0f, 1.0f };
				for (int v = 0; v < 4; v++)
				{
					tq.verts[v].x = xs[v]; tq.verts[v].y = ys[v]; tq.verts[v].z = 0.0f;
					tq.verts[v].u = us[v]; tq.verts[v].v = vs[v];
					tq.verts[v].rgba.r = tq.verts[v].rgba.g = tq.verts[v].rgba.b = tq.verts[v].rgba.a = 255;
				}
				g_pDrawPrim->SetTexture(&tex);
				g_pDrawPrim->SetColorOp(DRAWPRIM_MODULATE);
				LTRESULT res = g_pDrawPrim->DrawPrim(&tq, 1);
				if (i == 0) Log("textured DrawPrim returned %d", res);
				g_pDrawPrim->SetTexture(NULL);
			}
			g_pDrawPrim->EndDrawPrim();
		}
		rs.End3D();
		rs.SwapBuffers(0);
		if (i == 0) Log("first frame done (Start3D %d)", b3d);
		Sleep(30);
	}
	Log("frames done");
	if (hSurf) rs.DeleteSurface(hSurf);
	if (tex.m_pRenderData) rs.UnbindTexture(&tex);
	rs.Term(true);
	Log("Term done");
	fclose(g_Log);
	return 0;
}
