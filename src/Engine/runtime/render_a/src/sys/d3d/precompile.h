
// This file includes the main headers for d3drender.

#ifndef __PRECOMPILE_H__
#define __PRECOMPILE_H__

#define DIRECT3D_VERSION        0x0800

#ifndef __BDEFS_H__
#include "bdefs.h"
#endif

#ifndef __LTBASEDEFS_H__
#include "ltbasedefs.h"
#endif

#ifndef __D3D8_H__
#include <d3d8.h>
#define __D3D8_H__
#endif

#ifndef __D3D8TYPES_H__
#include <d3d8types.h>
#define __D3D8TYPES_H__
#endif

#ifndef __D3DX8_H__
#include <d3dx8.h>
#define __D3DX8_H__
#endif


#ifndef __D3D8CAPS_H__
#include <d3d8caps.h>
#define __D3D8CAPS_H__
#endif

#ifndef __D3D_DEFS_H__
#include "d3d_defs.h"
#endif

 
#define FASTCALL __fastcall

 
// STL
#pragma warning(disable : 4786)
#include <vector>
#include <list>
#ifndef __CODEWARRIOR
using namespace std;
#endif
#endif  // __PRECOMPILE_H__



