// nolf2src: stand-ins for what the link needs of the world files that do
// not compile yet (docs/engine/PLAN.md, "skeleton"): each does nothing and
// fails. Delete a block when its file builds.

#include "bdefs.h"
#include "de_world.h"
#include "objectmgr.h"
#include "intersect_line.h"
#include "fullintersectline.h"


// fullintersectline.cpp (Jupiter's model OBB intersection: ModelOBB,
// INTERSECT_MODELOBBS, FLAG2_USEMODELOBBS, IntersectInfo::m_hNode)

uint32 g_Ticks_Intersect, g_nIntersectCalls;

bool i_BoundingBoxTest(const LTVector& Point1, const LTVector& Point2, const LTObject *pServerObj,
    LTVector *pIntersectPt, LTPlane *pIntersectPlane)
{
	return false;
}

bool i_IntersectSegment(IntersectQuery *pQuery, IntersectInfo *pInfo, WorldTree *pWorldTree)
{
	return false;
}
