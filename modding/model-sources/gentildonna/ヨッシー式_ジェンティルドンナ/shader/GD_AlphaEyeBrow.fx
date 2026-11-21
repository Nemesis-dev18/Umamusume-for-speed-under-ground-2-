/* ------------------------------------------------------------
 * 眉透過特化影光沢シェーダー[AlternativeShadowGloss]
 * ------------------------------------------------------------ */
 /* AlternativeFull Base Effect [AlternativeShadowGloss]*/

//シェーディングヒントテクスチャ
#define TEXTURE_THRESHOLD "shading_hint_katturi.png"

//影テクスチャ
#define TEXTURE_SHADOW "../textures/S_tex/GD_Hair_Tail_S.tga"

//[AlphaEyeBrowNeo]眉透過ON
#define ENABLE_ALPHA_EYEBROW

#include "AlternativeShadowGloss.fxsub"