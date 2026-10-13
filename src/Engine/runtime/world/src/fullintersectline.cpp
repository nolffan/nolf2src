
// nolf2src: Jupiter turns the optimizer off here ("the raycasting is all
// screwed up"); NOLF2's server.dll compiled this module with the project's
// flags, and its i_IntersectSegment counted no ticks.

#include "bdefs.h"
#include "de_world.h"
#include "objectmgr.h"
#include "geometry.h"
#include "syscounter.h"
#include "intersect_line.h"



uint32 g_Ticks_Intersect, g_nIntersectCalls;


static void (*g_FindIntersectionsFn)(const WorldBsp *pWorldBsp, const Node **pNodeIntersectionPtr, 
    LTVector *pIntersectionPosPtr, float *pDistSqrPtr, HPOLY *hWorldPoly,
    LTVector *pPoint1, LTVector *pPoint2, uint8 bWorldModel);


// The current query.
static IntersectQuery *g_pCurQuery;
static uint8 g_bProcessNonSolid;
static uint8 g_bProcessObjects;
static uint8 g_bCheckIfFromPointIsInsideObject;


// The current best intersection (LTNULL if none).
static const Node *g_pWorldIntersection; // The node we intersected if we hit a BSP.
static LTObject *g_pIntersection;
static float g_IntersectionBestDistSqr; // Distance to intersection point squared.
static LTPlane g_IntersectionPlane;
static LTVector g_IntersectionPos;
static HPOLY g_hWorldPoly;  // The WorldModel poly we're touching.

static LTVector g_V, g_VTimesInvVV;
static float g_VPTimesInvVV, g_LineLen;




// Get the intersection point and see if it's inside the other dimensions.
#define DO_PLANE_TEST_X(planeCoord, coord0, coord1, coord2, normalDirection) \
    t = (planeCoord - Point1.coord0) / (Point2.coord0 - Point1.coord0);\
    testCoords[0] = Point1.coord1 + ((Point2.coord1 - Point1.coord1) * t);\
    if (testCoords[0] > min.coord1 && testCoords[0] < max.coord1)\
    {\
        testCoords[1] = Point1.coord2 + ((Point2.coord2 - Point1.coord2) * t);\
        if (testCoords[1] > min.coord2 && testCoords[1] < max.coord2)\
        {\
            pIntersectPt->coord0 = planeCoord;\
            pIntersectPt->coord1 = testCoords[0];\
            pIntersectPt->coord2 = testCoords[1];\
            pIntersectPlane->m_Normal.x = normalDirection;\
            pIntersectPlane->m_Normal.y = 0.0f;\
            pIntersectPlane->m_Normal.z = 0.0f;\
            pIntersectPlane->m_Dist = min.x * normalDirection;\
            return true;\
        }\
    }

#define DO_PLANE_TEST_Y(planeCoord, coord0, coord1, coord2, normalDirection) \
    t = (planeCoord - Point1.coord0) / (Point2.coord0 - Point1.coord0);\
    testCoords[0] = Point1.coord1 + ((Point2.coord1 - Point1.coord1) * t);\
    if (testCoords[0] > min.coord1 && testCoords[0] < max.coord1)\
    {\
        testCoords[1] = Point1.coord2 + ((Point2.coord2 - Point1.coord2) * t);\
        if (testCoords[1] > min.coord2 && testCoords[1] < max.coord2)\
        {\
            pIntersectPt->coord0 = planeCoord;\
            pIntersectPt->coord1 = testCoords[0];\
            pIntersectPt->coord2 = testCoords[1];\
            pIntersectPlane->m_Normal.x = 0.0f;\
            pIntersectPlane->m_Normal.y = normalDirection;\
            pIntersectPlane->m_Normal.z = 0.0f;\
            pIntersectPlane->m_Dist = min.y * normalDirection;\
            return true;\
        }\
    }

#define DO_PLANE_TEST_Z(planeCoord, coord0, coord1, coord2, normalDirection) \
    t = (planeCoord - Point1.coord0) / (Point2.coord0 - Point1.coord0);\
    testCoords[0] = Point1.coord1 + ((Point2.coord1 - Point1.coord1) * t);\
    if (testCoords[0] > min.coord1 && testCoords[0] < max.coord1)\
    {\
        testCoords[1] = Point1.coord2 + ((Point2.coord2 - Point1.coord2) * t);\
        if (testCoords[1] > min.coord2 && testCoords[1] < max.coord2)\
        {\
            pIntersectPt->coord0 = planeCoord;\
            pIntersectPt->coord1 = testCoords[0];\
            pIntersectPt->coord2 = testCoords[1];\
            pIntersectPlane->m_Normal.x = 0.0f;\
            pIntersectPlane->m_Normal.y = 0.0f;\
            pIntersectPlane->m_Normal.z = normalDirection;\
            pIntersectPlane->m_Dist = min.z * normalDirection;\
            return true;\
        }\
    }



