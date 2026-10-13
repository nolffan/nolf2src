// iltsound.h: ILTSoundSys, the engine's interface to a sound driver, as the
// NOLF2 engine (Lithtech.exe) calls it and SndDrv.dll implements it. The
// slot order is the retail driver's vtable's (0x1000b194, 104 slots; the
// abstract table at 0x1000b334 has 103): Monolith's later revision of this
// header less CommitDeferred.

#ifndef __ILTSOUND_H__
#define __ILTSOUND_H__

#ifndef __LTBASETYPES_H__
#include "ltbasetypes.h"
#endif

#ifndef __LTBASEDEFS_H__
#include "ltbasedefs.h"
#endif

#ifndef NULL
#define NULL			0x0
#endif

#ifndef MAKE_BOOL
#define MAKE_BOOL( ltBoolVal )	( ( ( ltBoolVal ) == 0 ) ? false : true )
#define MAKE_LTBOOL( bBoolVal )	( ( ( bBoolVal ) == false ) ? LTFALSE : LTTRUE )
#endif

#define LS_8_MONO_PCM			0
#define LS_16					1
#define LS_STEREO				2
#define	LS_ADPCM				4
#define LS_ASI					16

#define LS_FREE					0x0001
#define LS_DONE					0x0002
#define LS_PLAYING				0x0004
#define LS_STOPPED				0x0008

#define LS_PROENUM_FIRST		0

#define LS_ROOM_GENERIC			0
#define LS_ROOM_TYPE_COUNT		26

#define LS_PREF_MIXER_CHANNELS		1
#define LS_PREF_USE_WAVEOUT			15
#define LS_PREF_LOCK_PROTECTION		18
#define LS_PREF_ENABLE_MMX			27
#define LS_PREF_REVERB_BUFFER_SIZE	40

#ifndef USE_EAX20_HARDWARE_FILTERS
#define USE_EAX20_HARDWARE_FILTERS
#endif

typedef short			sint16;
typedef unsigned short	uint16;
typedef long			sint32;
typedef unsigned int	uint32;
typedef void*			lpvoid;

#define LS_OK			0x0
#define LS_ERROR		0x1

typedef sint32			( *LTLENGTHYCB )	( uint32 uiState, uint32 uiUser );

typedef uint32			LHPROVIDER;
typedef uint32			LHPROENUM;

typedef lpvoid			LHSAMPLE;
typedef lpvoid			LH3DPOBJECT;
typedef lpvoid			LH3DSAMPLE;
typedef lpvoid			LHDIGDRIVER;
typedef lpvoid			LHSTREAM;

typedef lpvoid			PHWAVEOUT;
typedef lpvoid			PTDIRECTSOUND;
typedef lpvoid			PTDIRECTSOUNDBUFFER;

typedef struct
{
	sint32 format;
	lpvoid data_ptr;
	uint32 data_len;
	uint32 rate;
	sint32 bits;
	sint32 channels;
	uint32 samples;
	uint32 block_size;
	lpvoid initial_ptr;
} LTSOUNDINFO;
typedef LTSOUNDINFO*	PTSOUNDINFO;

class LTSOUNDFILTER
{
public:
	virtual void SetParam( const char* pszParam, float fValue ) = 0;
	uint32	uiFilterParamFlags;
};

#ifdef USE_EAX20_HARDWARE_FILTERS

class LTFILTERREVERB : public LTSOUNDFILTER
{
public:
  void SetParam( const char* pszParam, float fValue );

  int	lEnvironment;
  int	lRoom;
  int	lRoomHF;
  float fRoomRolloffFactor;
  float fDecayTime;
  float fDecayHFRatio;
  int   lReflections;
  float fReflectionsDelay;
  int	lReverb;
  float fReverbDelay;
  float fDiffusion;
  float fSize;
  float fAirAbsorptionHF;
  int	lDirect;
};

#endif

#define NULL_FILTER	-1

#define MIN_DOPPLER	0.0f
#define MAX_DOPPLER 10.0f

#ifdef USE_EAX20_HARDWARE_FILTERS

