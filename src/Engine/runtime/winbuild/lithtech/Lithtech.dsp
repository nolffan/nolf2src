# Microsoft Developer Studio Project File - Name="Lithtech" - Package Owner=<4>
# Microsoft Developer Studio Generated Build File, Format Version 6.00
# ** DO NOT EDIT **

# TARGTYPE "Win32 (x86) Application" 0x0101

CFG=Lithtech - Win32 Final
!MESSAGE This is not a valid makefile. To build this project using NMAKE,
!MESSAGE use the Export Makefile command and run
!MESSAGE 
!MESSAGE NMAKE /f "Lithtech.mak".
!MESSAGE 
!MESSAGE You can specify a configuration when running NMAKE
!MESSAGE by defining the macro CFG on the command line. For example:
!MESSAGE 
!MESSAGE NMAKE /f "Lithtech.mak" CFG="Lithtech - Win32 Final"
!MESSAGE 
!MESSAGE Possible choices for configuration are:
!MESSAGE 
!MESSAGE "Lithtech - Win32 Final" (based on "Win32 (x86) Application")
!MESSAGE 

# nolf2src: Lithtech.exe, the engine, from the LithTech Jupiter runtime
# (Engine.dsw). The files are those of Jupiter's EXE_Lithtech list that the
# retail image has, in the retail link order (docs/engine/anatomy.md):
# controlfilemgr, the rest alphabetically, then the interface
# implementations; the libraries after them in the order the retail image
# has them (d3dx8, ltmem, the renderer, the sound loader, RezMgr, the UI).
# Files marked Exclude_From_Build do not compile yet: they are each module
# package's worklist (docs/engine/PLAN.md); runtime/*/nolf2src_*_stubs.cpp
# stands in for what of them the link needs.
# Begin Project
# PROP AllowPerConfigDependencies 0
# PROP Scc_ProjName ""
# PROP Scc_LocalPath ""
CPP=cl.exe
MTL=midl.exe
RSC=rc.exe

!IF  "$(CFG)" == "Lithtech - Win32 Final"

# PROP BASE Use_MFC 0
# PROP BASE Use_Debug_Libraries 0
# PROP BASE Output_Dir "Final"
# PROP BASE Intermediate_Dir "Final"
# PROP BASE Target_Dir ""
# PROP Use_MFC 0
# PROP Use_Debug_Libraries 0
# PROP Output_Dir "..\..\..\built\Final\Lithtech"
# PROP Intermediate_Dir "..\..\..\built\Final\Lithtech"
# PROP Target_Dir ""
# ADD BASE CPP /nologo /W3 /GX /O2 /D "WIN32" /D "NDEBUG" /D "_WINDOWS" /D "_MBCS" /YX /FD /c
# ADD CPP /nologo /MD /W3 /GX /O2 /I "..\..\..\..\libs\STLPort-4.0\stlport" /I "..\..\client\src" /I "..\..\shared\src" /I "..\..\kernel\src" /I "..\..\kernel\mem\src" /I "..\..\world\src" /I "..\..\kernel\io\src" /I "..\..\kernel\net\src" /I "..\..\model\src" /I "..\..\sound\src" /I "..\..\shared\src\sys\win" /I "..\..\lithtemplate" /I "..\..\physics\src" /I "..\..\render_b\src" /I "..\..\ui\src" /I "..\..\controlfilemgr" /I "..\..\server\src" /I "..\..\kernel\src\sys\win" /I "..\..\kernel\io\src\sys\win" /I "..\..\kernel\mem\src\sys\win" /I "..\..\kernel\net\src\sys\win" /I "..\..\client\src\sys\win" /I "..\..\render_a\src\sys\d3d" /I "..\..\..\sdk\inc" /I "..\..\..\sdk\inc\physics" /I "..\..\..\..\libs\stdlith" /I "..\..\..\..\libs\lith" /I "..\..\..\libs\rezmgr" /D "WIN32" /D "NDEBUG" /D "_WINDOWS" /D "_MBCS" /D "_FINAL" /D "__D3D" /D "__D3DREND" /D "DE_CLIENT_COMPILE" /D "DE_LOCAL_SERVERBIND" /D "DIRECTENGINE_COMPILE" /D "DSNDMGR_NO_MFC" /D "MODEL_SUPPORT_ABC" /FD /c
# ADD BASE MTL /nologo /D "NDEBUG" /mktyplib203 /win32
# ADD MTL /nologo /D "NDEBUG" /mktyplib203 /win32
# ADD BASE RSC /l 0x409 /d "NDEBUG"
# ADD RSC /l 0x409 /d "NDEBUG"
BSC32=bscmake.exe
# ADD BASE BSC32 /nologo
# ADD BSC32 /nologo
LINK32=link.exe
# ADD BASE LINK32 kernel32.lib user32.lib /nologo /subsystem:windows /machine:I386
# ADD LINK32 d3dx8.lib kernel32.lib user32.lib gdi32.lib advapi32.lib ole32.lib winmm.lib wsock32.lib dinput8.lib dxguid.lib d3d8.lib /nologo /subsystem:windows /machine:I386 /out:"..\..\..\built\Final\Lithtech\Lithtech.exe"
!ENDIF 