// Just sets up the current 'closest object'.
#define USE_THIS_OBJECT(pServerObj, distSqr, plane, intersectionPt, hPoly) \
    g_IntersectionBestDistSqr = distSqr;\
    g_pIntersection = pServerObj;\
    g_IntersectionPlane = plane;\
    g_IntersectionPos = intersectionPt;\
    g_hWorldPoly = hPoly;


// Replaces macro above (left in for reference), so filtering can be done...
inline bool UseThisObject(LTObject* pServerObj, 
						  const float fDistSqr, 
						  const LTPlane & plane, 
						  const LTVector & intersectionPt, 
						  const HPOLY & hPoly)
{
	if (g_pCurQuery->m_FilterActualIntersectFn && 
		!g_pCurQuery->m_FilterActualIntersectFn((HOBJECT)pServerObj, g_pCurQuery->m_pActualIntersectUserData))
	{
		// They said to ignore it..
		return false;
	}
	
	USE_THIS_OBJECT(pServerObj, fDistSqr, plane, intersectionPt, hPoly);
	return true;
}

bool i_BoundingBoxTest(const LTVector& Point1, const LTVector& Point2, const LTObject *pServerObj, 
    LTVector *pIntersectPt, LTPlane *pIntersectPlane)
{
    float t;
    float testCoords[2];
	const LTVector& min = pServerObj->GetBBoxMin();
	const LTVector& max = pServerObj->GetBBoxMax();

    // Left/Right.
    if (Point1.x < min.x) 
	{
        if (Point2.x < min.x) 
		{
            return false;
        }
    
        DO_PLANE_TEST_X(min.x, x, y, z, -1.0f);
    }
    else if (Point1.x > max.x) 
	{
        if (Point2.x > max.x) 
		{
            return false;
        }

        DO_PLANE_TEST_X(max.x, x, y, z, 1.0f);
    }

    // Top/Bottom.
    if (Point1.y < min.y) 
	{
        if (Point2.y < min.y) 
		{
            return false;
        }
    
        DO_PLANE_TEST_Y(min.y, y, x, z, -1.0f);
    }
    else if (Point1.y > max.y) 
	{
        if (Point2.y > max.y) 
		{
            return false;
        }

        DO_PLANE_TEST_Y(max.y, y, x, z, 1.0f);
    }

    // Front/Back.
    if (Point1.z < min.z) 
	{
        if (Point2.z < min.z) 
		{
            return false;
        }
    
        DO_PLANE_TEST_Z(min.z, z, x, y, -1.0f);
    }
    else if (Point1.z > max.z) 
	{
        if (Point2.z > max.z) 
		{
            return false;
        }

        DO_PLANE_TEST_Z(max.z, z, x, y, 1.0f);
    }


	// If we get here and our hackish backwards compatibility flag is set, we need to check
	// to see if Point1 is completely inside the dims.  The above checks don't catch this case...

	if (g_bCheckIfFromPointIsInsideObject)
	{
		if ( (min.x <= Point1.x && Point1.x <= max.x) &&
			 (min.y <= Point1.y && Point1.y <= max.y) &&
			 (min.z <= Point1.z && Point1.z <= max.z) )
		{
			LTVector vNormal = (Point1 - Point2);
			vNormal.Normalize();

			LTPlane pPlane;
			pPlane.Init(vNormal, Point1);

			*pIntersectPt = Point1;
			*pIntersectPlane = pPlane;

			return true;
		}
	}

    return false;
}


inline bool i_QuickSphereTest(const LTObject *pServerObj) 
{
    // Find the closest point to the line.
    // Here's the equation for t:
    // P = point1
    // V = point2 - point1 (ie: direction vector)
    // S = point you're testing
    // t = parametric (P + Vt)
    // t = -(-VS + VP) / VV

    //dirVec = *pPoint2 - *pPoint1;
    //t = pServerObj->m_Pos.Dot(dirVec) - dirVec.Dot(*pPoint1);
    //t /= dirVec.Dot(dirVec);

    float t = g_VTimesInvVV.Dot(pServerObj->GetPos()) - g_VPTimesInvVV;

	//cache this radius since it is a virtual function call and can be somewhat expensive on some
	//object types
	float fRadius = pServerObj->GetRadius();

    if (t < -fRadius || t > (g_LineLen + fRadius)) 
	{
        return false;
    }
    
    // Now see if it's within range.
    LTVector vecTo = g_pCurQuery->m_From + g_V * t - pServerObj->GetPos();
    return vecTo.MagSqr() < pServerObj->GetRadiusSquared();
}

