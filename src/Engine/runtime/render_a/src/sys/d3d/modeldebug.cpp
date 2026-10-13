#include "precompile.h"
#include "modeldebug.h"

#include "d3dmeshrendobj_skel.h"
#include "d3dmeshrendobj_rigid.h"

#include "setupmodel.h"
#include "d3d_utils.h"
#include "d3d_device.h"
#include "common_stuff.h"
#include "common_init.h"
#include "iltdrawprim.h"
#include "d3d_texture.h"

static ILTDrawPrim* g_pILTDrawPrimInternal;
define_holder_to_instance(ILTDrawPrim, g_pILTDrawPrimInternal, Internal);

//draws a box around the model of the size of the model dimensions
void NModelDebug::DrawModelBox(ModelInstance* pInstance)
{
	const LTVector& Pos  = pInstance->GetPos();
	const LTVector& Dims = pInstance->GetDims();

	//make sure that D3D is in a desired state
	StateSet ssZWrite(D3DRS_ZWRITEENABLE, FALSE);
	StateSet ssZRead(D3DRS_ZENABLE, FALSE);
	d3d_DisableTexture(0);

	//now render the actual box
	d3d_DrawWireframeBox(Pos - Dims, Pos + Dims, 0xFFFFFFFF);
}

//draws all lights touching a model
void NModelDebug::DrawTouchingLights(const CRelevantLightList& LightList)
{
	if (!g_pILTDrawPrimInternal) return; 
	g_pILTDrawPrimInternal->SetTexture(NULL);
	g_pILTDrawPrimInternal->SetTransformType(DRAWPRIM_TRANSFORM_WORLD);
	g_pILTDrawPrimInternal->SetColorOp(DRAWPRIM_NOCOLOROP);
	g_pILTDrawPrimInternal->SetAlphaBlendMode(DRAWPRIM_BLEND_MOD_SRCALPHA);
	
	if (g_CV_ModelDebug_DrawTouchingLights > 1 || g_CV_DrawCastShadowLights > 1) 
	{
		g_pILTDrawPrimInternal->SetZBufferMode(DRAWPRIM_ZRO); 
	}
	else 
		g_pILTDrawPrimInternal->SetZBufferMode(DRAWPRIM_ZRW);

	g_pILTDrawPrimInternal->SetAlphaTestMode(DRAWPRIM_NOALPHATEST);
	g_pILTDrawPrimInternal->SetClipMode(DRAWPRIM_FASTCLIP);
 
	static uint32 ThisFrameCode;
	static list<CRenderLight> DrawLightInfos;	// Keep a list of drawn lights (don;t want to draw the same one twice a frame)...
	if (ThisFrameCode != g_CurFrameCode) 
	{	
		// New Frame, clear the list...
		DrawLightInfos.erase(DrawLightInfos.begin(),DrawLightInfos.end()); 
		ThisFrameCode = g_CurFrameCode; 
	}

	for (uint32 i=0; i < LightList.GetNumLights(); i++) 
	{
		const CRenderLight& Light = LightList.GetLight(i);

		//ignore it if it isn't a point or spot light
		if(	(Light.GetType() != CRenderLight::eLight_Point) &&
			(Light.GetType() != CRenderLight::eLight_Spot))
		{
			continue;
		}

		bool bAlreadyDrawn = false;			// Figure out if it's already drawn (in the list)...
		list<CRenderLight>::iterator it = DrawLightInfos.begin();
		
		while (it != DrawLightInfos.end()) 
		{
			if (*it == Light) 
			{ 
				bAlreadyDrawn = true; 
				break; 
			} 
			++it; 
		}

		if (bAlreadyDrawn) 
		{ 
			continue; 
		}
		else 
		{ 	
			DrawLightInfos.push_back(Light); 
		}

		float fLightRadius = Light.GetRadius();
		float fCirDiff	   = 0.7071f * fLightRadius;
		float fCirDiff2	   = 0.7071f * fCirDiff;
 
		if ((g_CV_DrawCastShadowLights && (Light.GetFlags() & FLAG_CASTSHADOWS)) || g_CV_ModelDebug_DrawTouchingLights) 
		{
			LT_LINEF Line;	// Draw an X at the center point (in the lights color)
			Line.rgba.a = 0xFF; Line.rgba.r = (uint8)Light.GetColor().x; Line.rgba.g = (uint8)Light.GetColor().y; Line.rgba.b = (uint8)Light.GetColor().z; 
			Line.verts[0].x = Light.GetPos().x - 20; Line.verts[0].y = Light.GetPos().y; Line.verts[0].z = Light.GetPos().z; Line.verts[1].x = Light.GetPos().x + 20; Line.verts[1].y = Light.GetPos().y; Line.verts[1].z = Light.GetPos().z;
			g_pILTDrawPrimInternal->DrawPrim(&Line,1);
			Line.verts[0].x = Light.GetPos().x; Line.verts[0].y = Light.GetPos().y - 20; Line.verts[0].z = Light.GetPos().z; Line.verts[1].x = Light.GetPos().x; Line.verts[1].y = Light.GetPos().y + 20; Line.verts[1].z = Light.GetPos().z;
			g_pILTDrawPrimInternal->DrawPrim(&Line,1);
			Line.verts[0].x = Light.GetPos().x; Line.verts[0].y = Light.GetPos().y; Line.verts[0].z = Light.GetPos().z - 20; Line.verts[1].x = Light.GetPos().x; Line.verts[1].y = Light.GetPos().y; Line.verts[1].z = Light.GetPos().z + 20;
			g_pILTDrawPrimInternal->DrawPrim(&Line,1); 
		}

		if (g_CV_ModelDebug_DrawTouchingLights == 2) 
		{
			LT_POLYF4 Quad;	// Draw a circle type thing now (in some off colors)...
			Quad.rgba.a = 0x10; Quad.rgba.r = MIN(0xFF,(uint8)((float)Light.GetColor().x * 1.2f)); Quad.rgba.g = (uint8)Light.GetColor().y; Quad.rgba.b = (uint8)Light.GetColor().z; 
			Quad.verts[0].x = Light.GetPos().x; Quad.verts[0].y = Light.GetPos().y; Quad.verts[0].z = Light.GetPos().z; Quad.verts[1].x = Light.GetPos().x + fLightRadius; Quad.verts[1].y = Light.GetPos().y; Quad.verts[1].z = Light.GetPos().z; Quad.verts[2].x = Light.GetPos().x + fCirDiff; Quad.verts[2].y = Light.GetPos().y + fCirDiff; Quad.verts[2].z = Light.GetPos().z; Quad.verts[3].x = Light.GetPos().x; Quad.verts[3].y = Light.GetPos().y + fLightRadius; Quad.verts[3].z = Light.GetPos().z;
			g_pILTDrawPrimInternal->DrawPrim(&Quad,1);

			Quad.verts[0].x = Light.GetPos().x; Quad.verts[0].y = Light.GetPos().y; Quad.verts[0].z = Light.GetPos().z; Quad.verts[1].x = Light.GetPos().x - fLightRadius; Quad.verts[1].y = Light.GetPos().y; Quad.verts[1].z = Light.GetPos().z; Quad.verts[2].x = Light.GetPos().x - fCirDiff; Quad.verts[2].y = Light.GetPos().y + fCirDiff; Quad.verts[2].z = Light.GetPos().z; Quad.verts[3].x = Light.GetPos().x; Quad.verts[3].y = Light.GetPos().y + fLightRadius; Quad.verts[3].z = Light.GetPos().z;
			g_pILTDrawPrimInternal->DrawPrim(&Quad,1);

			Quad.verts[0].x = Light.GetPos().x; Quad.verts[0].y = Light.GetPos().y; Quad.verts[0].z = Light.GetPos().z; Quad.verts[1].x = Light.GetPos().x - fLightRadius; Quad.verts[1].y = Light.GetPos().y; Quad.verts[1].z = Light.GetPos().z; Quad.verts[2].x = Light.GetPos().x - fCirDiff; Quad.verts[2].y = Light.GetPos().y - fCirDiff; Quad.verts[2].z = Light.GetPos().z; Quad.verts[3].x = Light.GetPos().x; Quad.verts[3].y = Light.GetPos().y - fLightRadius; Quad.verts[3].z = Light.GetPos().z;
			g_pILTDrawPrimInternal->DrawPrim(&Quad,1);

			Quad.verts[0].x = Light.GetPos().x; Quad.verts[0].y = Light.GetPos().y; Quad.verts[0].z = Light.GetPos().z; Quad.verts[1].x = Light.GetPos().x + fLightRadius; Quad.verts[1].y = Light.GetPos().y; Quad.verts[1].z = Light.GetPos().z; Quad.verts[2].x = Light.GetPos().x + fCirDiff; Quad.verts[2].y = Light.GetPos().y - fCirDiff; Quad.verts[2].z = Light.GetPos().z; Quad.verts[3].x = Light.GetPos().x; Quad.verts[3].y = Light.GetPos().y - fLightRadius; Quad.verts[3].z = Light.GetPos().z;
			g_pILTDrawPrimInternal->DrawPrim(&Quad,1);

			Quad.rgba.a = 0x10; Quad.rgba.r = (uint8)Light.GetColor().x; Quad.rgba.g = (uint8)Light.GetColor().y; Quad.rgba.b = MIN(0xFF,(uint8)((float)Light.GetColor().z * 1.2f)); 
			Quad.verts[0].x = Light.GetPos().x; Quad.verts[0].y = Light.GetPos().y; Quad.verts[0].z = Light.GetPos().z; Quad.verts[1].x = Light.GetPos().x; Quad.verts[1].y = Light.GetPos().y; Quad.verts[1].z = Light.GetPos().z + fLightRadius; Quad.verts[2].x = Light.GetPos().x; Quad.verts[2].y = Light.GetPos().y + fCirDiff; Quad.verts[2].z = Light.GetPos().z + fCirDiff; Quad.verts[3].x = Light.GetPos().x; Quad.verts[3].y = Light.GetPos().y + fLightRadius; Quad.verts[3].z = Light.GetPos().z; g_pILTDrawPrimInternal->DrawPrim(&Quad,1);

			Quad.verts[0].x = Light.GetPos().x; Quad.verts[0].y = Light.GetPos().y; Quad.verts[0].z = Light.GetPos().z; Quad.verts[1].x = Light.GetPos().x; Quad.verts[1].y = Light.GetPos().y; Quad.verts[1].z = Light.GetPos().z - fLightRadius; Quad.verts[2].x = Light.GetPos().x; Quad.verts[2].y = Light.GetPos().y + fCirDiff; Quad.verts[2].z = Light.GetPos().z - fCirDiff; Quad.verts[3].x = Light.GetPos().x; Quad.verts[3].y = Light.GetPos().y + fLightRadius; Quad.verts[3].z = Light.GetPos().z;
			g_pILTDrawPrimInternal->DrawPrim(&Quad,1);

			Quad.verts[0].x = Light.GetPos().x; Quad.verts[0].y = Light.GetPos().y; Quad.verts[0].z = Light.GetPos().z; Quad.verts[1].x = Light.GetPos().x; Quad.verts[1].y = Light.GetPos().y; Quad.verts[1].z = Light.GetPos().z - fLightRadius; Quad.verts[2].x = Light.GetPos().x; Quad.verts[2].y = Light.GetPos().y - fCirDiff; Quad.verts[2].z = Light.GetPos().z - fCirDiff; Quad.verts[3].x = Light.GetPos().x; Quad.verts[3].y = Light.GetPos().y - fLightRadius; Quad.verts[3].z = Light.GetPos().z;
			g_pILTDrawPrimInternal->DrawPrim(&Quad,1);

			Quad.verts[0].x = Light.GetPos().x; Quad.verts[0].y = Light.GetPos().y; Quad.verts[0].z = Light.GetPos().z; Quad.verts[1].x = Light.GetPos().x; Quad.verts[1].y = Light.GetPos().y; Quad.verts[1].z = Light.GetPos().z + fLightRadius; Quad.verts[2].x = Light.GetPos().x; Quad.verts[2].y = Light.GetPos().y - fCirDiff; Quad.verts[2].z = Light.GetPos().z + fCirDiff; Quad.verts[3].x = Light.GetPos().x; Quad.verts[3].y = Light.GetPos().y - fLightRadius; Quad.verts[3].z = Light.GetPos().z;
			g_pILTDrawPrimInternal->DrawPrim(&Quad,1); 
		} 

		if (g_CV_ModelDebug_DrawTouchingLights == 3) 
		{
			LT_POLYF4 Quad;	// Draw a circle type thing now (in some off colors)...
			Quad.rgba.a = 0x10; Quad.rgba.r = MIN(0xFF,(uint8)((float)Light.GetColor().x * 1.2f)); Quad.rgba.g = (uint8)Light.GetColor().y; Quad.rgba.b = (uint8)Light.GetColor().z; 
			Quad.verts[0].x = Light.GetPos().x; 	Quad.verts[0].y = Light.GetPos().y;Quad.verts[0].z = Light.GetPos().z; Quad.verts[1].x = Light.GetPos().x + fCirDiff; Quad.verts[1].y = Light.GetPos().y; Quad.verts[1].z = Light.GetPos().z + fCirDiff; Quad.verts[2].x = Light.GetPos().x + fCirDiff2; 	Quad.verts[2].y = Light.GetPos().y + fCirDiff; 	Quad.verts[2].z = Light.GetPos().z + fCirDiff2; 	Quad.verts[3].x = Light.GetPos().x; Quad.verts[3].y = Light.GetPos().y + fLightRadius; Quad.verts[3].z = Light.GetPos().z;
			g_pILTDrawPrimInternal->DrawPrim(&Quad,1);

			Quad.verts[0].x = Light.GetPos().x; Quad.verts[0].y = Light.GetPos().y;Quad.verts[0].z = Light.GetPos().z; Quad.verts[1].x = Light.GetPos().x - fCirDiff; Quad.verts[1].y = Light.GetPos().y; Quad.verts[1].z = Light.GetPos().z - fCirDiff; Quad.verts[2].x = Light.GetPos().x - fCirDiff2; Quad.verts[2].y = Light.GetPos().y + fCirDiff; Quad.verts[2].z = Light.GetPos().z - fCirDiff2; Quad.verts[3].x = Light.GetPos().x; Quad.verts[3].y = Light.GetPos().y + fLightRadius; Quad.verts[3].z = Light.GetPos().z;
			g_pILTDrawPrimInternal->DrawPrim(&Quad,1);

			Quad.verts[0].x = Light.GetPos().x; Quad.verts[0].y = Light.GetPos().y; Quad.verts[0].z = Light.GetPos().z; Quad.verts[1].x = Light.GetPos().x + fCirDiff; Quad.verts[1].y = Light.GetPos().y; Quad.verts[1].z = Light.GetPos().z + fCirDiff; Quad.verts[2].x = Light.GetPos().x + fCirDiff2; Quad.verts[2].y = Light.GetPos().y - fCirDiff; Quad.verts[2].z = Light.GetPos().z + fCirDiff2; Quad.verts[3].x = Light.GetPos().x; Quad.verts[3].y = Light.GetPos().y - fLightRadius; Quad.verts[3].z = Light.GetPos().z;
			g_pILTDrawPrimInternal->DrawPrim(&Quad,1);

			Quad.verts[0].x = Light.GetPos().x; Quad.verts[0].y = Light.GetPos().y;Quad.verts[0].z = Light.GetPos().z; Quad.verts[1].x = Light.GetPos().x - fCirDiff; Quad.verts[1].y = Light.GetPos().y; Quad.verts[1].z = Light.GetPos().z - fCirDiff; Quad.verts[2].x = Light.GetPos().x - fCirDiff2; Quad.verts[2].y = Light.GetPos().y - fCirDiff; Quad.verts[2].z = Light.GetPos().z - fCirDiff2; Quad.verts[3].x = Light.GetPos().x; Quad.verts[3].y = Light.GetPos().y - fLightRadius; Quad.verts[3].z = Light.GetPos().z;
			g_pILTDrawPrimInternal->DrawPrim(&Quad,1);

			Quad.rgba.a = 0x10; Quad.rgba.r = (uint8)Light.GetColor().x; Quad.rgba.g = (uint8)Light.GetColor().y; Quad.rgba.b = MIN(0xFF,(uint8)((float)Light.GetColor().z * 1.2f)); 
			Quad.verts[0].x = Light.GetPos().x; Quad.verts[0].y = Light.GetPos().y;Quad.verts[0].z = Light.GetPos().z; Quad.verts[1].x = Light.GetPos().x - fCirDiff; Quad.verts[1].y = Light.GetPos().y; Quad.verts[1].z = Light.GetPos().z + fCirDiff; Quad.verts[2].x = Light.GetPos().x - fCirDiff2; Quad.verts[2].y = Light.GetPos().y + fCirDiff; Quad.verts[2].z = Light.GetPos().z + fCirDiff2; Quad.verts[3].x = Light.GetPos().x; Quad.verts[3].y = Light.GetPos().y + fLightRadius; Quad.verts[3].z = Light.GetPos().z;
			g_pILTDrawPrimInternal->DrawPrim(&Quad,1);

			Quad.verts[0].x = Light.GetPos().x; Quad.verts[0].y = Light.GetPos().y;Quad.verts[0].z = Light.GetPos().z; Quad.verts[1].x = Light.GetPos().x + fCirDiff; Quad.verts[1].y = Light.GetPos().y; Quad.verts[1].z = Light.GetPos().z - fCirDiff; Quad.verts[2].x = Light.GetPos().x + fCirDiff2; Quad.verts[2].y = Light.GetPos().y + fCirDiff; Quad.verts[2].z = Light.GetPos().z - fCirDiff2; Quad.verts[3].x = Light.GetPos().x; Quad.verts[3].y = Light.GetPos().y + fLightRadius; Quad.verts[3].z = Light.GetPos().z;
			g_pILTDrawPrimInternal->DrawPrim(&Quad,1);

			Quad.verts[0].x = Light.GetPos().x; Quad.verts[0].y = Light.GetPos().y;Quad.verts[0].z = Light.GetPos().z; Quad.verts[1].x = Light.GetPos().x - fCirDiff; Quad.verts[1].y = Light.GetPos().y; Quad.verts[1].z = Light.GetPos().z + fCirDiff; Quad.verts[2].x = Light.GetPos().x - fCirDiff2; Quad.verts[2].y = Light.GetPos().y - fCirDiff; Quad.verts[2].z = Light.GetPos().z + fCirDiff2; 	Quad.verts[3].x = Light.GetPos().x; Quad.verts[3].y = Light.GetPos().y - fLightRadius; Quad.verts[3].z = Light.GetPos().z;
			g_pILTDrawPrimInternal->DrawPrim(&Quad,1);

			Quad.verts[0].x = Light.GetPos().x; Quad.verts[0].y = Light.GetPos().y;Quad.verts[0].z = Light.GetPos().z; Quad.verts[1].x = Light.GetPos().x + fCirDiff; Quad.verts[1].y = Light.GetPos().y; Quad.verts[1].z = Light.GetPos().z - fCirDiff; Quad.verts[2].x = Light.GetPos().x + fCirDiff2; Quad.verts[2].y = Light.GetPos().y - fCirDiff; Quad.verts[2].z = Light.GetPos().z - fCirDiff2; Quad.verts[3].x = Light.GetPos().x; Quad.verts[3].y = Light.GetPos().y - fLightRadius; Quad.verts[3].z = Light.GetPos().z;
			g_pILTDrawPrimInternal->DrawPrim(&Quad,1); 
		} 
	}
}

