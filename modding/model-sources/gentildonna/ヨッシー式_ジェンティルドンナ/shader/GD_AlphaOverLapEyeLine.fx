/* ------------------------------------------------------------
 * 眉透過特化影光沢シェーダー[AlternativeShadowGloss]
 * ------------------------------------------------------------ */
 /* AlternativeFull Base Effect [AlternativeShadowGloss]*/

//シェーディングヒントテクスチャ
#define TEXTURE_THRESHOLD "shading_hint_none.png"

//[AlphaOverLapEyeLineNeo]青影透過ON
#define ENABLE_ALPHA_OVER_LAP_EYELINE

#include "AlternativeShadowGloss.fxsub"