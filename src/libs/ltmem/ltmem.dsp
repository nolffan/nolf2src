# Microsoft Developer Studio Project File - Name="ltmem" - Package Owner=<4>
# Microsoft Developer Studio Generated Build File, Format Version 6.00
# ** DO NOT EDIT **

# TARGTYPE "Win32 (x86) Static Library" 0x0104

CFG=ltmem - Win32 Final
!MESSAGE This is not a valid makefile. To build this project using NMAKE,
!MESSAGE use the Export Makefile command and run
!MESSAGE 
!MESSAGE NMAKE /f "ltmem.mak".
!MESSAGE 
!MESSAGE You can specify a configuration when running NMAKE
!MESSAGE by defining the macro CFG on the command line. For example:
!MESSAGE 
!MESSAGE NMAKE /f "ltmem.mak" CFG="ltmem - Win32 Final"
!MESSAGE 
!MESSAGE Possible choices for configuration are:
!MESSAGE 
!MESSAGE "ltmem - Win32 Final" (based on "Win32 (x86) Static Library")
!MESSAGE 

# nolf2src: ltmem.lib, the LithTech memory library the engine's modules and
# Monolith's game DLLs link (TO2.dsw names it as a dependency; the source
# release does not have it). Written for this project from what the sound
# driver links of it (ltmem.cpp) and what the engine adds (ltmemstats.cpp,
# the "mem" console command) and links of the heap (ltmemheap.cpp, the fear
# tree's, its globals only: nothing calls it). A static library project's flags (the C
# runtime not imported: its calls go through import thunks, in the sound
# driver and in Lithtech.exe alike), with /Ob2 as the driver's own.
# Begin Project
# PROP AllowPerConfigDependencies 0
# PROP Scc_ProjName ""
# PROP Scc_LocalPath ""
CPP=cl.exe
RSC=rc.exe

!IF  "$(CFG)" == "ltmem - Win32 Final"

# PROP BASE Use_MFC 0
# PROP BASE Use_Debug_Libraries 0
# PROP BASE Output_Dir "Final"
# PROP BASE Intermediate_Dir "Final"
# PROP BASE Target_Dir ""
# PROP Use_MFC 0
# PROP Use_Debug_Libraries 0
# PROP Output_Dir "..\..\Engine\built\Final\ltmem"
# PROP Intermediate_Dir "..\..\Engine\built\Final\ltmem"
# PROP Target_Dir ""
# ADD BASE CPP /nologo /W3 /GX /O2 /D "WIN32" /D "NDEBUG" /D "_MBCS" /D "_LIB" /YX /FD /c
# ADD CPP /nologo /W3 /GX /O2 /Ob2 /I "..\..\Engine\sdk\inc" /D "WIN32" /D "NDEBUG" /D "_MBCS" /D "_LIB" /FD /c
BSC32=bscmake.exe
# ADD BASE BSC32 /nologo
# ADD BSC32 /nologo
LIB32=link.exe -lib
# ADD BASE LIB32 /nologo
# ADD LIB32 /nologo /out:"..\..\Engine\built\Final\ltmem\ltmem.lib"
!ENDIF 

# Begin Target

# Name "ltmem - Win32 Final"
# Begin Group "Source Files"

# PROP Default_Filter "cpp;c;cxx;rc;def;r;odl;idl;hpj;bat"
# Begin Source File

SOURCE=.\ltmem.cpp
# End Source File
# Begin Source File

SOURCE=.\ltmemstats.cpp
# End Source File
# Begin Source File

SOURCE=.\ltmemheap.cpp
# End Source File
# End Group
# End Target
# End Project
