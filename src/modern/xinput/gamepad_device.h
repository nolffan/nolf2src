// ----------------------------------------------------------------------- //
//
// MODULE  : gamepad_device.h
//
// PURPOSE : The modern build's controller, the engine's half (MODERN.md
//           M-E20): the ##gamepad input device.  Included once, by
//           src/Engine/runtime/kernel/src/sys/win/input.cpp, in its
//           NOLF2SRC_MODERN blocks; nothing of the release build sees it.
//
//           An XInput pad (an Xbox-style controller; what Steam Input
//           presents to Proton on a Steam Deck, and what Wine makes of most
//           pads) as one more DirectInput device: an object behind the
//           IDirectInputDevice8A interface that answers the calls the
//           engine makes of a gamepad from XInput's state (padread.h).  So
//           binding ("A Button" to Jump), the buffered reads, the analog
//           axes, the bindings saved in autoexec.cfg and the profile, and
//           the Controls screen's "press a key" capture all work on it
//           unchanged.  It is a DirectInput gamepad (DI8DEVTYPE_GAMEPAD),
//           the third column of the game's bindings, and the modern build's
//           only one: DirectInput's own joysticks and gamepads are left out
//           (M-E21; under Wine one of them would be the same pad).
//
//           Six absolute axes and sixteen push buttons:
//
//             Left Stick X / Y, Right Stick X / Y    -1000 .. 1000, y down
//                                                    positive (as a
//                                                    joystick's)
//             Left / Right Trigger Axis              0 .. 1000
//             A / B / X / Y Button, Left / Right Bumper, Back, Start,
//             Left / Right Stick Click, D-Pad Up / Down / Left / Right,
//             Left / Right Trigger (pressed past XInput's own threshold)
//
//           It does what a foreground DirectInput device does: it can be
//           acquired only while the game's window is the foreground one,
//           and losing the foreground loses the acquisition.  Changes are
//           buffered as DIDEVICEOBJECTDATA in whatever data format the
//           engine set (c_dfDIJoystick2, or the engine's own: one DWORD per
//           bound object).
//
//           The client can hold buttons back from the bindings
//           (PadDevice_SetHold): while it reads them itself -- a dialogue
//           decision's choice -- a button pressed then stays released for
//           the engine until it is let go.
//
// ----------------------------------------------------------------------- //

#ifndef __NOLF2SRC_GAMEPAD_DEVICE_H__
#define __NOLF2SRC_GAMEPAD_DEVICE_H__

#include "padread.h"

namespace
{
	// {4E4F4C46-3253-5243-4741-4D4550414431}: "NOLF", "2S", "RC", "GAMEPAD1"
	const GUID c_guidPadDevice =
		{ 0x4e4f4c46, 0x3253, 0x5243, { 0x47, 0x41, 0x4d, 0x45, 0x50, 0x41, 0x44, 0x31 } };

	// The buttons the client holds back from the bindings (XInput's bits).
	WORD s_wPadDeviceHold;

	enum { PADOBJ_AXIS, PADOBJ_BUTTON };

	struct PadObject
	{
		const char*	m_pName;
		const GUID*	m_pGuid;
		int			m_nKind;
		DWORD		m_nInstance;
		DWORD		m_dwStdOfs;			// its offset in c_dfDIJoystick2's DIJOYSTATE2
		LONG		m_nMin;
		LONG		m_nMax;
	};

