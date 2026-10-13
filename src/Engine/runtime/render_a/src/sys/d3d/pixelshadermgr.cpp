//------------------------------------------------------------------
//
//  FILE      : PixelShaderMgr.cpp
//
//  PURPOSE   :	Pixel shader manager singleton
//
//  COPYRIGHT : LithTech Inc., 1996-2002
//
//------------------------------------------------------------------
//
// Reconstructed: the Jupiter tree replaced this file with the D3D9
// LTPixelShaderMgr. Rebuilt from the NOLF2 retail Lithtech.exe (D3D8):
//
//		0x5095e0	define_holder(IClientFileMgr, ...) static init
//		0x509620	CPixelShaderMgr::~CPixelShaderMgr (FreeShader inlined)
//		0x509740	CPixelShaderMgr::GetSingleton (ctor 0x509780 inlined)
//		0x5097a0	CPixelShaderMgr::LoadPixelShader (SPixelShader ctor inlined)
//		0x509a70	CPixelShaderMgr::FreeDeviceObjects
//		0x509ab0	CPixelShaderMgr::RecreatePixelShaders
//		0x509b00	CPixelShaderMgr::SetPixelShaderConstants
//		0x509b40	CPixelShaderMgr::InstallPixelShader
//		0x509b80	CPixelShaderMgr::UninstallPixelShaders
//		0x509ba0	CPixelShaderMgr::ReleasePixelShader (FreeShader inlined)
//
// Method names and signatures are from the Mac build's symbols. The
// meaning of LoadPixelShader's bool is not known: retail only stores it
// in the shader (screenglow passes false, BlurShadow and envbumpmap pass
// true); the name bCompileShader is borrowed from Jupiter's AddPixelShader.
//
// .ps file format: uint32 'LTPS', uint32 version (1), uint32 size,
// then size bytes of D3D8 pixel shader tokens.
//------------------------------------------------------------------

#include "precompile.h"
#include "d3d_device.h"
#include "pixelshadermgr.h"

//Interface for the client file manager
#include "client_filemgr.h"
static IClientFileMgr* g_pIClientFileMgr;
define_holder(IClientFileMgr, g_pIClientFileMgr);

//the identifier at the start of every pixel shader file ('LTPS')
#define PIXELSHADER_FILE_ID			0x5350544C

//the version of the pixel shader files that we can read
#define PIXELSHADER_FILE_VERSION	1

//------------------------------------------------------------------
// CPixelShaderMgr::SPixelShader
//------------------------------------------------------------------

CPixelShaderMgr::SPixelShader::SPixelShader(const char* pszName, uint8* pFunction, DWORD hShader, bool bCompileShader) :
	m_hShader(hShader),
	m_pFunction(NULL),
	m_pszName(NULL),
	m_nRefCount(1),
	m_bCompileShader(bCompileShader),
	m_bCreated(true)
{
	uint32 nNameLen = strlen(pszName) + 1;
	m_pszName = new char[nNameLen];
	LTStrCpy(m_pszName, pszName, nNameLen);

	m_pFunction = pFunction;
}

CPixelShaderMgr::SPixelShader::~SPixelShader()
{
	delete [] m_pFunction;
	m_pFunction = NULL;

	delete [] m_pszName;
	m_pszName = NULL;

	m_nRefCount = 0;
	m_hShader = 0;
}

//------------------------------------------------------------------
// CPixelShaderMgr
//------------------------------------------------------------------

CPixelShaderMgr::CPixelShaderMgr()
{
}

CPixelShaderMgr::~CPixelShaderMgr()
{
	for(uint32 nCurrShader = 0; nCurrShader < m_PixelShaders.size(); nCurrShader++)
	{
		if(m_PixelShaders[nCurrShader])
			FreeShader(nCurrShader);
	}
}

//singleton access
CPixelShaderMgr& CPixelShaderMgr::GetSingleton()
{
	static CPixelShaderMgr s_Singleton;
	return s_Singleton;
}

