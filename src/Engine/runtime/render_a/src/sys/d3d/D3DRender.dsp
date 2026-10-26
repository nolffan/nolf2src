# Microsoft Developer Studio Project File - Name="D3DRender" - Package Owner=<4>
# Microsoft Developer Studio Generated Build File, Format Version 6.00
# ** DO NOT EDIT **

# TARGTYPE "Win32 (x86) Static Library" 0x0104

CFG=D3DRender - Win32 Final
!MESSAGE This is not a valid makefile. To build this project using NMAKE,
!MESSAGE use the Export Makefile command and run
!MESSAGE 
!MESSAGE NMAKE /f "D3DRender.mak".
!MESSAGE 
!MESSAGE You can specify a configuration when running NMAKE
!MESSAGE by defining the macro CFG on the command line. For example:
!MESSAGE 
!MESSAGE NMAKE /f "D3DRender.mak" CFG="D3DRender - Win32 Final"
!MESSAGE 
!MESSAGE Possible choices for configuration are:
!MESSAGE 
!MESSAGE "D3DRender - Win32 Final" (based on "Win32 (x86) Static Library")
!MESSAGE 

# nolf2src: the renderer, render_a (LIB_D3DRender in the LithTech Jupiter
# tree, ported there to Direct3D 9; NOLF2's is Direct3D 8), a static
# library of Lithtech.exe (Engine.dsw). It precompiles precompile.h, as
# retail's did: retail's renderer has math_phys.h's initializer group only
# in rendererconsolevars (taken as the /Yc file), memstats_world and
# texturescriptinterpreter (which does not include precompile.h), the two
# built without the header.
# Begin Project
# PROP AllowPerConfigDependencies 0
# PROP Scc_ProjName ""
# PROP Scc_LocalPath ""
CPP=cl.exe
RSC=rc.exe

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP BASE Use_MFC 0
# PROP BASE Use_Debug_Libraries 0
# PROP BASE Output_Dir "Final"
# PROP BASE Intermediate_Dir "Final"
# PROP BASE Target_Dir ""
# PROP Use_MFC 0
# PROP Use_Debug_Libraries 0
# PROP Output_Dir "..\..\..\..\..\built\Final\D3DRender"
# PROP Intermediate_Dir "..\..\..\..\..\built\Final\D3DRender"
# PROP Target_Dir ""
# ADD BASE CPP /nologo /W3 /GX /O2 /D "WIN32" /D "NDEBUG" /D "_WINDOWS" /D "_MBCS" /YX /FD /c
# ADD CPP /nologo /MD /W3 /GX /O2 /Ob2 /Zm200 /I "..\..\..\..\..\..\libs\STLPort-4.0\stlport" /I "." /I "..\shadows" /I "..\..\..\..\client\src" /I "..\..\..\..\shared\src" /I "..\..\..\..\kernel\src" /I "..\..\..\..\kernel\mem\src" /I "..\..\..\..\world\src" /I "..\..\..\..\kernel\io\src" /I "..\..\..\..\kernel\net\src" /I "..\..\..\..\model\src" /I "..\..\..\..\sound\src" /I "..\..\..\..\shared\src\sys\win" /I "..\..\..\..\lithtemplate" /I "..\..\..\..\physics\src" /I "..\..\..\..\render_b\src" /I "..\..\..\..\ui\src" /I "..\..\..\..\controlfilemgr" /I "..\..\..\..\server\src" /I "..\..\..\..\kernel\src\sys\win" /I "..\..\..\..\kernel\io\src\sys\win" /I "..\..\..\..\kernel\mem\src\sys\win" /I "..\..\..\..\kernel\net\src\sys\win" /I "..\..\..\..\client\src\sys\win" /I "." /I "..\..\..\..\..\sdk\inc" /I "..\..\..\..\..\sdk\inc\physics" /I "..\..\..\..\..\..\libs\stdlith" /I "..\..\..\..\..\..\libs\lith" /I "..\..\..\..\..\libs\rezmgr" /D "WIN32" /D "NDEBUG" /D "_WINDOWS" /D "_MBCS" /D "_FINAL" /D "__D3D" /D "__D3DREND" /D "_LIB" /Yu"precompile.h" /FD /c
BSC32=bscmake.exe
# ADD BASE BSC32 /nologo
# ADD BSC32 /nologo
LIB32=link.exe -lib
# ADD BASE LIB32 /nologo
# ADD LIB32 /nologo /out:"..\..\..\..\..\built\Final\D3DRender\D3DRender.lib"
!ENDIF 

# Begin Target

# Name "D3DRender - Win32 Final"
# Begin Group "Source Files"

# PROP Default_Filter "cpp;c;cxx;rc;def;r;odl;idl;hpj;bat"
# Begin Source File

SOURCE=.\d3d_device.cpp
# End Source File
# Begin Source File

SOURCE=.\common_init.cpp
# End Source File
# Begin Source File

SOURCE=.\d3d_renderstyleinterface.cpp
# End Source File
# Begin Source File

SOURCE=.\d3d_texture.cpp
# End Source File
# Begin Source File

SOURCE=.\d3d_init.cpp
# End Source File
# Begin Source File

SOURCE=.\d3d_device_wrapper.cpp
# End Source File
# Begin Source File

SOURCE=.\d3d_renderworld.cpp
# End Source File
# Begin Source File

SOURCE=.\d3d_draw.cpp
# End Source File
# Begin Source File