	const PadObject s_PadObjects[] =
	{
		{ "Left Stick X",		&GUID_XAxis,	PADOBJ_AXIS,	0,	DIJOFS_X,			-1000, 1000 },
		{ "Left Stick Y",		&GUID_YAxis,	PADOBJ_AXIS,	1,	DIJOFS_Y,			-1000, 1000 },
		{ "Left Trigger Axis",	&GUID_ZAxis,	PADOBJ_AXIS,	2,	DIJOFS_Z,			0, 1000 },
		{ "Right Stick X",		&GUID_RxAxis,	PADOBJ_AXIS,	3,	DIJOFS_RX,			-1000, 1000 },
		{ "Right Stick Y",		&GUID_RyAxis,	PADOBJ_AXIS,	4,	DIJOFS_RY,			-1000, 1000 },
		{ "Right Trigger Axis",	&GUID_RzAxis,	PADOBJ_AXIS,	5,	DIJOFS_RZ,			0, 1000 },
		{ "A Button",			&GUID_Button,	PADOBJ_BUTTON,	0,	DIJOFS_BUTTON(0),	0, 0 },
		{ "B Button",			&GUID_Button,	PADOBJ_BUTTON,	1,	DIJOFS_BUTTON(1),	0, 0 },
		{ "X Button",			&GUID_Button,	PADOBJ_BUTTON,	2,	DIJOFS_BUTTON(2),	0, 0 },
		{ "Y Button",			&GUID_Button,	PADOBJ_BUTTON,	3,	DIJOFS_BUTTON(3),	0, 0 },
		{ "Left Bumper",		&GUID_Button,	PADOBJ_BUTTON,	4,	DIJOFS_BUTTON(4),	0, 0 },
		{ "Right Bumper",		&GUID_Button,	PADOBJ_BUTTON,	5,	DIJOFS_BUTTON(5),	0, 0 },
		{ "Back",				&GUID_Button,	PADOBJ_BUTTON,	6,	DIJOFS_BUTTON(6),	0, 0 },
		{ "Start",				&GUID_Button,	PADOBJ_BUTTON,	7,	DIJOFS_BUTTON(7),	0, 0 },
		{ "Left Stick Click",	&GUID_Button,	PADOBJ_BUTTON,	8,	DIJOFS_BUTTON(8),	0, 0 },
		{ "Right Stick Click",	&GUID_Button,	PADOBJ_BUTTON,	9,	DIJOFS_BUTTON(9),	0, 0 },
		{ "D-Pad Up",			&GUID_Button,	PADOBJ_BUTTON,	10,	DIJOFS_BUTTON(10),	0, 0 },
		{ "D-Pad Down",			&GUID_Button,	PADOBJ_BUTTON,	11,	DIJOFS_BUTTON(11),	0, 0 },
		{ "D-Pad Left",			&GUID_Button,	PADOBJ_BUTTON,	12,	DIJOFS_BUTTON(12),	0, 0 },
		{ "D-Pad Right",		&GUID_Button,	PADOBJ_BUTTON,	13,	DIJOFS_BUTTON(13),	0, 0 },
		{ "Left Trigger",		&GUID_Button,	PADOBJ_BUTTON,	14,	DIJOFS_BUTTON(14),	0, 0 },
		{ "Right Trigger",		&GUID_Button,	PADOBJ_BUTTON,	15,	DIJOFS_BUTTON(15),	0, 0 },
	};

	enum
	{
		PADOBJ_COUNT	= sizeof(s_PadObjects) / sizeof(s_PadObjects[0]),
		PADOBJ_AXES		= 6,
		PADOBJ_BUTTONS	= 16,
		PADOBJ_BUFFER	= 256			// the most events a buffer holds
	};

	// The XInput bit of each button, in s_PadObjects' order from the
	// first button (the triggers' are not bits).
	const WORD s_PadButtonBits[PADOBJ_BUTTONS - 2] =
	{
		PAD_A, PAD_B, PAD_X, PAD_Y, PAD_LEFT_SHOULDER, PAD_RIGHT_SHOULDER, PAD_BACK, PAD_START,
		PAD_LEFT_THUMB, PAD_RIGHT_THUMB, PAD_DPAD_UP, PAD_DPAD_DOWN, PAD_DPAD_LEFT, PAD_DPAD_RIGHT
	};

	DWORD PadObjectType(int i)
	{
		return (s_PadObjects[i].m_nKind == PADOBJ_AXIS ? DIDFT_ABSAXIS : DIDFT_PSHBUTTON) |
		       DIDFT_MAKEINSTANCE(s_PadObjects[i].m_nInstance);
	}

