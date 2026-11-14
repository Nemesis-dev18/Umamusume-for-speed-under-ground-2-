#define COBJMACROS
#include <windows.h>
#include <d3d9.h>
#include <stdio.h>
#define UMA_LOG_TEST
#include "uma_pipeline_probe.c"

static const DWORD texture_only_shader[]={0xffff0101,0x42,0xb00f0000,0x1,0x800f0000,0xb0e40000,0xffff};
#define CHECK(call) do { HRESULT hr=(call); if(FAILED(hr)){fprintf(stderr,"FAIL %s HRESULT=%08lx\n",#call,(unsigned long)hr); return 1;} } while(0)
struct Vertex {float x,y,z,rhw,u,v;};
int main(void){
 freopen("modding/diagnostics/pipeline-probe-result.txt","w",stdout);freopen("modding/diagnostics/pipeline-probe-errors.txt","w",stderr);
 puts("START standalone Direct3D9 test");fflush(stdout);
 HWND window=CreateWindowA("STATIC","Uma material test",WS_POPUP,0,0,16,16,NULL,NULL,GetModuleHandle(NULL),NULL);
 if(!window){fprintf(stderr,"FAIL window\n");return 1;}
 IDirect3D9 *d3d=Direct3DCreate9(D3D_SDK_VERSION);if(!d3d)return 1;
 D3DPRESENT_PARAMETERS pp={0};pp.Windowed=TRUE;pp.SwapEffect=D3DSWAPEFFECT_DISCARD;pp.hDeviceWindow=window;pp.BackBufferWidth=16;pp.BackBufferHeight=16;pp.BackBufferFormat=D3DFMT_A8R8G8B8;
 IDirect3DDevice9 *device=NULL;
 CHECK(IDirect3D9_CreateDevice(d3d,D3DADAPTER_DEFAULT,D3DDEVTYPE_HAL,window,D3DCREATE_HARDWARE_VERTEXPROCESSING,&pp,&device));
 IDirect3DPixelShader9 *shader=NULL;CHECK(IDirect3DDevice9_CreatePixelShader(device,texture_only_shader,&shader));
 IDirect3DTexture9 *texture=NULL;CHECK(IDirect3DDevice9_CreateTexture(device,2,2,1,0,D3DFMT_A8R8G8B8,D3DPOOL_MANAGED,&texture,NULL));
 D3DLOCKED_RECT locked;CHECK(IDirect3DTexture9_LockRect(texture,0,&locked,NULL,0));
 for(int y=0;y<2;y++)for(int x=0;x<2;x++)*(DWORD*)((BYTE*)locked.pBits+y*locked.Pitch+x*4)=0xffff8040;
 CHECK(IDirect3DTexture9_UnlockRect(texture,0));
 CHECK(IDirect3DDevice9_SetPixelShader(device,shader));CHECK(IDirect3DDevice9_SetTexture(device,0,(IDirect3DBaseTexture9*)texture));
 CHECK(IDirect3DDevice9_SetRenderState(device,D3DRS_CULLMODE,D3DCULL_NONE));CHECK(IDirect3DDevice9_SetRenderState(device,D3DRS_LIGHTING,FALSE));CHECK(IDirect3DDevice9_SetRenderState(device,D3DRS_ZENABLE,FALSE));
 CHECK(IDirect3DDevice9_SetFVF(device,D3DFVF_XYZRHW|D3DFVF_TEX1));
 struct Vertex quad[]={{-.5f,-.5f,0,1,0,0},{15.5f,-.5f,0,1,1,0},{-.5f,15.5f,0,1,0,1},{15.5f,15.5f,0,1,1,1}};
 CHECK(IDirect3DDevice9_Clear(device,0,NULL,D3DCLEAR_TARGET,0xff000000,1,0));CHECK(IDirect3DDevice9_BeginScene(device));
 IDirect3DVertexBuffer9 *vb=NULL;IDirect3DIndexBuffer9 *ib=NULL;void *data=NULL;
 CHECK(IDirect3DDevice9_CreateVertexBuffer(device,sizeof(quad),0,D3DFVF_XYZRHW|D3DFVF_TEX1,D3DPOOL_MANAGED,&vb,NULL));
 CHECK(IDirect3DVertexBuffer9_Lock(vb,0,sizeof(quad),&data,0));CopyMemory(data,quad,sizeof(quad));CHECK(IDirect3DVertexBuffer9_Unlock(vb));
 const WORD indices[]={0,1,2,2,1,3};CHECK(IDirect3DDevice9_CreateIndexBuffer(device,sizeof(indices),0,D3DFMT_INDEX16,D3DPOOL_MANAGED,&ib,NULL));CHECK(IDirect3DIndexBuffer9_Lock(ib,0,sizeof(indices),&data,0));CopyMemory(data,indices,sizeof(indices));CHECK(IDirect3DIndexBuffer9_Unlock(ib));
 CHECK(IDirect3DDevice9_SetStreamSource(device,0,vb,0,sizeof(struct Vertex)));CHECK(IDirect3DDevice9_SetIndices(device,ib));
 /* A diagnostic hook must preserve the original white output and bound shader. */
 static const DWORD white_code[]={0xffff0101,0x51,0xa00f0000,0x3f800000,0x3f800000,0x3f800000,0x3f800000,0x1,0x800f0000,0xa0e40000,0xffff};
 IDirect3DPixelShader9 *white=NULL;CHECK(IDirect3DDevice9_CreatePixelShader(device,white_code,&white));CHECK(IDirect3DDevice9_SetPixelShader(device,white));
 InitializeCriticalSection(&log_lock);draw_log=fopen("modding/diagnostics/pipeline-probe-draw.log","w");if(!draw_log)return 1;
 IDirect3DDevice9 *probe=NULL;CHECK(IDirect3D9_CreateDevice(d3d,D3DADAPTER_DEFAULT,D3DDEVTYPE_HAL,window,D3DCREATE_SOFTWARE_VERTEXPROCESSING,&pp,&probe));
 if(!install_hooks(probe)){fprintf(stderr,"FAIL hook install\n");return 1;}
 const DWORD vertex_code[]={0xfffe0101,20,0xc00f0000,0x90e40000,0xa0e40008,0xffff};
 IDirect3DVertexShader9 *vertex=NULL;CHECK(IDirect3DDevice9_CreateVertexShader(device,vertex_code,&vertex));
 const float constants[4][4]={{.7f,.1f,0,.2f},{0,.6f,.2f,-.1f},{.1f,0,.4f,.3f},{0,0,0,1}};
 CHECK(IDirect3DDevice9_SetVertexShader(device,vertex));CHECK(IDirect3DDevice9_SetVertexShaderConstantF(device,8,&constants[0][0],4));
 if(record_shader(device)!=1 || record_shader(device)!=1 || known_shader_count!=1){fputs("FAIL shader identity/capture\n",stderr);return 1;}
 record_constants(device);
 IDirect3DVertexShader9 *same=NULL;CHECK(IDirect3DDevice9_GetVertexShader(device,&same));if(same!=vertex)return 1;IDirect3DVertexShader9_Release(same);
 DWORD saved_code[6];UINT saved_bytes=sizeof(saved_code);CHECK(IDirect3DVertexShader9_GetFunction(vertex,saved_code,&saved_bytes));if(saved_bytes!=sizeof(vertex_code) || memcmp(saved_code,vertex_code,sizeof(vertex_code)))return 1;
 float saved_constants[4][4];CHECK(IDirect3DDevice9_GetVertexShaderConstantF(device,8,&saved_constants[0][0],4));if(memcmp(saved_constants,constants,sizeof(constants)))return 1;
 DWORD alternate_code[6];memcpy(alternate_code,vertex_code,sizeof(vertex_code));alternate_code[4]=0xa0e40009;
 IDirect3DVertexShader9 *alternate=NULL;CHECK(IDirect3DDevice9_CreateVertexShader(device,alternate_code,&alternate));CHECK(IDirect3DDevice9_SetVertexShader(device,alternate));
 known_shader_count=64;if(record_shader(device)!=~0u || !shader_limit_noted)return 1;known_shader_count=1;IDirect3DVertexShader9_Release(alternate);
 CHECK(IDirect3DDevice9_SetVertexShader(device,NULL));IDirect3DVertexShader9_Release(vertex);
 CHECK(IDirect3DDevice9_DrawIndexedPrimitive(device,D3DPT_TRIANGLELIST,0,0,4,0,2));
 IDirect3DPixelShader9 *restored=NULL;CHECK(IDirect3DDevice9_GetPixelShader(device,&restored));if(restored!=white){fprintf(stderr,"FAIL shader not restored\n");return 1;}IDirect3DPixelShader9_Release(restored);
 CHECK(IDirect3DDevice9_EndScene(device));
 IDirect3DSurface9 *target=NULL,*readback=NULL;CHECK(IDirect3DDevice9_GetRenderTarget(device,0,&target));CHECK(IDirect3DDevice9_CreateOffscreenPlainSurface(device,16,16,D3DFMT_A8R8G8B8,D3DPOOL_SYSTEMMEM,&readback,NULL));
 CHECK(IDirect3DDevice9_GetRenderTargetData(device,target,readback));CHECK(IDirect3DSurface9_LockRect(readback,&locked,NULL,D3DLOCK_READONLY));DWORD pixel=*(DWORD*)((BYTE*)locked.pBits+8*locked.Pitch+8*4);CHECK(IDirect3DSurface9_UnlockRect(readback));
 if(pixel!=0xffffffff){fprintf(stderr,"FAIL output=%08lx expected=ffffffff\n",(unsigned long)pixel);return 1;}
 if(draws!=1 || characters!=1 || pair_count!=1){fprintf(stderr,"FAIL cross-device draw hook counters\n");return 1;}
 CHECK(IDirect3DDevice9_Present(device,NULL,NULL,NULL,NULL));if(frames!=1){fprintf(stderr,"FAIL Present hook\n");return 1;}
 fclose(draw_log);draw_log=fopen("modding/diagnostics/pipeline-limit-test.log","w+");if(!draw_log)return 1;
 if(fseek(draw_log,8*1024*1024,SEEK_SET) || fputc(0,draw_log)==EOF)return 1;
 CHECK(IDirect3DDevice9_BeginScene(device));CHECK(IDirect3DDevice9_DrawIndexedPrimitive(device,D3DPT_TRIANGLELIST,0,0,4,0,2));CHECK(IDirect3DDevice9_EndScene(device));if(draw_log)return 1;
 if(remove("modding/diagnostics/pipeline-limit-test.log"))return 1;
 puts("PASS: GPU vertex shader words, constants, binding unchanged and deduplicated; shader/log limits exercised; hook installed through separate software-processing device observes hardware-processing draw; GPU readback and shader unchanged; Present and candidate metadata exercised.");
 fflush(stdout);if(draw_log)fclose(draw_log);draw_log=NULL;for(UINT i=0;i<known_shader_count;i++)IDirect3DVertexShader9_Release(known_shaders[i]);known_shader_count=0;IDirect3DDevice9_Release(probe);
 IDirect3DSurface9_Release(readback);IDirect3DSurface9_Release(target);IDirect3DTexture9_Release(texture);IDirect3DPixelShader9_Release(shader);IDirect3DDevice9_Release(device);IDirect3D9_Release(d3d);DestroyWindow(window);return 0;
}
