# Microsoft Developer Studio Project File - Name="Lib_UI" - Package Owner=<4>
# Microsoft Developer Studio Generated Build File, Format Version 6.00
# ** DO NOT EDIT **

# TARGTYPE "Win32 (x86) Static Library" 0x0104

CFG=Lib_UI - Win32 Final
!MESSAGE This is not a valid makefile. To build this project using NMAKE,
!MESSAGE use the Export Makefile command and run
!MESSAGE 
!MESSAGE NMAKE /f "Lib_UI.mak".
!MESSAGE 
!MESSAGE You can specify a configuration when running NMAKE
!MESSAGE by defining the macro CFG on the command line. For example:
!MESSAGE 
!MESSAGE NMAKE /f "Lib_UI.mak" CFG="Lib_UI - Win32 Final"
!MESSAGE 
!MESSAGE Possible choices for configuration are:
!MESSAGE 
!MESSAGE "Lib_UI - Win32 Final" (based on "Win32 (x86) Static Library")
!MESSAGE 

# nolf2src: the UI library (Lib_UI: the CUI widgets, the bitmap and GDI
# vector fonts), a static library of Lithtech.exe (Engine.dsw).
# Begin Project
# PROP AllowPerConfigDependencies 0
# PROP Scc_ProjName ""
# PROP Scc_LocalPath ""
CPP=cl.exe
RSC=rc.exe

!IF  "$(CFG)" == "Lib_UI - Win32 Final"

# PROP BASE Use_MFC 0
# PROP BASE Use_Debug_Libraries 0
# PROP BASE Output_Dir "Final"
# PROP BASE Intermediate_Dir "Final"
# PROP BASE Target_Dir ""
# PROP Use_MFC 0
# PROP Use_Debug_Libraries 0
# PROP Output_Dir "..\..\built\Final\Lib_UI"
# PROP Intermediate_Dir "..\..\built\Final\Lib_UI"
# PROP Target_Dir ""
# ADD BASE CPP /nologo /W3 /GX /O2 /D "WIN32" /D "NDEBUG" /D "_WINDOWS" /D "_MBCS" /YX /FD /c
# ADD CPP /nologo /MD /W3 /GX /O2 /I "..\..\..\libs\STLPort-4.0\stlport" /I "src" /I "..\client\src" /I "..\shared\src" /I "..\kernel\src" /I "..\kernel\mem\src" /I "..\world\src" /I "..\kernel\io\src" /I "..\kernel\net\src" /I "..\model\src" /I "..\sound\src" /I "..\shared\src\sys\win" /I "..\lithtemplate" /I "..\physics\src" /I "..\render_b\src" /I "src" /I "..\controlfilemgr" /I "..\server\src" /I "..\kernel\src\sys\win" /I "..\kernel\io\src\sys\win" /I "..\kernel\mem\src\sys\win" /I "..\kernel\net\src\sys\win" /I "..\client\src\sys\win" /I "..\render_a\src\sys\d3d" /I "..\..\sdk\inc" /I "..\..\sdk\inc\physics" /I "..\..\..\libs\stdlith" /I "..\..\..\libs\lith" /I "..\..\libs\rezmgr" /D "WIN32" /D "NDEBUG" /D "_WINDOWS" /D "_MBCS" /D "_FINAL" /D "__D3D" /D "__D3DREND" /D "_LIB" /FD /c
BSC32=bscmake.exe
# ADD BASE BSC32 /nologo
# ADD BSC32 /nologo
LIB32=link.exe -lib
# ADD BASE LIB32 /nologo
# ADD LIB32 /nologo /out:"..\..\built\Final\Lib_UI\Lib_UI.lib"
!ENDIF 

# Begin Target

# Name "Lib_UI - Win32 Final"
# Begin Group "Source Files"

# PROP Default_Filter "cpp;c;cxx;rc;def;r;odl;idl;hpj;bat"
# Begin Source File