	LONG PadScaleThumb(SHORT n, BOOL bFlip)
	{
		LONG v = ((LONG)n * 1000) / 32767;

		if (bFlip)
			v = -v;

		return v < -1000 ? -1000 : v > 1000 ? 1000 : v;
	}

	// Every object's value from the pad's state, in s_PadObjects' order;
	// the buttons in wButtons are the ones the bindings may see.
	void PadValues(const PadState& pad, WORD wButtons, LONG* pValues)
	{
		int i;

		pValues[0] = PadScaleThumb(pad.sThumbLX, FALSE);
		pValues[1] = PadScaleThumb(pad.sThumbLY, TRUE);
		pValues[2] = ((LONG)pad.bLeftTrigger * 1000) / 255;
		pValues[3] = PadScaleThumb(pad.sThumbRX, FALSE);
		pValues[4] = PadScaleThumb(pad.sThumbRY, TRUE);
		pValues[5] = ((LONG)pad.bRightTrigger * 1000) / 255;

		for (i = 0; i < PADOBJ_BUTTONS - 2; i++)
			pValues[PADOBJ_AXES + i] = (wButtons & s_PadButtonBits[i]) ? 0x80 : 0;

		pValues[PADOBJ_AXES + 14] = pad.bLeftTrigger > PAD_TRIGGER_THRESHOLD ? 0x80 : 0;
		pValues[PADOBJ_AXES + 15] = pad.bRightTrigger > PAD_TRIGGER_THRESHOLD ? 0x80 : 0;
	}

	// The object a property header names, or -1.
	int PadFindObject(DWORD dwObj, DWORD dwHow, const int* pFormatOfs)
	{
		int i;

		for (i = 0; i < PADOBJ_COUNT; i++)
		{
			if (dwHow == DIPH_BYID && dwObj == PadObjectType(i))
				return i;

			if (dwHow == DIPH_BYOFFSET && pFormatOfs[i] >= 0 && dwObj == (DWORD)pFormatOfs[i])
				return i;
		}

		return -1;
	}

	// Is the window, or one it belongs to, the foreground one?
	BOOL PadIsForeground(HWND hWnd)
	{
		HWND h;

		if (!hWnd)
			return TRUE;

		for (h = GetForegroundWindow(); h; h = GetParent(h))
		{
			if (h == hWnd)
				return TRUE;
		}

		return FALSE;
	}

	void PadDevice_GetInstance(DIDEVICEINSTANCEA* pInstance)
	{
		memset(pInstance, 0, sizeof(DIDEVICEINSTANCEA));
		pInstance->dwSize       = sizeof(DIDEVICEINSTANCEA);
		pInstance->guidInstance = c_guidPadDevice;
		pInstance->guidProduct  = c_guidPadDevice;
		pInstance->dwDevType    = DI8DEVTYPE_GAMEPAD | (DI8DEVTYPEGAMEPAD_STANDARD << 8) | DIDEVTYPE_HID;
		strcpy(pInstance->tszInstanceName, "##gamepad");
		strcpy(pInstance->tszProductName, "XInput Controller");
	}

	// ------------------------------------------------------------------ //
	// The device.

	class CPadDevice : public IDirectInputDevice8A
	{
	public:
		CPadDevice()
		{
			int i;

			m_nRef       = 1;
			m_hWnd       = NULL;
			m_dwCoop     = 0;
			m_bAcquired  = FALSE;
			m_bLost      = FALSE;
			m_bFormat    = FALSE;
			m_dwBufSize  = 0;
			m_nBuf       = 0;
			m_bOverflow  = FALSE;
			m_dwSequence = 0;
			m_wMasked    = 0;

			for (i = 0; i < PADOBJ_COUNT; i++)
			{
				m_FormatOfs[i] = -1;
				m_Value[i]     = 0;
				m_Range[i][0]  = s_PadObjects[i].m_nMin;
				m_Range[i][1]  = s_PadObjects[i].m_nMax;
			}
		}