# Begin Target

# Name "Lithtech - Win32 Final"
# Begin Group "Source Files"

# PROP Default_Filter "cpp;c;cxx;rc;def;r;odl;idl;hpj;bat"
# Begin Source File

SOURCE=..\..\controlfilemgr\controlfilemgr.cpp
# End Source File
# Begin Source File

SOURCE=..\..\model\src\animtracker.cpp
# End Source File
# Begin Source File

SOURCE=..\..\shared\src\bdefs.cpp
# End Source File
# Begin Source File

SOURCE=..\..\kernel\src\sys\win\bindmgr.cpp
# End Source File
# Begin Source File

SOURCE=..\..\kernel\src\sys\win\binkvideomgrimpl.cpp

!IF  "$(CFG)" == "Lithtech - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=..\..\shared\src\classbind.cpp
# End Source File
# Begin Source File

SOURCE=..\..\server\src\classmgr.cpp
# End Source File
# Begin Source File

SOURCE=..\..\kernel\src\sys\win\client.cpp
# End Source File
# Begin Source File

SOURCE=..\..\client\src\client_formatmgr.cpp
# End Source File
# Begin Source File

SOURCE=..\..\client\src\client_graphmgr.cpp
# End Source File
# Begin Source File

SOURCE=..\..\client\src\client_ticks.cpp
# End Source File
# Begin Source File

SOURCE=..\..\client\src\clientde_impl.cpp

!IF  "$(CFG)" == "Lithtech - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=..\..\client\src\clientmgr.cpp
# End Source File
# Begin Source File

SOURCE=..\..\client\src\clientshell.cpp
# End Source File
# Begin Source File

SOURCE=..\..\client\src\cmoveabstract.cpp
# End Source File
# Begin Source File

SOURCE=..\..\client\src\cnet.cpp
# End Source File
# Begin Source File

SOURCE=..\..\client\src\cobject.cpp
# End Source File
# Begin Source File

SOURCE=..\..\shared\src\collision.cpp
# End Source File
# Begin Source File

SOURCE=..\..\shared\src\compress.cpp
# End Source File
# Begin Source File

SOURCE=..\..\shared\src\concommand.cpp
# End Source File
# Begin Source File

SOURCE=..\..\shared\src\conparse.cpp
# End Source File
# Begin Source File

SOURCE=..\..\client\src\console.cpp
# End Source File
# Begin Source File

SOURCE=..\..\client\src\consolecommands.cpp
# End Source File
# Begin Source File

SOURCE=..\..\kernel\src\sys\win\counter.cpp
# End Source File
# Begin Source File

SOURCE=..\..\client\src\cutil.cpp
# End Source File
# Begin Source File

SOURCE=..\..\model\src\sys\d3d\d3d_model_load.cpp
# End Source File
# Begin Source File

SOURCE=..\..\render_b\src\sys\d3d\d3ddrawprim.cpp
# End Source File
# Begin Source File

SOURCE=..\..\render_b\src\sys\d3d\d3dtexinterface.cpp
# End Source File
# Begin Source File

SOURCE=..\..\kernel\io\src\sys\win\de_file.cpp
# End Source File
# Begin Source File

SOURCE=..\..\world\src\de_mainworld.cpp
# End Source File
# Begin Source File

SOURCE=..\..\kernel\mem\src\sys\win\de_memory.cpp
# End Source File
# Begin Source File

SOURCE=..\..\world\src\de_nodes.cpp
# End Source File
# Begin Source File

SOURCE=..\..\world\src\de_objects.cpp
# End Source File
# Begin Source File

SOURCE=..\..\shared\src\debuggeometry.cpp
# End Source File
# Begin Source File

SOURCE=..\..\kernel\src\debugging.cpp
# End Source File
# Begin Source File

SOURCE=..\..\client\src\debuggraphmgr.cpp
# End Source File
# Begin Source File

SOURCE=..\..\shared\src\dhashtable.cpp
# End Source File
# Begin Source File

