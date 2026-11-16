#ifndef UMA_EFFECTS_H
#define UMA_EFFECTS_H
typedef struct {UINT width,height,bytes;BYTE pixels[16384];} UmaEffectTexture;
static UmaEffectTexture uma_effects[3];
static int uma_effects_ready;
static unsigned uma_effects_hidden;
static int uma_effects_load(const WCHAR *root){
 const WCHAR *names[]={L"GLOBAL\\InGameCommon.bun",L"GLOBAL\\InGameCommon.bun",L"GLOBAL\\GLOBALB.BUN"};
 const long offsets[]={72704,78208,117632};const UINT widths[]={64,128,64};
 WCHAR path[4096];if(wcslen(root)>3800)return 0;
 uma_effects_ready=0;
 for(int i=0;i<3;i++){
  swprintf(path,4096,L"%ls\\%ls",root,names[i]);FILE *file=_wfopen(path,L"rb");if(!file)return 0;
  UINT bytes=widths[i]*widths[i];int valid=!fseek(file,offsets[i],SEEK_SET) && fread(uma_effects[i].pixels,1,bytes,file)==bytes;fclose(file);if(!valid)return 0;
  uint32_t hash=2166136261u;for(UINT j=0;j<bytes;j++)hash=(hash^uma_effects[i].pixels[j])*16777619u;
  const uint32_t expected[]={0x91fe5fa0u,0xc6121c04u,0xc2c8ac0eu};if(hash!=expected[i])return 0;
  uma_effects[i].width=uma_effects[i].height=widths[i];uma_effects[i].bytes=bytes;
 }
 return uma_effects_ready=1;
}
static int uma_effect_texture(IDirect3DTexture9 *texture){
 if(!uma_effects_ready)return 0;
 D3DSURFACE_DESC desc;if(FAILED(IDirect3DTexture9_GetLevelDesc(texture,0,&desc)) || desc.Format!=D3DFMT_DXT3)return 0;
 for(int i=0;i<3;i++)if(desc.Width==uma_effects[i].width && desc.Height==uma_effects[i].height){
  D3DLOCKED_RECT locked;if(FAILED(IDirect3DTexture9_LockRect(texture,0,&locked,NULL,D3DLOCK_READONLY)))return 0;
  UINT row=desc.Width*4;int same=locked.Pitch>0 && (UINT)locked.Pitch>=row;
  for(UINT y=0;same && y<desc.Height/4;y++)if(memcmp((BYTE*)locked.pBits+y*locked.Pitch,uma_effects[i].pixels+y*row,row))same=0;
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
