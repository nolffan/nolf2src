# Microsoft Developer Studio Project File - Name="snddrv" - Package Owner=<4>
# Microsoft Developer Studio Generated Build File, Format Version 6.00
# ** DO NOT EDIT **

# TARGTYPE "Win32 (x86) Dynamic-Link Library" 0x0102

CFG=snddrv - Win32 Final
!MESSAGE This is not a valid makefile. To build this project using NMAKE,
!MESSAGE use the Export Makefile command and run
!MESSAGE 
!MESSAGE NMAKE /f "snddrv.mak".
!MESSAGE 
!MESSAGE You can specify a configuration when running NMAKE
!MESSAGE by defining the macro CFG on the command line. For example:
!MESSAGE 
!MESSAGE NMAKE /f "snddrv.mak" CFG="snddrv - Win32 Final"
!MESSAGE 
!MESSAGE Possible choices for configuration are:
!MESSAGE 
!MESSAGE "snddrv - Win32 Final" (based on "Win32 (x86) Dynamic-Link Library")
!MESSAGE 

# nolf2src: SndDrv.dll, the engine's sound driver (DirectSound 8), which the
# engine loads and asks for its ILTSoundSys through the exports SoundSysMake
# and SoundSysDesc. Monolith's release has none of its source: written for
# this project, reconstructed from the retail 1.3 binary (snddrv.dsw). The
# flags are the ones the retail code shows: /O2 with /Ob2 (initializers
# expanded in place, no jump thunks; functions laid out as auto-inlining
# defers them), /GX (the C++ exception frames of the constructors and
# destructors), no precompiled header (every object carries its own copy of
# the math constants' initializers). /YX (Developer Studio's default
# automatic precompiled header) is what puts each object's header
# initializers after its functions, as retail has them.
# Begin Project
# PROP AllowPerConfigDependencies 0
# PROP Scc_ProjName ""
# PROP Scc_LocalPath ""
CPP=cl.exe
MTL=midl.exe
RSC=rc.exe

!IF  "$(CFG)" == "snddrv - Win32 Final"

# PROP BASE Use_MFC 0
# PROP BASE Use_Debug_Libraries 0
# PROP BASE Output_Dir "Final"
# PROP BASE Intermediate_Dir "Final"
# PROP BASE Target_Dir ""
# PROP Use_MFC 0
# PROP Use_Debug_Libraries 0
# PROP Output_Dir "..\built\Final\snddrv"
# PROP Intermediate_Dir "..\built\Final\snddrv"
# PROP Ignore_Export_Lib 0
# PROP Target_Dir ""
# ADD BASE CPP /nologo /MD /W3 /GX /O2 /D "WIN32" /D "NDEBUG" /D "_WINDOWS" /D "_MBCS" /D "_USRDLL" /D "_FINAL" /YX /FD /c
# ADD CPP /nologo /MD /W3 /GX /O2 /Ob2 /I "." /I "..\..\libs\STLPORT-4.0\STLPORT" /I "..\sdk\inc" /D "WIN32" /D "NDEBUG" /D "_WINDOWS" /D "_MBCS" /D "_USRDLL" /D "_FINAL" /YX /FD /c
# ADD BASE MTL /nologo /D "NDEBUG" /mktyplib203 /win32
# ADD MTL /nologo /D "NDEBUG" /mktyplib203 /win32
# ADD BASE RSC /l 0x409 /d "NDEBUG"
# ADD RSC /l 0x409 /d "NDEBUG"
BSC32=bscmake.exe
# ADD BASE BSC32 /nologo
# ADD BSC32 /nologo
LINK32=link.exe
# ADD BASE LINK32 kernel32.lib user32.lib /nologo /subsystem:windows /dll /machine:I386
# ADD LINK32 kernel32.lib user32.lib ole32.lib winmm.lib msacm32.lib dxguid.lib /nologo /subsystem:windows /dll /machine:I386 /out:"..\built\Final\snddrv\SndDrv.dll"
!ENDIF 

# Begin Target

# Name "snddrv - Win32 Final"
# Begin Group "Source Files"

# PROP Default_Filter "cpp;c;cxx;rc;def;r;odl;idl;hpj;bat"
# Begin Source File

SOURCE=.\counter.cpp
# End Source File
# Begin Source File

SOURCE=.\parsewavefile.cpp
# End Source File
# Begin Source File

SOURCE=.\s_dx8.cpp
# End Source File
# Begin Source File

SOURCE=.\stdafx.cpp
# End Source File
# End Group
# Begin Group "Header Files"

# PROP Default_Filter "h;hpp;hxx;hm;inl"
# Begin Source File

SOURCE=.\counter.h
# End Source File
# Begin Source File

SOURCE=.\eax.h
# End Source File
# Begin Source File

SOURCE=.\iltsound.h
# End Source File
# Begin Source File

SOURCE=.\s_dx8.h
# End Source File
# Begin Source File

SOURCE=.\stdafx.h
# End Source File
# Begin Source File

SOURCE=.\winsync.h
# End Source File
# End Group
# End Target
# End Project
