// nolf2src: stand-ins for what the link needs of the server files that do
// not compile yet (docs/engine/PLAN.md, "skeleton"): each does nothing and
// fails. Delete a block when its file builds.

#include "bdefs.h"
#include "servermgr.h"
#include "s_net.h"
#include "soundtrack.h"
#include "serverevent.h"
#include "s_client.h"


// s_net.cpp (LTAnimTracker::m_bDirty, Jupiter's per-tracker dirty flag)

bool CServerMgr::NewConnectionNotify(CBaseConn *id, bool bIsLocal)
{
	return false;
}

void CServerMgr::DisconnectNotify(CBaseConn *id, EDisconnectReason eDisconnectReason)
{
}

void CServerMgr::HandleUnknownPacket(const CPacket_Read &cPacket, uint8 senderAddr[4], uint16 senderPort)
{
}

void WriteAnimInfo(ModelInstance *pInst, CPacket_Write &cPacket)
{
}

bool FillPacketFromInfo(Client *pClient, LTObject *pObj, ObjInfo *pInfo, CPacket_Write &cPacket)
{
	return false;
}

void SendServerMessage(const CPacket_Read &cPacket, uint32 packetFlags)
{
}

void SendToClient(Client *pClient, const CPacket_Read &cPacket, bool bSendToAttachments, uint32 packetFlags)
{
}

CServerEvent* CreateServerEvent(int type)
{
	return LTNULL;
}

void FillSoundTrackPacketFromInfo(CSoundTrack *pSoundTrack, ObjInfo *pInfo, Client *pClient, CPacket_Write &cPacket)
{
}

void WriteEventToPacket(CServerEvent *pEvent, Client *pClient, CPacket_Write &cPacket)
{
}

LTRESULT ProcessIncomingPackets()
{
	return LT_ERROR;
}

void InitServerNetHandlers()
{
}
