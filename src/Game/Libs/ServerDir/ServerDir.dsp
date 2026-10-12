# Microsoft Developer Studio Project File - Name="ServerDir" - Package Owner=<4>
# Microsoft Developer Studio Generated Build File, Format Version 6.00
# ** DO NOT EDIT **

# TARGTYPE "Win32 (x86) Dynamic-Link Library" 0x0102

CFG=ServerDir - Win32 Final
!MESSAGE This is not a valid makefile. To build this project using NMAKE,
!MESSAGE use the Export Makefile command and run
!MESSAGE 
!MESSAGE NMAKE /f "ServerDir.mak".
!MESSAGE 
!MESSAGE You can specify a configuration when running NMAKE
!MESSAGE by defining the macro CFG on the command line. For example:
!MESSAGE 
!MESSAGE NMAKE /f "ServerDir.mak" CFG="ServerDir - Win32 Final"
!MESSAGE 
!MESSAGE Possible choices for configuration are:
!MESSAGE 
!MESSAGE "ServerDir - Win32 Final" (based on "Win32 (x86) Dynamic-Link Library")
!MESSAGE 

# nolf2src: ServerDir.dll, which Monolith's release has only the headers
# and import library of (final/serverdir.lib). Written for this project:
# the Jupiter SDK's ServerDir.dsp (a static library) as a DLL --
# CServerDir_Titan and stdafx with that project's Release flags, plus _FINAL
# (no TitanTest) and SERVERDIR_EXPORTS (IServerDir.h), linked with the SDK's
# WONAPI (its own WONAPI.dsp, Release; ServerDir.dsw) into the DLL whose
# exports are retail's. tools/jupitersrc.py puts the SDK's files here.

# Begin Project
# PROP AllowPerConfigDependencies 0
# PROP Scc_ProjName ""
# PROP Scc_LocalPath ""
CPP=cl.exe
MTL=midl.exe
RSC=rc.exe

!IF  "$(CFG)" == "ServerDir - Win32 Final"

# PROP BASE Use_MFC 0
# PROP BASE Use_Debug_Libraries 0
# PROP BASE Output_Dir "Final"
# PROP BASE Intermediate_Dir "Final"
# PROP BASE Target_Dir ""
# PROP Use_MFC 0
# PROP Use_Debug_Libraries 0
# PROP Output_Dir "..\..\built\Final\libs\ServerDir"
# PROP Intermediate_Dir "..\..\built\Final\libs\ServerDir"
# PROP Ignore_Export_Lib 0
# PROP Target_Dir ""
# ADD BASE CPP /nologo /MD /W3 /GX /O2 /D "WIN32" /D "NDEBUG" /D "_WINDOWS" /YX /FD /c
# ADD CPP /nologo /MD /W3 /GX /O2 /I ".\\" /I "..\..\..\Engine\sdk\inc" /I "..\..\..\libs\STLPORT-4.0\STLPORT" /I "..\..\libs\wonapi" /D "WIN32" /D "NDEBUG" /D "_WINDOWS" /D "_FINAL" /D "SERVERDIR_EXPORTS" /YX /FD /c
# ADD BASE MTL /nologo /D "NDEBUG" /mktyplib203 /win32
# ADD MTL /nologo /D "NDEBUG" /mktyplib203 /win32
# ADD BASE RSC /l 0x409 /d "NDEBUG"
# ADD RSC /l 0x409 /d "NDEBUG"
BSC32=bscmake.exe
# ADD BASE BSC32 /nologo
# ADD BSC32 /nologo
LINK32=link.exe
# ADD BASE LINK32 kernel32.lib user32.lib advapi32.lib /nologo /subsystem:windows /dll /machine:I386
# ADD LINK32 kernel32.lib user32.lib advapi32.lib wsock32.lib /nologo /subsystem:windows /dll /machine:I386 /out:"..\..\built\Final\libs\ServerDir\ServerDir.dll"

!ENDIF 

# Begin Target

# Name "ServerDir - Win32 Final"
# Begin Group "Source Files"

# PROP Default_Filter "cpp;c;cxx;rc;def;r;odl;idl;hpj;bat"
# Begin Source File

SOURCE=.\CServerDir_Titan.cpp
# End Source File
# Begin Source File

SOURCE=.\stdafx.cpp
# End Source File
# End Group
# Begin Group "Header Files"

# PROP Default_Filter "h;hpp;hxx;hm;inl"
# Begin Source File

SOURCE=.\CServerDir_Titan.h
# End Source File
# Begin Source File

SOURCE=.\IServerDir.h
# End Source File
# Begin Source File

SOURCE=.\IServerDir_Titan.h
# End Source File
# Begin Source File

SOURCE=.\stdafx.h
# End Source File
# Begin Source File

SOURCE=.\WinSync.h
# End Source File
# End Group
# End Target
# End Project
