// eax.h: what the sound driver uses of Creative's EAX 2.0 interface -- the
// property sets it reaches through IKsPropertySet, their property ids and
// the two property structures. Written for this project from the interface
// as the retail driver uses it (the ids it passes, the sizes it reserves);
// the GUIDs themselves are defined in eaxguid/eaxguid.cpp.

#ifndef __EAX_H__
#define __EAX_H__

#ifdef __cplusplus
extern "C" {
#endif

// EAX 1.0
extern const GUID DSPROPSETID_EAX_ReverbProperties;
extern const GUID DSPROPSETID_EAXBUFFER_ReverbProperties;

// EAX 2.0
extern const GUID DSPROPSETID_EAX20_ListenerProperties;
extern const GUID DSPROPSETID_EAX20_BufferProperties;
extern const GUID CLSID_EAX20_Manager;
extern const GUID IID_EAX20_Manager;
extern const GUID CLSID_EAXDirectSound;

#ifdef __cplusplus
}
#endif

#define DSPROPSETID_EAX_ListenerProperties	DSPROPSETID_EAX20_ListenerProperties
#define DSPROPSETID_EAX_BufferProperties	DSPROPSETID_EAX20_BufferProperties

// listener properties
typedef enum
{
	DSPROPERTY_EAXLISTENER_NONE,
	DSPROPERTY_EAXLISTENER_ALLPARAMETERS,
	DSPROPERTY_EAXLISTENER_ROOM,
	DSPROPERTY_EAXLISTENER_ROOMHF,
	DSPROPERTY_EAXLISTENER_ROOMROLLOFFFACTOR,
	DSPROPERTY_EAXLISTENER_DECAYTIME,
	DSPROPERTY_EAXLISTENER_DECAYHFRATIO,
	DSPROPERTY_EAXLISTENER_REFLECTIONS,
	DSPROPERTY_EAXLISTENER_REFLECTIONSDELAY,
	DSPROPERTY_EAXLISTENER_REVERB,
	DSPROPERTY_EAXLISTENER_REVERBDELAY,
	DSPROPERTY_EAXLISTENER_ENVIRONMENT,
	DSPROPERTY_EAXLISTENER_ENVIRONMENTSIZE,
	DSPROPERTY_EAXLISTENER_ENVIRONMENTDIFFUSION,
	DSPROPERTY_EAXLISTENER_AIRABSORPTIONHF,
	DSPROPERTY_EAXLISTENER_FLAGS
} DSPROPERTY_EAX_LISTENERPROPERTY;

typedef struct _EAXLISTENERPROPERTIES
{
	long lRoom;
	long lRoomHF;
	float flRoomRolloffFactor;
	float flDecayTime;
	float flDecayHFRatio;
	long lReflections;
	float flReflectionsDelay;
	long lReverb;
	float flReverbDelay;
	unsigned long dwEnvironment;
	float flEnvironmentSize;
	float flEnvironmentDiffusion;
	float flAirAbsorptionHF;
	unsigned long dwFlags;
} EAXLISTENERPROPERTIES, *LPEAXLISTENERPROPERTIES;

// buffer properties
typedef enum
{
	DSPROPERTY_EAXBUFFER_NONE,
	DSPROPERTY_EAXBUFFER_ALLPARAMETERS,
	DSPROPERTY_EAXBUFFER_DIRECT,
	DSPROPERTY_EAXBUFFER_DIRECTHF,
	DSPROPERTY_EAXBUFFER_ROOM,
	DSPROPERTY_EAXBUFFER_ROOMHF,
	DSPROPERTY_EAXBUFFER_ROOMROLLOFFFACTOR,
	DSPROPERTY_EAXBUFFER_OBSTRUCTION,
	DSPROPERTY_EAXBUFFER_OBSTRUCTIONLFRATIO,
	DSPROPERTY_EAXBUFFER_OCCLUSION,
	DSPROPERTY_EAXBUFFER_OCCLUSIONLFRATIO,
	DSPROPERTY_EAXBUFFER_OCCLUSIONROOMRATIO,
	DSPROPERTY_EAXBUFFER_OUTSIDEVOLUMEHF,
	DSPROPERTY_EAXBUFFER_AIRABSORPTIONFACTOR,
	DSPROPERTY_EAXBUFFER_FLAGS
} DSPROPERTY_EAX_BUFFERPROPERTY;

typedef struct _EAXBUFFERPROPERTIES
{
	long lDirect;
	long lDirectHF;
	long lRoom;
	long lRoomHF;
	float flRoomRolloffFactor;
	long lObstruction;
	float flObstructionLFRatio;
	long lOcclusion;
	float flOcclusionLFRatio;
	float flOcclusionRoomRatio;
	long lOutsideVolumeHF;
	float flAirAbsorptionFactor;
	unsigned long dwFlags;
} EAXBUFFERPROPERTIES, *LPEAXBUFFERPROPERTIES;

#endif // __EAX_H__