// Returns true if the segment hits the world model.
static bool i_TestWorldModel(WorldModelInstance *pObj) 
{
    const Node *pNodeIntersection;
    LTVector intersectionPt;
    LTFLOAT distToIntersectionSqr;
    HPOLY hWorldPoly;
    LTVector points[2], planePt;
    LTPlane tempPlane;


    // Pre-rotate the endpoints for the worldmodel.
    MatVMul_H(&points[0], &pObj->m_BackTransform, (LTVector*)&g_pCurQuery->m_From);
    MatVMul_H(&points[1], &pObj->m_BackTransform, (LTVector*)&g_pCurQuery->m_To);

    g_FindIntersectionsFn(pObj->m_pOriginalBsp, 
        &pNodeIntersection, &intersectionPt, &distToIntersectionSqr, &hWorldPoly,
        &points[0], &points[1], true);
    
    if (!pNodeIntersection) 
	{
        return false;
    }

    MatVMul_InPlace_H(&pObj->m_Transform, &intersectionPt);
    distToIntersectionSqr = g_pCurQuery->m_From.DistSqr(intersectionPt);

    if (distToIntersectionSqr < g_IntersectionBestDistSqr) 
	{
        planePt = pNodeIntersection->GetPlane()->m_Normal * pNodeIntersection->GetPlane()->m_Dist;
        MatVMul_3x3(&tempPlane.m_Normal, &pObj->m_Transform, &pNodeIntersection->GetPlane()->m_Normal);
        tempPlane.m_Dist = tempPlane.m_Normal.Dot(planePt);

        g_pWorldIntersection = pNodeIntersection;

        //USE_THIS_OBJECT(pObj, distToIntersectionSqr, tempPlane, intersectionPt, hWorldPoly);
 		//return true;
		return UseThisObject(pObj, distToIntersectionSqr, tempPlane, intersectionPt, hWorldPoly);
	}

    return false;
}

// Tries everything it can think of to reject this object intersection.
// If it does intersect and is closer than the current best world intersection
// then it replaces the current one.
inline bool i_HandlePossibleIntersection(const LTVector& Point1, const LTVector& Point2, LTObject *pServerObj)
{
    // Quick sphere test.
    if (i_QuickSphereTest(pServerObj)) 
	{
        // Ok, filter if necessary.
        if (g_pCurQuery->m_FilterFn && 
            !g_pCurQuery->m_FilterFn((HOBJECT)pServerObj, g_pCurQuery->m_pUserData))
        {
            // They said to ignore it..
        }
        else 
		{
            // If it's a WorldModel, add it to the list to be tested later.
            // You can't treat it like a solid box here because a ray could go
            // right through all its geometry.

            // [kls 5/16/00 Always do full intersection tests on world models
            // so we get the correct hpoly information
            // if (HasWorldModel(pServerObj) && !(pServerObj->m_Flags & FLAG_BOXPHYSICS))
            
            if (HasWorldModel(pServerObj)) 
			{
				return i_TestWorldModel(pServerObj->ToWorldModel());
            }
            else 
			{
                // Bounding box test...
				LTVector testPt;
				LTPlane testPlane;
                if (i_BoundingBoxTest(Point1, Point2, pServerObj, &testPt, &testPlane)) 
				{
                    // Is this intersection closer than the current best?
                    float distToIntersectionSqr = testPt.DistSqr(g_pCurQuery->m_From);
                    
                    if (g_pIntersection) 
					{
                        if (distToIntersectionSqr < g_IntersectionBestDistSqr) 
						{
                            return UseThisObject(pServerObj, distToIntersectionSqr, testPlane, testPt, INVALID_HPOLY);
                        }
                    }
                    else 
					{
                        //USE_THIS_OBJECT(pServerObj, distToIntersectionSqr, testPlane, testPt, INVALID_HPOLY);
                        //return true;
                        return UseThisObject(pServerObj, distToIntersectionSqr, testPlane, testPt, INVALID_HPOLY);
                    }
                }
            }
        }
    }

    return false;
}


// Finds intersections a slower way, but fills in hWorldPoly.
static void i_FindIntersectionsHPoly(const WorldBsp *pWorldBsp, const Node **pNodeIntersectionPtr, 
    LTVector *pIntersectionPosPtr, float *pDistSqrPtr, HPOLY *hWorldPoly, 
    LTVector *pPoint1, LTVector *pPoint2, uint8 bWorldModel)
{
    IntersectRequest req;

    req.m_pPoints[0] = pPoint1;
    req.m_pPoints[1] = pPoint2;
    req.m_pIPos      = pIntersectionPosPtr;
    req.m_pQuery     = g_pCurQuery;
    req.m_pWorldBsp  = pWorldBsp;
    
    if (IntersectLineNode(pWorldBsp->GetRootNode(), &req)) 
	{
        ASSERT(req.m_pNodeHit);

        *hWorldPoly = pWorldBsp->MakeHPoly(req.m_pNodeHit);
        *pNodeIntersectionPtr = req.m_pNodeHit;
        *pDistSqrPtr = g_pCurQuery->m_From.DistSqr(*req.m_pIPos);
    }
    else 
	{
        *hWorldPoly = INVALID_HPOLY;
        *pNodeIntersectionPtr = LTNULL;
    }
}


