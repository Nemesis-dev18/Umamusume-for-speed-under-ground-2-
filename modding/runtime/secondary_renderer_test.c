#include "uma_d3d.h"
#include "uma_secondary.h"
#include <assert.h>
#include <time.h>
#define CHECK(call) do{HRESULT hr=(call);if(FAILED(hr)){fprintf(stderr,"FAIL %s: %08lx\n",#call,(unsigned long)hr);return 1;}}while(0)
static DWORD *pixels(IDirect3DDevice9 *device){
 IDirect3DSurface9 *target=NULL,*copy=NULL;D3DLOCKED_RECT rect;
 assert(SUCCEEDED(IDirect3DDevice9_GetRenderTarget(device,0,&target)));
 assert(SUCCEEDED(IDirect3DDevice9_CreateOffscreenPlainSurface(device,640,800,D3DFMT_A8R8G8B8,D3DPOOL_SYSTEMMEM,&copy,NULL)));
 assert(SUCCEEDED(IDirect3DDevice9_GetRenderTargetData(device,target,copy)));assert(SUCCEEDED(IDirect3DSurface9_LockRect(copy,&rect,NULL,D3DLOCK_READONLY)));
 DWORD *result=malloc(640*800*4);assert(result);for(int row=0;row<800;row++)memcpy(result+row*640,(BYTE*)rect.pBits+(size_t)row*rect.Pitch,640*4);
 assert(SUCCEEDED(IDirect3DSurface9_UnlockRect(copy)));IDirect3DSurface9_Release(copy);IDirect3DSurface9_Release(target);return result;
}
int main(void){
 HWND window=CreateWindowA("STATIC","Native fleet renderer verification",WS_OVERLAPPEDWINDOW,0,0,640,800,NULL,NULL,GetModuleHandle(NULL),NULL);assert(window);
 IDirect3D9 *api=Direct3DCreate9(D3D_SDK_VERSION);assert(api);D3DPRESENT_PARAMETERS pp={0};pp.Windowed=TRUE;pp.SwapEffect=D3DSWAPEFFECT_DISCARD;pp.hDeviceWindow=window;pp.BackBufferWidth=640;pp.BackBufferHeight=800;pp.BackBufferFormat=D3DFMT_A8R8G8B8;pp.EnableAutoDepthStencil=TRUE;pp.AutoDepthStencilFormat=D3DFMT_D24S8;
 IDirect3DDevice9 *device=NULL;CHECK(IDirect3D9_CreateDevice(api,0,D3DDEVTYPE_HAL,window,D3DCREATE_HARDWARE_VERTEXPROCESSING,&pp,&device));UmaDrawIndexed draw=(UmaDrawIndexed)(*(void***)device)[82];
 const int ids[]={1068,1052,1032,1062,1015,1006,1058};FILE *report=fopen("modding/runtime/secondary-gpu/result.txt","w");assert(report);
 for(unsigned c=0;c<sizeof(ids)/sizeof(ids[0]);c++){
  char path[256];snprintf(path,sizeof(path),"modding/staged-runtime/fleet-secondary/%d/model-atlas.umab",ids[c]);FILE *f=fopen(path,"rb");assert(f);UmaMotion asset={0};assert(uma_motion_load(f,&asset));fclose(f);
  snprintf(path,sizeof(path),"modding/staged-runtime/fleet-secondary/%d/atlas.dds",ids[c]);f=fopen(path,"rb");assert(f);UmaD3D renderer={0};CHECK(uma_d3d_open(&renderer,device,&asset,f,draw));fclose(f);
  UmaSecondary *cloth=calloc(1,sizeof(*cloth));UmaSecondaryState *spring=calloc(1,sizeof(*spring));assert(cloth && spring);snprintf(path,sizeof(path),"modding/staged-runtime/fleet-secondary/%d/secondary.bin",ids[c]);f=fopen(path,"rb");assert(f && uma_secondary_load(f,&asset,cloth));fclose(f);asset.secondary_mask=cloth->mask;
  D3DMATRIX combined={0};combined.m[1][0]=.85f;combined.m[2][1]=.85f;combined.m[0][2]=-.1f;combined.m[3][1]=-.85f;combined.m[3][2]=.5f;combined.m[3][3]=1;
  for(int frame=0;frame<4;frame++){
   UmaMotionState state={0,frame==0?0:frame*.25f,frame?1:0};float acceleration[3]={-12,0,0};for(int step=0;step<120;step++)assert(uma_secondary_step(cloth,spring,&asset,&state,1.f/120,frame?8:0,acceleration));renderer.secondary=spring->rotation;renderer.secondary_revision=spring->revision;CHECK(IDirect3DDevice9_Clear(device,0,NULL,D3DCLEAR_TARGET|D3DCLEAR_ZBUFFER,0xff252a32,frame==3?0:1,0));CHECK(IDirect3DDevice9_BeginScene(device));CHECK(uma_d3d_draw(&renderer,&state,&combined,-1,NULL));CHECK(IDirect3DDevice9_EndScene(device));
   DWORD *image=pixels(device);unsigned changed=0;for(int i=0;i<640*800;i++)if(image[i]!=0xff252a32)changed++;
   if(frame==3)assert(changed==0);else{
    assert(changed>5000);snprintf(path,sizeof(path),"modding/runtime/secondary-gpu/%d-%d.ppm",ids[c],frame);f=fopen(path,"wb");assert(f);fputs("P6\n640 800\n255\n",f);for(int i=0;i<640*800;i++){unsigned char rgb[]={(unsigned char)(image[i]>>16),(unsigned char)(image[i]>>8),(unsigned char)image[i]};assert(fwrite(rgb,1,3,f)==3);}fclose(f);
   }
   free(image);
  }
  UmaVertex *sample=malloc((size_t)asset.vertices*36);assert(sample);clock_t begin=clock();for(int n=0;n<100;n++)assert(uma_motion_sample(&asset,0,n/100.f,1,sample,(size_t)asset.vertices*36));double ms=(double)(clock()-begin)*1000/CLOCKS_PER_SEC/100;free(sample);
  fprintf(report,"PASS id=%d vertices=%u bones=%u; idle/run visible; full depth occlusion; CPU skin %.3f ms\n",ids[c],asset.vertices,asset.bones,ms);fflush(report);uma_d3d_close(&renderer);free(cloth);free(spring);uma_motion_free(&asset);
 }
 fclose(report);IDirect3DDevice9_Release(device);IDirect3D9_Release(api);DestroyWindow(window);return 0;
}
