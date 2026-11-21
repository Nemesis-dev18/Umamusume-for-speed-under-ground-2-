/* ------------------------------------------------------------
 * 眉透過特化影光沢シェーダー[AlternativeShadowGloss]
 * ------------------------------------------------------------ */
 /* AlternativeFull Base Effect [AlternativeShadowGloss]*/

//シェーディングヒントテクスチャ
#define TEXTURE_THRESHOLD "shading_hint_face.png"

//影テクスチャ
#define TEXTURE_SHADOW "../textures/S_tex/GD_Face_S.tga"

//影のなりやすさテクスチャ
#define TEXTURE_SHADOW_BIAS "../textures/SB_tex/GD_Face_SB.tga"

//顔用傾向処理有効化+顔用シャドウバイアステクスチャ参照
#define ENABLE_BIASTYPE_FACE "../textures/SB_tex/GD_Face_SB2.tga"

#include "AlternativeShadowGloss.fxsub"