static void i_FindIntersections(const WorldBsp *pWorldBsp, const Node **pNodeIntersectionPtr, 
    LTVector *pIntersectionPosPtr, float *pDistSqrPtr, HPOLY *hWorldPoly, 
    LTVector *pPoint1, LTVector *pPoint2, uint8 bWorldModel)
{
    LTPlane iPlane;


    *hWorldPoly = INVALID_HPOLY;
    *pNodeIntersectionPtr = IntersectLine(pWorldBsp->GetRootNode(), pPoint1, pPoint2, pIntersectionPosPtr, &iPlane);
    if (*pNodeIntersectionPtr) 
	{
        *pDistSqrPtr = pPoint1->DistSqr(*pIntersectionPosPtr);
    }
}


// Called by the WorldTree in IntersectSegment.
static bool i_ISCallback(WorldTreeObj *pObj, void *pCBUser) 
{    
    ASSERT(pObj->GetObjType() == WTObj_DObject);
    LTObject *pObject = (LTObject*)pObj;
    
    if (pObject->m_Flags & (FLAG_RAYHIT|FLAG_SOLID) || g_bProcessNonSolid) 
	{
        // Honor the INTERSECT_OBJECTS flag (or lack thereof...)
        if (!g_bProcessObjects && !pObject->IsMainWorldModel()) 
		{
            return false;
        }

        // Hit the object if it has the ray hit flag, is solid, or if non-solid and it
        // query doesn't have ignore non-solid...
        // This is basically everything except for objects with only touch-notify...
        // Do further tests..
        return i_HandlePossibleIntersection(g_pCurQuery->m_From, g_pCurQuery->m_To, pObject);
    }

    return false;
}       


bool i_IntersectSegment(IntersectQuery *pQuery, IntersectInfo *pInfo, WorldTree *pWorldTree)
{
    float InvVV, VP, testMag;

    ++g_nIntersectCalls;
        
    // Init..
    g_pCurQuery = pQuery;
    g_pIntersection = LTNULL;
    g_pWorldIntersection = LTNULL;
    g_hWorldPoly = INVALID_HPOLY;
    g_bProcessNonSolid = !(pQuery->m_Flags & IGNORE_NONSOLID);
    g_bProcessObjects = !!(pQuery->m_Flags & INTERSECT_OBJECTS);
	g_bCheckIfFromPointIsInsideObject = !!(pQuery->m_Flags & CHECK_FROM_POINT_INSIDE_OBJECTS);
    g_IntersectionBestDistSqr = (pQuery->m_From - pQuery->m_To).MagSqr() + 1.0f;

    // Precalculate stuff to totally accelerate i_QuickSphereTest.
    g_V = pQuery->m_To - pQuery->m_From;
    g_LineLen = g_V.Mag();
    g_V /= g_LineLen;
    
    // Was it too short?
    testMag = g_V.MagSqr();
    if (testMag < 0.5f || testMag > 2.0f) 
	{
        return false;
    }
    
    VP = g_V.Dot(pQuery->m_From);
    InvVV = 1.0f / g_V.MagSqr();
    g_VTimesInvVV = g_V * InvVV;
    g_VPTimesInvVV = VP * InvVV;

    if (pQuery->m_Flags & INTERSECT_HPOLY) 
	{
        g_FindIntersectionsFn = i_FindIntersectionsHPoly;
    }
    else 
	{
        g_FindIntersectionsFn = i_FindIntersections;
    }

    // Start at the world tree.
    pWorldTree->IntersectSegment((LTVector*)&pQuery->m_From, (LTVector*)&pQuery->m_To, i_ISCallback, LTNULL);

    // If an object was hit, use it!
    if (g_pIntersection) 
	{
        pInfo->m_Point = g_IntersectionPos;
        pInfo->m_Plane = g_IntersectionPlane;
        pInfo->m_hObject = (HOBJECT)g_pIntersection;
        pInfo->m_hPoly = g_hWorldPoly;
        
        if (g_pWorldIntersection) 
		{
            pInfo->m_SurfaceFlags = g_pWorldIntersection->m_pPoly->GetSurface()->m_TextureFlags;
        }
        else 
		{
            pInfo->m_SurfaceFlags = 0;
        }

        return true;
    }
    else 
	{
        return false;
    }
}

