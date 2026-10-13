// nolf2src: stand-ins for what the link needs of the model files that do
// not compile yet (docs/engine/PLAN.md, "skeleton"): each does nothing and
// fails. Delete a block when its file builds.

#include "bdefs.h"
#include "model.h"


// model_load.cpp (Jupiter's ModelOBB_Depricated)

LTRESULT Model::Load(ModelLoadRequest *pRequest, const char *pFilename)
{
	return LT_ERROR;
}
