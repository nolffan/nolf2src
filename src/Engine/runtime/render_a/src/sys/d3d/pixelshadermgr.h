//------------------------------------------------------------------
//
//  FILE      : PixelShaderMgr.h
//
//  PURPOSE   :	Pixel shader manager singleton. Loads compiled
//				pixel shaders (.ps files) from the resource trees,
//				reference counts them by name, and recreates them
//				when the device is lost.
//
//  COPYRIGHT : LithTech Inc., 1996-2002
//
//------------------------------------------------------------------

#ifndef __PIXELSHADERMGR_H__
#define __PIXELSHADERMGR_H__

#ifndef __VECTOR__
#include <vector>
#define __VECTOR__
#endif

class CPixelShaderMgr;

// CPixelShaderHandle -- a reference to a shader held by the pixel shader
//						 manager. It is just the index into the manager's list.
class CPixelShaderHandle
{
public:

	enum	{ INVALID_HANDLE = 0xFFFFFFFF };

	CPixelShaderHandle() : m_nHandle(INVALID_HANDLE)				{}
	explicit CPixelShaderHandle(uint32 nHandle) : m_nHandle(nHandle)	{}

	//determines if this handle refers to a loaded shader
	bool	IsValid() const			{ return (m_nHandle != INVALID_HANDLE); }

	//clears out the handle so that it no longer refers to a shader
	void	Invalidate()			{ m_nHandle = INVALID_HANDLE; }

	bool	operator==(const CPixelShaderHandle& rhs) const	{ return m_nHandle == rhs.m_nHandle; }
	bool	operator!=(const CPixelShaderHandle& rhs) const	{ return m_nHandle != rhs.m_nHandle; }

private:

	friend class CPixelShaderMgr;

	//the index into the pixel shader manager's list
	uint32	m_nHandle;
};


// CPixelShaderMgr -- manages the loaded pixel shaders
class CPixelShaderMgr
{
public:

	~CPixelShaderMgr();

	//singleton access
	static CPixelShaderMgr&	GetSingleton();

	//loads the specified pixel shader (or adds a reference to it if it is already loaded),
	//returning an invalid handle on failure
	CPixelShaderHandle	LoadPixelShader(const char* pszFilename, bool bCompileShader);

	//frees all the device shader handles
	void				FreeDeviceObjects();

	//recreates all the shaders. This is necessary when the device changes.
	void				RecreatePixelShaders();

	//sets the specified number of constants (4 floats each) starting at the specified register
	bool				SetPixelShaderConstants(uint32 nNumConstants, const float* pConstants, uint32 nStartRegister) const;

	//installs the specified shader into the device
	bool				InstallPixelShader(const CPixelShaderHandle& hShader) const;

	//uninstalls any currently installed shaders
	void				UninstallPixelShaders() const;

	//releases a reference to the shader, freeing it once nothing references it
	bool				ReleasePixelShader(const CPixelShaderHandle& hShader);

private:

	struct SPixelShader
	{
		SPixelShader(const char* pszName, uint8* pFunction, DWORD hShader, bool bCompileShader);
		~SPixelShader();

		DWORD		m_hShader;			//the D3D shader handle
		uint8*		m_pFunction;		//the shader tokens loaded from the file
		char*		m_pszName;			//the file this shader was loaded from
		uint32		m_nRefCount;		//the number of handles that refer to this shader
		bool		m_bCompileShader;	//the flag passed into LoadPixelShader
		bool		m_bCreated;			//is m_hShader a valid device shader
	};

	CPixelShaderMgr();

	//frees the shader in the specified slot of the list
	void				FreeShader(uint32 nShader);

	typedef std::vector<SPixelShader*>	TPixelShaderList;

	TPixelShaderList	m_PixelShaders;
};

#endif