		// IUnknown
		STDMETHODIMP QueryInterface(REFIID riid, LPVOID* ppv)
		{
			if (IsEqualGUID(riid, IID_IUnknown) || IsEqualGUID(riid, IID_IDirectInputDevice8A))
			{
				*ppv = (IDirectInputDevice8A*)this;
				AddRef();
				return S_OK;
			}

			*ppv = NULL;
			return E_NOINTERFACE;
		}

		STDMETHODIMP_(ULONG) AddRef()
		{
			return ++m_nRef;
		}

		STDMETHODIMP_(ULONG) Release()
		{
			ULONG n = --m_nRef;

			if (n == 0)
				delete this;

			return n;
		}

		// IDirectInputDevice8A
		STDMETHODIMP GetCapabilities(LPDIDEVCAPS pCaps)
		{
			PadState pad;
			DIDEVICEINSTANCEA inst;

			if (!pCaps || pCaps->dwSize < sizeof(DIDEVCAPS))
				return DIERR_INVALIDPARAM;

			PadDevice_GetInstance(&inst);
			memset(pCaps, 0, sizeof(DIDEVCAPS));
			pCaps->dwSize     = sizeof(DIDEVCAPS);
			pCaps->dwFlags    = (PadRead_State(&pad) ? DIDC_ATTACHED : 0) | DIDC_POLLEDDATAFORMAT;
			pCaps->dwDevType  = inst.dwDevType;
			pCaps->dwAxes     = PADOBJ_AXES;
			pCaps->dwButtons  = PADOBJ_BUTTONS;
			pCaps->dwPOVs     = 0;
			return DI_OK;
		}

		STDMETHODIMP EnumObjects(LPDIENUMDEVICEOBJECTSCALLBACKA pCallback, LPVOID pvRef, DWORD dwFlags)
		{
			DIDEVICEOBJECTINSTANCEA doi;
			int i;

			if (!pCallback)
				return DIERR_INVALIDPARAM;

			for (i = 0; i < PADOBJ_COUNT; i++)
			{
				if (dwFlags != DIDFT_ALL && !(DIDFT_GETTYPE(dwFlags) & DIDFT_GETTYPE(PadObjectType(i))))
					continue;

				GetObject(i, &doi);

				if (pCallback(&doi, pvRef) == DIENUM_STOP)
					break;
			}

			return DI_OK;
		}

		STDMETHODIMP GetProperty(REFGUID rguidProp, LPDIPROPHEADER pHeader)
		{
			int i;

			if (!pHeader)
				return DIERR_INVALIDPARAM;

			// DIPROP_* are small numbers cast to GUID references
			if (&rguidProp == &DIPROP_BUFFERSIZE)
			{
				((LPDIPROPDWORD)pHeader)->dwData = m_dwBufSize;
				return DI_OK;
			}

			if (&rguidProp == &DIPROP_RANGE)
			{
				i = PadFindObject(pHeader->dwObj, pHeader->dwHow, m_FormatOfs);

				if (i < 0 || s_PadObjects[i].m_nKind != PADOBJ_AXIS)
					return DIERR_OBJECTNOTFOUND;

				((LPDIPROPRANGE)pHeader)->lMin = m_Range[i][0];
				((LPDIPROPRANGE)pHeader)->lMax = m_Range[i][1];
				return DI_OK;
			}

			return DIERR_UNSUPPORTED;
		}

