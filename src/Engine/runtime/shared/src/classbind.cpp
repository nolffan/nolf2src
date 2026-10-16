#include "bdefs.h"

#include "classbind.h"
#include "bindmgr.h"
#include "iservershell.h"
#include "ltproperty.h"

//------------------------------------------------------------------
//------------------------------------------------------------------
// Holders and their headers.
//------------------------------------------------------------------
//------------------------------------------------------------------

//the ILTServer game interface
#include "iltserver.h"
static ILTServer *ilt_server;
define_holder(ILTServer, ilt_server);





typedef ClassDef** (*ObjectDLLSetupFn)(int *nDefs, void *pServer, int *version);


#ifdef NOLF2SRC_MODERN
// MODERN.md M-E50: retail rewrote a property type outside PT_STRING..
// PT_ROTATION to NUM_PROPERTYTYPES (8), which is out of range too, and
// accepted the DLL. Now such a DLL is refused (as nolfsrc does): false.
static bool cb_VerifyClassDefProperties(ClassBindModule *pModule)
{
    int i, j;
    PropDef *pProp;

    for (i=0; i < pModule->m_nClassDefs; i++)
    {
        for (j=0; j < pModule->m_pClassDefs[i]->m_nProps; j++)
        {
            pProp = &pModule->m_pClassDefs[i]->m_Props[j];

            if (pProp->m_PropType >= NUM_PROPERTYTYPES || pProp->m_PropType < 0)
                return false;
        }
    }
    return true;
}
#else
static void cb_VerifyClassDefProperties(ClassBindModule *pModule)
{
    int i, j;
    PropDef *pProp;

    for (i=0; i < pModule->m_nClassDefs; i++)
    {
        for (j=0; j < pModule->m_pClassDefs[i]->m_nProps; j++)
        {
            pProp = &pModule->m_pClassDefs[i]->m_Props[j];

            if (pProp->m_PropType >= NUM_PROPERTYTYPES || pProp->m_PropType < 0)
                pProp->m_PropType = NUM_PROPERTYTYPES;
        }
    }
}
#endif

#ifdef __XBOX
extern ClassDef** ObjectDLLSetup(int *nDefs, ILTServer *pServer, int *version);
#endif

// [dlj] Linux doesn't need this because we use dynamic linking 
//#ifndef _WIN32
//extern ClassDef** ObjectDLLSetup(int *nDefs, ILTServer *pServer, int *version);
//#endif // !_WIN32

int cb_LoadModule(const char *pModuleName, bool bTempFile, ClassBindModule& classBindModule, int *version)

{
    CBindModuleType *hModule;
    ObjectDLLSetupFn theFunction;
    int status;

    status = bm_BindModule(pModuleName, bTempFile, hModule);
    if (status == BIND_CANTFINDMODULE)
        return CB_CANTFINDMODULE;

    // Get the function.
    theFunction = (ObjectDLLSetupFn)bm_GetFunctionPointer(hModule, "ObjectDLLSetup");
    if (!theFunction)
    {
        bm_UnbindModule(hModule);
        return CB_NOTCLASSMODULE;
    }

    // Ok.. setup the classbindmodule.
    classBindModule.m_hModule = hModule;
    classBindModule.m_pClassDefs = theFunction(&classBindModule.m_nClassDefs, ilt_server, version);

#ifdef NOLF2SRC_MODERN
    // MODERN.md M-E49: retail unbound the module but left it in
    // classBindModule, and CClassMgr::Term unbound it again (a second
    // FreeLibrary, a second delete).
    if (*version != SERVEROBJ_VERSION)
    {
        bm_UnbindModule(hModule);
        classBindModule.m_hModule = NULL;
        classBindModule.m_pClassDefs = NULL;
        classBindModule.m_nClassDefs = 0;
        return CB_VERSIONMISMATCH;
    }

    // Verify all properties!
    if (!cb_VerifyClassDefProperties(&classBindModule))
    {
        bm_UnbindModule(hModule);
        classBindModule.m_hModule = NULL;
        classBindModule.m_pClassDefs = NULL;
        classBindModule.m_nClassDefs = 0;
        return CB_NOTCLASSMODULE;
    }
#else
    if (*version != SERVEROBJ_VERSION)
    {
        bm_UnbindModule(hModule);
        return CB_VERSIONMISMATCH;
    }

    // Verify all properties!
    cb_VerifyClassDefProperties(&classBindModule);
#endif

    return CB_NOERROR;
}


void cb_UnloadModule( ClassBindModule& classBindModule )
{
	if( classBindModule.m_hModule )
{
		bm_UnbindModule( classBindModule.m_hModule );
		classBindModule.m_hModule = NULL;
	}
}


int cb_GetNumClassDefs(ClassBindModule *hModule)
{
    return hModule->m_nClassDefs;
}


ClassDef** cb_GetClassDefs(ClassBindModule *hModule)
{
    return hModule->m_pClassDefs;
}


ClassDef* cb_FindClass(ClassBindModule *pModule, const char *pClassName)
{
    int i;

    for (i=0; i < pModule->m_nClassDefs; i++)
        if (strcmp(pModule->m_pClassDefs[i]->m_ClassName, pClassName) == 0)
            return pModule->m_pClassDefs[i];

    return LTNULL;
}


PropDef* cb_FindVarFull(ClassBindModule *hModule, ClassDef *pClass, const char *pVarName)
{
    int i;

    while (pClass)
    {
        for (i=0; i < pClass->m_nProps; i++)
            if (strcmp(pClass->m_Props[i].m_PropName, pVarName) == 0)
                return &pClass->m_Props[i];
    
        pClass = pClass->m_ParentClass;
    }

    return LTNULL;
}


// IsClassFlagSet
//
// Finds if class flags are set in this or any parent class...
ClassDef *cb_IsClassFlagSet(ClassBindModule *hModule, ClassDef *pClass, const uint32 dwClassFlag)
{
    while (pClass)
    {
        if (pClass->m_ClassFlags & dwClassFlag)
            return pClass;
    
        pClass = pClass->m_ParentClass;
    }

    return LTNULL;
}


