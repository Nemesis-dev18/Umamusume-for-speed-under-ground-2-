/* ------------------------------------------------------------
 * 眉透過特化影光沢シェーダー[AlternativeShadowGloss]
 * ------------------------------------------------------------ */
 /* AlternativeFull Base Effect [AlternativeShadowGloss]*/

//シェーディングヒントテクスチャ
#define TEXTURE_THRESHOLD "shading_hint_katturi.png"

//影テクスチャ
#define TEXTURE_SHADOW "../textures/S_tex/GD_Hair_Tail_S.tga"

#define ENABLE_RIM_LIGHT_MASK_TEXTURE "../textures/M_tex/GD_Hair_Tail_M.tga"

float RimLightPower = 0.2;
float RimLightThreshold = 10.0f;

#include "AlternativeShadowGloss.fxsub"