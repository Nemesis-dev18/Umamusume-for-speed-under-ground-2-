#include "uma_d3d.h"
#include <assert.h>
#define CHECK(call) do{HRESULT hr=(call);if(FAILED(hr)){fprintf(stderr,"FAIL %s: %08lx\n",#call,(unsigned long)hr);return 1;}}while(0)
static UmaDrawIndexed native_draw;static UINT draws;static int fail_draw;
static HRESULT WINAPI observed_draw(IDirect3DDevice9 *d,D3DPRIMITIVETYPE t,INT b,UINT m,UINT v,UINT s,UINT n){draws++;return fail_draw?E_FAIL:native_draw(d,t,b,m,v,s,n);}
struct Quad {float x,y,z,rhw,u,v;};
static DWORD *read_pixels(IDirect3DDevice9 *device){
 IDirect3DSurface9 *target=NULL,*copy=NULL;D3DLOCKED_RECT locked;
 assert(SUCCEEDED(IDirect3DDevice9_GetRenderTarget(device,0,&target)));
 assert(SUCCEEDED(IDirect3DDevice9_CreateOffscreenPlainSurface(device,640,480,D3DFMT_A8R8G8B8,D3DPOOL_SYSTEMMEM,&copy,NULL)));
 assert(SUCCEEDED(IDirect3DDevice9_GetRenderTargetData(device,target,copy)));
 assert(SUCCEEDED(IDirect3DSurface9_LockRect(copy,&locked,NULL,D3DLOCK_READONLY)));
 DWORD *pixels=malloc(640*480*4);assert(pixels);
 for(int row=0;row<480;row++)memcpy(pixels+row*640,(BYTE*)locked.pBits+(size_t)row*locked.Pitch,640*4);
 assert(SUCCEEDED(IDirect3DSurface9_UnlockRect(copy)));IDirect3DSurface9_Release(copy);IDirect3DSurface9_Release(target);return pixels;
}
static void save_ppm(const char *path,const DWORD *pixels){
 FILE *out=fopen(path,"wb");assert(out);fputs("P6\n640 480\n255\n",out);
 for(int i=0;i<640*480;i++){unsigned char rgb[]={(unsigned char)(pixels[i]>>16),(unsigned char)(pixels[i]>>8),(unsigned char)pixels[i]};assert(fwrite(rgb,1,3,out)==3);}fclose(out);
}
static void check_restored(IDirect3DDevice9 *d,IDirect3DPixelShader9 *shader,IDirect3DVertexBuffer9 *vb,IDirect3DIndexBuffer9 *ib,const D3DMATRIX *world){
 DWORD value;assert(SUCCEEDED(IDirect3DDevice9_GetFVF(d,&value)));assert(value==(D3DFVF_XYZRHW|D3DFVF_TEX1));
 assert(SUCCEEDED(IDirect3DDevice9_GetRenderState(d,D3DRS_ALPHABLENDENABLE,&value)));assert(value==TRUE);
 assert(SUCCEEDED(IDirect3DDevice9_GetRenderState(d,D3DRS_ALPHATESTENABLE,&value)));assert(value==FALSE);
 assert(SUCCEEDED(IDirect3DDevice9_GetRenderState(d,D3DRS_ZENABLE,&value)));assert(value==FALSE);
 assert(SUCCEEDED(IDirect3DDevice9_GetRenderState(d,D3DRS_COLORWRITEENABLE,&value)));assert(value==15);
 assert(SUCCEEDED(IDirect3DDevice9_GetSamplerState(d,0,D3DSAMP_MINFILTER,&value)));assert(value==D3DTEXF_POINT);
 IDirect3DPixelShader9 *ps=NULL;assert(SUCCEEDED(IDirect3DDevice9_GetPixelShader(d,&ps)));assert(ps==shader);IDirect3DPixelShader9_Release(ps);
 IDirect3DVertexBuffer9 *v=NULL;UINT offset,stride;assert(SUCCEEDED(IDirect3DDevice9_GetStreamSource(d,0,&v,&offset,&stride)));assert(v==vb && stride==sizeof(struct Quad) && offset==0);IDirect3DVertexBuffer9_Release(v);
 IDirect3DIndexBuffer9 *i=NULL;assert(SUCCEEDED(IDirect3DDevice9_GetIndices(d,&i)));assert(i==ib);IDirect3DIndexBuffer9_Release(i);
 D3DMATRIX restored;assert(SUCCEEDED(IDirect3DDevice9_GetTransform(d,D3DTS_WORLD,&restored)));assert(!memcmp(world,&restored,sizeof(restored)));
}
static void check_invalid_textures(IDirect3DDevice9 *device){
 FILE *source=fopen("modding/runtime/atlas.dds","rb");assert(source);
 assert(!fseek(source,0,SEEK_END));long length=ftell(source);assert(length>128);rewind(source);
 unsigned char *bytes=malloc((size_t)length);assert(bytes);assert(fread(bytes,1,(size_t)length,source)==(size_t)length);fclose(source);
 for(int kind=0;kind<7;kind++){
  unsigned char saved[128];memcpy(saved,bytes,128);size_t size=(size_t)length;
  if(kind==0)bytes[0]='X';
  if(kind==1)bytes[17]=3;
  if(kind==2)bytes[28]=1;
  if(kind==3)bytes[84]='X';
  if(kind==4)bytes[112]=1;
  if(kind==5)size--;
  FILE *bad=tmpfile();assert(bad);assert(fwrite(bytes,1,size,bad)==size);
  if(kind==6)assert(fputc(0,bad)!=EOF);
  rewind(bad);IDirect3DTexture9 *output=NULL;assert(FAILED(uma_texture_load(device,bad,&output)));assert(output==NULL);fclose(bad);memcpy(bytes,saved,128);
 }
 free(bytes);puts("PASS seven invalid DDS inputs rejected without publishing a texture");
}
int main(void){
 freopen("modding/runtime/gpu-test/result.txt","w",stdout);freopen("modding/runtime/gpu-test/errors.txt","w",stderr);
 puts("START independent renderer test; not NFSU2");fflush(stdout);
 FILE *input=fopen("modding/runtime/kitasan.umab","rb");assert(input);UmaMotion motion={0};assert(uma_motion_load(input,&motion));fclose(input);
 HWND window=CreateWindowA("STATIC","Independent Kitasan renderer test",WS_POPUP,0,0,640,480,NULL,NULL,GetModuleHandle(NULL),NULL);assert(window);
 IDirect3D9 *api=Direct3DCreate9(D3D_SDK_VERSION);assert(api);
 D3DPRESENT_PARAMETERS pp={0};pp.Windowed=TRUE;pp.SwapEffect=D3DSWAPEFFECT_DISCARD;pp.hDeviceWindow=window;pp.BackBufferWidth=640;pp.BackBufferHeight=480;pp.BackBufferFormat=D3DFMT_A8R8G8B8;pp.EnableAutoDepthStencil=TRUE;pp.AutoDepthStencilFormat=D3DFMT_D24S8;
 IDirect3DDevice9 *device=NULL;CHECK(IDirect3D9_CreateDevice(api,0,D3DDEVTYPE_HAL,window,D3DCREATE_HARDWARE_VERTEXPROCESSING,&pp,&device));native_draw=(UmaDrawIndexed)(*(void***)device)[82];
 check_invalid_textures(device);
 struct Quad q[]={{-.5f,-.5f,0,1,0,0},{15.5f,-.5f,0,1,1,0},{-.5f,15.5f,0,1,0,1},{15.5f,15.5f,0,1,1,1}};const WORD indices[]={0,1,2,2,1,3};void *mapped=NULL;
 IDirect3DVertexBuffer9 *vb=NULL;IDirect3DIndexBuffer9 *ib=NULL;
 CHECK(IDirect3DDevice9_CreateVertexBuffer(device,sizeof(q),0,D3DFVF_XYZRHW|D3DFVF_TEX1,D3DPOOL_MANAGED,&vb,NULL));CHECK(IDirect3DVertexBuffer9_Lock(vb,0,sizeof(q),&mapped,0));memcpy(mapped,q,sizeof(q));CHECK(IDirect3DVertexBuffer9_Unlock(vb));
 CHECK(IDirect3DDevice9_CreateIndexBuffer(device,sizeof(indices),0,D3DFMT_INDEX16,D3DPOOL_MANAGED,&ib,NULL));CHECK(IDirect3DIndexBuffer9_Lock(ib,0,sizeof(indices),&mapped,0));memcpy(mapped,indices,sizeof(indices));CHECK(IDirect3DIndexBuffer9_Unlock(ib));
 const DWORD white_code[]={0xffff0101,0x51,0xa00f0000,0x3f800000,0x3f800000,0x3f800000,0x3f800000,0x1,0x800f0000,0xa0e40000,0xffff};IDirect3DPixelShader9 *white=NULL;CHECK(IDirect3DDevice9_CreatePixelShader(device,white_code,&white));
 D3DMATRIX original={0};for(int k=0;k<4;k++)original.m[k][k]=1;original.m[3][0]=.123f;
 CHECK(IDirect3DDevice9_SetTransform(device,D3DTS_WORLD,&original));CHECK(IDirect3DDevice9_SetFVF(device,D3DFVF_XYZRHW|D3DFVF_TEX1));CHECK(IDirect3DDevice9_SetStreamSource(device,0,vb,0,sizeof(q[0])));CHECK(IDirect3DDevice9_SetIndices(device,ib));CHECK(IDirect3DDevice9_SetPixelShader(device,white));
 CHECK(IDirect3DDevice9_SetRenderState(device,D3DRS_ALPHABLENDENABLE,TRUE));CHECK(IDirect3DDevice9_SetRenderState(device,D3DRS_SRCBLEND,D3DBLEND_SRCALPHA));CHECK(IDirect3DDevice9_SetRenderState(device,D3DRS_DESTBLEND,D3DBLEND_INVSRCALPHA));CHECK(IDirect3DDevice9_SetRenderState(device,D3DRS_ALPHATESTENABLE,FALSE));CHECK(IDirect3DDevice9_SetRenderState(device,D3DRS_ZENABLE,FALSE));CHECK(IDirect3DDevice9_SetRenderState(device,D3DRS_CULLMODE,D3DCULL_NONE));CHECK(IDirect3DDevice9_SetRenderState(device,D3DRS_LIGHTING,FALSE));CHECK(IDirect3DDevice9_SetRenderState(device,D3DRS_COLORWRITEENABLE,15));CHECK(IDirect3DDevice9_SetSamplerState(device,0,D3DSAMP_MINFILTER,D3DTEXF_POINT));
 D3DMATRIX combined={0};combined.m[1][0]=.6f;combined.m[2][1]=.8f;combined.m[0][2]=-.1f;combined.m[3][1]=-.85f;combined.m[3][2]=.5f;combined.m[3][3]=1;
 const char *textures[]={"modding/runtime/gpu-test/half-alpha.dds","modding/runtime/gpu-test/zero-alpha.dds","modding/runtime/atlas.dds"};UmaD3D renderer={0};UmaMotionState state={0};DWORD previous_hash=0;
 for(int kind=0;kind<3;kind++){
  FILE *tex=fopen(textures[kind],"rb");assert(tex);CHECK(uma_d3d_open(&renderer,device,&motion,tex,observed_draw));fclose(tex);
  for(int frame=0;frame<(kind==2?4:1);frame++){
   state.idle_phase=0;state.run_phase=frame*.25f;state.run_blend=kind==2?1:0;
   CHECK(IDirect3DDevice9_Clear(device,0,NULL,D3DCLEAR_TARGET|D3DCLEAR_ZBUFFER,0xff252a32,1,0));CHECK(IDirect3DDevice9_BeginScene(device));CHECK(uma_d3d_draw(&renderer,&state,&combined));check_restored(device,white,vb,ib,&original);
   CHECK(IDirect3DDevice9_DrawIndexedPrimitive(device,D3DPT_TRIANGLELIST,0,0,4,0,2));CHECK(IDirect3DDevice9_EndScene(device));
   DWORD *pixels=read_pixels(device);assert(pixels[8*640+8]==0xffffffff);UINT different=0,orange=0;DWORD hash=2166136261u;
   for(int y=20;y<480;y++)for(int x=0;x<640;x++){DWORD p=pixels[y*640+x];if(p!=0xff252a32)different++;if(p==0xffff8040)orange++;hash=(hash^p)*16777619u;}
   if(kind==0){assert(orange>1000 && orange==different);puts("PASS half-alpha texture produces opaque RGB without background blending");}
   if(kind==1){assert(different==0);puts("PASS zero-alpha texture is discarded");}
   if(kind==2){assert(different>1000);if(frame)assert(hash!=previous_hash);previous_hash=hash;char path[128];snprintf(path,sizeof(path),"modding/runtime/gpu-test/run-%d.ppm",frame);save_ppm(path,pixels);printf("PASS animated frame %d; %u non-background pixels; unrelated quad remains white\n",frame,different);}
   free(pixels);
  }
  fail_draw=1;CHECK(IDirect3DDevice9_BeginScene(device));assert(uma_d3d_draw(&renderer,&state,&combined)==E_FAIL);check_restored(device,white,vb,ib,&original);CHECK(IDirect3DDevice9_EndScene(device));fail_draw=0;
  uma_d3d_close(&renderer);
 }
 CHECK(IDirect3DDevice9_Reset(device,&pp));input=fopen("modding/runtime/atlas.dds","rb");assert(input);CHECK(uma_d3d_open(&renderer,device,&motion,input,observed_draw));fclose(input);CHECK(IDirect3DDevice9_BeginScene(device));CHECK(uma_d3d_draw(&renderer,&state,&combined));CHECK(IDirect3DDevice9_EndScene(device));uma_d3d_close(&renderer);
 assert(uma_motion_step(&state,1.f/60,6,0));uma_motion_free(&motion);IDirect3DVertexBuffer9_Release(vb);IDirect3DIndexBuffer9_Release(ib);IDirect3DPixelShader9_Release(white);IDirect3DDevice9_Release(device);IDirect3D9_Release(api);DestroyWindow(window);
 printf("PASS all renderer checks, failure restoration and device reset; %u intercepted draws. No game integration tested.\n",draws);return 0;
}