//loads the specified pixel shader (or adds a reference to it if it is already loaded)
CPixelShaderHandle CPixelShaderMgr::LoadPixelShader(const char* pszFilename, bool bCompileShader)
{
	//see if we already have this shader loaded, and look for a free slot along the way
	uint32 nFreeSlot = CPixelShaderHandle::INVALID_HANDLE;

	for(uint32 nCurrShader = 0; nCurrShader < m_PixelShaders.size(); nCurrShader++)
	{
		SPixelShader* pShader = m_PixelShaders[nCurrShader];
		if(pShader)
		{
			if(stricmp(pShader->m_pszName, pszFilename) == 0)
			{
				//we already have it, just add a reference
				m_PixelShaders[nCurrShader]->m_nRefCount++;
				return CPixelShaderHandle(nCurrShader);
			}
		}
		else
		{
			nFreeSlot = nCurrShader;
		}
	}

	//we need to load it from disk. Note: retail sets the file type to
	//TYPECODE_UNKNOWN (0xFF) rather than a FILE_ type, and asks for (and
	//discards) a file identifier before opening the file.
	FileRef ref;
	ref.m_FileType	= TYPECODE_UNKNOWN;
	ref.m_pFilename = pszFilename;

	g_pIClientFileMgr->GetFileIdentifier(&ref, TYPECODE_UNKNOWN);

	ILTStream* pStream = g_pIClientFileMgr->OpenFile(&ref);
	if(!pStream)
		return CPixelShaderHandle();

	//make sure that this is a pixel shader file of a version we understand
	uint32 nFileID;
	pStream->Read(&nFileID, sizeof(nFileID));
	if(nFileID != PIXELSHADER_FILE_ID)
	{
		pStream->Release();
		return CPixelShaderHandle();
	}

	uint32 nVersion;
	pStream->Read(&nVersion, sizeof(nVersion));
	if(nVersion != PIXELSHADER_FILE_VERSION)
	{
		pStream->Release();
		return CPixelShaderHandle();
	}

	//now read in the shader tokens
	uint32 nFunctionSize;
	pStream->Read(&nFunctionSize, sizeof(nFunctionSize));

	uint8* pFunction = new uint8[nFunctionSize];
	if(!pFunction)
	{
		pStream->Release();
		return CPixelShaderHandle();
	}

	pStream->Read(pFunction, nFunctionSize);
	pStream->Release();

	//create the shader on the device
	DWORD hShader;
	if(FAILED(PD3DDEVICE->CreatePixelShader((DWORD*)pFunction, &hShader)))
	{
		delete [] pFunction;
		return CPixelShaderHandle();
	}

	//make sure the device will actually accept it
	if(FAILED(PD3DDEVICE->SetPixelShader(hShader)))
	{
		delete [] pFunction;
		PD3DDEVICE->DeletePixelShader(hShader);
		return CPixelShaderHandle();
	}

	PD3DDEVICE->SetPixelShader(NULL);

	//and add it to our list, reusing a free slot if we have one
	SPixelShader* pNewShader = new SPixelShader(pszFilename, pFunction, hShader, bCompileShader);

	if(nFreeSlot < m_PixelShaders.size())
	{
		m_PixelShaders[nFreeSlot] = pNewShader;
	}
	else
	{
		nFreeSlot = m_PixelShaders.size();
		m_PixelShaders.push_back(pNewShader);
	}

	return CPixelShaderHandle(nFreeSlot);
}

//frees all the device shader handles
void CPixelShaderMgr::FreeDeviceObjects()
{
	for(TPixelShaderList::iterator it = m_PixelShaders.begin(); it != m_PixelShaders.end(); it++)
	{
		if(*it && (*it)->m_bCreated)
		{
			PD3DDEVICE->DeletePixelShader((*it)->m_hShader);
			(*it)->m_bCreated = false;
		}
	}
}

//recreates all the shaders. This is necessary when the device changes.
void CPixelShaderMgr::RecreatePixelShaders()
{
	for(TPixelShaderList::iterator it = m_PixelShaders.begin(); it != m_PixelShaders.end(); it++)
	{
		if(*it)
		{
			if(SUCCEEDED(PD3DDEVICE->CreatePixelShader((DWORD*)(*it)->m_pFunction, &(*it)->m_hShader)))
			{
				(*it)->m_bCreated = true;
			}
		}
	}
}

//sets the specified number of constants (4 floats each) starting at the specified register
bool CPixelShaderMgr::SetPixelShaderConstants(uint32 nNumConstants, const float* pConstants, uint32 nStartRegister) const
{
	if((nNumConstants > 0) && pConstants)
	{
		if(SUCCEEDED(PD3DDEVICE->SetPixelShaderConstant(nStartRegister, pConstants, nNumConstants)))
			return true;
	}

	return false;
}

//installs the specified shader into the device
bool CPixelShaderMgr::InstallPixelShader(const CPixelShaderHandle& hShader) const
{
	SPixelShader* pShader = m_PixelShaders[hShader.m_nHandle];

	if(pShader->m_bCreated)
	{
		if(SUCCEEDED(PD3DDEVICE->SetPixelShader(pShader->m_hShader)))
			return true;
	}

	return false;
}

//uninstalls any currently installed shaders
void CPixelShaderMgr::UninstallPixelShaders() const
{
	PD3DDEVICE->SetPixelShader(NULL);
}

//releases a reference to the shader, freeing it once nothing references it
bool CPixelShaderMgr::ReleasePixelShader(const CPixelShaderHandle& hShader)
{
	m_PixelShaders[hShader.m_nHandle]->m_nRefCount--;

	if(m_PixelShaders[hShader.m_nHandle]->m_nRefCount == 0)
	{
		FreeShader(hShader.m_nHandle);
	}

	return true;
}

//frees the shader in the specified slot of the list
void CPixelShaderMgr::FreeShader(uint32 nShader)
{
	SPixelShader* pShader = m_PixelShaders[nShader];
	if(!pShader)
		return;

	if(pShader->m_bCreated)
	{
		PD3DDEVICE->DeletePixelShader(pShader->m_hShader);
	}

	delete m_PixelShaders[nShader];
	m_PixelShaders[nShader] = NULL;
}
