/* ------------------------------------------------------------
 * 眉透過特化影光沢シェーダー[AlternativeShadowGloss]
 * ------------------------------------------------------------ */
 /* AlternativeFull Base Effect [AlternativeShadowGloss]*/

//シェーディングヒントテクスチャ
#define TEXTURE_THRESHOLD "shading_hint_katturi.png"

//影テクスチャ
#define TEXTURE_SHADOW "../textures/S_tex/GD_Hair_Tail_S.tga"

#define ENABLE_REF_LIGHT_MASK_TEXTURE "../textures/M_tex/GD_Hair_Tail_M.tga"

//反射範囲指定(広い← 0～1 →狭い)
float RefRange = 0.8;

float RefPower = 0.2;

#include "AlternativeShadowGloss.fxsub"