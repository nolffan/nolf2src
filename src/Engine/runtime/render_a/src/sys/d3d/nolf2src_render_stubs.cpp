// nolf2src: the renderer, stubbed (docs/engine/PLAN.md, "skeleton"): none
// of render_a compiles yet (it is Direct3D 9; NOLF2's is Direct3D 8), so
// this is what Lithtech.exe's link needs of it. There is no device:
// rdll_RenderDLLSetup leaves the render struct as it is, so the engine
// finds no renderer.

#include "bdefs.h"
#include "renderstruct.h"

class D3DRenderStyles;
D3DRenderStyles* __impl_ptr_D3DRenderStyles_Default__ = LTNULL;

void rdll_RenderDLLSetup(RenderStruct *pStruct)
{
}

RMode* rdll_GetSupportedModes()
{
	return LTNULL;
}

void rdll_FreeModeList(RMode *pModes)
{
}
