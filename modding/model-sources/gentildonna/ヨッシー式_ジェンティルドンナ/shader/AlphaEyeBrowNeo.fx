/*================================
        AlphaEyeBrowNeo
================================*/

////////////////////////////////////////////////////////////////////////////////////////////////
// パラメータ宣言

//眉材質
#define EB_SUBSET  "12"

//髪材質
#define HR_SUBSET "0"

//青影材質
#define BS_SUBSET "31"

//目を明るく描画する係数
float EyeLight = 1.5;

//髪が透過する目との間の最大距離
float MaxDistance = 10000.0f;

////////////////////////////////////////////////////////////////////////////////////////////////
// 座法変換行列
float4x4 WorldViewProjMatrix      : WORLDVIEWPROJECTION;
float4x4 WorldMatrix              : WORLD;
float4x4 LightWorldViewProjMatrix : WORLDVIEWPROJECTION < string Object = "Light"; > ;

float3   LightDirection    : DIRECTION < string Object = "Light"; > ;
float3   CameraPosition    : POSITION < string Object = "Camera"; > ;
float3   CameraDirection   : DIRECTION < string Object = "Camera"; > ;

// マテリアル色
float4   MaterialDiffuse   : DIFFUSE < string Object = "Geometry"; > ;
float3   MaterialAmbient   : AMBIENT < string Object = "Geometry"; > ;
float3   MaterialEmmisive  : EMISSIVE < string Object = "Geometry"; > ;
float3   MaterialSpecular  : SPECULAR < string Object = "Geometry"; > ;
float    SpecularPower : SPECULARPOWER < string Object = "Geometry"; > ;
float3   MaterialToon      : TOONCOLOR;

// ライト色
float3   LightDiffuse      : DIFFUSE < string Object = "Light"; > ;
float3   LightAmbient      : AMBIENT < string Object = "Light"; > ;
float3   LightSpecular     : SPECULAR < string Object = "Light"; > ;
static float4 DiffuseColor = MaterialDiffuse * float4(LightDiffuse, 1.0f);
static float3 AmbientColor = saturate(MaterialAmbient * LightAmbient + MaterialEmmisive);
static float3 SpecularColor = MaterialSpecular * LightSpecular;

bool use_texture;  //テクスチャの有無
bool use_toon;     //トゥーンの有無


// オブジェクトテクスチャ
texture ObjectTexture: MATERIALTEXTURE;
sampler ObjTexSampler = sampler_state
{
    texture = <ObjectTexture>;
    MINFILTER = LINEAR;
    MAGFILTER = LINEAR;
};

// MMD本来のsamplerを上書きしないための記述です。削除不可。
sampler MMDSamp0 : register(s0);
sampler MMDSamp1 : register(s1);
sampler MMDSamp2 : register(s2);


///////////////////////////////////////////////////////////////////////////////////////////////
// 眉描画

struct VS_OUTPUT
{
    float4 Pos        : POSITION;    // 射影変換座標
    float2 Tex        : TEXCOORD1;   // テクスチャ
    float3 Normal     : TEXCOORD2;   // 法線
    float3 Eye        : TEXCOORD3;   // カメラとの相対位置
    float4 Color      : COLOR0;      // ディフューズ色
};

// 頂点シェーダ
VS_OUTPUT Basic_VS(float4 Pos : POSITION, float3 Normal : NORMAL, float2 Tex : TEXCOORD0)
{
    VS_OUTPUT Out = (VS_OUTPUT)0;

    // カメラ視点のワールドビュー射影変換
    Out.Pos = mul(Pos, WorldViewProjMatrix);

    // カメラとの相対位置
    Out.Eye = CameraPosition - mul(Pos, WorldMatrix);

    // 頂点法線
    Out.Normal = normalize(mul(Normal, (float3x3)WorldMatrix));

    // ディフューズ色＋アンビエント色 計算
    Out.Color.rgb = saturate(max(0, dot(Out.Normal, -LightDirection)) * DiffuseColor.rgb + AmbientColor);
    Out.Color.a = 1;

    // テクスチャ座標
    Out.Tex = Tex;

    return Out;
}

// ピクセルシェーダ
float4 Basic_PS(VS_OUTPUT IN) : COLOR0
{
    float4 Color = IN.Color;
 
    // テクスチャ適用
      Color *= tex2D(ObjTexSampler, IN.Tex);

    return Color;
}