#define SET_REVERB_ENVIRONMENT			(1<<0)
#define SET_REVERB_ROOM					(1<<1)
#define SET_REVERB_ROOMHF				(1<<2)
#define SET_REVERB_ROOMROLLOFFFACTOR	(1<<3)
#define SET_REVERB_DECAYTIME			(1<<4)
#define SET_REVERB_DECAYHFRATIO			(1<<5)
#define SET_REVERB_REFLECTIONS			(1<<6)
#define SET_REVERB_REFLECTIONSDELAY		(1<<7)
#define SET_REVERB_REVERB				(1<<8)
#define SET_REVERB_REVERBDELAY			(1<<9)
#define SET_REVERB_DIFFUSION			(1<<10)
#define SET_REVERB_SIZE					(1<<11)
#define SET_REVERB_AIRABSORPTIONHF		(1<<12)
#define SET_REVERB_DIRECT				(1<<13)

enum
{
	FilterReverb = 0,
	NUM_SOUND_FILTER_TYPES
};

#endif

typedef struct
{
	bool	bUseFilter;
	uint32	uiFilterType;
	LTSOUNDFILTER* pSoundFilter;
} LTSOUNDFILTERDATA;

#ifndef DDI_ID_LPDIRECTSOUND

#define DDI_ID_LPDIRECTSOUND	0x1
#define DDI_ID_HDIGDRIVER		0x2

#endif

enum
{
	SBP_BUFFER_SIZE,
	SBP_BITS_PER_CHANNEL,
	SBP_CHANNELS_PER_SAMPLE,
	SBP_SAMPLES_PER_SEC,

	SBP_NUM_PARAMS

};

struct streamBufferParams_t
{
	sint32	m_siParams[ SBP_NUM_PARAMS ];
};

class ILTSoundSys
{
protected:
	ILTSoundSys( ) {}
	virtual ~ILTSoundSys( ) {}

public:
	virtual bool		Init( ) = 0;
	virtual void		Term( ) = 0;

public:
	virtual void*		GetDDInterface( uint uiDDInterfaceId ) = 0;

public:

	virtual void		Lock( void ) = 0;
	virtual void		Unlock( void ) = 0;
	virtual sint32		Startup( void ) = 0;
	virtual void		Shutdown( void ) = 0;
	virtual uint32		MsCount( void ) = 0;
	virtual sint32		SetPreference( uint32 uiNumber, sint32 siValue ) = 0;
	virtual sint32		GetPreference( uint32 uiNumber ) = 0;
	virtual void		MemFreeLock( void* ptr ) = 0;
	virtual void*		MemAllocLock( uint32 uiSize ) = 0;
	virtual char*		LastError( void ) = 0;

	virtual sint32		WaveOutOpen( LHDIGDRIVER* phDriver, PHWAVEOUT* pphWaveOut, sint32 siDeviceId, WAVEFORMAT* pWaveFormat ) = 0;
	virtual void		WaveOutClose( LHDIGDRIVER hDriver ) = 0;
	virtual void		SetDigitalMasterVolume( LHDIGDRIVER hDig, sint32 siMasterVolume ) = 0;
	virtual sint32		GetDigitalMasterVolume( LHDIGDRIVER hDig ) = 0;
	virtual sint32		DigitalHandleRelease( LHDIGDRIVER hDriver ) = 0;
	virtual sint32		DigitalHandleReacquire( LHDIGDRIVER hDriver ) = 0;
#ifdef USE_EAX20_HARDWARE_FILTERS
	virtual bool		SetEAX20Filter( bool bEnable, LTSOUNDFILTERDATA* pFilterData ) = 0;
	virtual bool		SupportsEAX20Filter() = 0;
	virtual bool		SetEAX20BufferSettings( LHSAMPLE hSample, LTSOUNDFILTERDATA* pFilterData ) = 0;
#endif

	virtual void		Set3DProviderMinBuffers( uint32 uiMinBuffers ) = 0;
	virtual sint32		Open3DProvider( LHPROVIDER hLib ) = 0;
	virtual void		Close3DProvider( LHPROVIDER hLib ) = 0;
	virtual void		Set3DProviderPreference( LHPROVIDER hLib, char* sName, void* pVal ) = 0;
	virtual void		Get3DProviderAttribute( LHPROVIDER hLib, char* sName, void* pVal ) = 0;
	virtual sint32		Enumerate3DProviders( LHPROENUM* phNext, LHPROVIDER* phDest, char** psName) = 0;

