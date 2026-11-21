/* ------------------------------------------------------------
 * 眉透過特化影光沢シェーダー[AlternativeShadowGloss]
 * ------------------------------------------------------------ */
 /* AlternativeFull Base Effect [AlternativeShadowGloss]*/

//シェーディングヒントテクスチャ
#define TEXTURE_THRESHOLD "shading_hint_none.png"

//ポリゴンエッジON
#define ENABLE_POLY_EDGE
//エッジ色(RGB)
float3 EColor = float3(0.1137255f, 0.08627451f, 0.08627451f);

#include "AlternativeShadowGloss.fxsub"