SOURCE=..\..\shared\src\sys\win\dstreamopenqueuemgr.cpp
# End Source File
# Begin Source File

SOURCE=..\..\kernel\src\sys\win\dsys_interface.cpp
# End Source File
# Begin Source File

SOURCE=..\..\shared\src\dtxmgr.cpp
# End Source File
# Begin Source File

SOURCE=..\..\kernel\src\sys\win\dutil.cpp
# End Source File
# Begin Source File

SOURCE=..\..\shared\src\engine_vars.cpp
# End Source File
# Begin Source File

SOURCE=..\..\client\src\errorlog.cpp
# End Source File
# Begin Source File

SOURCE=..\..\shared\src\findobj.cpp
# End Source File
# Begin Source File

SOURCE=..\..\shared\src\ftclient.cpp
# End Source File
# Begin Source File

SOURCE=..\..\shared\src\ftserv.cpp
# End Source File
# Begin Source File

SOURCE=..\..\world\src\fullintersectline.cpp

!IF  "$(CFG)" == "Lithtech - Win32 Final"

# ADD CPP /Ob2
# SUBTRACT CPP /GX

!ENDIF 

# End Source File
# Begin Source File

SOURCE=..\..\server\src\game_serialize.cpp

!IF  "$(CFG)" == "Lithtech - Win32 Final"

# ADD CPP /Ob2
# SUBTRACT CPP /GX

!ENDIF 

# End Source File
# Begin Source File

SOURCE=..\..\shared\src\gamemath.cpp
# End Source File
# Begin Source File

SOURCE=..\..\shared\src\genericprop_setup.cpp
# End Source File
# Begin Source File

SOURCE=..\..\shared\src\genltstream.cpp
# End Source File
# Begin Source File

SOURCE=..\..\shared\src\geometry.cpp
# End Source File
# Begin Source File

SOURCE=..\..\shared\src\geomroutines.cpp
# End Source File
# Begin Source File

SOURCE=..\..\shared\src\impl_common.cpp
# End Source File
# Begin Source File

SOURCE=..\..\kernel\src\sys\win\input.cpp
# End Source File
# Begin Source File

SOURCE=..\..\kernel\src\sys\win\interface_helpers.cpp
# End Source File
# Begin Source File

SOURCE=..\..\shared\src\interface_linkage.cpp
# End Source File
# Begin Source File

SOURCE=..\..\server\src\interlink.cpp
# End Source File
# Begin Source File

SOURCE=..\..\world\src\intersect_line.cpp
# End Source File
# Begin Source File

SOURCE=..\..\world\src\intersectsweptsphere.cpp
# End Source File
# Begin Source File

SOURCE=..\..\shared\src\leech.cpp
# End Source File
# Begin Source File

SOURCE=..\..\world\src\light_table.cpp
# End Source File
# Begin Source File

SOURCE=..\..\shared\src\lightmap_compress.cpp
# End Source File
# Begin Source File

SOURCE=..\..\shared\src\lightmap_planes.cpp
# End Source File
# Begin Source File

SOURCE=..\..\client\src\linesystem.cpp
# End Source File
# Begin Source File

SOURCE=..\..\kernel\src\sys\win\load_pcx.cpp
# End Source File
# Begin Source File

SOURCE=..\..\kernel\net\src\localdriver.cpp
# End Source File
# Begin Source File

SOURCE=..\..\client\src\ltbenchmark_impl.cpp
# End Source File
# Begin Source File

SOURCE=..\..\kernel\src\sys\win\ltdirectmusic_impl.cpp
# End Source File
# Begin Source File

SOURCE=..\..\kernel\src\sys\win\ltdirectmusiccontrolfile.cpp
# End Source File
# Begin Source File

SOURCE=..\..\kernel\src\sys\win\ltdirectmusicloader.cpp
# End Source File
# Begin Source File

SOURCE=..\..\..\sdk\inc\lterror.cpp
# End Source File
# Begin Source File

SOURCE=..\..\kernel\src\sys\win\lthread.cpp
# End Source File
# Begin Source File

SOURCE=..\..\client\src\ltinfo_impl.cpp
# End Source File
# Begin Source File

SOURCE=..\..\kernel\src\sys\win\ltlibraryloader.cpp
# End Source File
# Begin Source File

SOURCE=..\..\kernel\mem\src\ltmemory.cpp
# End Source File
# Begin Source File

SOURCE=..\..\shared\src\ltmessage.cpp
# End Source File
# Begin Source File

SOURCE=..\..\client\src\ltmessage_client.cpp
# End Source File
# Begin Source File