	virtual LH3DPOBJECT	Open3DListener( LHPROVIDER hLib ) = 0;
	virtual void		Close3DListener( LH3DPOBJECT hListener ) = 0;
	virtual void		SetListenerDoppler( LH3DPOBJECT hListener, float fDoppler ) = 0;

	virtual void		Set3DPosition( LH3DPOBJECT hObj, float fX, float fY, float fZ) = 0;
	virtual void		Set3DVelocityVector( LH3DPOBJECT hObj, float fDX_per_s, float fDY_per_s, float fDZ_per_s ) = 0;
	virtual void		Set3DOrientation( LH3DPOBJECT hObj, float fX_face, float fY_face, float fZ_face, float fX_up, float fY_up, float fZ_up ) = 0;
	virtual void		Set3DUserData( LH3DPOBJECT hObj, uint32 uiIndex, sint32 siValue ) = 0;
	virtual void		Get3DPosition( LH3DPOBJECT hObj, float* pfX, float* pfY, float* pfZ) = 0;
	virtual void		Get3DVelocity( LH3DPOBJECT hObj, float* pfDX_per_ms, float* pfDY_per_ms, float* pfDZ_per_ms ) = 0;
	virtual void		Get3DOrientation( LH3DPOBJECT hObj, float* pfX_face, float* pfY_face, float* pfZ_face, float* pfX_up, float* pfY_up, float* pfZ_up ) = 0;
	virtual sint32		Get3DUserData( LH3DPOBJECT hObj, uint32 uiIndex) = 0;

	virtual LH3DSAMPLE	Allocate3DSampleHandle( LHPROVIDER hLib ) = 0;
	virtual void		Release3DSampleHandle( LH3DSAMPLE hS ) = 0;
	virtual void		Stop3DSample( LH3DSAMPLE hS ) = 0;
	virtual void		Start3DSample( LH3DSAMPLE hS ) = 0;
	virtual void		Resume3DSample( LH3DSAMPLE hS ) = 0;
	virtual void		End3DSample( LH3DSAMPLE hS ) = 0;
	virtual sint32		Init3DSampleFromAddress( LH3DSAMPLE hS, void* pStart, uint32 uiLen, WAVEFORMATEX* pWaveFormat, sint32 siPlaybackRate, LTSOUNDFILTERDATA* pFilterData  ) = 0;
	virtual sint32		Init3DSampleFromFile( LH3DSAMPLE hS, void* pFile_image, sint32 siBlock, sint32 siPlaybackRate, LTSOUNDFILTERDATA* pFilterData ) = 0;
	virtual sint32		Get3DSampleVolume( LH3DSAMPLE hS ) = 0;
	virtual void		Set3DSampleVolume( LH3DSAMPLE hS, sint32 siVolume ) = 0;
	virtual uint32		Get3DSampleStatus( LH3DSAMPLE hS ) = 0;
	virtual void		Set3DSampleMsPosition( LHSAMPLE hS, sint32 siMilliseconds ) = 0;
	virtual sint32		Set3DSampleInfo( LH3DSAMPLE hS, LTSOUNDINFO* pInfo ) = 0;
	virtual void		Set3DSampleDistances( LH3DSAMPLE hS, float fMax_dist, float fMin_dist ) = 0;
	virtual void		Set3DSamplePreference( LH3DSAMPLE hSample, char* sName, void* pVal ) = 0;
	virtual void		Set3DSampleLoopBlock( LH3DSAMPLE hS, sint32 siLoop_start_offset, sint32 siLoop_end_offset, bool bEnable ) = 0;
	virtual void		Set3DSampleLoop( LH3DSAMPLE hS, bool bLoop ) = 0;
	virtual void		Set3DSampleObstruction( LH3DSAMPLE hS, float fObstruction ) = 0;
	virtual float		Get3DSampleObstruction( LH3DSAMPLE hS ) = 0;
	virtual void		Set3DSampleOcclusion( LH3DSAMPLE hS, float fOcclusion ) = 0;
	virtual float		Get3DSampleOcclusion( LH3DSAMPLE hS ) = 0;

