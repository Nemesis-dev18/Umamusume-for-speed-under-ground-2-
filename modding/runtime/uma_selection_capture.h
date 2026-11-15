#ifndef UMA_SELECTION_CAPTURE_H
#define UMA_SELECTION_CAPTURE_H
/* One requested frame only: identify which draw adds the black selection artifact. */
typedef struct {int enabled,armed,done;unsigned seen,draws,best,geometry_best;IDirect3DSurface9 *small,*cpu,*resolved;UINT resolved_width,resolved_height;D3DFORMAT format;FILE *log;WCHAR folder[4096];DWORD before[64*64];} UmaSelectionCapture;
static UmaSelectionCapture uma_selection;
static inline void uma_selection_release(void){if(uma_selection.small)IDirect3DSurface9_Release(uma_selection.small);if(uma_selection.cpu)IDirect3DSurface9_Release(uma_selection.cpu);if(uma_selection.resolved)IDirect3DSurface9_Release(uma_selection.resolved);uma_selection.small=uma_selection.cpu=uma_selection.resolved=NULL;}
static inline void uma_selection_ppm(const WCHAR *name,const DWORD *pixels,UINT width,UINT height){
 WCHAR path[4096];if(wcslen(uma_selection.folder)>3900)return;swprintf(path,4096,L"%ls\\%ls",uma_selection.folder,name);FILE *file=_wfopen(path,L"wb");if(!file)return;
 fprintf(file,"P6\n%u %u\n255\n",width,height);for(UINT i=0;i<width*height;i++){BYTE rgb[3]={(BYTE)(pixels[i]>>16),(BYTE)(pixels[i]>>8),(BYTE)pixels[i]};fwrite(rgb,1,3,file);}fclose(file);
}
static inline int uma_selection_read(IDirect3DDevice9 *device,DWORD *pixels){
 IDirect3DSurface9 *source=NULL;D3DSURFACE_DESC desc;if(FAILED(IDirect3DDevice9_GetRenderTarget(device,0,&source)) || !source)return 0;
 HRESULT result=IDirect3DSurface9_GetDesc(source,&desc);
 if(SUCCEEDED(result) && uma_selection.log){
  static D3DSURFACE_DESC seen[32];static unsigned count;int known=0;
  for(unsigned i=0;i<count;i++)if(seen[i].Width==desc.Width && seen[i].Height==desc.Height && seen[i].Format==desc.Format && seen[i].MultiSampleType==desc.MultiSampleType)known=1;
  if(!known && count<32){seen[count++]=desc;fprintf(uma_selection.log,"TARGET width=%u height=%u format=%u multisample=%u\n",desc.Width,desc.Height,desc.Format,desc.MultiSampleType);fflush(uma_selection.log);}
 }
 if(FAILED(result) || desc.Width<640 || desc.Height<480 || (desc.Format!=D3DFMT_A8R8G8B8 && desc.Format!=D3DFMT_X8R8G8B8)){IDirect3DSurface9_Release(source);return 0;}
 if(uma_selection.small && uma_selection.format!=desc.Format)uma_selection_release();
 if(!uma_selection.small){
  result=IDirect3DDevice9_CreateRenderTarget(device,64,64,desc.Format,D3DMULTISAMPLE_NONE,0,FALSE,&uma_selection.small,NULL);
  if(SUCCEEDED(result))result=IDirect3DDevice9_CreateOffscreenPlainSurface(device,64,64,desc.Format,D3DPOOL_SYSTEMMEM,&uma_selection.cpu,NULL);
  if(FAILED(result)){uma_selection_release();IDirect3DSurface9_Release(source);return 0;}uma_selection.format=desc.Format;
 }
 if(desc.MultiSampleType!=D3DMULTISAMPLE_NONE){
  if(uma_selection.resolved && (uma_selection.resolved_width!=desc.Width || uma_selection.resolved_height!=desc.Height)){IDirect3DSurface9_Release(uma_selection.resolved);uma_selection.resolved=NULL;}
  if(!uma_selection.resolved){result=IDirect3DDevice9_CreateRenderTarget(device,desc.Width,desc.Height,desc.Format,D3DMULTISAMPLE_NONE,0,FALSE,&uma_selection.resolved,NULL);uma_selection.resolved_width=desc.Width;uma_selection.resolved_height=desc.Height;}
  if(SUCCEEDED(result))result=IDirect3DDevice9_StretchRect(device,source,NULL,uma_selection.resolved,NULL,D3DTEXF_NONE);
  IDirect3DSurface9_Release(source);source=uma_selection.resolved;if(FAILED(result) || !source)return 0;IDirect3DSurface9_AddRef(source);
 }
 RECT rect={(LONG)(desc.Width*.55f),(LONG)(desc.Height*.45f),(LONG)(desc.Width*.9f),(LONG)(desc.Height*.85f)};
 result=IDirect3DDevice9_StretchRect(device,source,&rect,uma_selection.small,NULL,D3DTEXF_POINT);IDirect3DSurface9_Release(source);
 if(SUCCEEDED(result))result=IDirect3DDevice9_GetRenderTargetData(device,uma_selection.small,uma_selection.cpu);
 D3DLOCKED_RECT locked;if(FAILED(result) || FAILED(IDirect3DSurface9_LockRect(uma_selection.cpu,&locked,NULL,D3DLOCK_READONLY)))return 0;
 for(UINT y=0;y<64;y++)memcpy(pixels+y*64,(BYTE*)locked.pBits+y*locked.Pitch,64*4);
 IDirect3DSurface9_UnlockRect(uma_selection.cpu);return 1;
}
static inline void uma_selection_texture(IDirect3DDevice9 *device,UINT sampler,const WCHAR *prefix){
 WCHAR path[4096];swprintf(path,4096,L"%ls\\%ls-texture-%u.dds",uma_selection.folder,prefix,sampler);DeleteFileW(path);
 IDirect3DBaseTexture9 *base=NULL;if(FAILED(IDirect3DDevice9_GetTexture(device,sampler,&base)) || !base)return;
 if(IDirect3DBaseTexture9_GetType(base)==D3DRTYPE_TEXTURE){
  IDirect3DTexture9 *texture=(IDirect3DTexture9*)base;D3DSURFACE_DESC desc;D3DLOCKED_RECT locked;
  if(SUCCEEDED(IDirect3DTexture9_GetLevelDesc(texture,0,&desc)) && desc.Width<=4096 && desc.Height<=4096 && SUCCEEDED(IDirect3DTexture9_LockRect(texture,0,&locked,NULL,D3DLOCK_READONLY))){
   UINT rows=desc.Height,row_bytes=desc.Width*4;DWORD header[32]={0};header[0]=0x20534444;header[1]=124;header[2]=0x1007;header[3]=desc.Height;header[4]=desc.Width;header[19]=32;header[27]=0x1000;
   int supported=1;
   if(desc.Format==D3DFMT_DXT1 || desc.Format==D3DFMT_DXT3 || desc.Format==D3DFMT_DXT5){rows=(desc.Height+3)/4;row_bytes=((desc.Width+3)/4)*(desc.Format==D3DFMT_DXT1?8:16);header[2]|=0x80000;header[5]=rows*row_bytes;header[20]=4;header[21]=desc.Format;}
   else if(desc.Format==D3DFMT_A8R8G8B8 || desc.Format==D3DFMT_X8R8G8B8){header[2]|=8;header[5]=row_bytes;header[20]=desc.Format==D3DFMT_A8R8G8B8?0x41:0x40;header[22]=32;header[23]=0xff0000;header[24]=0xff00;header[25]=0xff;header[26]=desc.Format==D3DFMT_A8R8G8B8?0xff000000:0;}
   else supported=0;
   if(supported && locked.Pitch>0 && (UINT)locked.Pitch>=row_bytes){FILE *file=_wfopen(path,L"wb");if(file){fwrite(header,1,128,file);for(UINT y=0;y<rows;y++)fwrite((BYTE*)locked.pBits+y*locked.Pitch,1,row_bytes,file);fclose(file);}}
   IDirect3DTexture9_UnlockRect(texture,0);
  }
 }
 IDirect3DBaseTexture9_Release(base);
}
static inline int uma_selection_before(IDirect3DDevice9 *device){return uma_selection.armed && uma_selection.draws<4096 && uma_selection_read(device,uma_selection.before);}
static inline int uma_selection_dark(DWORD p){return (p&255)<8 && ((p>>8)&255)<8 && ((p>>16)&255)<8;}
static inline void uma_selection_after(IDirect3DDevice9 *device,int pending,const char *method,UINT vertices,UINT primitives){
 if(!pending)return;
 DWORD pixels[64*64];uma_selection.draws++;if(!uma_selection_read(device,pixels))return;
 unsigned gain=0,lost=0;for(UINT i=0;i<64*64;i++){int a=uma_selection_dark(uma_selection.before[i]),b=uma_selection_dark(pixels[i]);if(b&&!a)gain++;if(a&&!b)lost++;}
 if(gain>4 && uma_selection.log){
  IDirect3DVertexBuffer9 *vb=NULL;UINT offset=0,stride=0;IDirect3DDevice9_GetStreamSource(device,0,&vb,&offset,&stride);if(vb)IDirect3DVertexBuffer9_Release(vb);
  IDirect3DVertexShader9 *shader=NULL;UINT bytes=0;IDirect3DDevice9_GetVertexShader(device,&shader);if(shader){IDirect3DVertexShader9_GetFunction(shader,NULL,&bytes);IDirect3DVertexShader9_Release(shader);}
  fprintf(uma_selection.log,"DRAW number=%u method=%s vertices=%u primitives=%u blackGain=%u blackLost=%u shaderBytes=%u stride=%u offset=%u\n",uma_selection.draws,method,vertices,primitives,gain,lost,bytes,stride,offset);fflush(uma_selection.log);
 }
 DWORD depth=0;
 if(gain>uma_selection.geometry_best && SUCCEEDED(IDirect3DDevice9_GetRenderState(device,D3DRS_ZENABLE,&depth)) && depth){
  uma_selection.geometry_best=gain;uma_selection_ppm(L"geometry-before.ppm",uma_selection.before,64,64);uma_selection_ppm(L"geometry-after.ppm",pixels,64,64);uma_selection_texture(device,0,L"geometry");uma_selection_texture(device,1,L"geometry");
  if(uma_selection.log){fprintf(uma_selection.log,"GEOMETRY bestDraw=%u blackGain=%u\n",uma_selection.draws,gain);fflush(uma_selection.log);}
 }
 if(gain>uma_selection.best){uma_selection.best=gain;uma_selection_ppm(L"before.ppm",uma_selection.before,64,64);uma_selection_ppm(L"after.ppm",pixels,64,64);uma_selection_texture(device,0,L"top");uma_selection_texture(device,1,L"top");}
}
static inline void uma_selection_finish(IDirect3DDevice9 *device,unsigned bodies){
 if(!uma_selection.enabled || uma_selection.done)return;
 if(uma_selection.armed){
  DWORD pixels[64*64];if(uma_selection_read(device,pixels))uma_selection_ppm(L"final-region.ppm",pixels,64,64);
  if(uma_selection.log){fprintf(uma_selection.log,"DONE draws=%u largestBlackGain=%u\n",uma_selection.draws,uma_selection.best);fclose(uma_selection.log);uma_selection.log=NULL;}
  uma_selection.armed=0;uma_selection.done=1;uma_selection_release();return;
 }
 if(bodies>0 && bodies<=2 && ++uma_selection.seen>=30)uma_selection.armed=1;
}
#endif
