/* ------------------------------------------------------------
 * AlternativeFull
 * ------------------------------------------------------------ */
/* created by AlternativeFullFrontend. */
#define TEXTURE_THRESHOLD "shading_hint_face.png"
//#define TEXTURE_THRESHOLD "shading_hint_katturi.png"
#define TEXTURE_SHADOW "../Textures/Kita_M_Face_S.tga"
#define TEXTURE_SHADOW_BIAS "Shadow_Bias.png"
#define USE_SELFSHADOW_MODE
#define USE_NONE_SELFSHADOW_MODE
float SelfShadowPower = 1;
#define USE_MATERIAL_SPHERE
#define USE_SPHERE_CHEET
float SphereBoost = 0.73;
float3 DefaultModeShadowColor = {1,1,1};
#define MAX_ANISOTROPY 16

#include "AlternativeFull.fxsub"