		STDMETHODIMP SetProperty(REFGUID rguidProp, LPCDIPROPHEADER pHeader)
		{
			int i;

			if (!pHeader)
				return DIERR_INVALIDPARAM;

			if (&rguidProp == &DIPROP_BUFFERSIZE)
			{
				if (m_bAcquired)
					return DIERR_ACQUIRED;

				m_dwBufSize = ((LPCDIPROPDWORD)pHeader)->dwData;

				if (m_dwBufSize > PADOBJ_BUFFER)
					m_dwBufSize = PADOBJ_BUFFER;

				m_nBuf = 0;
				return DI_OK;
			}

			if (&rguidProp == &DIPROP_RANGE)
			{
				LONG nMin = ((LPCDIPROPRANGE)pHeader)->lMin;
				LONG nMax = ((LPCDIPROPRANGE)pHeader)->lMax;

				for (i = 0; i < PADOBJ_COUNT; i++)
				{
					if (s_PadObjects[i].m_nKind != PADOBJ_AXIS)
						continue;

					if (pHeader->dwHow == DIPH_DEVICE ||
					    PadFindObject(pHeader->dwObj, pHeader->dwHow, m_FormatOfs) == i)
					{
						m_Range[i][0] = nMin;
						m_Range[i][1] = nMax;
					}
				}

				return DI_OK;
			}

			// Dead zone, saturation, ...: the game applies its own.
			return DI_PROPNOEFFECT;
		}

		STDMETHODIMP Acquire()
		{
			PadState pad;

			if (!m_bFormat)
				return DIERR_INVALIDPARAM;

			if ((m_dwCoop & DISCL_FOREGROUND) && !PadIsForeground(m_hWnd))
				return DIERR_OTHERAPPHASPRIO;

			if (!m_bAcquired)
			{
				// What is held now is the state the buffer's changes start
				// from, as DirectInput's.
				PadRead_State(&pad);
				m_wMasked = (m_wMasked & pad.wButtons) | (pad.wButtons & s_wPadDeviceHold);
				PadValues(pad, pad.wButtons & ~m_wMasked, m_Value);

				m_bAcquired = TRUE;
				m_bLost     = FALSE;
				m_nBuf      = 0;
				m_bOverflow = FALSE;
			}

			return DI_OK;
		}

		STDMETHODIMP Unacquire()
		{
			if (!m_bAcquired)
				return DI_NOEFFECT;

			m_bAcquired = FALSE;
			m_nBuf      = 0;
			m_bOverflow = FALSE;
			return DI_OK;
		}

		STDMETHODIMP GetDeviceState(DWORD cbData, LPVOID pvData)
		{
			int i;

			if (!pvData)
				return DIERR_INVALIDPARAM;

			if (!Update())
				return m_bLost ? DIERR_INPUTLOST : DIERR_NOTACQUIRED;

			memset(pvData, 0, cbData);

			for (i = 0; i < PADOBJ_COUNT; i++)
			{
				DWORD dwOfs = (DWORD)m_FormatOfs[i];

				if (m_FormatOfs[i] < 0)
					continue;

				if (s_PadObjects[i].m_nKind == PADOBJ_AXIS)
				{
					if (dwOfs + sizeof(LONG) <= cbData)
						*(LONG*)((BYTE*)pvData + dwOfs) = Scaled(i, m_Value[i]);
				}
				else if (dwOfs < cbData)
				{
					*((BYTE*)pvData + dwOfs) = (BYTE)m_Value[i];
				}
			}

			return DI_OK;
		}

		STDMETHODIMP GetDeviceData(DWORD cbObjectData, LPDIDEVICEOBJECTDATA rgdod, LPDWORD pdwInOut,
		                           DWORD dwFlags)
		{
			DWORD   n;
			DWORD   i;
			HRESULT hr;

			if (!pdwInOut)
				return DIERR_INVALIDPARAM;

			if (!Update())
				return m_bLost ? DIERR_INPUTLOST : DIERR_NOTACQUIRED;

			hr = m_bOverflow ? DI_BUFFEROVERFLOW : DI_OK;

			// A null array and INFINITE: throw the buffer away.
			if (!rgdod && *pdwInOut == INFINITE)
			{
				*pdwInOut   = m_nBuf;
				m_nBuf      = 0;
				m_bOverflow = FALSE;
				return hr;
			}

			n = *pdwInOut < m_nBuf ? *pdwInOut : m_nBuf;

			if (rgdod)
			{
				for (i = 0; i < n; i++)
					memcpy((BYTE*)rgdod + i * cbObjectData, &m_Buf[i],
					       cbObjectData < sizeof(DIDEVICEOBJECTDATA) ? cbObjectData : sizeof(DIDEVICEOBJECTDATA));
			}

			if (!(dwFlags & DIGDD_PEEK))
			{
				memmove(m_Buf, m_Buf + n, (m_nBuf - n) * sizeof(DIDEVICEOBJECTDATA));
				m_nBuf     -= n;
				m_bOverflow = FALSE;
			}

			*pdwInOut = n;
			return hr;
		}

