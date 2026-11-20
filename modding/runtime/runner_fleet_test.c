#define UMA_RUNNER_TEST
#include "uma_runner.c"
#define main renderer_component_main
#include "renderer_test.c"
#undef main
int main(int argc,char **argv){
 (void)uma_effects_load;
 assert(argc==2);WCHAR root[4096];assert(MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,argv[1],-1,root,4096));
 assert(!runner_load_models(L"modding\\runtime\\absent-fleet",1));assert(runner_model_count==1);assert(runner_load_models(root,1));assert(runner_model_count==7);assert(!runner_load_models(root,1));
 const unsigned ids[]={1068,1052,1032,1062,1015,1006,1058};for(unsigned i=0;i<7;i++){WCHAR path[4096];swprintf(path,4096,L"%ls\\modding\\runtime\\fleet\\%u\\carrier.bin",root,ids[i]);FILE *f=_wfopen(path,L"rb");assert(f);unsigned char expected[216];assert(fread(expected,1,216,f)==216 && fgetc(f)==EOF);fclose(f);assert(!memcmp(expected,runner_models[i].carrier,216));}
 for(unsigned i=0;i<7;i++){
  UmaMatrix body={0},object={0};for(int k=0;k<4;k++)body.m[k][k]=object.m[k][k]=1;
  const UmaAnchors *anchors=runner_anchors(i);assert(anchors);
  for(int wheel=0;wheel<4;wheel++){memcpy(object.m[3],anchors->wheel[wheel],12);assert(uma_model_wheel(&object,&body,anchors));object.m[3][0]+=10;assert(!uma_model_wheel(&object,&body,anchors));}
  for(int side=0;side<2;side++){memcpy(object.m[3],anchors->side[side],12);assert(uma_model_side_attachment(&object,&body,anchors));object.m[3][0]+=10;assert(!uma_model_side_attachment(&object,&body,anchors));}
 }
 for(unsigned frame=0;frame<120;frame++){
  UmaMatrix bodies[7];unsigned models[7];
  for(unsigned j=0;j<7;j++){unsigned index=frame&1?6-j:j;models[index]=j;memset(&bodies[index],0,sizeof(bodies[index]));for(int k=0;k<4;k++)bodies[index].m[k][k]=1;bodies[index].m[3][0]=j*frame*.05f;}
  runner_frames=frame;runner_scene.anchor_valid=1;runner_scene.anchor_key=(UmaSceneKey){.buffer=444};memset(&runner_scene.anchor,0,sizeof(runner_scene.anchor));for(int k=0;k<4;k++)runner_scene.anchor.m[k][k]=1;
  assert(runner_actor_update_models(bodies,models,7,.01f,NULL));
  for(unsigned j=0;j<7;j++){
   UmaMotionState *state=runner_actor_pose_model(&bodies[j],models[j]);assert(state && state!=&runner_models[models[j]].idle);
   if(frame==119){
    UmaMatrix reflected=bodies[j];for(int k=0;k<3;k++)reflected.m[0][k]*=-1;
    assert(runner_actor_pose_model(&reflected,models[j])==&runner_models[models[j]].idle);
    for(int angle=0;angle<=180;angle+=15){
     UmaMatrix turned=bodies[j];float radians=angle*3.14159265f/180;
     turned.m[0][0]=turned.m[2][2]=cosf(radians);turned.m[0][2]=sinf(radians);turned.m[2][0]=-sinf(radians);
     assert(runner_actor_pose_model(&turned,models[j])==state);
    }
   }
   if(runner_models[models[j]].secondary.nodes){int found=0;for(int a=0;a<16;a++)if(state==&runner_actors[a].state){assert(runner_actors[a].secondary.initialized);assert(runner_actors[a].secondary.revision>0);found=1;}assert(found);}
   assert(fabsf(state->idle_phase-uma_fraction((frame+1)*.01f/runner_models[models[j]].motion.idle_seconds))<1e-4f);
   if(frame>100)assert(models[j]?state->run_blend>.9f:state->run_blend<.001f);
   for(unsigned k=j+1;k<7;k++)assert(state!=runner_actor_pose_model(&bodies[k],models[k]));
  }
 }
 RunnerActor *moving=NULL;for(int i=0;i<16;i++)if(runner_actors[i].used && runner_actors[i].model==0)moving=&runner_actors[i];assert(moving);moving->speed=20;moving->state.run_blend=1;memset(moving->velocity,0,sizeof(moving->velocity));
 UmaMatrix noisy=moving->view;noisy.m[3][0]+=1.3f;unsigned model_zero=0;runner_frames++;RunnerActor *held=runner_actor_update_models(&noisy,&model_zero,1,.01f,NULL);assert(held==moving && held->speed==20 && held->state.run_blend>.99f);
 runner_frames++;RunnerActor *stopped=runner_actor_update_models(&noisy,&model_zero,1,.01f,NULL);assert(stopped==moving && stopped->speed==0);
 /* Rotation during a collision must not turn an existing running actor into idle. */
 for(int angle=180;angle>=0;angle-=15){
  UmaMatrix turned=noisy;float radians=angle*3.14159265f/180;
  turned.m[0][0]=turned.m[2][2]=cosf(radians);turned.m[0][2]=sinf(radians);turned.m[2][0]=-sinf(radians);
  assert(runner_actor_pose_model(&turned,0)==&moving->state);
  runner_frames++;assert(runner_actor_update_models(&turned,&model_zero,1,.01f,NULL)==moving);
 }
 assert(!runner_actor_pose_model(&runner_actors[0].view,7));memset(runner_actors,0,sizeof(runner_actors));runner_scene=(UmaSceneSpeed){0};runner_frames=0;runner_actor_world_valid=0;
 InitializeCriticalSection(&runner_lock);HWND window=CreateWindowA("STATIC","Independent seven-model routing",WS_POPUP,0,0,640,480,NULL,NULL,GetModuleHandle(NULL),NULL);assert(window);IDirect3D9 *api=Direct3DCreate9(D3D_SDK_VERSION);assert(api);
 D3DPRESENT_PARAMETERS pp={0};pp.Windowed=TRUE;pp.SwapEffect=D3DSWAPEFFECT_DISCARD;pp.hDeviceWindow=window;pp.BackBufferWidth=640;pp.BackBufferHeight=480;pp.BackBufferFormat=D3DFMT_A8R8G8B8;pp.EnableAutoDepthStencil=TRUE;pp.AutoDepthStencilFormat=D3DFMT_D24S8;
 IDirect3DDevice9 *device=NULL;CHECK(IDirect3D9_CreateDevice(api,0,D3DDEVTYPE_HAL,window,D3DCREATE_HARDWARE_VERTEXPROCESSING,&pp,&device));assert(runner_install(device));assert(uma_upload_model_count==7);
 IDirect3DVertexShader9 *shader=NULL;CHECK(IDirect3DDevice9_CreateVertexShader(device,uma_vs_5,&shader));
 const D3DVERTEXELEMENT9 elements[]={{0,0,D3DDECLTYPE_FLOAT3,0,D3DDECLUSAGE_POSITION,0},{0,12,D3DDECLTYPE_FLOAT3,0,D3DDECLUSAGE_NORMAL,0},{0,24,D3DDECLTYPE_D3DCOLOR,0,D3DDECLUSAGE_COLOR,0},{0,28,D3DDECLTYPE_FLOAT2,0,D3DDECLUSAGE_TEXCOORD,0},D3DDECL_END()};IDirect3DVertexDeclaration9 *declaration=NULL;CHECK(IDirect3DDevice9_CreateVertexDeclaration(device,elements,&declaration));
 const DWORD white_code[]={0xffff0101,0x51,0xa00f0000,0x3f800000,0x3f800000,0x3f800000,0x3f800000,0x1,0x800f0000,0xa0e40000,0xffff};IDirect3DPixelShader9 *white=NULL;CHECK(IDirect3DDevice9_CreatePixelShader(device,white_code,&white));
 CHECK(IDirect3DDevice9_SetVertexShader(device,shader));CHECK(IDirect3DDevice9_SetVertexDeclaration(device,declaration));CHECK(IDirect3DDevice9_SetPixelShader(device,white));CHECK(IDirect3DDevice9_SetRenderState(device,D3DRS_ZENABLE,TRUE));CHECK(IDirect3DDevice9_SetRenderState(device,D3DRS_CULLMODE,D3DCULL_NONE));CHECK(IDirect3DDevice9_SetRenderState(device,D3DRS_COLORWRITEENABLE,7));
 D3DMATRIX combined={0};combined.m[1][0]=.6f;combined.m[2][1]=.8f;combined.m[0][2]=-.1f;combined.m[3][1]=-.85f;combined.m[3][2]=.5f;combined.m[3][3]=1;float constants[4][4];for(int r=0;r<4;r++)for(int c=0;c<4;c++)constants[r][c]=combined.m[c][r];CHECK(IDirect3DDevice9_SetVertexShaderConstantF(device,10,&constants[0][0],4));
 float view[3][4]={{1,0,0,0},{0,1,0,0},{0,0,1,0}},eye[]={2,-6,1.3f,1},paint[]={.4f,0,0,1};CHECK(IDirect3DDevice9_SetVertexShaderConstantF(device,14,&view[0][0],3));CHECK(IDirect3DDevice9_SetVertexShaderConstantF(device,17,eye,1));CHECK(IDirect3DDevice9_SetVertexShaderConstantF(device,18,paint,1));
 IDirect3DVertexBuffer9 *vb[7]={0};IDirect3DIndexBuffer9 *ib[7]={0};DWORD hashes[7]={0};void *mapped=NULL;
 for(unsigned i=0;i<7;i++){
  UINT bytes=runner_input_count(&runner_models[i])*36;CHECK(IDirect3DDevice9_CreateVertexBuffer(device,bytes+72,D3DUSAGE_DYNAMIC|D3DUSAGE_WRITEONLY,0,D3DPOOL_DEFAULT,&vb[i],NULL));CHECK(IDirect3DVertexBuffer9_Lock(vb[i],0,0,&mapped,D3DLOCK_DISCARD));memset(mapped,0,72);memcpy((BYTE*)mapped+72,runner_input_vertices(&runner_models[i]),bytes);CHECK(IDirect3DVertexBuffer9_Unlock(vb[i]));UINT model=99;assert(uma_upload_model_at(vb[i],72,&model) && model==i);
  CHECK(IDirect3DDevice9_CreateIndexBuffer(device,12,0,D3DFMT_INDEX16,D3DPOOL_MANAGED,&ib[i],NULL));CHECK(IDirect3DIndexBuffer9_Lock(ib[i],0,0,&mapped,0));const WORD carrier_indices[]={0,1,2,3,4,5};memcpy(mapped,carrier_indices,12);CHECK(IDirect3DIndexBuffer9_Unlock(ib[i]));runner_models[i].idle=(UmaMotionState){0,.25f,1};
 }
 for(unsigned pass=0;pass<2;pass++)for(unsigned n=0;n<7;n++){
  unsigned i=pass?6-n:n;CHECK(IDirect3DDevice9_SetStreamSource(device,0,vb[i],72,36));CHECK(IDirect3DDevice9_SetIndices(device,ib[i]));CHECK(IDirect3DDevice9_Clear(device,0,NULL,D3DCLEAR_TARGET|D3DCLEAR_ZBUFFER,0xff252a32,1,0));unsigned before=runner_replaced;CHECK(IDirect3DDevice9_BeginScene(device));CHECK(IDirect3DDevice9_DrawIndexedPrimitive(device,D3DPT_TRIANGLELIST,0,0,runner_input_count(&runner_models[i]),0,runner_input_triangles(&runner_models[i])));CHECK(IDirect3DDevice9_EndScene(device));assert(runner_replaced==before+1);assert(runner_active_renderer==&runner_models[i].renderer);
  DWORD *image=read_pixels(device),hash=2166136261u;unsigned changed=0;for(int p=0;p<640*480;p++){hash=(hash^image[p])*16777619u;if(image[p]!=0xff252a32)changed++;}assert(changed>1000);if(pass)assert(hash==hashes[i]);else hashes[i]=hash;free(image);
 }
 assert(runner_scene.bodies==7);for(unsigned i=0;i<7;i++)for(unsigned j=i+1;j<7;j++)assert(hashes[i]!=hashes[j]);
 unsigned before=runner_replaced;CHECK(IDirect3DVertexBuffer9_Lock(vb[0],0,0,&mapped,D3DLOCK_DISCARD));memset(mapped,0,72);memcpy((BYTE*)mapped+72,runner_input_vertices(&runner_models[0]),216);((BYTE*)mapped)[72+215]^=1;CHECK(IDirect3DVertexBuffer9_Unlock(vb[0]));CHECK(IDirect3DDevice9_SetStreamSource(device,0,vb[0],72,36));CHECK(IDirect3DDevice9_SetIndices(device,ib[0]));CHECK(IDirect3DDevice9_BeginScene(device));CHECK(IDirect3DDevice9_DrawIndexedPrimitive(device,D3DPT_TRIANGLELIST,0,0,runner_input_count(&runner_models[0]),0,runner_input_triangles(&runner_models[0])));CHECK(IDirect3DDevice9_EndScene(device));assert(runner_replaced==before);
 CHECK(IDirect3DDevice9_SetStreamSource(device,0,NULL,0,0));CHECK(IDirect3DDevice9_SetIndices(device,NULL));for(unsigned i=0;i<7;i++){IDirect3DVertexBuffer9_Release(vb[i]);IDirect3DIndexBuffer9_Release(ib[i]);}CHECK(IDirect3DDevice9_Reset(device,&pp));for(unsigned i=0;i<7;i++)assert(!runner_models[i].renderer.device);assert(runner_model_count==7);assert(runner_remove());assert(!uma_upload_model_count);runner_free_models();
 IDirect3DVertexShader9_Release(shader);IDirect3DVertexDeclaration9_Release(declaration);IDirect3DPixelShader9_Release(white);IDirect3DDevice9_Release(device);IDirect3D9_Release(api);DestroyWindow(window);DeleteCriticalSection(&runner_lock);
 puts("PASS seven exact native models through runtime hook; distinct textures, reverse-order pixel identity, per-model actor gait/durations, stationary actor, impostor preservation, all-renderer reset and hook removal; not NFSU2 gameplay");return 0;
}