//draws the skeleton of a model
void NModelDebug::DrawModelSkeleton(ModelInstance* pInstance)
{
	//setup the draw primitive for line rendering
	if (!g_pILTDrawPrimInternal) 
		return; 

	g_pILTDrawPrimInternal->SetTexture(NULL);
	g_pILTDrawPrimInternal->SetTransformType(DRAWPRIM_TRANSFORM_WORLD);
	g_pILTDrawPrimInternal->SetColorOp(DRAWPRIM_NOCOLOROP);
	g_pILTDrawPrimInternal->SetAlphaBlendMode(DRAWPRIM_BLEND_MOD_SRCALPHA);
	g_pILTDrawPrimInternal->SetZBufferMode(DRAWPRIM_ZRW);
	g_pILTDrawPrimInternal->SetAlphaTestMode(DRAWPRIM_NOALPHATEST);
	g_pILTDrawPrimInternal->SetClipMode(DRAWPRIM_FASTCLIP);

	//figure out how long they want each axis to be from the console variable (ie typing 10
	//will make all axis 10 units long)
	float fAxisLength = LTMAX((float)g_CV_ModelDebug_DrawSkeleton.m_Val, 1.0f);

	//cache the model pointer
	Model* pModel = pInstance->GetModelDB();

	ModelDraw model_draw;
	float fDistToModel = 0.0f;
	fDistToModel = (g_ViewParams.m_Pos - pInstance->GetPos()).Mag();

	// first see which nodes we are being used by the geometry.
	for (uint32 nCurrPiece = 0; nCurrPiece < pModel->NumPieces(); nCurrPiece++) 
	{
		ModelPiece* pPiece			= pModel->GetPiece(nCurrPiece);
		CDIModelDrawable* pLOD      = pPiece->GetLODFromDist( g_CV_ModelLODOffset.m_Val, fDistToModel );	
	
		//if it doesn't have an associated LOD to render, we can't do anything
		if (!pLOD) 
			continue;
		pInstance->SetupLODNodePath(pLOD);
	}

	//the current node transform
	LTMatrix mTrans;

	//the transform of the specified child
	LTMatrix mChildTrans;

	//we just need to run through each node, and for each node render the basis space, as well
	//as a link from the node to all of its children
	for(uint32 nCurrNode = 0; nCurrNode < pModel->NumNodes(); nCurrNode++)
	{
		//figure out which transform we will be using
		if(!pInstance->GetCachedTransform(nCurrNode, mTrans))
			continue;

		//we need to draw the basis space using ModelEdit color scheme (x=r) (y=g) (z=b)
		LTVector vTransOrigin;
		mTrans.GetTranslation(vTransOrigin);

		//find out where the axis each go
		LTVector vAxis[3];
		vAxis[0] = LTVector(1.0f, 0, 0);
		vAxis[1] = LTVector(0, 1.0f, 0);
		vAxis[2] = LTVector(0, 0, 1.0f);

		//now render away
		for(uint32 nCurrAxis = 0; nCurrAxis < 3; nCurrAxis++)
		{
			LT_LINEF Line;


			//setup the line color
			Line.rgba.r = (uint8)(vAxis[nCurrAxis].x * 255.0f);
			Line.rgba.g = (uint8)(vAxis[nCurrAxis].y * 255.0f);
			Line.rgba.b = (uint8)(vAxis[nCurrAxis].z * 255.0f);
			Line.rgba.a = 255;

			//now the positions
			LTVector vTransAxis = mTrans * (vAxis[nCurrAxis] * fAxisLength);
			Line.verts[0].x = vTransAxis.x;
			Line.verts[0].y = vTransAxis.y;
			Line.verts[0].z = vTransAxis.z;

			Line.verts[1].x = vTransOrigin.x;
			Line.verts[1].y = vTransOrigin.y;
			Line.verts[1].z = vTransOrigin.z;

			//and render that line
			g_pILTDrawPrimInternal->DrawPrim(&Line, 1);
		}

		//now we need to draw a link to all of its children, with white fading to black from
		//parent to child, this way it is always visible and the relation can be established
		ModelNode* pNode = pModel->GetNode(nCurrNode);
		assert(pNode);

		for(uint32 nCurrChild = 0; nCurrChild < pNode->NumChildren(); nCurrChild++)
		{
			//now figure out the child node
			ModelNode* pChild = pNode->GetChild(nCurrChild);
			assert(pChild);

			//and figure out which transfor it maps to
			if(!pInstance->GetCachedTransform(pChild->GetNodeIndex(), mChildTrans))
				continue;

			LT_LINEG Line;

			//setup the parent
			Line.verts[0].x = vTransOrigin.x;
			Line.verts[0].y = vTransOrigin.y;
			Line.verts[0].z = vTransOrigin.z;
			Line.verts[0].rgba.r = 255;
			Line.verts[0].rgba.g = 255;
			Line.verts[0].rgba.b = 255;
			Line.verts[0].rgba.a = 255;

			//extract out the position from that matrix
			LTVector vChildPos;
			mChildTrans.GetTranslation(vChildPos);

			//and now setup the vertex
			Line.verts[1].x = vChildPos.x;
			Line.verts[1].y = vChildPos.y;
			Line.verts[1].z = vChildPos.z;
			Line.verts[1].rgba.r = 0;
			Line.verts[1].rgba.g = 0;
			Line.verts[1].rgba.b = 0;
			Line.verts[1].rgba.a = 255;

			//and render that line
			g_pILTDrawPrimInternal->DrawPrim(&Line, 1);
		}
	}
}
