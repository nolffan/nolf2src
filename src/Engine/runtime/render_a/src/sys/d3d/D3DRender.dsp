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
# library of Lithtech.exe (Engine.dsw). Files marked Exclude_From_Build do
# not compile yet (docs/engine/PLAN.md).
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
# ADD CPP /nologo /MD /W3 /GX /O2 /Zm200 /I "..\..\..\..\..\..\libs\STLPort-4.0\stlport" /I "." /I "..\shadows" /I "..\..\..\..\client\src" /I "..\..\..\..\shared\src" /I "..\..\..\..\kernel\src" /I "..\..\..\..\kernel\mem\src" /I "..\..\..\..\world\src" /I "..\..\..\..\kernel\io\src" /I "..\..\..\..\kernel\net\src" /I "..\..\..\..\model\src" /I "..\..\..\..\sound\src" /I "..\..\..\..\shared\src\sys\win" /I "..\..\..\..\lithtemplate" /I "..\..\..\..\physics\src" /I "..\..\..\..\render_b\src" /I "..\..\..\..\ui\src" /I "..\..\..\..\controlfilemgr" /I "..\..\..\..\server\src" /I "..\..\..\..\kernel\src\sys\win" /I "..\..\..\..\kernel\io\src\sys\win" /I "..\..\..\..\kernel\mem\src\sys\win" /I "..\..\..\..\kernel\net\src\sys\win" /I "..\..\..\..\client\src\sys\win" /I "." /I "..\..\..\..\..\sdk\inc" /I "..\..\..\..\..\sdk\inc\physics" /I "..\..\..\..\..\..\libs\stdlith" /I "..\..\..\..\..\..\libs\lith" /I "..\..\..\..\..\libs\rezmgr" /D "WIN32" /D "NDEBUG" /D "_WINDOWS" /D "_MBCS" /D "_FINAL" /D "__D3D" /D "__D3DREND" /D "_LIB" /FD /c
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

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\common_init.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\d3d_renderstyleinterface.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\d3d_texture.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\d3d_init.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\d3d_renderworld.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\d3d_draw.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\d3d_utils.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\d3d_shell.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\screenglowmgr.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\d3dmeshrendobj_rigid.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\rendershadowlist.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\drawobjects.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\tagnodes.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\d3d_surface.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\memstats_world.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\d3d_renderblock.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\modelshadowshader.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\d3d_rendershader_dynamiclight.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\d3d_renderworld_occluder.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\texturescriptmgr.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\drawpolygrid.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\3d_ops.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\aabb.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\common_draw.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\common_stuff.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\d3d_device_wrapper.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\d3d_drawsky.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\d3d_optimizedsurface.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\d3d_rendershader_glow.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\d3d_rendershader_gouraud.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\d3d_rendershader_gouraud_fullbright.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\d3d_rendershader_lightmap.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\d3d_renderstatemgr.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\d3d_renderstyle.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\d3d_viewparams.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\d3dmeshrendobj_skel.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\d3dmeshrendobj_vertanim.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=..\shadows\d3dshadowtexture.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\devicelightlist.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\dirtyrect.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\draw_canvas.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\drawlight.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\drawlinesystem.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\drawmodel.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\drawparticles.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\drawparticles_A.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\drawsky.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\drawsprite.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\drawvolumeeffects.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\drawworldmodel.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\modeldebug.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\objectgroupmgr.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\relevantlightlist.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\rendererconsolevars.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\renderlight.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\rendermodelinfolist.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\rendermodelpiecelist.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\renderstylelookuptables.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\renderstylemap.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\setupmodel.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\setuptouchinglights.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\texturescriptinstance.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\texturescriptinterpreter.cpp
# End Source File
# Begin Source File

SOURCE=.\texturescriptvarmgr.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\VertexBufferController.cpp

!IF  "$(CFG)" == "D3DRender - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\nolf2src_render_stubs.cpp
# End Source File
# End Group
# End Target
# End Project
