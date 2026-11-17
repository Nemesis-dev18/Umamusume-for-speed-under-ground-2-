#ifndef UMA_EFFECTS_H
#define UMA_EFFECTS_H
typedef struct {UINT width,height,bytes;D3DFORMAT format;BYTE pixels[16384];} UmaEffectTexture;
static UmaEffectTexture uma_effects[8];
static int uma_effects_ready;
static unsigned uma_effects_hidden;
static int uma_effects_load(const WCHAR *root){
 const WCHAR *names[]={L"GLOBAL\\InGameCommon.bun",L"GLOBAL\\InGameCommon.bun",L"GLOBAL\\GLOBALB.BUN",L"GLOBAL\\InGameCommon.bun",L"GLOBAL\\InGameCommon.bun",L"GLOBAL\\InGameCommon.bun",L"GLOBAL\\InGameCommon.bun",L"GLOBAL\\GLOBALB.BUN"};
 const long offsets[]={72704,78208,117632,404736,475648,794112,407424,499200};const UINT widths[]={64,128,64,64,64,64,64,128},heights[]={64,128,64,32,32,64,32,128};
 WCHAR path[4096];if(wcslen(root)>3800)return 0;
 uma_effects_ready=0;
 for(int i=0;i<8;i++){
  swprintf(path,4096,L"%ls\\%ls",root,names[i]);FILE *file=_wfopen(path,L"rb");if(!file)return 0;
  UINT bytes=i==6?2048:widths[i]*heights[i];int valid=!fseek(file,offsets[i],SEEK_SET) && fread(uma_effects[i].pixels,1,bytes,file)==bytes;fclose(file);if(!valid)return 0;
  uint32_t hash=2166136261u;for(UINT j=0;j<bytes;j++)hash=(hash^uma_effects[i].pixels[j])*16777619u;
  const uint32_t expected[]={0x91fe5fa0u,0xc6121c04u,0xc2c8ac0eu,0x18baa344u,0x18baa344u,0x22421f65u,0x3ab11daau,0xac557b8eu};if(hash!=expected[i])return 0;
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
/* Cache managed immutable texture identities; every CPU write invalidates the owning texture. */
static const GUID uma_effect_cache_guid={0x27f3ec38,0xc3bd,0x4a78,{0x84,0xd6,0x96,0x52,0x72,0x56,0xd8,0x3d}};
static const GUID uma_effect_texture_iid={0x85c31227,0x3de5,0x4f00,{0x9b,0x3a,0xf1,0x1a,0xc3,0x8c,0x18,0xb5}};
typedef HRESULT (WINAPI *UmaEffectLock)(IDirect3DTexture9*,UINT,D3DLOCKED_RECT*,const RECT*,DWORD);
typedef HRESULT (WINAPI *UmaEffectSurfaceLock)(IDirect3DSurface9*,D3DLOCKED_RECT*,const RECT*,DWORD);
typedef HRESULT (WINAPI *UmaEffectDC)(IDirect3DSurface9*,HDC*);
static struct {void **table;UINT slot;void *native,*hook;} uma_effect_hooks[12];
static volatile LONG uma_effect_hook_count;
static unsigned uma_effect_reads,uma_effect_cache_hits;
static void *uma_effect_native(void *object,UINT slot){
 void **table=*(void***)object;for(LONG i=0;i<uma_effect_hook_count;i++)if(uma_effect_hooks[i].table==table && uma_effect_hooks[i].slot==slot)return uma_effect_hooks[i].native;
 return NULL;
}
static void uma_effect_surface_write(IDirect3DSurface9 *surface){
 IDirect3DTexture9 *parent=NULL;
 if(SUCCEEDED(IDirect3DSurface9_GetContainer(surface,&uma_effect_texture_iid,(void**)&parent)) && parent){IDirect3DTexture9_FreePrivateData(parent,&uma_effect_cache_guid);IDirect3DTexture9_Release(parent);}
}
static HRESULT WINAPI uma_effect_lock(IDirect3DTexture9 *texture,UINT level,D3DLOCKED_RECT *locked,const RECT *rect,DWORD flags){
 UmaEffectLock native=(UmaEffectLock)uma_effect_native(texture,19);if(!native)return D3DERR_INVALIDCALL;
 if(!(flags&D3DLOCK_READONLY))IDirect3DTexture9_FreePrivateData(texture,&uma_effect_cache_guid);
 return native(texture,level,locked,rect,flags);
}
static HRESULT WINAPI uma_effect_surface_lock(IDirect3DSurface9 *surface,D3DLOCKED_RECT *locked,const RECT *rect,DWORD flags){
 UmaEffectSurfaceLock native=(UmaEffectSurfaceLock)uma_effect_native(surface,13);if(!native)return D3DERR_INVALIDCALL;
 if(!(flags&D3DLOCK_READONLY))uma_effect_surface_write(surface);
 return native(surface,locked,rect,flags);
}
static HRESULT WINAPI uma_effect_dc(IDirect3DSurface9 *surface,HDC *dc){
 UmaEffectDC native=(UmaEffectDC)uma_effect_native(surface,15);if(!native)return D3DERR_INVALIDCALL;
 uma_effect_surface_write(surface);return native(surface,dc);
}
static int uma_effect_hook(void *object,UINT slot,void *hook){
 void **table=*(void***)object;
 for(LONG i=0;i<uma_effect_hook_count;i++)if(uma_effect_hooks[i].table==table && uma_effect_hooks[i].slot==slot)return table[slot]==hook;
 if(uma_effect_hook_count==12)return 0;
 DWORD protection;if(!VirtualProtect(table+slot,sizeof(void*),PAGE_READWRITE,&protection))return 0;
 LONG i=uma_effect_hook_count;uma_effect_hooks[i].table=table;uma_effect_hooks[i].slot=slot;uma_effect_hooks[i].native=table[slot];uma_effect_hooks[i].hook=hook;
 InterlockedIncrement(&uma_effect_hook_count);InterlockedExchangePointer(table+slot,hook);
 DWORD ignored;VirtualProtect(table+slot,sizeof(void*),protection,&ignored);return 1;
}
static int uma_effect_watch(IDirect3DTexture9 *texture){
 IDirect3DSurface9 *surface=NULL;if(FAILED(IDirect3DTexture9_GetSurfaceLevel(texture,0,&surface)))return 0;
 int ok=uma_effect_hook(texture,19,(void*)uma_effect_lock) && uma_effect_hook(surface,13,(void*)uma_effect_surface_lock) && uma_effect_hook(surface,15,(void*)uma_effect_dc);
 IDirect3DSurface9_Release(surface);return ok;
}
static inline void uma_effects_remove(void){
 for(LONG i=0;i<uma_effect_hook_count;i++){
  void **slot=uma_effect_hooks[i].table+uma_effect_hooks[i].slot;DWORD protection;
  if(*slot==uma_effect_hooks[i].hook && VirtualProtect(slot,sizeof(void*),PAGE_READWRITE,&protection)){InterlockedExchangePointer(slot,uma_effect_hooks[i].native);DWORD ignored;VirtualProtect(slot,sizeof(void*),protection,&ignored);}
 }
 uma_effect_hook_count=0;
}
static int uma_effect_texture(IDirect3DTexture9 *texture){
 if(!uma_effects_ready)return 0;
 DWORD tag=0,bytes=sizeof(tag);
 if(SUCCEEDED(IDirect3DTexture9_GetPrivateData(texture,&uma_effect_cache_guid,&tag,&bytes)) && bytes==sizeof(tag) && (tag==1 || tag==2)){uma_effect_cache_hits++;return tag==2;}
 D3DSURFACE_DESC desc;if(FAILED(IDirect3DTexture9_GetLevelDesc(texture,0,&desc)))return 0;
 int cache=desc.Pool==D3DPOOL_MANAGED && !(desc.Usage&(D3DUSAGE_DYNAMIC|D3DUSAGE_RENDERTARGET|D3DUSAGE_DEPTHSTENCIL)) && uma_effect_watch(texture),possible=0,match=0;
 for(int i=0;i<8;i++)if(desc.Width==uma_effects[i].width && desc.Height==uma_effects[i].height && desc.Format==uma_effects[i].format)possible=1;
 if(possible){
  D3DLOCKED_RECT locked;uma_effect_reads++;if(FAILED(IDirect3DTexture9_LockRect(texture,0,&locked,NULL,D3DLOCK_READONLY)))return 0;
  UINT row=desc.Width*4,rows=desc.Format==D3DFMT_DXT3?desc.Height/4:desc.Height;
  for(int i=0;i<8 && !match;i++)if(desc.Width==uma_effects[i].width && desc.Height==uma_effects[i].height && desc.Format==uma_effects[i].format){
   int same=locked.Pitch>0 && (UINT)locked.Pitch>=row;
   for(UINT y=0;same && y<rows;y++)if(memcmp((BYTE*)locked.pBits+y*locked.Pitch,uma_effects[i].pixels+y*row,row))same=0;
   if(same)match=1;
  }
  IDirect3DTexture9_UnlockRect(texture,0);
 }
 if(cache){tag=match?2:1;IDirect3DTexture9_SetPrivateData(texture,&uma_effect_cache_guid,&tag,sizeof(tag),0);}return match;
}
static int uma_effect_draw(IDirect3DDevice9 *device){
 IDirect3DBaseTexture9 *base=NULL;if(!uma_effects_ready || FAILED(IDirect3DDevice9_GetTexture(device,0,&base)) || !base)return 0;
 int match=IDirect3DBaseTexture9_GetType(base)==D3DRTYPE_TEXTURE && uma_effect_texture((IDirect3DTexture9*)base);
 IDirect3DBaseTexture9_Release(base);if(match)uma_effects_hidden++;return match;
}
#endif