SOURCE=.\d3d_utils.cpp
# End Source File
# Begin Source File

SOURCE=.\d3d_shell.cpp
# End Source File
# Begin Source File

SOURCE=.\pixelshadermgr.cpp
# End Source File
# Begin Source File

SOURCE=.\screenglowmgr.cpp
# End Source File
# Begin Source File

SOURCE=.\d3dmeshrendobj_rigid.cpp
# End Source File
# Begin Source File

SOURCE=.\rendershadowlist.cpp
# End Source File
# Begin Source File

SOURCE=.\drawobjects.cpp
# End Source File
# Begin Source File

SOURCE=.\tagnodes.cpp
# End Source File
# Begin Source File

SOURCE=.\d3d_surface.cpp
# End Source File
# Begin Source File

SOURCE=.\memstats_world.cpp
# SUBTRACT CPP /YX /Yc /Yu
# End Source File
# Begin Source File

SOURCE=.\d3d_renderblock.cpp
# End Source File
# Begin Source File

SOURCE=.\modelshadowshader.cpp
# End Source File
# Begin Source File

SOURCE=.\d3d_rendershader_dynamiclight.cpp
# End Source File
# Begin Source File

SOURCE=.\d3d_renderworld_occluder.cpp
# End Source File
# Begin Source File

SOURCE=.\texturescriptmgr.cpp
# End Source File
# Begin Source File

SOURCE=.\drawpolygrid.cpp
# End Source File
# Begin Source File

SOURCE=.\3d_ops.cpp
# End Source File
# Begin Source File

SOURCE=.\aabb.cpp
# End Source File
# Begin Source File

SOURCE=.\common_draw.cpp
# End Source File
# Begin Source File

SOURCE=.\common_stuff.cpp
# End Source File
# Begin Source File

SOURCE=.\d3d_drawsky.cpp
# End Source File
# Begin Source File

SOURCE=.\d3d_optimizedsurface.cpp
# End Source File
# Begin Source File

SOURCE=.\d3d_rendershader_glow.cpp
# End Source File
# Begin Source File

SOURCE=.\d3d_rendershader_gouraud.cpp
# End Source File
# Begin Source File

SOURCE=.\d3d_rendershader_gouraud_fullbright.cpp
# End Source File
# Begin Source File

SOURCE=.\d3d_rendershader_lightmap.cpp
# End Source File
# Begin Source File

SOURCE=.\d3d_renderstatemgr.cpp
# End Source File
# Begin Source File

SOURCE=.\d3d_renderstyle.cpp
# End Source File
# Begin Source File

SOURCE=.\d3d_viewparams.cpp
# End Source File
# Begin Source File

SOURCE=.\d3dmeshrendobj_skel.cpp
# End Source File
# Begin Source File

SOURCE=.\d3dmeshrendobj_vertanim.cpp
# End Source File
# Begin Source File

SOURCE=..\shadows\d3dshadowtexture.cpp
# End Source File
# Begin Source File

SOURCE=.\devicelightlist.cpp
# End Source File
# Begin Source File

SOURCE=.\dirtyrect.cpp
# End Source File
# Begin Source File

SOURCE=.\draw_canvas.cpp
# End Source File
# Begin Source File

SOURCE=.\drawlight.cpp
# End Source File
# Begin Source File

SOURCE=.\drawlinesystem.cpp
# End Source File
# Begin Source File

SOURCE=.\drawmodel.cpp
# End Source File
# Begin Source File

SOURCE=.\drawparticles.cpp
# End Source File
# Begin Source File

SOURCE=.\drawparticles_A.cpp
# End Source File
# Begin Source File

SOURCE=.\drawsky.cpp
# End Source File
# Begin Source File

SOURCE=.\drawsprite.cpp
# End Source File
# Begin Source File

SOURCE=.\drawvolumeeffects.cpp
# End Source File
# Begin Source File

SOURCE=.\drawworldmodel.cpp
# End Source File
# Begin Source File

SOURCE=.\modeldebug.cpp
# End Source File
# Begin Source File

SOURCE=.\objectgroupmgr.cpp
# End Source File
# Begin Source File

SOURCE=.\relevantlightlist.cpp
# End Source File
# Begin Source File

SOURCE=.\rendererconsolevars.cpp
# ADD CPP /Yc"precompile.h"
# End Source File
# Begin Source File

SOURCE=.\renderlight.cpp
# End Source File
# Begin Source File

SOURCE=.\rendermodelinfolist.cpp
# End Source File
# Begin Source File

SOURCE=.\rendermodelpiecelist.cpp
# End Source File
# Begin Source File

SOURCE=.\renderstylelookuptables.cpp
# End Source File
# Begin Source File

SOURCE=.\renderstylemap.cpp
# End Source File
# Begin Source File

SOURCE=.\setupmodel.cpp
# End Source File
# Begin Source File

SOURCE=.\setuptouchinglights.cpp
# End Source File
# Begin Source File

SOURCE=.\texturescriptinstance.cpp
# End Source File
# Begin Source File

SOURCE=.\texturescriptinterpreter.cpp
# SUBTRACT CPP /YX /Yc /Yu
# End Source File
# Begin Source File

SOURCE=.\texturescriptvarmgr.cpp
# End Source File
# Begin Source File

SOURCE=.\VertexBufferController.cpp
# End Source File
# End Group
# End Target
# End Project