		STDMETHODIMP SetDataFormat(LPCDIDATAFORMAT pFormat)
		{
			BOOL  bUsed[PADOBJ_COUNT];
			DWORD i;
			int   j;

			if (!pFormat)
				return DIERR_INVALIDPARAM;

			if (m_bAcquired)
				return DIERR_ACQUIRED;

			for (j = 0; j < PADOBJ_COUNT; j++)
			{
				m_FormatOfs[j] = -1;
				bUsed[j]       = FALSE;
			}

			// Each entry takes the first object not yet taken that it
			// describes: by type, instance (or any) and GUID (or any).
			for (i = 0; i < pFormat->dwNumObjs; i++)
			{
				const DIOBJECTDATAFORMAT* pEntry =
					(const DIOBJECTDATAFORMAT*)((const BYTE*)pFormat->rgodf + i * pFormat->dwObjSize);
				DWORD dwType = pEntry->dwType;

				for (j = 0; j < PADOBJ_COUNT; j++)
				{
					if (bUsed[j])
						continue;

					if (DIDFT_GETTYPE(dwType) && !(DIDFT_GETTYPE(dwType) & DIDFT_GETTYPE(PadObjectType(j))))
						continue;

					if ((dwType & DIDFT_INSTANCEMASK) != DIDFT_ANYINSTANCE &&
					    DIDFT_GETINSTANCE(dwType) != s_PadObjects[j].m_nInstance)
						continue;

					if (pEntry->pguid && !IsEqualGUID(*pEntry->pguid, *s_PadObjects[j].m_pGuid))
						continue;

					bUsed[j]       = TRUE;
					m_FormatOfs[j] = (int)pEntry->dwOfs;
					break;
				}
			}

			m_bFormat = TRUE;
			m_nBuf    = 0;
			return DI_OK;
		}

		STDMETHODIMP SetEventNotification(HANDLE)
		{
			return DI_OK;
		}

		STDMETHODIMP SetCooperativeLevel(HWND hWnd, DWORD dwFlags)
		{
			m_hWnd   = hWnd;
			m_dwCoop = dwFlags;
			return DI_OK;
		}

		STDMETHODIMP GetObjectInfo(LPDIDEVICEOBJECTINSTANCEA pdoi, DWORD dwObj, DWORD dwHow)
		{
			int i;

			if (!pdoi)
				return DIERR_INVALIDPARAM;

			i = PadFindObject(dwObj, dwHow, m_FormatOfs);

			if (i < 0)
				return DIERR_OBJECTNOTFOUND;

			GetObject(i, pdoi);
			return DI_OK;
		}

		STDMETHODIMP GetDeviceInfo(LPDIDEVICEINSTANCEA pdidi)
		{
			if (!pdidi)
				return DIERR_INVALIDPARAM;

			PadDevice_GetInstance(pdidi);
			return DI_OK;
		}

		STDMETHODIMP RunControlPanel(HWND, DWORD)
		{
			return DI_OK;
		}

		STDMETHODIMP Initialize(HINSTANCE, DWORD, REFGUID)
		{
			return DI_OK;
		}

