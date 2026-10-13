//////////////////////////////////////////////////////////////////////////////
// D3D device wrapper implementation

#include "precompile.h"

#include "d3d_device_wrapper.h"

// Valid renderstate list, used to avoid retrieving invalid renderstates
bool g_aValidRSList [174] =
{
	false, false, false, false, false, false, false, // 0-6 = bad
	true, true, true, true, // 7-10 = OK
	false, false, false, // 11-13 = bad
	true, true, true, // 14-16 = OK
	false, false, // 17-18 = bad
	true, true, // 19-20 = OK
	false, // 21 = bad
	true, true, true, true, true, true, true, true, true, // 22-30 = OK
	false, false, false, // 31-33 = bad
	true, true, true, true, true, // 34-38 = OK
	false, // 39 = bad
	true, // 40 = OK
	false, false, false, false, false, false, // 41-46 = bad
	true, true, // 47-48 = OK
	false, false, false, // 49-51 = bad
	true, true, true, true, true, true, true, true, true, // 52-60 = OK
	false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, // 61-127 = bad
	true, true, true, true, true, true, true, true, true, true, // 128-137 = OK
	false, // 138 = bad
	true, true, true, true, true, // 139-143 = OK
	false, // 144 = bad
	true, true, true, true, // 145-148 = OK
	false, false, // 149-150 = bad
	true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, // 151-168 = OK
	false, // 169 = bad
	true, true, true, true // 170-173 = OK
};

bool g_aValidTSSList [29] =
{
	false, // 0 = bad
	true, true, true, true, true, true, true, true, true, true, true, // 1-11 = OK
	false, // 12 = bad
	true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true // 13-28 = OK
};

CDirect3DDevice8Wrapper::CDirect3DDevice8Wrapper() :
	m_nDirtyCount(0),
	m_nRefCount(0)
{
}

CDirect3DDevice8Wrapper::~CDirect3DDevice8Wrapper()
{
	ASSERT((m_pDevice == 0) && (m_nRefCount == 0));
}

// Get the current state of the device
void CDirect3DDevice8Wrapper::ReadCurrentDeviceState()
{
	// Read the normal renderstates
	uint32 nStateID = 0;
	for (; nStateID < k_nNumRenderStates; ++nStateID)
	{
		m_aCurrentDirtyIndex[nStateID] = k_nInvalidIndex;
		if (g_aValidRSList[nStateID])
			GetDevice()->GetRenderState((D3DRENDERSTATETYPE)nStateID, (DWORD*)&m_aCurrentStates[nStateID]);
		else
			m_aCurrentDirtyIndex[nStateID] = 0;
	}

	// Read the TSS renderstates
	for (uint32 nTextureStage = 0; nTextureStage < k_nNumTextureStages; ++nTextureStage)
	{
		for (uint32 nTSSState = 0; nTSSState < k_nNumTSSStates; ++nTSSState, ++nStateID)
		{
			m_aCurrentDirtyIndex[nStateID] = k_nInvalidIndex;
			if (g_aValidTSSList[nTSSState])
				GetDevice()->GetTextureStageState(nTextureStage, (D3DTEXTURESTAGESTATETYPE)nTSSState, (DWORD*)&m_aCurrentStates[nStateID]);
			else
				m_aCurrentDirtyIndex[nStateID] = 0;
		}
	}

	ASSERT(nStateID == k_nNumD3DStates);

	// You're all clean
	m_nDirtyCount = 0;
}

void CDirect3DDevice8Wrapper::FlushStates()
{
	// Run through the dirty list
	for (uint32 nFlushLoop = 0; nFlushLoop < m_nDirtyCount; ++nFlushLoop)
	{
		// Get our next update
		uint32 nDirtyID = m_aDirtyStateIDs[nFlushLoop];
		uint32 nDirtyValue = m_aDirtyStates[nFlushLoop];
		// Don't actually do anything if the state was reset to the current value on the device
		if (nDirtyValue != m_aCurrentStates[nDirtyID])
		{
			// Update our state
			m_aCurrentStates[nDirtyID] = nDirtyValue;
			// Tell the device
			if (nDirtyID < k_nNumRenderStates)
			{
				GetDevice()->SetRenderState((D3DRENDERSTATETYPE)nDirtyID, nDirtyValue);
				ASSERT(g_aValidRSList[nDirtyID]);
			}
			else
			{
				uint32 nTSSOfs = nDirtyID - k_nNumRenderStates;
				GetDevice()->SetTextureStageState(nTSSOfs / k_nNumTSSStates, (D3DTEXTURESTAGESTATETYPE)(nTSSOfs % k_nNumTSSStates), nDirtyValue);
				ASSERT(g_aValidTSSList[nTSSOfs % k_nNumTSSStates]);
			}
		}
		// Clear the dirty index
		m_aCurrentDirtyIndex[nDirtyID] = k_nInvalidIndex;
	}

	// And now you're clean!
	m_nDirtyCount = 0;
}

void CDirect3DDevice8Wrapper::FlushState(uint32 nID)
{
	// Check to make sure it's dirty
	if (m_aCurrentDirtyIndex[nID] == k_nInvalidIndex)
		return;
	// Get the new value
	uint32 nDirtyValue = m_aDirtyStates[m_aCurrentDirtyIndex[nID]];
	// Is it really dirty?
	if (nDirtyValue != m_aCurrentStates[nID])
	{
		// Update the device
		if (nID < k_nNumRenderStates)
		{
			GetDevice()->SetRenderState((D3DRENDERSTATETYPE)nID, nDirtyValue);
		}
		else
		{
			uint32 nTSSOfs = nID - k_nNumRenderStates;
			GetDevice()->SetTextureStageState(nTSSOfs / k_nNumTSSStates, (D3DTEXTURESTAGESTATETYPE)(nTSSOfs % k_nNumTSSStates), nDirtyValue);
		}
	}
	// Update the current state
	m_aCurrentStates[nID] = nDirtyValue;
	// Note : We're still occupying an entry in the dirty list, so this doesn't clear the index
	// (Otherwise states will end up with a double-entry...)
}

