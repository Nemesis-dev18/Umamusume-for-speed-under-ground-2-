#ifndef UMA_EFFECTS_H
#define UMA_EFFECTS_H
typedef struct {UINT width,height,bytes;D3DFORMAT format;BYTE pixels[16384];} UmaEffectTexture;
static UmaEffectTexture uma_effects[7];
static int uma_effects_ready;
static unsigned uma_effects_hidden;
static int uma_effects_load(const WCHAR *root){
 const WCHAR *names[]={L"GLOBAL\\InGameCommon.bun",L"GLOBAL\\InGameCommon.bun",L"GLOBAL\\GLOBALB.BUN",L"GLOBAL\\InGameCommon.bun",L"GLOBAL\\InGameCommon.bun",L"GLOBAL\\InGameCommon.bun",L"GLOBAL\\InGameCommon.bun"};
 const long offsets[]={72704,78208,117632,404736,475648,794112,407424};const UINT widths[]={64,128,64,64,64,64,64},heights[]={64,128,64,32,32,64,32};
 WCHAR path[4096];if(wcslen(root)>3800)return 0;
 uma_effects_ready=0;
 for(int i=0;i<7;i++){
  swprintf(path,4096,L"%ls\\%ls",root,names[i]);FILE *file=_wfopen(path,L"rb");if(!file)return 0;
  UINT bytes=i==6?2048:widths[i]*heights[i];int valid=!fseek(file,offsets[i],SEEK_SET) && fread(uma_effects[i].pixels,1,bytes,file)==bytes;fclose(file);if(!valid)return 0;
  uint32_t hash=2166136261u;for(UINT j=0;j<bytes;j++)hash=(hash^uma_effects[i].pixels[j])*16777619u;
  const uint32_t expected[]={0x91fe5fa0u,0xc6121c04u,0xc2c8ac0eu,0x18baa344u,0x18baa344u,0x22421f65u,0x3ab11daau};if(hash!=expected[i])return 0;
  uma_effects[i].width=widths[i];uma_effects[i].height=heights[i];uma_effects[i].bytes=bytes;uma_effects[i].format=D3DFMT_DXT3;
  if(i==6){
   BYTE palette[1024],indices[2048];memcpy(indices,uma_effects[i].pixels,2048);FILE *colors=_wfopen(path,L"rb");if(!colors)return 0;
   int ok=!fseek(colors,46080,SEEK_SET) && fread(palette,1,1024,colors)==1024;fclose(colors);if(!ok)return 0;
   uint32_t palette_hash=2166136261u;for(UINT byte=0;byte<1024;byte++)palette_hash=(palette_hash^palette[byte])*16777619u;if(palette_hash!=0x97ba193du)return 0;
   for(UINT pixel=0;pixel<2048;pixel++)memcpy(uma_effects[i].pixels+pixel*4,palette+indices[pixel]*4,4);
   uma_effects[i].bytes=8192;uma_effects[i].format=D3DFMT_A8R8G8B8;
  }
 }
 return uma_effects_ready=1;
}
static int uma_effect_texture(IDirect3DTexture9 *texture){
 if(!uma_effects_ready)return 0;
 D3DSURFACE_DESC desc;if(FAILED(IDirect3DTexture9_GetLevelDesc(texture,0,&desc)))return 0;
 for(int i=0;i<7;i++)if(desc.Width==uma_effects[i].width && desc.Height==uma_effects[i].height && desc.Format==uma_effects[i].format){
  D3DLOCKED_RECT locked;if(FAILED(IDirect3DTexture9_LockRect(texture,0,&locked,NULL,D3DLOCK_READONLY)))return 0;
  UINT row=desc.Width*4;int same=locked.Pitch>0 && (UINT)locked.Pitch>=row;
  for(UINT y=0;same && y<(desc.Format==D3DFMT_DXT3?desc.Height/4:desc.Height);y++)if(memcmp((BYTE*)locked.pBits+y*locked.Pitch,uma_effects[i].pixels+y*row,row))same=0;
  IDirect3DTexture9_UnlockRect(texture,0);if(same)return 1;
 }
 return 0;
}
static int uma_effect_draw(IDirect3DDevice9 *device){
 IDirect3DBaseTexture9 *base=NULL;if(!uma_effects_ready || FAILED(IDirect3DDevice9_GetTexture(device,0,&base)) || !base)return 0;
 int match=IDirect3DBaseTexture9_GetType(base)==D3DRTYPE_TEXTURE && uma_effect_texture((IDirect3DTexture9*)base);
 IDirect3DBaseTexture9_Release(base);if(match)uma_effects_hidden++;return match;
}
#endif
