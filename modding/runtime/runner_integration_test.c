#define UMA_RUNNER_TEST
#include "uma_runner.c"
#define main renderer_component_main
#include "renderer_test.c"
#undef main
static int headlight_expected,headlight_fail;static float headlight_original[16];
static HRESULT WINAPI headlight_probe(IDirect3DDevice9 *d,D3DPRIMITIVETYPE t,INT b,UINT m,UINT v,UINT s,UINT n){
 (void)t;(void)b;(void)m;(void)v;(void)s;(void)n;float current[16];assert(SUCCEEDED(IDirect3DDevice9_GetVertexShaderConstantF(d,4,current,4)));
 if(headlight_expected){for(int i=0;i<16;i++)assert(current[i]==(i==15?-100.f:0));}else assert(!memcmp(current,headlight_original,sizeof(current)));
 return headlight_fail?E_FAIL:S_OK;
}
static UmaMatrix headlight_fixture(void){
 UmaMatrix view={0},projection={0},bias={0};view.m[0][2]=1;view.m[1][0]=-1;view.m[2][1]=-1;view.m[3][1]=.75f;view.m[3][2]=-10;view.m[3][3]=1;
 projection.m[0][0]=projection.m[1][1]=1;projection.m[2][2]=100.f/99;projection.m[2][3]=1;projection.m[3][2]=-100.f/99;
 for(int k=0;k<4;k++){bias.m[k][k]=1;}bias.m[3][0]=bias.m[3][1]=.5f;
 UmaMatrix vp=uma_matrix_product(&view,&projection);return uma_matrix_product(&vp,&bias);
}
int main(void){
 freopen("modding/runtime/integration-test/result.txt","w",stdout);freopen("modding/runtime/integration-test/errors.txt","w",stderr);
 /* Visual root stays upright through a complete car roll and pitch, without translation changes. */
 runner_scene.anchor_valid=1;runner_actors[0].up_valid=1;runner_actors[0].up[2]=1;runner_actors[0].heading[0]=1;
 for(int axis=0;axis<2;axis++)for(int angle=0;angle<=360;angle+=15){
  float t=angle*3.14159265f/180,root[9];UmaMatrix body={0};for(int k=0;k<4;k++)body.m[k][k]=1;
  int a=axis?0:1,b=2;body.m[a][a]=body.m[b][b]=cosf(t);body.m[a][b]=sinf(t);body.m[b][a]=-sinf(t);body.m[3][0]=23;
  runner_actors[0].world=body;assert(runner_actor_root(&runner_actors[0].state,root));
  for(int r=0;r<3;r++)for(int c=0;c<3;c++){float v=0;for(int k=0;k<3;k++)v+=root[r*3+k]*body.m[k][c];assert(fabsf(v-(r==c))<.0001f);}
  assert(runner_actors[0].world.m[3][0]==23);
 }
 memset(runner_actors,0,sizeof(runner_actors));puts("PASS visual root: full roll/pitch cancellation with position unchanged");
 /* A stationary actor must remain idle while another runs and the camera orbits. */
 runner_scene.anchor_key=(UmaSceneKey){.buffer=777};runner_scene.anchor_valid=1;
 for(int f=0;f<180;f++){
  UmaMatrix camera={0},stationary={0},moving={0};for(int k=0;k<4;k++)camera.m[k][k]=stationary.m[k][k]=moving.m[k][k]=1;
  float angle=(float)f*.01f;camera.m[0][0]=camera.m[1][1]=cosf(angle);camera.m[0][1]=sinf(angle);camera.m[1][0]=-sinf(angle);camera.m[3][1]=-10;camera.m[3][2]=-2;
  stationary.m[3][2]=.05f*sinf((float)f*.2f);moving.m[3][0]=10+fminf((float)f,100)*.1f;
  moving.m[3][2]=(moving.m[3][0]-10)*.3f;moving.m[0][0]=moving.m[2][2]=cosf(.3f);moving.m[0][2]=sinf(.3f);moving.m[2][0]=-sinf(.3f);
  UmaMatrix still_view=uma_matrix_product(&stationary,&camera),run_view=uma_matrix_product(&moving,&camera),actors[2];actors[f&1]=still_view;actors[!(f&1)]=run_view;
  UmaMatrix other_anchor=camera;for(int k=0;k<3;k++)other_anchor.m[3][k]+=37*camera.m[0][k]-12*camera.m[1][k];
  runner_scene.anchor=f<80?camera:other_anchor;runner_scene.anchor_key.buffer=f<80?777:(f<90?778:779);runner_scene.anchor_valid=f!=60 && f!=61;runner_frames=100+(unsigned)f;assert(runner_actor_update(actors,2,.01f,NULL));
  UmaMotionState *still=runner_actor_pose(&still_view),*running=runner_actor_pose(&run_view);
  assert(still!=running && still!=&runner_idle_state && running!=&runner_idle_state);assert(still->run_blend<.001f);
  if(f==99)assert(running->run_blend>.99f);
  if(f==80)assert(running->run_blend>.99f);
  if(f==60 || f==61 || f==62)assert(running->run_blend>.95f);
  if(f==90)assert(running->run_blend>.99f);
  if(f==179)assert(running->run_blend<.01f);
  runner_previous_anchor=runner_scene.anchor;runner_previous_reference_count=1;runner_previous_references[0]=(UmaReference){.matrix=other_anchor,.key={.buffer=778}};
 }
 UmaMatrix unknown={0};for(int k=0;k<4;k++)unknown.m[k][k]=1;unknown.m[3][0]=1000;assert(runner_actor_pose(&unknown)==&runner_idle_state);
 runner_scene.bodies=0;uma_scene_body(&runner_scene,&unknown);uma_scene_body(&runner_scene,&unknown);assert(runner_scene.bodies==1);
 puts("PASS independent actor gait: draw-order reversal, camera orbit and vertical suspension cannot animate a stopped actor; another runs then returns to idle");
 memset(runner_actors,0,sizeof(runner_actors));runner_actor_world_valid=0;runner_tracking_gap=0;runner_previous_reference_count=0;
 float last_phase=0;
 for(int frame=0;frame<150;frame++){
  UmaMatrix camera={0},actor={0};for(int k=0;k<4;k++)camera.m[k][k]=actor.m[k][k]=1;
  float time=(float)frame*.01f,flight=fmaxf(0,time-.4f);actor.m[3][0]=time*25;
  actor.m[3][2]=frame>=40 && frame<120?fmaxf(0,8*flight-9.8f*flight*flight):0;
  float pitch=frame>=40 && frame<120?.35f*sinf(flight*4):0;
  actor.m[0][0]=actor.m[2][2]=cosf(pitch);actor.m[0][2]=sinf(pitch);actor.m[2][0]=-sinf(pitch);
  camera.m[3][0]=-time*25;camera.m[3][1]=-5;camera.m[3][2]=-2;
  UmaMatrix view=uma_matrix_product(&actor,&camera);runner_scene.anchor=camera;runner_scene.anchor_valid=1;runner_scene.anchor_key=(UmaSceneKey){.buffer=900};runner_frames=1000+(unsigned)frame;
  RunnerActor *tracked=runner_actor_update(&view,1,.01f,NULL);assert(tracked);
  if(frame>40){assert(tracked->state.run_blend>.9f);assert(tracked->state.run_phase!=last_phase);assert(tracked->speed>20);}
  last_phase=tracked->state.run_phase;
 }
 puts("PASS ballistic jump with stable scenery: horizontal motion, pitch and chase camera preserve running phase; missing-scene jump still needs live evidence");
 RunnerActor *fast=NULL;for(int i=0;i<16;i++)if(runner_actors[i].used){fast=&runner_actors[i];break;}assert(fast);
 UmaMatrix fast_view=fast->view;fast_view.m[3][0]+=6;runner_frame_seconds=.05f;
 assert(runner_actor_pose(&fast_view)==&fast->state);
 fast_view.m[3][0]+=100;assert(runner_actor_pose(&fast_view)==&runner_idle_state);runner_frame_seconds=1.f/60;
 puts("PASS pose lookup admits six-meter high-speed frame displacement but rejects a remote actor");
 /* A cinematic camera cut must not turn a moving actor into the idle fallback. */
 UmaMatrix old_camera={0},cut_camera={0};for(int k=0;k<4;k++)old_camera.m[k][k]=cut_camera.m[k][k]=1;
 cut_camera.m[0][0]=cut_camera.m[1][1]=0;cut_camera.m[0][1]=1;cut_camera.m[1][0]=-1;cut_camera.m[3][0]=100;
 runner_frames++;runner_scene.references=runner_previous_reference_count=1;
 runner_previous_references[0]=(UmaReference){.matrix=old_camera,.key={.buffer=456}};runner_scene.reference[0]=(UmaReference){.matrix=cut_camera,.key={.buffer=456}};
 fast->seen=runner_frames;UmaMatrix after_cut=uma_matrix_product(&fast->view,&cut_camera);
 assert(runner_actor_pose(&after_cut)==&fast->state);after_cut.m[3][2]+=1000;assert(runner_actor_pose(&after_cut)==&runner_idle_state);
 puts("PASS pose association through a 90-degree camera cut and 100m view translation; distant impostor still rejected");
 {
  unsigned original_count=runner_model_count;runner_model_count=7;
  for(unsigned model=0;model<7;model++){
  memset(runner_actors,0,sizeof(runner_actors));runner_scene=(UmaSceneSpeed){0};runner_actor_world_valid=0;runner_tracking_gap=0;runner_previous_reference_count=0;runner_actor_anchor=(UmaSceneKey){0};
  UmaMatrix normal={0},mirror={0};for(int k=0;k<4;k++)normal.m[k][k]=mirror.m[k][k]=1;mirror.m[2][2]=-1;
  runner_scene.anchor=normal;runner_scene.anchor_valid=1;runner_scene.anchor_key=(UmaSceneKey){.buffer=950};runner_frames=5000;
  RunnerActor *actor=runner_actor_update_models(&normal,&model,1,.016f,NULL);assert(actor && actor->up[2]>.99f);
  runner_previous_anchor=normal;runner_scene.anchor=mirror;runner_scene.anchor_key=(UmaSceneKey){.buffer=951,.pass=1};runner_frames++;
  actor=runner_actor_update_models(&mirror,&model,1,.016f,&normal);assert(actor && actor->model==model);
  float root[9];assert(runner_actor_root(&actor->state,root));assert(actor->up[2]>.99f && root[8]>.99f);
  runner_previous_anchor=mirror;runner_frames++;actor=runner_actor_update_models(&mirror,&model,1,.016f,&normal);assert(actor && actor->up[2]>.99f);
  }
  runner_model_count=original_count;
  puts("PASS all seven models preserve the vertical axis and visual root through main-to-reflection anchor handoff");
 }
 runner_scene=(UmaSceneSpeed){0};memset(runner_actors,0,sizeof(runner_actors));runner_frames=0;
 FILE *asset=fopen("modding/runtime/kitasan.umab","rb");assert(asset);assert(uma_motion_load(asset,&runner_motion));fclose(asset);
 InitializeCriticalSection(&runner_lock);runner_log=fopen("modding/runtime/integration-test/runner.log","w");assert(runner_log);wcscpy(runner_atlas,L"modding\\runtime\\atlas.dds");
 HWND window=CreateWindowA("STATIC","Independent runtime routing test",WS_POPUP,0,0,640,480,NULL,NULL,GetModuleHandle(NULL),NULL);assert(window);IDirect3D9 *api=Direct3DCreate9(D3D_SDK_VERSION);assert(api);
 D3DPRESENT_PARAMETERS pp={0};pp.Windowed=TRUE;pp.SwapEffect=D3DSWAPEFFECT_DISCARD;pp.hDeviceWindow=window;pp.BackBufferWidth=640;pp.BackBufferHeight=480;pp.BackBufferFormat=D3DFMT_A8R8G8B8;pp.EnableAutoDepthStencil=TRUE;pp.AutoDepthStencilFormat=D3DFMT_D24S8;
 IDirect3DDevice9 *device=NULL;CHECK(IDirect3D9_CreateDevice(api,0,D3DDEVTYPE_HAL,window,D3DCREATE_HARDWARE_VERTEXPROCESSING,&pp,&device));IDirect3DDevice9 *bootstrap=NULL;D3DPRESENT_PARAMETERS init=pp;init.EnableAutoDepthStencil=FALSE;CHECK(IDirect3D9_CreateDevice(api,0,D3DDEVTYPE_HAL,window,D3DCREATE_SOFTWARE_VERTEXPROCESSING,&init,&bootstrap));assert(runner_install(bootstrap));IDirect3DDevice9_Release(bootstrap);
 WCHAR effect_root[4096];assert(GetCurrentDirectoryW(4096,effect_root));assert(uma_effects_load(effect_root));
 for(int effect=0;effect<8;effect++){
  IDirect3DTexture9 *sample=NULL;UINT width=uma_effects[effect].width;CHECK(IDirect3DDevice9_CreateTexture(device,width,uma_effects[effect].height,1,0,uma_effects[effect].format,D3DPOOL_MANAGED,&sample,NULL));
  D3DLOCKED_RECT lock;CHECK(IDirect3DTexture9_LockRect(sample,0,&lock,NULL,0));for(UINT y=0;y<(uma_effects[effect].format==D3DFMT_DXT3?uma_effects[effect].height/4:uma_effects[effect].height);y++)memcpy((BYTE*)lock.pBits+y*lock.Pitch,uma_effects[effect].pixels+y*width*4,width*4);CHECK(IDirect3DTexture9_UnlockRect(sample,0));
  assert(uma_effect_texture(sample));unsigned cached_reads=uma_effect_reads;for(int repeat=0;repeat<1000;repeat++)assert(uma_effect_texture(sample));assert(uma_effect_reads==cached_reads);CHECK(IDirect3DDevice9_SetTexture(device,0,(IDirect3DBaseTexture9*)sample));assert(uma_effect_draw(device));
  IDirect3DBaseTexture9 *retained=NULL;CHECK(IDirect3DDevice9_GetTexture(device,0,&retained));assert(retained==(IDirect3DBaseTexture9*)sample);IDirect3DBaseTexture9_Release(retained);
  CHECK(IDirect3DTexture9_LockRect(sample,0,&lock,NULL,0));((BYTE*)lock.pBits)[0]^=1;CHECK(IDirect3DTexture9_UnlockRect(sample,0));assert(!uma_effect_texture(sample));assert(!uma_effect_draw(device));
  IDirect3DSurface9 *surface=NULL;CHECK(IDirect3DTexture9_GetSurfaceLevel(sample,0,&surface));
  CHECK(IDirect3DSurface9_LockRect(surface,&lock,NULL,0));((BYTE*)lock.pBits)[0]^=1;CHECK(IDirect3DSurface9_UnlockRect(surface));assert(uma_effect_texture(sample));
  IDirect3DSurface9_Release(surface);
  CHECK(IDirect3DDevice9_SetTexture(device,0,NULL));IDirect3DTexture9_Release(sample);
 }
 assert(uma_effects_hidden==8);uma_effects_ready=0;
 puts("PASS eight exact effect textures: 8000 cached queries add zero readbacks; texture and surface writes invalidate positive/negative cache; impostors and bindings preserved");
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
 float eye[]={2,-6,1.3f,1},view[3][4]={{1,0,0,0},{0,1,0,0},{0,0,1,0}};CHECK(IDirect3DDevice9_SetVertexShaderConstantF(device,14,&view[0][0],3));CHECK(IDirect3DDevice9_SetVertexShaderConstantF(device,17,eye,1));float paint[]={.4f,0,0,1};CHECK(IDirect3DDevice9_SetVertexShaderConstantF(device,18,paint,1));runner_state=runner_idle_state=(UmaMotionState){0,.25f,1};
 for(int kind=0;kind<3;kind++){
  CHECK(IDirect3DDevice9_SetStreamSource(device,0,kind==1?other:vb,kind==0?72:0,36));CHECK(IDirect3DDevice9_Clear(device,0,NULL,D3DCLEAR_TARGET|D3DCLEAR_ZBUFFER,0xff252a32,1,0));CHECK(IDirect3DDevice9_BeginScene(device));CHECK(IDirect3DDevice9_DrawIndexedPrimitive(device,D3DPT_TRIANGLELIST,kind==2?2:0,0,runner_motion.vertices,0,runner_motion.indices/3));CHECK(IDirect3DDevice9_EndScene(device));
  assert(runner_replaced==(kind==2?2u:1u) && runner_owned==runner_replaced);DWORD *pixels=read_pixels(device);UINT changed=0,colored=0,textured=0,not_red=0;
  for(int i=0;i<640*480;i++)if(pixels[i]!=0xff252a32){changed++;if(pixels[i]!=0xffffffff)colored++;unsigned r=(pixels[i]>>16)&255,g=(pixels[i]>>8)&255,b=pixels[i]&255;if(g>25 && b>25)not_red++;if(r+g+b>60 && (abs((int)r-(int)b)>8 || abs((int)r-(int)g)>8))textured++;}
  assert(changed>1000);if(kind==1)assert(colored==0);else{assert(colored>1000 && textured>1000 && not_red>100);float restored_paint[4];CHECK(IDirect3DDevice9_GetVertexShaderConstantF(device,18,restored_paint,1));assert(!memcmp(restored_paint,paint,sizeof(paint)));save_ppm("modding/runtime/integration-test/replaced.ppm",pixels);}free(pixels);
 }
 UmaMatrix light=headlight_fixture(),identity={0};for(int k=0;k<4;k++)identity.m[k][k]=1;
 /* Exercise the real DIP wrapper, including constant restoration after a failed native draw. */
 float before_headlight[256][4];CHECK(IDirect3DDevice9_GetVertexShaderConstantF(device,0,&before_headlight[0][0],256));
 IDirect3DVertexShader9 *headlight_shader=NULL;CHECK(IDirect3DDevice9_CreateVertexShader(device,uma_vs_7,&headlight_shader));
 CHECK(IDirect3DDevice9_SetVertexShader(device,headlight_shader));CHECK(IDirect3DDevice9_SetStreamSource(device,0,other,0,36));
 for(int r=0;r<4;r++)for(int c=0;c<4;c++)headlight_original[r*4+c]=light.m[c][r];
 CHECK(IDirect3DDevice9_SetVertexShaderConstantF(device,4,headlight_original,4));
 float geometry[3][4]={{1,0,0,0},{0,1,0,0},{0,0,1,0}};CHECK(IDirect3DDevice9_SetVertexShaderConstantF(device,8,&geometry[0][0],3));
 memset(runner_actors,0,sizeof(runner_actors));runner_actors[0].used=1;runner_actors[0].seen=runner_frames;runner_actors[0].view=identity;runner_actors[0].view.m[3][0]=10;
 runner_scene.references=runner_previous_reference_count=1;runner_scene.reference[0]=(UmaReference){.matrix=identity,.key={.buffer=123}};runner_previous_references[0]=runner_scene.reference[0];runner_previous_anchor=identity;
 UmaDrawIndexed real_draw=runner_original_draw;runner_original_draw=headlight_probe;
 for(int pass=0;pass<3;pass++){
  headlight_expected=1;headlight_fail=pass==2;runner_actors[0].view.m[3][0]=pass==1?15:10;
  CHECK(IDirect3DDevice9_BeginScene(device));HRESULT status=IDirect3DDevice9_DrawIndexedPrimitive(device,D3DPT_TRIANGLELIST,0,0,runner_motion.vertices,0,runner_motion.indices/3);assert(status==(headlight_fail?E_FAIL:S_OK));CHECK(IDirect3DDevice9_EndScene(device));
  float restored[16];CHECK(IDirect3DDevice9_GetVertexShaderConstantF(device,4,restored,4));assert(!memcmp(restored,headlight_original,sizeof(restored)));
 }
 runner_original_draw=real_draw;CHECK(IDirect3DDevice9_SetVertexShader(device,shader));CHECK(IDirect3DDevice9_SetVertexShaderConstantF(device,0,&before_headlight[0][0],256));IDirect3DVertexShader9_Release(headlight_shader);
 runner_scene.references=runner_previous_reference_count=0;memset(runner_actors,0,sizeof(runner_actors));
 puts("PASS headlight DIP: all car projectors suppressed under expanded user scope, exact constants restored after success and native draw failure");
 /* Route every material at the Corolla's own wheel mount; a foreign car must pass through. */
 IDirect3DVertexBuffer9 *wheel_vb=NULL;IDirect3DIndexBuffer9 *wheel_ib=NULL;IDirect3DTexture9 *tire=NULL,*non_tire=NULL;
 UmaVertex quad[4]={0};for(int i=0;i<4;i++){quad[i].position[1]=(i&1)?.2f:-.2f;quad[i].position[2]=(i&2)?1.2f:.7f;quad[i].normal[0]=1;memset(quad[i].bgra,255,4);}const WORD wheel_indices[]={0,1,2,2,1,3};
 CHECK(IDirect3DDevice9_CreateVertexBuffer(device,sizeof(quad),D3DUSAGE_WRITEONLY,0,D3DPOOL_DEFAULT,&wheel_vb,NULL));CHECK(IDirect3DVertexBuffer9_Lock(wheel_vb,0,0,&mapped,0));memcpy(mapped,quad,sizeof(quad));CHECK(IDirect3DVertexBuffer9_Unlock(wheel_vb));
 CHECK(IDirect3DDevice9_CreateIndexBuffer(device,sizeof(wheel_indices),0,D3DFMT_INDEX16,D3DPOOL_MANAGED,&wheel_ib,NULL));CHECK(IDirect3DIndexBuffer9_Lock(wheel_ib,0,0,&mapped,0));memcpy(mapped,wheel_indices,sizeof(wheel_indices));CHECK(IDirect3DIndexBuffer9_Unlock(wheel_ib));
 CHECK(IDirect3DDevice9_CreateTexture(device,128,128,1,0,D3DFMT_DXT1,D3DPOOL_MANAGED,&tire,NULL));CHECK(IDirect3DDevice9_CreateTexture(device,128,128,1,0,D3DFMT_A8R8G8B8,D3DPOOL_MANAGED,&non_tire,NULL));
 CHECK(IDirect3DDevice9_SetStreamSource(device,0,wheel_vb,0,36));CHECK(IDirect3DDevice9_SetIndices(device,wheel_ib));
 runner_scene.bodies=1;memset(&runner_scene.body[0],0,sizeof(UmaMatrix));for(int i=0;i<4;i++)runner_scene.body[0].m[i][i]=1;
 native_draw=runner_original_draw;runner_original_draw=observed_draw;draws=0;unsigned hidden=runner_hidden_wheels;
 for(int kind=0;kind<3;kind++){
  float wheel_view[3][4]={{1,0,0,1.35f},{0,1,0,.78f},{0,0,1,.275f}};if(kind==1)wheel_view[0][3]+=10;
  CHECK(IDirect3DDevice9_SetVertexShaderConstantF(device,14,&wheel_view[0][0],3));CHECK(IDirect3DDevice9_SetTexture(device,1,(IDirect3DBaseTexture9*)(kind==2?non_tire:tire)));
  CHECK(IDirect3DDevice9_BeginScene(device));CHECK(IDirect3DDevice9_DrawIndexedPrimitive(device,D3DPT_TRIANGLELIST,0,0,4,0,2));CHECK(IDirect3DDevice9_EndScene(device));assert(draws==(kind?1u:0u));assert(runner_hidden_wheels==hidden+(kind==2?2u:1u));
 }
 runner_original_draw=native_draw;
 const D3DVERTEXELEMENT9 elements32[]={{0,0,D3DDECLTYPE_FLOAT3,0,D3DDECLUSAGE_POSITION,0},{0,12,D3DDECLTYPE_FLOAT3,0,D3DDECLUSAGE_NORMAL,0},{0,24,D3DDECLTYPE_FLOAT2,0,D3DDECLUSAGE_TEXCOORD,0},D3DDECL_END()};IDirect3DVertexDeclaration9 *declaration32=NULL;CHECK(IDirect3DDevice9_CreateVertexDeclaration(device,elements32,&declaration32));
 struct {float position[3],normal[3],uv[2];} quad32[4];for(int i=0;i<4;i++){memcpy(quad32[i].position,quad[i].position,12);memcpy(quad32[i].normal,quad[i].normal,12);memcpy(quad32[i].uv,quad[i].uv,8);}
 hidden=runner_hidden_wheels;
 for(int method=0;method<3;method++)for(int foreign=0;foreign<2;foreign++){
  float wheel_view[3][4]={{1,0,0,1.35f+(foreign?10:0)},{0,1,0,.78f},{0,0,1,.275f}};CHECK(IDirect3DDevice9_SetVertexShaderConstantF(device,14,&wheel_view[0][0],3));
  CHECK(IDirect3DDevice9_SetVertexDeclaration(device,method?declaration32:declaration));CHECK(IDirect3DDevice9_SetStreamSource(device,0,wheel_vb,0,36));CHECK(IDirect3DDevice9_SetIndices(device,wheel_ib));
  CHECK(IDirect3DDevice9_Clear(device,0,NULL,D3DCLEAR_TARGET|D3DCLEAR_ZBUFFER,0xff252a32,1,0));CHECK(IDirect3DDevice9_BeginScene(device));
  if(method==0){CHECK(IDirect3DDevice9_DrawPrimitive(device,D3DPT_TRIANGLESTRIP,0,2));}
  else if(method==1){CHECK(IDirect3DDevice9_DrawPrimitiveUP(device,D3DPT_TRIANGLESTRIP,2,quad32,32));}
  else {CHECK(IDirect3DDevice9_DrawIndexedPrimitiveUP(device,D3DPT_TRIANGLELIST,0,4,2,wheel_indices,D3DFMT_INDEX16,quad32,32));}
  CHECK(IDirect3DDevice9_EndScene(device));assert(runner_hidden_wheels==hidden+(unsigned)method+1);
  DWORD *pixels=read_pixels(device);unsigned changed=0;for(int i=0;i<640*480;i++)if(pixels[i]!=0xff252a32)changed++;free(pixels);assert(foreign?changed>100:changed==0);
  if(method){IDirect3DVertexBuffer9 *bound=NULL;UINT offset,stride;CHECK(IDirect3DDevice9_GetStreamSource(device,0,&bound,&offset,&stride));assert(!bound);}
  if(method==2){IDirect3DIndexBuffer9 *bound=NULL;CHECK(IDirect3DDevice9_GetIndices(device,&bound));assert(!bound);}
 }
 /* CPU-baked wheel vertices use the body root matrix rather than a wheel mount matrix. */
 for(int i=0;i<4;i++){quad[i].position[0]=1.35f;quad[i].position[1]=.78f+((i&1)?.2f:-.2f);quad[i].position[2]=.275f+((i&2)?.2f:-.2f);memcpy(quad32[i].position,quad[i].position,12);}
 IDirect3DVertexBuffer9 *baked_vb=NULL;CHECK(IDirect3DDevice9_CreateVertexBuffer(device,sizeof(quad32),D3DUSAGE_WRITEONLY,0,D3DPOOL_DEFAULT,&baked_vb,NULL));CHECK(IDirect3DVertexBuffer9_Lock(baked_vb,0,0,&mapped,0));memcpy(mapped,quad32,sizeof(quad32));CHECK(IDirect3DVertexBuffer9_Unlock(baked_vb));
 UmaVertexBounds cached;assert(uma_upload_bounds(baked_vb,0,4,32,0,&cached));hidden=runner_hidden_wheels;
 for(int method=0;method<4;method++)for(int foreign=0;foreign<2;foreign++){
  float baked_view[3][4]={{1,0,0,foreign?10:0},{0,1,0,0},{0,0,1,0}};CHECK(IDirect3DDevice9_SetVertexShaderConstantF(device,14,&baked_view[0][0],3));
  CHECK(IDirect3DDevice9_SetVertexDeclaration(device,declaration32));CHECK(IDirect3DDevice9_SetStreamSource(device,0,baked_vb,0,32));CHECK(IDirect3DDevice9_SetIndices(device,wheel_ib));
  CHECK(IDirect3DDevice9_Clear(device,0,NULL,D3DCLEAR_TARGET|D3DCLEAR_ZBUFFER,0xff252a32,1,0));CHECK(IDirect3DDevice9_BeginScene(device));
  if(method==0){CHECK(IDirect3DDevice9_DrawIndexedPrimitive(device,D3DPT_TRIANGLELIST,0,0,4,0,2));}
  else if(method==1){CHECK(IDirect3DDevice9_DrawPrimitive(device,D3DPT_TRIANGLESTRIP,0,2));}
  else if(method==2){CHECK(IDirect3DDevice9_DrawPrimitiveUP(device,D3DPT_TRIANGLESTRIP,2,quad32,32));}
  else {CHECK(IDirect3DDevice9_DrawIndexedPrimitiveUP(device,D3DPT_TRIANGLELIST,0,4,2,wheel_indices,D3DFMT_INDEX16,quad32,32));}
  CHECK(IDirect3DDevice9_EndScene(device));assert(runner_hidden_wheels==hidden+(unsigned)method+1);
  DWORD *pixels=read_pixels(device);unsigned changed=0;for(int i=0;i<640*480;i++)if(pixels[i]!=0xff252a32)changed++;free(pixels);assert(foreign?changed>100:changed==0);
 }
 CHECK(IDirect3DVertexBuffer9_Lock(baked_vb,0,4,&mapped,0));memset(mapped,0,4);CHECK(IDirect3DVertexBuffer9_Unlock(baked_vb));assert(!uma_upload_bounds(baked_vb,0,4,32,0,&cached));
 IDirect3DVertexBuffer9_Release(baked_vb);
 puts("PASS CPU-baked wheel vertices across all four draw APIs; foreign pixels intact; partial writes invalidate bounds");
 /* Combined tires in a shared upload must be tested vertex by vertex. */
 float batch[16][8]={0};WORD batch_indices[24];
 for(int k=0;k<4;k++)for(int j=0;j<4;j++){
  int v=k*4+j;batch[v][0]=(k<2?1.35f:-1.05f)+(j&1?.2f:-.2f);batch[v][1]=k&1?-.78f:.78f;batch[v][2]=.275f+(j&2?.2f:-.2f);
 }
 for(int k=0;k<4;k++)for(int j=0;j<6;j++)batch_indices[k*6+j]=k*4+wheel_indices[j];
 IDirect3DVertexBuffer9 *batch_vb=NULL;IDirect3DIndexBuffer9 *batch_ib=NULL;
 CHECK(IDirect3DDevice9_CreateVertexBuffer(device,96240,D3DUSAGE_WRITEONLY,0,D3DPOOL_DEFAULT,&batch_vb,NULL));CHECK(IDirect3DVertexBuffer9_Lock(batch_vb,0,0,&mapped,0));memset(mapped,0,96240);memcpy((BYTE*)mapped+128,batch,sizeof(batch));CHECK(IDirect3DVertexBuffer9_Unlock(batch_vb));
 CHECK(IDirect3DDevice9_CreateIndexBuffer(device,sizeof(batch_indices),0,D3DFMT_INDEX16,D3DPOOL_MANAGED,&batch_ib,NULL));CHECK(IDirect3DIndexBuffer9_Lock(batch_ib,0,0,&mapped,0));memcpy(mapped,batch_indices,sizeof(batch_indices));CHECK(IDirect3DIndexBuffer9_Unlock(batch_ib));
 for(int method=0;method<4;method++)for(int foreign=0;foreign<2;foreign++){
  float batch_view[3][4]={{1,0,0,foreign?10:0},{0,1,0,0},{0,0,1,.2f}};CHECK(IDirect3DDevice9_SetVertexShaderConstantF(device,14,&batch_view[0][0],3));
  CHECK(IDirect3DDevice9_SetVertexDeclaration(device,declaration32));CHECK(IDirect3DDevice9_SetStreamSource(device,0,batch_vb,128,32));CHECK(IDirect3DDevice9_SetIndices(device,batch_ib));
  hidden=runner_hidden_wheels;CHECK(IDirect3DDevice9_BeginScene(device));
  if(method==0){CHECK(IDirect3DDevice9_DrawIndexedPrimitive(device,D3DPT_TRIANGLELIST,0,0,16,0,8));}
  else if(method==1){CHECK(IDirect3DDevice9_DrawPrimitive(device,D3DPT_TRIANGLESTRIP,0,14));}
  else if(method==2){CHECK(IDirect3DDevice9_DrawPrimitiveUP(device,D3DPT_TRIANGLESTRIP,14,batch,32));}
  else {CHECK(IDirect3DDevice9_DrawIndexedPrimitiveUP(device,D3DPT_TRIANGLELIST,0,16,8,batch_indices,D3DFMT_INDEX16,batch,32));}
  CHECK(IDirect3DDevice9_EndScene(device));assert(runner_hidden_wheels==hidden+(foreign?0:1));
 }
 IDirect3DVertexBuffer9_Release(batch_vb);IDirect3DIndexBuffer9_Release(batch_ib);
 puts("PASS four-tire shared upload batch through all draw APIs with suspension offset; foreign actor not hidden");
 /* Optional attachments can fall back to the body origin when their marker is absent. */
 float root_view[3][4]={{1,0,0,0},{0,1,0,0},{0,0,1,0}};CHECK(IDirect3DDevice9_SetVertexShaderConstantF(device,14,&root_view[0][0],3));
 CHECK(IDirect3DDevice9_SetVertexDeclaration(device,declaration));CHECK(IDirect3DDevice9_SetStreamSource(device,0,wheel_vb,0,36));CHECK(IDirect3DDevice9_SetIndices(device,wheel_ib));
 hidden=runner_hidden_wheels;CHECK(IDirect3DDevice9_BeginScene(device));CHECK(IDirect3DDevice9_DrawIndexedPrimitive(device,D3DPT_TRIANGLELIST,0,0,4,0,2));CHECK(IDirect3DDevice9_EndScene(device));assert(runner_hidden_wheels==hidden+1);
 root_view[0][3]=2;CHECK(IDirect3DDevice9_SetVertexShaderConstantF(device,14,&root_view[0][0],3));CHECK(IDirect3DDevice9_BeginScene(device));CHECK(IDirect3DDevice9_DrawIndexedPrimitive(device,D3DPT_TRIANGLELIST,0,0,4,0,2));CHECK(IDirect3DDevice9_EndScene(device));assert(runner_hidden_wheels==hidden+1);
 for(int foreign=0;foreign<2;foreign++){
  root_view[0][3]=.6322f+(foreign?10:0);root_view[1][3]=.7031f;root_view[2][3]=.9397f;CHECK(IDirect3DDevice9_SetVertexShaderConstantF(device,14,&root_view[0][0],3));
  hidden=runner_hidden_wheels;CHECK(IDirect3DDevice9_BeginScene(device));CHECK(IDirect3DDevice9_DrawIndexedPrimitive(device,D3DPT_TRIANGLELIST,0,0,4,0,2));CHECK(IDirect3DDevice9_EndScene(device));assert(runner_hidden_wheels==hidden+(foreign?0:1));
 }
 puts("PASS car-style side anchor attachment hidden at Corolla socket; foreign actor preserved");
 puts("PASS car-style root attachment hidden only at a recognized Corolla root; translated actor preserved");
 /* The real native batch uses a 96,240-byte VB; queries must cover draw subranges. */
 IDirect3DVertexBuffer9 *shared=NULL;CHECK(IDirect3DDevice9_CreateVertexBuffer(device,96240,D3DUSAGE_DYNAMIC|D3DUSAGE_WRITEONLY,0,D3DPOOL_DEFAULT,&shared,NULL));
 CHECK(IDirect3DVertexBuffer9_Lock(shared,0,0,&mapped,D3DLOCK_DISCARD));memset(mapped,0,96240);memcpy((BYTE*)mapped+96000,quad,sizeof(quad));CHECK(IDirect3DVertexBuffer9_Unlock(shared));assert(uma_upload_bounds(shared,96000,4,36,0,&cached));
 CHECK(IDirect3DVertexBuffer9_Lock(shared,40,80,&mapped,0));memset(mapped,0,80);for(int i=0;i<4;i++)memcpy((BYTE*)mapped+i*20+4,quad[i].position,12);CHECK(IDirect3DVertexBuffer9_Unlock(shared));
 assert(uma_upload_bounds(shared,40,4,20,4,&cached));assert(!uma_upload_bounds(shared,96000,4,36,0,&cached));
 CHECK(IDirect3DVertexBuffer9_Lock(shared,40,80,&mapped,D3DLOCK_READONLY));CHECK(IDirect3DVertexBuffer9_Unlock(shared));assert(uma_upload_bounds(shared,40,4,20,4,&cached));
 IDirect3DVertexBuffer9_Release(shared);puts("PASS native 96KB shared buffer, draw subrange, partial upload at offset, stride20 position offset and READONLY preservation");
 CHECK(IDirect3DDevice9_SetVertexDeclaration(device,declaration));IDirect3DVertexDeclaration9_Release(declaration32);
 puts("PASS DP, DPUP and DIPUP wheel mounts, stride32, triangle strips, foreign pixels preserved and UP binding side effects");
 CHECK(IDirect3DDevice9_SetTexture(device,1,NULL));IDirect3DTexture9_Release(tire);IDirect3DTexture9_Release(non_tire);IDirect3DVertexBuffer9_Release(wheel_vb);CHECK(IDirect3DDevice9_SetIndices(device,indices));IDirect3DIndexBuffer9_Release(wheel_ib);
 puts("PASS wheel-mounted attachments hidden across materials; foreign tire draw retained");
 /* Exercise actual CTAB/COM draw-key collection with a moving camera and body. */
 IDirect3DVertexBuffer9 *ground=NULL;IDirect3DIndexBuffer9 *ground_indices=NULL;IDirect3DVertexShader9 *ground_shader=NULL;IDirect3DVertexDeclaration9 *ground_decl=NULL;
 const D3DVERTEXELEMENT9 ground_elements[]={{0,0,D3DDECLTYPE_FLOAT3,0,D3DDECLUSAGE_POSITION,0},{0,12,D3DDECLTYPE_D3DCOLOR,0,D3DDECLUSAGE_COLOR,0},{0,16,D3DDECLTYPE_FLOAT2,0,D3DDECLUSAGE_TEXCOORD,0},D3DDECL_END()};
 CHECK(IDirect3DDevice9_CreateVertexBuffer(device,64*24,D3DUSAGE_WRITEONLY,0,D3DPOOL_MANAGED,&ground,NULL));CHECK(IDirect3DVertexBuffer9_Lock(ground,0,0,&mapped,0));memset(mapped,0,64*24);CHECK(IDirect3DVertexBuffer9_Unlock(ground));
 CHECK(IDirect3DDevice9_CreateIndexBuffer(device,32*3*2,0,D3DFMT_INDEX16,D3DPOOL_MANAGED,&ground_indices,NULL));CHECK(IDirect3DIndexBuffer9_Lock(ground_indices,0,0,&mapped,0));memset(mapped,0,32*3*2);CHECK(IDirect3DIndexBuffer9_Unlock(ground_indices));
 CHECK(IDirect3DDevice9_CreateVertexShader(device,uma_vs_1,&ground_shader));CHECK(IDirect3DDevice9_CreateVertexDeclaration(device,ground_elements,&ground_decl));
 runner_scene=(UmaSceneSpeed){0};UmaMatrix projection;memcpy(&projection,&combined,sizeof(projection));
 CHECK(IDirect3DDevice9_SetRenderState(device,D3DRS_ZWRITEENABLE,TRUE));CHECK(IDirect3DDevice9_SetRenderState(device,D3DRS_ALPHABLENDENABLE,FALSE));
 for(int f=0;f<3;f++){
  UmaMatrix scenery={0},actor={0};for(int i=0;i<4;i++)scenery.m[i][i]=actor.m[i][i]=1;
  scenery.m[3][0]=20-100-(float)f*2;actor.m[3][0]=5+(float)f*.1f-100-(float)f*2;
  UmaMatrix reference_clip=uma_matrix_product(&scenery,&projection),actor_clip=uma_matrix_product(&actor,&projection);float constants[4][4];
  for(int r=0;r<4;r++)for(int c=0;c<4;c++)constants[r][c]=reference_clip.m[c][r];
  CHECK(IDirect3DDevice9_SetVertexShader(device,ground_shader));CHECK(IDirect3DDevice9_SetVertexDeclaration(device,ground_decl));CHECK(IDirect3DDevice9_SetVertexShaderConstantF(device,0,&constants[0][0],4));CHECK(IDirect3DDevice9_SetStreamSource(device,0,ground,0,24));CHECK(IDirect3DDevice9_SetIndices(device,ground_indices));
  CHECK(IDirect3DDevice9_BeginScene(device));CHECK(IDirect3DDevice9_DrawIndexedPrimitive(device,D3DPT_TRIANGLELIST,0,0,64,0,32));
  for(int r=0;r<4;r++)for(int c=0;c<4;c++)constants[r][c]=actor_clip.m[c][r];
  float actor_view[3][4];for(int r=0;r<3;r++)for(int c=0;c<4;c++)actor_view[r][c]=actor.m[c][r];
  CHECK(IDirect3DDevice9_SetVertexShader(device,shader));CHECK(IDirect3DDevice9_SetVertexDeclaration(device,declaration));CHECK(IDirect3DDevice9_SetVertexShaderConstantF(device,10,&constants[0][0],4));CHECK(IDirect3DDevice9_SetVertexShaderConstantF(device,14,&actor_view[0][0],3));CHECK(IDirect3DDevice9_SetStreamSource(device,0,vb,72,36));CHECK(IDirect3DDevice9_SetIndices(device,indices));CHECK(IDirect3DDevice9_DrawIndexedPrimitive(device,D3DPT_TRIANGLELIST,0,0,runner_motion.vertices,0,runner_motion.indices/3));CHECK(IDirect3DDevice9_EndScene(device));
  assert(runner_scene.references && runner_scene.bodies);float actual_speed=99;assert(uma_scene_finish(&runner_scene,.01f,&actual_speed));assert(f?fabsf(actual_speed-10)<.1f:actual_speed==0);
 }
 IDirect3DVertexBuffer9_Release(ground);IDirect3DIndexBuffer9_Release(ground_indices);IDirect3DVertexShader9_Release(ground_shader);IDirect3DVertexDeclaration9_Release(ground_decl);
 puts("PASS runtime GPU constants, COM resource identities and stable scenery draw key recover 10 m/s while camera moves");
 CHECK(IDirect3DDevice9_Present(device,NULL,NULL,NULL,NULL));assert(runner_frames==1);
 CHECK(IDirect3DDevice9_SetStreamSource(device,0,NULL,0,0));IDirect3DVertexBuffer9_Release(vb);IDirect3DVertexBuffer9_Release(other);CHECK(IDirect3DDevice9_Reset(device,&pp));assert(!runner_renderer.device);assert(runner_remove());
 IDirect3DVertexShader9_Release(shader);IDirect3DVertexDeclaration9_Release(declaration);IDirect3DPixelShader9_Release(white);IDirect3DIndexBuffer9_Release(indices);uma_motion_free(&runner_motion);fclose(runner_log);runner_log=NULL;DeleteCriticalSection(&runner_lock);IDirect3DDevice9_Release(device);IDirect3D9_Release(api);DestroyWindow(window);
 puts("PASS native shader 5 renders animated textured body through runtime hook; stream offset and base vertex pass, cross-device hooks pass, same-size impostor retains original white output; Present, Reset and hook removal pass. Not NFSU2 gameplay.");return 0;
}