	virtual LHSAMPLE	AllocateSampleHandle( LHDIGDRIVER hDig ) = 0;
	virtual void		ReleaseSampleHandle( LHSAMPLE hS ) = 0;
	virtual void		InitSample( LHSAMPLE hS ) = 0;
	virtual void		StopSample( LHSAMPLE hS ) = 0;
	virtual void		StartSample( LHSAMPLE hS ) = 0;
	virtual void		ResumeSample( LHSAMPLE hS ) = 0;
	virtual void		EndSample( LHSAMPLE hS ) = 0;
	virtual void		SetSampleVolume( LHSAMPLE hS, sint32 siVolume ) = 0;
	virtual void		SetSamplePan( LHSAMPLE hS, sint32 siPan ) = 0;
	virtual sint32		GetSampleVolume( LHSAMPLE hS ) = 0;
	virtual sint32		GetSamplePan( LHSAMPLE hS ) = 0;
	virtual void		SetSampleUserData( LHSAMPLE hS, uint32 uiIndex, sint32 siValue ) = 0;
	virtual void		GetDirectSoundInfo( LHSAMPLE hS, PTDIRECTSOUND* ppDS, PTDIRECTSOUNDBUFFER* ppDSB ) = 0;
	virtual void		SetSampleReverb( LHSAMPLE hS, float fReverb_level, float fReverb_reflect_time, float fReverb_decay_time ) = 0;
	virtual sint32		InitSampleFromAddress( LHSAMPLE hS, void* pStart, uint32 uiLen, WAVEFORMATEX* pWaveFormat, sint32 siPlaybackRate, LTSOUNDFILTERDATA* pFilterData ) = 0;
	virtual sint32		InitSampleFromFile( LHSAMPLE hS, void* pFile_image, sint32 siBlock, sint32 siPlaybackRate, LTSOUNDFILTERDATA* pFilterData ) = 0;
	virtual void		SetSampleLoopBlock( LHSAMPLE hS, sint32 siLoop_start_offset, sint32 siLoop_end_offset, bool bEnable ) = 0;
	virtual void		SetSampleLoop( LHSAMPLE hS, bool bLoop ) = 0;
	virtual void		SetSampleMsPosition( LHSAMPLE hS, sint32 siMilliseconds ) = 0;
	virtual sint32		GetSampleUserData( LHSAMPLE hS, uint32 uiIndex ) = 0;
	virtual uint32		GetSampleStatus( LHSAMPLE hS ) = 0;

	virtual LHSTREAM	OpenStream( char* sFilename, uint32 nOffset, LHDIGDRIVER hDig, char* sStream, sint32 siStream_mem ) = 0;
	virtual void		SetStreamLoop( LHSTREAM hStream, bool bLoop ) = 0;
	virtual void		SetStreamPlaybackRate( LHSTREAM hStream, sint32 siRate ) = 0;
	virtual void		SetStreamMsPosition( LHSTREAM hS, sint32 siMilliseconds ) = 0;
	virtual void		SetStreamUserData( LHSTREAM hS, uint32 uiIndex, sint32 siValue) = 0;
	virtual sint32		GetStreamUserData( LHSTREAM hS, uint32 uiIndex) = 0;

	virtual void		CloseStream( LHSTREAM hStream ) = 0;
	virtual void		StartStream( LHSTREAM hStream ) = 0;
	virtual void		PauseStream( LHSTREAM hStream, sint32 siOnOff ) = 0;
	virtual void		ResetStream( LHSTREAM hStream ) = 0;
	virtual void		SetStreamVolume( LHSTREAM hStream, sint32 siVolume ) = 0;
	virtual void		SetStreamPan( LHSTREAM hStream, sint32 siPan ) = 0;
	virtual sint32		GetStreamVolume( LHSTREAM hStream ) = 0;
	virtual sint32		GetStreamPan( LHSTREAM hStream ) = 0;
	virtual uint32		GetStreamStatus( LHSTREAM hStream ) = 0;
	virtual sint32		GetStreamBufferParam( LHSTREAM hStream, uint32 uiParam ) = 0;
	virtual void		ClearStreamBuffer( LHSTREAM hStream, bool bClearStreamDataQueue = true) = 0;

	virtual sint32		DecompressADPCM( LTSOUNDINFO* pInfo, void** ppOutData, uint32* puiOutSize ) = 0;
	virtual sint32		DecompressASI( void* pInData, uint32 uiInSize, char* sFilename_ext, void** ppWav, uint32* puiWavSize, LTLENGTHYCB fnCallback ) = 0;

	virtual uint32		GetThreadedSoundTicks( ) = 0;

	virtual bool		HasOnBoardMemory( ) = 0;

public:
};

#endif