		// No force feedback: rumble would be XInput's (not done).
		STDMETHODIMP CreateEffect(REFGUID, LPCDIEFFECT, LPDIRECTINPUTEFFECT* ppEffect, LPUNKNOWN)
		{
			if (ppEffect)
				*ppEffect = NULL;

			return DIERR_UNSUPPORTED;
		}

		STDMETHODIMP EnumEffects(LPDIENUMEFFECTSCALLBACKA, LPVOID, DWORD)
		{
			return DI_OK;
		}

		STDMETHODIMP GetEffectInfo(LPDIEFFECTINFOA, REFGUID)
		{
			return DIERR_UNSUPPORTED;
		}

		STDMETHODIMP GetForceFeedbackState(LPDWORD)
		{
			return DIERR_UNSUPPORTED;
		}

		STDMETHODIMP SendForceFeedbackCommand(DWORD)
		{
			return DIERR_UNSUPPORTED;
		}

		STDMETHODIMP EnumCreatedEffectObjects(LPDIENUMCREATEDEFFECTOBJECTSCALLBACK, LPVOID, DWORD)
		{
			return DI_OK;
		}

		STDMETHODIMP Escape(LPDIEFFESCAPE)
		{
			return DIERR_UNSUPPORTED;
		}

		STDMETHODIMP Poll()
		{
			if (!Update())
				return m_bLost ? DIERR_INPUTLOST : DIERR_NOTACQUIRED;

			return DI_OK;
		}

		STDMETHODIMP SendDeviceData(DWORD, LPCDIDEVICEOBJECTDATA, LPDWORD, DWORD)
		{
			return DIERR_UNSUPPORTED;
		}

		STDMETHODIMP EnumEffectsInFile(LPCSTR, LPDIENUMEFFECTSINFILECALLBACK, LPVOID, DWORD)
		{
			return DIERR_UNSUPPORTED;
		}

		STDMETHODIMP WriteEffectToFile(LPCSTR, DWORD, LPDIFILEEFFECT, DWORD)
		{
			return DIERR_UNSUPPORTED;
		}

		STDMETHODIMP BuildActionMap(LPDIACTIONFORMATA, LPCSTR, DWORD)
		{
			return DIERR_UNSUPPORTED;
		}

		STDMETHODIMP SetActionMap(LPDIACTIONFORMATA, LPCSTR, DWORD)
		{
			return DIERR_UNSUPPORTED;
		}

		STDMETHODIMP GetImageInfo(LPDIDEVICEIMAGEINFOHEADERA)
		{
			return DIERR_UNSUPPORTED;
		}

	private:
		~CPadDevice()
		{
		}

		void GetObject(int i, LPDIDEVICEOBJECTINSTANCEA pdoi)
		{
			memset(pdoi, 0, sizeof(DIDEVICEOBJECTINSTANCEA));
			pdoi->dwSize   = sizeof(DIDEVICEOBJECTINSTANCEA);
			pdoi->guidType = *s_PadObjects[i].m_pGuid;
			pdoi->dwOfs    = m_FormatOfs[i] >= 0 ? (DWORD)m_FormatOfs[i] : s_PadObjects[i].m_dwStdOfs;
			pdoi->dwType   = PadObjectType(i);
			pdoi->dwFlags  = s_PadObjects[i].m_nKind == PADOBJ_AXIS ? DIDOI_ASPECTPOSITION : 0;
			strncpy(pdoi->tszName, s_PadObjects[i].m_pName, sizeof(pdoi->tszName) - 1);
		}

		// An axis value in the range the application set (the native one
		// unless it set another).
		LONG Scaled(int i, LONG nValue)
		{
			LONG nMin = s_PadObjects[i].m_nMin, nMax = s_PadObjects[i].m_nMax;

			if (m_Range[i][0] == nMin && m_Range[i][1] == nMax)
				return nValue;

			return m_Range[i][0] +
			       (LONG)(((double)(nValue - nMin) * (m_Range[i][1] - m_Range[i][0])) / (nMax - nMin));
		}