SOURCE=..\..\server\src\ltmessage_server.cpp
# End Source File
# Begin Source File

SOURCE=..\..\..\sdk\inc\ltmodule.cpp
# End Source File
# Begin Source File

SOURCE=..\..\..\sdk\inc\ltobjref.cpp
# End Source File
# Begin Source File

SOURCE=..\..\..\sdk\inc\ltquatbase.cpp
# End Source File
# Begin Source File

SOURCE=..\..\kernel\src\sys\win\ltthread.cpp
# End Source File
# Begin Source File

SOURCE=..\..\shared\src\lttimer.cpp
# End Source File
# Begin Source File

SOURCE=..\..\model\src\model.cpp
# End Source File
# Begin Source File

SOURCE=..\..\model\src\model_load.cpp

!IF  "$(CFG)" == "Lithtech - Win32 Final"

# ADD CPP /Ob2
# SUBTRACT CPP /GX

!ENDIF 

# End Source File
# Begin Source File

SOURCE=..\..\model\src\modelallocations.cpp
# End Source File
# Begin Source File

SOURCE=..\..\shared\src\motion.cpp
# End Source File
# Begin Source File

SOURCE=..\..\shared\src\moveobject.cpp
# End Source File
# Begin Source File

SOURCE=..\..\shared\src\moveplayer.cpp
# End Source File
# Begin Source File

SOURCE=..\..\kernel\src\sys\win\musicdriver.cpp
# End Source File
# Begin Source File

SOURCE=..\..\kernel\net\src\netmgr.cpp
# End Source File
# Begin Source File

SOURCE=..\..\shared\src\nexus.cpp
# End Source File
# Begin Source File

SOURCE=..\..\shared\src\objectmgr.cpp
# End Source File
# Begin Source File

SOURCE=..\..\kernel\net\src\packet.cpp
# End Source File
# Begin Source File

SOURCE=..\..\shared\src\parse_world_info.cpp
# End Source File
# Begin Source File

SOURCE=..\..\client\src\particlesystem.cpp
# End Source File
# Begin Source File

SOURCE=..\..\shared\src\pixelformat.cpp
# End Source File
# Begin Source File

SOURCE=..\..\client\src\polygrid.cpp
# End Source File
# Begin Source File

SOURCE=..\..\client\src\predict.cpp
# End Source File
# Begin Source File

SOURCE=..\..\shared\src\ratetracker.cpp
# End Source File
# Begin Source File

SOURCE=..\..\kernel\src\sys\win\render.cpp
# End Source File
# Begin Source File

SOURCE=..\..\server\src\s_client.cpp
# End Source File
# Begin Source File

SOURCE=..\..\server\src\s_concommand.cpp
# End Source File
# Begin Source File

SOURCE=..\..\server\src\s_intersect.cpp
# End Source File
# Begin Source File

SOURCE=..\..\server\src\s_net.cpp

!IF  "$(CFG)" == "Lithtech - Win32 Final"

# ADD CPP /Ob2
# SUBTRACT CPP /GX

!ENDIF 

# End Source File
# Begin Source File

SOURCE=..\..\server\src\s_object.cpp
# End Source File
# Begin Source File

SOURCE=..\..\server\src\server_consolestate.cpp
# End Source File
# Begin Source File

SOURCE=..\..\server\src\server_extradata.cpp
# End Source File
# Begin Source File

SOURCE=..\..\server\src\server_filemgr.cpp
# End Source File
# Begin Source File

SOURCE=..\..\server\src\serverde_impl.cpp
# End Source File
# Begin Source File

SOURCE=..\..\server\src\serverevent.cpp
# End Source File
# Begin Source File

SOURCE=..\..\server\src\servermgr.cpp
# End Source File
# Begin Source File

SOURCE=..\..\client\src\setupobject.cpp
# End Source File
# Begin Source File

SOURCE=..\..\client\src\shellnet.cpp
# End Source File
# Begin Source File

SOURCE=..\..\client\src\shelltransfer.cpp
# End Source File
# Begin Source File

SOURCE=..\..\client\src\shellutil.cpp
# End Source File
# Begin Source File

SOURCE=..\..\server\src\smoveabstract.cpp
# End Source File
# Begin Source File

SOURCE=..\..\sound\src\soundbuffer.cpp
# End Source File
# Begin Source File

SOURCE=..\..\sound\src\sounddata.cpp
# End Source File
# Begin Source File

SOURCE=..\..\sound\src\soundinstance.cpp
# End Source File
# Begin Source File

SOURCE=..\..\server\src\soundtrack.cpp
# End Source File
# Begin Source File

