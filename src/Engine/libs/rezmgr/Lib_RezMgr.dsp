# Microsoft Developer Studio Project File - Name="Lib_RezMgr" - Package Owner=<4>
# Microsoft Developer Studio Generated Build File, Format Version 6.00
# ** DO NOT EDIT **

# TARGTYPE "Win32 (x86) Static Library" 0x0104

CFG=Lib_RezMgr - Win32 Final
!MESSAGE This is not a valid makefile. To build this project using NMAKE,
!MESSAGE use the Export Makefile command and run
!MESSAGE 
!MESSAGE NMAKE /f "Lib_RezMgr.mak".
!MESSAGE 
!MESSAGE You can specify a configuration when running NMAKE
!MESSAGE by defining the macro CFG on the command line. For example:
!MESSAGE 
!MESSAGE NMAKE /f "Lib_RezMgr.mak" CFG="Lib_RezMgr - Win32 Final"
!MESSAGE 
!MESSAGE Possible choices for configuration are:
!MESSAGE 
!MESSAGE "Lib_RezMgr - Win32 Final" (based on "Win32 (x86) Static Library")
!MESSAGE 

# nolf2src: RezMgr, the .rez archive library, a static library of
# Lithtech.exe and server.dll (Engine.dsw), from the LithTech Jupiter tree
# (Monolith's Source/Engine/libs/rezmgr).
# Begin Project
# PROP AllowPerConfigDependencies 0
# PROP Scc_ProjName ""
# PROP Scc_LocalPath ""
CPP=cl.exe
RSC=rc.exe

!IF  "$(CFG)" == "Lib_RezMgr - Win32 Final"

# PROP BASE Use_MFC 0
# PROP BASE Use_Debug_Libraries 0
# PROP BASE Output_Dir "Final"
# PROP BASE Intermediate_Dir "Final"
# PROP BASE Target_Dir ""
# PROP Use_MFC 0
# PROP Use_Debug_Libraries 0
# PROP Output_Dir "..\..\built\Final\Lib_RezMgr"
# PROP Intermediate_Dir "..\..\built\Final\Lib_RezMgr"
# PROP Target_Dir ""
# ADD BASE CPP /nologo /W3 /GX /O2 /D "WIN32" /D "NDEBUG" /D "_WINDOWS" /D "_MBCS" /YX /FD /c
# ADD CPP /nologo /MD /W3 /GX /O2 /I "..\..\..\libs\STLPort-4.0\stlport" /I "." /I "..\..\..\libs\lith" /I "..\..\sdk\inc" /I "..\..\sdk\inc\physics" /D "WIN32" /D "NDEBUG" /D "_WINDOWS" /D "_MBCS" /D "_FINAL" /D "__D3D" /D "__D3DREND" /D "_LIB" /FD /c
BSC32=bscmake.exe
# ADD BASE BSC32 /nologo
# ADD BSC32 /nologo
LIB32=link.exe -lib
# ADD BASE LIB32 /nologo
# ADD LIB32 /nologo /out:"..\..\built\Final\Lib_RezMgr\Lib_RezMgr.lib"
!ENDIF 

# Begin Target

# Name "Lib_RezMgr - Win32 Final"
# Begin Group "Source Files"

# PROP Default_Filter "cpp;c;cxx;rc;def;r;odl;idl;hpj;bat"
# Begin Source File

SOURCE=.\rezfile.cpp
# End Source File
# Begin Source File

SOURCE=.\rezhash.cpp
# End Source File
# Begin Source File

SOURCE=.\rezmgr.cpp
# End Source File
# Begin Source File

SOURCE=.\rezutils.cpp
# End Source File
# End Group
# End Target
# End Project