		// Read the pad and buffer what changed; FALSE when not acquired.
		BOOL Update()
		{
			PadState pad;
			LONG     values[PADOBJ_COUNT];
			DWORD    dwNow;
			int      n, i;

			if (!m_bAcquired)
				return FALSE;

			if ((m_dwCoop & DISCL_FOREGROUND) && !PadIsForeground(m_hWnd))
			{
				m_bAcquired = FALSE;
				m_bLost     = TRUE;
				m_nBuf      = 0;
				return FALSE;
			}

			PadRead_State(&pad);

			// A button the client holds back stays released here until it
			// is let go.
			m_wMasked = (m_wMasked & pad.wButtons) | (pad.wButtons & s_wPadDeviceHold);
			PadValues(pad, pad.wButtons & ~m_wMasked, values);
			dwNow = GetTickCount();

			// The buttons first: a small buffer (the Controls screen's
			// capture asks for 8) is not to lose a press to the sticks.
			for (n = 0; n < PADOBJ_COUNT; n++)
			{
				i = (n + PADOBJ_AXES) % PADOBJ_COUNT;

				if (values[i] == m_Value[i])
					continue;

				m_Value[i] = values[i];

				if (m_FormatOfs[i] < 0 || !m_dwBufSize)
					continue;

				if (m_nBuf >= m_dwBufSize)
				{
					m_bOverflow = TRUE;
					continue;
				}

				m_Buf[m_nBuf].dwOfs       = (DWORD)m_FormatOfs[i];
				m_Buf[m_nBuf].dwData      = s_PadObjects[i].m_nKind == PADOBJ_AXIS ? (DWORD)Scaled(i, values[i])
				                                                                   : (DWORD)values[i];
				m_Buf[m_nBuf].dwTimeStamp = dwNow;
				m_Buf[m_nBuf].dwSequence  = ++m_dwSequence;
				m_nBuf++;
			}

			return TRUE;
		}

		ULONG				m_nRef;
		HWND				m_hWnd;
		DWORD				m_dwCoop;
		BOOL				m_bAcquired;
		BOOL				m_bLost;
		BOOL				m_bFormat;
		int					m_FormatOfs[PADOBJ_COUNT];	// -1: not in the data format
		LONG				m_Value[PADOBJ_COUNT];		// as last buffered, native range
		LONG				m_Range[PADOBJ_COUNT][2];
		DWORD				m_dwBufSize;
		DIDEVICEOBJECTDATA	m_Buf[PADOBJ_BUFFER];
		DWORD				m_nBuf;
		BOOL				m_bOverflow;
		DWORD				m_dwSequence;
		WORD				m_wMasked;					// buttons held back until released
	};

	// ------------------------------------------------------------------ //
	// What input.cpp calls.

	// Whether the device exists: XInput could be loaded (or the test pad,
	// NOLF2SRC_PADTEST, is on).  Decided once.
	BOOL PadDevice_Available()
	{
		return PadRead_Available() ? TRUE : FALSE;
	}

	BOOL PadDevice_IsPad(REFGUID guidInstance)
	{
		return IsEqualGUID(guidInstance, c_guidPadDevice);
	}

	// CreateDevice for any device: ours for its GUID, DirectInput's
	// otherwise.
	HRESULT PadDevice_CreateDevice(LPDIRECTINPUT8 pDI, REFGUID guid, LPDIRECTINPUTDEVICE8* ppDevice)
	{
		if (PadDevice_IsPad(guid))
		{
			*ppDevice = new CPadDevice;
			return *ppDevice ? DI_OK : DIERR_OUTOFMEMORY;
		}

		return pDI->CreateDevice(guid, ppDevice, NULL);
	}

	// The buttons (XInput's bits) the client reads itself for now and
	// holds back from the bindings.
	void PadDevice_SetHold(WORD wButtons)
	{
		s_wPadDeviceHold = wButtons;
	}
}

#endif // __NOLF2SRC_GAMEPAD_DEVICE_H__
