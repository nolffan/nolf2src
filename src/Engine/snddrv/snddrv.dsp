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
# destructors). The objects are what a clean build with Developer Studio's
# automatic precompiled header (/YX) makes, which decides where each
# object's header initializers go: parsewavefile.cpp, compiled first, makes
# the header (stdafx.h, s_dx8.h) and gets its initializers after its code;
# s_dx8.cpp cannot use that one and makes its own, which puts its
# initializers among the EAX functions; counter.cpp and stdafx.cpp use none
# (counter.obj has its initializers first, in source order). /YX depends on
# what the previous compile left, so each of the two is spelled here as the
# /Yc it amounts to, with a header of its own: the same objects, from any
# starting state.

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
# ADD BASE CPP /nologo /MD /W3 /GX /O2 /D "WIN32" /D "NDEBUG" /D "_WINDOWS" /D "_MBCS" /D "_USRDLL" /D "_FINAL" /FD /c
# ADD CPP /nologo /MD /W3 /GX /O2 /Ob2 /I "." /I "..\..\libs\STLPORT-4.0\STLPORT" /I "..\sdk\inc" /D "WIN32" /D "NDEBUG" /D "_WINDOWS" /D "_MBCS" /D "_USRDLL" /D "_FINAL" /FD /c
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
# ADD CPP /Yc"s_dx8.h" /Fp"..\built\Final\snddrv\parsewavefile.pch"
# End Source File
# Begin Source File

SOURCE=.\s_dx8.cpp
# ADD CPP /Yc"counter.h" /Fp"..\built\Final\snddrv\s_dx8.pch"
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