SOURCE=..\..\client\src\sprite.cpp
# End Source File
# Begin Source File

SOURCE=..\..\shared\src\spritecontrolimpl.cpp
# End Source File
# Begin Source File

SOURCE=..\..\shared\src\stacktrace.cpp
# End Source File
# Begin Source File

SOURCE=..\..\shared\src\stdlterror.cpp
# End Source File
# Begin Source File

SOURCE=..\..\kernel\src\sys\win\streamsim.cpp
# End Source File
# Begin Source File

SOURCE=..\..\kernel\src\sys\win\stringmgr.cpp
# End Source File
# Begin Source File

SOURCE=..\..\shared\src\strtools.cpp
# End Source File
# Begin Source File

SOURCE=..\..\kernel\src\sys\win\text_mgr.cpp
# End Source File
# Begin Source File

SOURCE=..\..\kernel\src\sys\win\timemgr.cpp
# End Source File
# Begin Source File

SOURCE=..\..\model\src\transformmaker.cpp
# End Source File
# Begin Source File

SOURCE=..\..\kernel\net\src\sys\win\udpdriver.cpp
# End Source File
# Begin Source File

SOURCE=..\..\shared\src\version_info.cpp
# End Source File
# Begin Source File

SOURCE=..\..\kernel\src\sys\win\version_resource.cpp
# End Source File
# Begin Source File

SOURCE=..\..\kernel\src\sys\win\videomgr.cpp
# End Source File
# Begin Source File

SOURCE=..\..\client\src\volumeeffect.cpp
# End Source File
# Begin Source File

SOURCE=..\..\sound\src\wave.cpp
# End Source File
# Begin Source File

SOURCE=..\..\client\src\sys\win\winclientde_impl.cpp

!IF  "$(CFG)" == "Lithtech - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=..\..\client\src\sys\win\winconsole_impl.cpp

!IF  "$(CFG)" == "Lithtech - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=..\..\world\src\world_blind_object_data.cpp
# End Source File
# Begin Source File

SOURCE=..\..\world\src\world_blocker_data.cpp
# End Source File
# Begin Source File

SOURCE=..\..\world\src\world_blocker_math.cpp
# End Source File
# Begin Source File

SOURCE=..\..\client\src\world_client_bsp.cpp
# End Source File
# Begin Source File

SOURCE=..\..\world\src\world_particle_blocker_data.cpp
# End Source File
# Begin Source File

SOURCE=..\..\server\src\world_server_bsp.cpp
# End Source File
# Begin Source File

SOURCE=..\..\world\src\world_shared_bsp.cpp
# End Source File
# Begin Source File

SOURCE=..\..\world\src\world_tree.cpp
# End Source File
# Begin Source File

SOURCE=..\..\kernel\src\icommandlineargs.cpp
# End Source File
# Begin Source File

SOURCE=..\..\client\src\client_filemgr.cpp
# End Source File
# Begin Source File

SOURCE=..\..\client\src\client_iltmodel.cpp
# End Source File
# Begin Source File

SOURCE=..\..\shared\src\modellt_impl.cpp
# End Source File
# Begin Source File

SOURCE=..\..\server\src\server_iltmodel.cpp
# End Source File
# Begin Source File

SOURCE=..\..\client\src\client_iltcommon.cpp
# End Source File
# Begin Source File

SOURCE=..\..\server\src\server_iltcommon.cpp
# End Source File
# Begin Source File

SOURCE=..\..\shared\src\shared_iltcommon.cpp
# End Source File
# Begin Source File

SOURCE=..\..\kernel\src\sys\win\lt_cursor_impl.cpp
# End Source File
# Begin Source File

SOURCE=..\..\client\src\client_iltphysics.cpp
# End Source File
# Begin Source File

SOURCE=..\..\server\src\server_iltphysics.cpp
# End Source File
# Begin Source File

SOURCE=..\..\shared\src\shared_iltphysics.cpp
# End Source File
# Begin Source File

SOURCE=..\..\shared\src\transformlt_impl.cpp
# End Source File
# Begin Source File

SOURCE=..\..\server\src\server_iltsoundmgr.cpp
# End Source File
# Begin Source File

SOURCE=..\..\sound\src\soundmgr.cpp
# End Source File
# Begin Source File

SOURCE=..\..\client\src\client_iltvideomgr.cpp
# End Source File
# Begin Source File

SOURCE=..\..\client\src\nolf2src_client_stubs.cpp
# End Source File
# Begin Source File

SOURCE=.\lithtech.rc
# End Source File
# End Group
# End Target
# End Project
