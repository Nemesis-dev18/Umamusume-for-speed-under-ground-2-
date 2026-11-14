#define UMA_RUNNER_TEST
#include "uma_runner.c"
#define main renderer_component_main
#include "renderer_test.c"
#undef main
int main(void){
 freopen("modding/runtime/integration-test/result.txt","w",stdout);freopen("modding/runtime/integration-test/errors.txt","w",stderr);
 FILE *asset=fopen("modding/runtime/kitasan.umab","rb");assert(asset);assert(uma_motion_load(asset,&runner_motion));fclose(asset);
 InitializeCriticalSection(&runner_lock);runner_log=fopen("modding/runtime/integration-test/runner.log","w");assert(runner_log);wcscpy(runner_atlas,L"modding\\runtime\\atlas.dds");
 HWND window=CreateWindowA("STATIC","Independent runtime routing test",WS_POPUP,0,0,640,480,NULL,NULL,GetModuleHandle(NULL),NULL);assert(window);IDirect3D9 *api=Direct3DCreate9(D3D_SDK_VERSION);assert(api);
 D3DPRESENT_PARAMETERS pp={0};pp.Windowed=TRUE;pp.SwapEffect=D3DSWAPEFFECT_DISCARD;pp.hDeviceWindow=window;pp.BackBufferWidth=640;pp.BackBufferHeight=480;pp.BackBufferFormat=D3DFMT_A8R8G8B8;pp.EnableAutoDepthStencil=TRUE;pp.AutoDepthStencilFormat=D3DFMT_D24S8;
 IDirect3DDevice9 *device=NULL;CHECK(IDirect3D9_CreateDevice(api,0,D3DDEVTYPE_HAL,window,D3DCREATE_HARDWARE_VERTEXPROCESSING,&pp,&device));IDirect3DDevice9 *bootstrap=NULL;D3DPRESENT_PARAMETERS init=pp;init.EnableAutoDepthStencil=FALSE;CHECK(IDirect3D9_CreateDevice(api,0,D3DDEVTYPE_HAL,window,D3DCREATE_SOFTWARE_VERTEXPROCESSING,&init,&bootstrap));assert(runner_install(bootstrap));IDirect3DDevice9_Release(bootstrap);
 IDirect3DVertexBuffer9 *vb=NULL,*other=NULL;UINT bytes=runner_motion.vertices*36;void *mapped=NULL;
 CHECK(IDirect3DDevice9_CreateVertexBuffer(device,bytes+72,D3DUSAGE_DYNAMIC|D3DUSAGE_WRITEONLY,0,D3DPOOL_DEFAULT,&vb,NULL));CHECK(IDirect3DVertexBuffer9_Lock(vb,0,0,&mapped,D3DLOCK_DISCARD));memset(mapped,0,bytes+72);memcpy((BYTE*)mapped+72,runner_motion.rest,bytes);CHECK(IDirect3DVertexBuffer9_Unlock(vb));assert(uma_upload_matches_at(vb,72));
 CHECK(IDirect3DDevice9_CreateVertexBuffer(device,bytes,D3DUSAGE_DYNAMIC|D3DUSAGE_WRITEONLY,0,D3DPOOL_DEFAULT,&other,NULL));CHECK(IDirect3DVertexBuffer9_Lock(other,0,0,&mapped,D3DLOCK_DISCARD));memcpy(mapped,runner_motion.rest,bytes);((BYTE*)mapped)[bytes-1]^=1;CHECK(IDirect3DVertexBuffer9_Unlock(other));assert(!uma_upload_is_character(other));
 IDirect3DIndexBuffer9 *indices=NULL;CHECK(IDirect3DDevice9_CreateIndexBuffer(device,runner_motion.indices*2,0,D3DFMT_INDEX16,D3DPOOL_MANAGED,&indices,NULL));CHECK(IDirect3DIndexBuffer9_Lock(indices,0,0,&mapped,0));memcpy(mapped,runner_motion.index,runner_motion.indices*2);CHECK(IDirect3DIndexBuffer9_Unlock(indices));
 IDirect3DVertexShader9 *shader=NULL;CHECK(IDirect3DDevice9_CreateVertexShader(device,uma_vs_5,&shader));
 const D3DVERTEXELEMENT9 elements[]={{0,0,D3DDECLTYPE_FLOAT3,0,D3DDECLUSAGE_POSITION,0},{0,12,D3DDECLTYPE_FLOAT3,0,D3DDECLUSAGE_NORMAL,0},{0,24,D3DDECLTYPE_D3DCOLOR,0,D3DDECLUSAGE_COLOR,0},{0,28,D3DDECLTYPE_FLOAT2,0,D3DDECLUSAGE_TEXCOORD,0},D3DDECL_END()};IDirect3DVertexDeclaration9 *declaration=NULL;CHECK(IDirect3DDevice9_CreateVertexDeclaration(device,elements,&declaration));
 const DWORD white_code[]={0xffff0101,0x51,0xa00f0000,0x3f800000,0x3f800000,0x3f800000,0x3f800000,0x1,0x800f0000,0xa0e40000,0xffff};IDirect3DPixelShader9 *white=NULL;CHECK(IDirect3DDevice9_CreatePixelShader(device,white_code,&white));
 CHECK(IDirect3DDevice9_SetVertexShader(device,shader));CHECK(IDirect3DDevice9_SetVertexDeclaration(device,declaration));CHECK(IDirect3DDevice9_SetPixelShader(device,white));CHECK(IDirect3DDevice9_SetIndices(device,indices));CHECK(IDirect3DDevice9_SetRenderState(device,D3DRS_ZENABLE,TRUE));CHECK(IDirect3DDevice9_SetRenderState(device,D3DRS_CULLMODE,D3DCULL_NONE));
 float captured[256][4];FILE *lighting=fopen("modding/runtime/captured-lighting.bin","rb");assert(lighting);assert(fread(captured,1,sizeof(captured),lighting)==sizeof(captured));fclose(lighting);CHECK(IDirect3DDevice9_SetVertexShaderConstantF(device,0,&captured[0][0],256));
 D3DMATRIX combined={0};combined.m[1][0]=.6f;combined.m[2][1]=.8f;combined.m[0][2]=-.1f;combined.m[3][1]=-.85f;combined.m[3][2]=.5f;combined.m[3][3]=1;float matrix[4][4];for(int r=0;r<4;r++)for(int c=0;c<4;c++)matrix[r][c]=combined.m[c][r];CHECK(IDirect3DDevice9_SetVertexShaderConstantF(device,10,&matrix[0][0],4));
 float eye[]={2,-6,1.3f,1},view[3][4]={{1,0,0,0},{0,1,0,0},{0,0,1,0}};CHECK(IDirect3DDevice9_SetVertexShaderConstantF(device,14,&view[0][0],3));CHECK(IDirect3DDevice9_SetVertexShaderConstantF(device,17,eye,1));float paint[]={.4f,0,0,1};CHECK(IDirect3DDevice9_SetVertexShaderConstantF(device,18,paint,1));runner_state=(UmaMotionState){0,.25f,1};
 for(int kind=0;kind<3;kind++){
  CHECK(IDirect3DDevice9_SetStreamSource(device,0,kind==1?other:vb,kind==0?72:0,36));CHECK(IDirect3DDevice9_Clear(device,0,NULL,D3DCLEAR_TARGET|D3DCLEAR_ZBUFFER,0xff252a32,1,0));CHECK(IDirect3DDevice9_BeginScene(device));CHECK(IDirect3DDevice9_DrawIndexedPrimitive(device,D3DPT_TRIANGLELIST,kind==2?2:0,0,runner_motion.vertices,0,runner_motion.indices/3));CHECK(IDirect3DDevice9_EndScene(device));
  assert(runner_replaced==(kind==2?2u:1u) && runner_owned==runner_replaced);DWORD *pixels=read_pixels(device);UINT changed=0,colored=0,textured=0,not_red=0;
  for(int i=0;i<640*480;i++)if(pixels[i]!=0xff252a32){changed++;if(pixels[i]!=0xffffffff)colored++;unsigned r=(pixels[i]>>16)&255,g=(pixels[i]>>8)&255,b=pixels[i]&255;if(g>25 && b>25)not_red++;if(r+g+b>60 && (abs((int)r-(int)b)>8 || abs((int)r-(int)g)>8))textured++;}
  assert(changed>1000);if(kind==1)assert(colored==0);else{assert(colored>1000 && textured>1000 && not_red>100);float restored_paint[4];CHECK(IDirect3DDevice9_GetVertexShaderConstantF(device,18,restored_paint,1));assert(!memcmp(restored_paint,paint,sizeof(paint)));save_ppm("modding/runtime/integration-test/replaced.ppm",pixels);}free(pixels);
 }
 CHECK(IDirect3DDevice9_Present(device,NULL,NULL,NULL,NULL));assert(runner_frames==1);
 CHECK(IDirect3DDevice9_SetStreamSource(device,0,NULL,0,0));IDirect3DVertexBuffer9_Release(vb);IDirect3DVertexBuffer9_Release(other);CHECK(IDirect3DDevice9_Reset(device,&pp));assert(!runner_renderer.device);assert(runner_remove());
 IDirect3DVertexShader9_Release(shader);IDirect3DVertexDeclaration9_Release(declaration);IDirect3DPixelShader9_Release(white);IDirect3DIndexBuffer9_Release(indices);uma_motion_free(&runner_motion);fclose(runner_log);runner_log=NULL;DeleteCriticalSection(&runner_lock);IDirect3DDevice9_Release(device);IDirect3D9_Release(api);DestroyWindow(window);
 puts("PASS native shader 5 renders animated textured body through runtime hook; stream offset and base vertex pass, cross-device hooks pass, same-size impostor retains original white output; Present, Reset and hook removal pass. Not NFSU2 gameplay.");return 0;
}
