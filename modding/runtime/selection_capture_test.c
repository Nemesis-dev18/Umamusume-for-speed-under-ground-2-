#define COBJMACROS
#include <windows.h>
#include <d3d9.h>
#include <stdio.h>
#include <wchar.h>
#include <string.h>
#include <assert.h>
#include "uma_selection_capture.h"
#define CHECK(x) assert(SUCCEEDED(x))
int main(void){
 CreateDirectoryW(L"modding\\runtime\\selection-test",NULL);wcscpy(uma_selection.folder,L"modding\\runtime\\selection-test");uma_selection.log=fopen("modding/runtime/selection-test/trace.log","w");assert(uma_selection.log);
 HWND window=CreateWindowA("STATIC","Read-only selection trace test",WS_POPUP,0,0,640,480,NULL,NULL,GetModuleHandle(NULL),NULL);assert(window);IDirect3D9 *api=Direct3DCreate9(D3D_SDK_VERSION);assert(api);
 D3DPRESENT_PARAMETERS pp={0};pp.Windowed=TRUE;pp.SwapEffect=D3DSWAPEFFECT_DISCARD;pp.hDeviceWindow=window;pp.BackBufferWidth=640;pp.BackBufferHeight=480;pp.BackBufferFormat=D3DFMT_A8R8G8B8;
 IDirect3DDevice9 *device=NULL;CHECK(IDirect3D9_CreateDevice(api,0,D3DDEVTYPE_HAL,window,D3DCREATE_SOFTWARE_VERTEXPROCESSING,&pp,&device));
 CHECK(IDirect3DDevice9_SetFVF(device,D3DFVF_XYZRHW|D3DFVF_DIFFUSE));CHECK(IDirect3DDevice9_SetRenderState(device,D3DRS_LIGHTING,FALSE));CHECK(IDirect3DDevice9_SetRenderState(device,D3DRS_ZENABLE,FALSE));CHECK(IDirect3DDevice9_SetRenderState(device,D3DRS_CULLMODE,D3DCULL_NONE));
 CHECK(IDirect3DDevice9_SetTextureStageState(device,0,D3DTSS_COLOROP,D3DTOP_SELECTARG1));CHECK(IDirect3DDevice9_SetTextureStageState(device,0,D3DTSS_COLORARG1,D3DTA_DIFFUSE));
 IDirect3DTexture9 *texture=NULL;CHECK(IDirect3DDevice9_CreateTexture(device,16,16,1,0,D3DFMT_A8R8G8B8,D3DPOOL_MANAGED,&texture,NULL));D3DLOCKED_RECT locked;CHECK(IDirect3DTexture9_LockRect(texture,0,&locked,NULL,0));for(UINT y=0;y<16;y++)memset((BYTE*)locked.pBits+y*locked.Pitch,255,16*4);CHECK(IDirect3DTexture9_UnlockRect(texture,0));CHECK(IDirect3DDevice9_SetTexture(device,0,(IDirect3DBaseTexture9*)texture));
 struct {float x,y,z,w;DWORD color;} quad[]={{360,220,.5f,1,0xff000000},{570,220,.5f,1,0xff000000},{360,400,.5f,1,0xff000000},{570,400,.5f,1,0xff000000}};
 CHECK(IDirect3DDevice9_Clear(device,0,NULL,D3DCLEAR_TARGET,0xffa0a0a0,1,0));CHECK(IDirect3DDevice9_BeginScene(device));uma_selection.enabled=uma_selection.armed=1;
 CHECK(IDirect3DDevice9_SetRenderState(device,D3DRS_ZENABLE,TRUE));
 int pending=uma_selection_before(device);assert(pending);CHECK(IDirect3DDevice9_DrawPrimitiveUP(device,D3DPT_TRIANGLESTRIP,2,quad,sizeof(quad[0])));uma_selection_after(device,pending,"DPUP",4,2);assert(uma_selection.best>1000);assert(uma_selection.geometry_best==uma_selection.best);
 assert(GetFileAttributesW(L"modding\\runtime\\selection-test\\geometry-after.ppm")!=INVALID_FILE_ATTRIBUTES);
 assert(GetFileAttributesW(L"modding\\runtime\\selection-test\\geometry-texture-0.dds")!=INVALID_FILE_ATTRIBUTES);
 DWORD after[64*64];assert(uma_selection_read(device,after));unsigned black=0;for(unsigned i=0;i<64*64;i++)black+=uma_selection_dark(after[i]);assert(black==uma_selection.best);
 IDirect3DBaseTexture9 *same=NULL;CHECK(IDirect3DDevice9_GetTexture(device,0,&same));assert(same==(IDirect3DBaseTexture9*)texture);IDirect3DBaseTexture9_Release(same);DWORD color;CHECK(IDirect3DDevice9_GetRenderState(device,D3DRS_COLORWRITEENABLE,&color));assert((color&7)==7);
 CHECK(IDirect3DDevice9_EndScene(device));uma_selection_finish(device,1);assert(uma_selection.done && !uma_selection.armed && !uma_selection.small && !uma_selection.cpu);
 IDirect3DSurface9 *back=NULL,*multi=NULL;CHECK(IDirect3DDevice9_GetRenderTarget(device,0,&back));
 DWORD quality=0;CHECK(IDirect3D9_CheckDeviceMultiSampleType(api,0,D3DDEVTYPE_HAL,D3DFMT_A8R8G8B8,TRUE,D3DMULTISAMPLE_2_SAMPLES,&quality));
 CHECK(IDirect3DDevice9_CreateRenderTarget(device,640,480,D3DFMT_A8R8G8B8,D3DMULTISAMPLE_2_SAMPLES,0,FALSE,&multi,NULL));CHECK(IDirect3DDevice9_SetRenderTarget(device,0,multi));
 CHECK(IDirect3DDevice9_Clear(device,0,NULL,D3DCLEAR_TARGET,0xffa0a0a0,1,0));CHECK(IDirect3DDevice9_BeginScene(device));CHECK(IDirect3DDevice9_DrawPrimitiveUP(device,D3DPT_TRIANGLESTRIP,2,quad,sizeof(quad[0])));assert(uma_selection_read(device,after));CHECK(IDirect3DDevice9_EndScene(device));
 black=0;for(unsigned i=0;i<64*64;i++)black+=uma_selection_dark(after[i]);assert(black>1000);IDirect3DSurface9 *bound=NULL;CHECK(IDirect3DDevice9_GetRenderTarget(device,0,&bound));assert(bound==multi);IDirect3DSurface9_Release(bound);
 CHECK(IDirect3DDevice9_SetRenderTarget(device,0,back));IDirect3DSurface9_Release(back);IDirect3DSurface9_Release(multi);uma_selection_release();
 puts("PASS multisample color resolve inside scene preserves the original render target");
 CHECK(IDirect3DDevice9_SetTexture(device,0,NULL));IDirect3DTexture9_Release(texture);CHECK(IDirect3DDevice9_Reset(device,&pp));IDirect3DDevice9_Release(device);IDirect3D9_Release(api);DestroyWindow(window);
 puts("PASS one-frame ROI readback inside scene, exact black-pixel attribution, texture binding/color state unchanged, DDS dump and Reset; no game capture yet");return 0;
}