// オブジェクト描画用テクニック
technique EBTec < string MMDPass = "object"; string Subset = EB_SUBSET; > {
    pass DrawObject
    {
        VertexShader = compile vs_3_0 Basic_VS();
        PixelShader = compile ps_3_0 Basic_PS();
    }
}

// オブジェクト描画用テクニック
technique EBTecBS < string MMDPass = "object_ss"; string Subset = EB_SUBSET; > {
    pass DrawObject {
        VertexShader = compile vs_3_0 Basic_VS();
        PixelShader = compile ps_3_0 Basic_PS();
    }
}

///////////////////////////////////////////////////////////////////////////////////////////////
// 髪・青影描画

struct VS_OUTPUT2
{
    float4 Pos        : POSITION;    // 射影変換座標
    float  Col        : TEXCOORD0;   //マスク値
    float2 Tex        : TEXCOORD1;   // テクスチャ
    float3 Normal     : TEXCOORD2;   // 法線
    float3 Eye        : TEXCOORD3;   // カメラとの相対位置
    float4 Color      : COLOR0;      // ディフューズ色
};

// 頂点シェーダ
VS_OUTPUT2 Mask_VS(float4 Pos : POSITION, float3 Normal : NORMAL, float2 Tex : TEXCOORD0, uniform bool hidden)
{
    VS_OUTPUT2 Out = (VS_OUTPUT2)0;

    Out.Pos = Pos;

    if (hidden) {
        //カメラから遠ざけることで目を前面に出す
        float3 camdir = normalize(Pos - CameraPosition);
        Out.Pos.xyz += camdir * MaxDistance;
    }

    // カメラ視点のワールドビュー射影変換
    Out.Pos = mul(Out.Pos, WorldViewProjMatrix);

    return Out;
}

// ピクセルシェーダ
float4 Mask_PS(VS_OUTPUT2 IN) : COLOR0
{
    return float4(0,0,0,0);
}

// オブジェクト描画用テクニック
technique HairTec < string MMDPass = "object"; string Subset = HR_SUBSET; > {
    pass DrawObject {
        AlphaBlendEnable = false;
        AlphaTestEnable = false;
        VertexShader = compile vs_3_0 Mask_VS(true);
        PixelShader = compile ps_3_0 Mask_PS();
    }
}

// オブジェクト描画用テクニック
technique HairTecBS < string MMDPass = "object_ss"; string Subset = HR_SUBSET; > {
    pass DrawObject {
        AlphaBlendEnable = false;
        AlphaTestEnable = false;
        VertexShader = compile vs_3_0 Mask_VS(true);
        PixelShader = compile ps_3_0 Mask_PS();
    }
}

// オブジェクト描画用テクニック
technique BSTec < string MMDPass = "object"; string Subset = BS_SUBSET; > {
    pass DrawObject {
        AlphaBlendEnable = false;
        AlphaTestEnable = false;
        VertexShader = compile vs_3_0 Mask_VS(true);
        PixelShader = compile ps_3_0 Mask_PS();
    }
}

// オブジェクト描画用テクニック
technique BSTecBS < string MMDPass = "object_ss"; string Subset = BS_SUBSET; > {
    pass DrawObject {
        AlphaBlendEnable = false;
        AlphaTestEnable = false;
        VertexShader = compile vs_3_0 Mask_VS(true);
        PixelShader = compile ps_3_0 Mask_PS();
    }
}

///////////////////////////////////////////////////////////////////////////////////////////////
// その他のオブジェクトをマスク描画

technique MainTecMask < string MMDPass = "object"; > {
    pass DrawObject {
        AlphaBlendEnable = false;
        AlphaTestEnable = false;
        VertexShader = compile vs_3_0 Mask_VS(false);
        PixelShader = compile ps_3_0 Mask_PS();
    }
}

// オブジェクト描画用テクニック
technique MainTecBSMask < string MMDPass = "object_ss"; > {
    pass DrawObject {
        AlphaBlendEnable = false;
        AlphaTestEnable = false;
        VertexShader = compile vs_3_0 Mask_VS(false);
        PixelShader = compile ps_3_0 Mask_PS();
    }
}

///////////////////////////////////////////////////////////////////////////////////////////////

technique EdgeTec < string MMDPass = "edge"; > { }
technique ShadowTech < string MMDPass = "shadow"; > { }
technique ZplotTec < string MMDPass = "zplot"; > { }

///////////////////////////////////////////////////////////////////////////////////////////////