SOURCE=.\src\cuifontmanager.cpp

!IF  "$(CFG)" == "Lib_UI - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\src\cuiwidgetmanager.cpp
# End Source File
# Begin Source File

SOURCE=.\src\cuimessagequeue.cpp
# End Source File
# Begin Source File

SOURCE=.\src\cuibitmapfont.cpp

!IF  "$(CFG)" == "Lib_UI - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\src\cuivectorfont.cpp

!IF  "$(CFG)" == "Lib_UI - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\src\cuipolystring.cpp
# End Source File
# Begin Source File

SOURCE=.\src\cuidropdownlist.cpp
# End Source File
# Begin Source File

SOURCE=.\src\cuilist.cpp
# End Source File
# Begin Source File

SOURCE=.\src\cuioption.cpp
# End Source File
# Begin Source File

SOURCE=.\src\cuicheck.cpp
# End Source File
# Begin Source File

SOURCE=.\src\cuiprogress.cpp
# End Source File
# Begin Source File

SOURCE=.\src\cuislider.cpp
# End Source File
# Begin Source File

SOURCE=.\src\cuibutton.cpp
# End Source File
# Begin Source File

SOURCE=.\src\cuistaticimage.cpp
# End Source File
# Begin Source File

SOURCE=.\src\cuistatictext.cpp
# End Source File
# Begin Source File

SOURCE=.\src\cuiwindow.cpp
# End Source File
# Begin Source File

SOURCE=.\src\cuiwidget.cpp
# End Source File
# Begin Source File

SOURCE=.\src\cuibase.cpp
# End Source File
# Begin Source File

SOURCE=.\src\cuibase_impl.cpp
# End Source File
# Begin Source File

SOURCE=.\src\cuibutton_impl.cpp
# End Source File
# Begin Source File

SOURCE=.\src\cuicheck_impl.cpp
# End Source File
# Begin Source File

SOURCE=.\src\cuidropdownlist_impl.cpp
# End Source File
# Begin Source File

SOURCE=.\src\cuifont_impl.cpp

!IF  "$(CFG)" == "Lib_UI - Win32 Final"

# PROP Exclude_From_Build 1

!ENDIF 

# End Source File
# Begin Source File

SOURCE=.\src\cuiformattedpolystring.cpp
# End Source File
# Begin Source File

SOURCE=.\src\cuiformattedpolystring_impl.cpp
# End Source File
# Begin Source File

SOURCE=.\src\cuiinterval.cpp
# End Source File
# Begin Source File

SOURCE=.\src\cuiinterval_impl.cpp
# End Source File
# Begin Source File

SOURCE=.\src\cuilinklist.cpp
# End Source File
# Begin Source File

SOURCE=.\src\cuilist_impl.cpp
# End Source File
# Begin Source File

SOURCE=.\src\cuioption_impl.cpp
# End Source File
# Begin Source File

SOURCE=.\src\cuipolystring_impl.cpp
# End Source File
# Begin Source File

SOURCE=.\src\cuipolytex.cpp
# End Source File
# Begin Source File

SOURCE=.\src\cuiprogress_impl.cpp
# End Source File
# Begin Source File

SOURCE=.\src\cuiredblack.cpp
# End Source File
# Begin Source File

SOURCE=.\src\cuirenderstate.cpp
# End Source File
# Begin Source File

SOURCE=.\src\cuislider_impl.cpp
# End Source File
# Begin Source File

SOURCE=.\src\cuistaticimage_impl.cpp
# End Source File
# Begin Source File

SOURCE=.\src\cuistatictext_impl.cpp
# End Source File
# Begin Source File

SOURCE=.\src\cuiwidget_impl.cpp
# End Source File
# Begin Source File

SOURCE=.\src\cuiwindow_impl.cpp
# End Source File
# Begin Source File

SOURCE=.\src\nolf2src_ui_stubs.cpp
# End Source File
# End Group
# End Target
# End Project
