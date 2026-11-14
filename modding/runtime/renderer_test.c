#include "uma_d3d.h"
#include "uma_camera.h"
#include "uma_upload.h"
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
static int check_native_lighting(IDirect3DDevice9 *device,const UmaMotion *motion,const D3DMATRIX *combined){
 const DWORD code[]={0xfffe0101,31,0x80000000,0x900f0000,31,0x80000005,0x900f0002,20,0xc00f0000,0x90e40000,0xa0e40000,1,0xd00f0000,0xa0e40004,1,0xe00f0001,0x90e40002,0xffff};
 const D3DVERTEXELEMENT9 elements[]={{0,0,D3DDECLTYPE_FLOAT3,0,D3DDECLUSAGE_POSITION,0},{0,12,D3DDECLTYPE_FLOAT3,0,D3DDECLUSAGE_NORMAL,0},{0,24,D3DDECLTYPE_D3DCOLOR,0,D3DDECLUSAGE_COLOR,0},{0,28,D3DDECLTYPE_FLOAT2,0,D3DDECLUSAGE_TEXCOORD,0},D3DDECL_END()};
 IDirect3DVertexShader9 *shader=NULL;IDirect3DVertexDeclaration9 *declaration=NULL;
 CHECK(IDirect3DDevice9_CreateVertexShader(device,code,&shader));CHECK(IDirect3DDevice9_CreateVertexDeclaration(device,elements,&declaration));
 CHECK(IDirect3DDevice9_SetVertexShader(device,shader));CHECK(IDirect3DDevice9_SetVertexDeclaration(device,declaration));
 float matrix[4][4];for(int r=0;r<4;r++)for(int c=0;c<4;c++)matrix[r][c]=combined->m[c][r];float diffuse[]={.25f,.25f,.25f,.125f};
 CHECK(IDirect3DDevice9_SetVertexShaderConstantF(device,0,&matrix[0][0],4));CHECK(IDirect3DDevice9_SetVertexShaderConstantF(device,4,diffuse,1));
 FILE *texture=fopen("modding/runtime/gpu-test/half-alpha.dds","rb");assert(texture);UmaD3D renderer={0};CHECK(uma_d3d_open(&renderer,device,motion,texture,observed_draw));fclose(texture);
 UmaMotionState state={0,.25f,1};CHECK(IDirect3DDevice9_Clear(device,0,NULL,D3DCLEAR_TARGET|D3DCLEAR_ZBUFFER,0xff252a32,1,0));CHECK(IDirect3DDevice9_BeginScene(device));CHECK(uma_d3d_draw(&renderer,&state,combined,0));CHECK(IDirect3DDevice9_EndScene(device));
 IDirect3DVertexShader9 *same_shader=NULL;IDirect3DVertexDeclaration9 *same_declaration=NULL;CHECK(IDirect3DDevice9_GetVertexShader(device,&same_shader));CHECK(IDirect3DDevice9_GetVertexDeclaration(device,&same_declaration));assert(same_shader==shader && same_declaration==declaration);IDirect3DVertexShader9_Release(same_shader);IDirect3DVertexDeclaration9_Release(same_declaration);
 DWORD *pixels=read_pixels(device);UINT count=0;for(int i=0;i<640*480;i++)if(pixels[i]!=0xff252a32){DWORD rgb=pixels[i]&0xffffff;assert(rgb==0x804020 || rgb==0x7f4020);count++;}assert(count>1000);free(pixels);
 const DWORD depth_code[]={0xfffe0101,31,0x80000000,0x900f0000,20,0xc00f0000,0x90e40000,0xa0e40000,0xffff};IDirect3DVertexShader9 *depth_shader=NULL;
 CHECK(IDirect3DDevice9_CreateVertexShader(device,depth_code,&depth_shader));CHECK(IDirect3DDevice9_SetVertexShader(device,depth_shader));CHECK(IDirect3DDevice9_SetRenderState(device,D3DRS_COLORWRITEENABLE,0));
 DWORD *before=read_pixels(device);CHECK(IDirect3DDevice9_BeginScene(device));CHECK(uma_d3d_draw(&renderer,&state,combined,0));CHECK(IDirect3DDevice9_EndScene(device));pixels=read_pixels(device);assert(!memcmp(before,pixels,640*480*4));free(before);free(pixels);
 DWORD write=99;CHECK(IDirect3DDevice9_GetRenderState(device,D3DRS_COLORWRITEENABLE,&write));assert(write==0);CHECK(IDirect3DDevice9_SetRenderState(device,D3DRS_COLORWRITEENABLE,7));IDirect3DVertexShader9_Release(depth_shader);
 puts("PASS position-only depth shader gains UV input on private clone; color writes remain disabled and pixels unchanged");
 uma_d3d_close(&renderer);CHECK(IDirect3DDevice9_SetVertexShader(device,NULL));IDirect3DVertexShader9_Release(shader);IDirect3DVertexDeclaration9_Release(declaration);
 puts("PASS native vertex shader/declaration preserved, native diffuse lighting applied and texture alpha retained without blending");return 0;
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
static void check_shader_bridge(void){
 for(UINT i=0;i<UMA_SHADER_PROFILE_COUNT;i++){
  UmaShaderEntry entry={0};entry.code=(DWORD*)uma_shader_profiles[i].words;entry.bytes=uma_shader_profiles[i].bytes;uma_shader_parse(&entry);assert(entry.supported && entry.uv>=0);assert(entry.worldview==uma_shader_profiles[i].worldview);assert(entry.worldviewproj==(int)uma_shader_profiles[i].rows[0]);
 }
 DWORD uv_only[]={0xfffe0101,31,0x80000000,0x900f0000,31,0x80000005,0x900f0002,1,0xc00f0000,0x90e40002,0xffff};
 UmaShaderEntry uv={0};uv.code=uv_only;uv.bytes=sizeof(uv_only);uma_shader_parse(&uv);assert(!uv.supported);
 DWORD mixed[]={0xfffe0101,31,0x80000000,0x900f0000,31,0x80000005,0x900f0002,2,0x800f0000,0x90e40000,0x90e40002,1,0xc00f0000,0x80e40000,0xffff};uv.code=mixed;uv.bytes=sizeof(mixed);uma_shader_parse(&uv);assert(!uv.supported);
 puts("PASS captured shader bridge parsing; UV-space composition passes rejected");
}
static int check_camera(IDirect3DDevice9 *device){
 DWORD vs1[]={0xfffe0101,20,0xc00f0000,0x90e40000,0xa0e40008,1,0xe0030000,0x90e40003,0xffff};
 DWORD vs2[]={0xfffe0200,0x0200001f,0x80000000,0x900f0000,0x03000014,0xc00f0000,0x90e40000,0xa0e40008,0xffff};
 UINT base=999;assert(uma_camera_constant(vs1,sizeof(vs1)/4,&base) && base==8);assert(uma_camera_constant(vs2,sizeof(vs2)/4,&base) && base==8);
 for(UINT n=0;n<sizeof(vs1)/4;n++){base=999;assert(!uma_camera_constant(vs1,n,&base) && base==999);}
 for(int kind=0;kind<6;kind++){
  DWORD bad[sizeof(vs1)/4];memcpy(bad,vs1,sizeof(vs1));
  if(kind==0)bad[3]=0x90e40001;
  if(kind==1)bad[4]|=0x2000;
  if(kind==2)bad[2]=0xc0030000;
  if(kind==3)bad[6]=0xc00f0000;
  if(kind==4)bad[1]=D3DSIO_DP4;
  if(kind==5)bad[4]=0xa0e400fd;
  base=999;assert(!uma_camera_constant(bad,sizeof(bad)/4,&base) && base==999);
 }
 float constants[4][4]={{.7f,.1f,0,.2f},{0,.6f,.2f,-.1f},{.1f,0,.4f,.3f},{0,0,0,1}};
 CHECK(IDirect3DDevice9_SetVertexShaderConstantF(device,8,&constants[0][0],4));
 for(int kind=0;kind<2;kind++){
  IDirect3DVertexShader9 *shader=NULL;CHECK(IDirect3DDevice9_CreateVertexShader(device,kind?vs2:vs1,&shader));CHECK(IDirect3DDevice9_SetVertexShader(device,shader));
  D3DMATRIX captured;CHECK(uma_camera_capture(device,&captured,NULL));
  for(int r=0;r<4;r++)for(int c=0;c<4;c++)assert(captured.m[r][c]==constants[c][r]);
  IDirect3DVertexShader9 *same=NULL;CHECK(IDirect3DDevice9_GetVertexShader(device,&same));assert(same==shader);IDirect3DVertexShader9_Release(same);CHECK(IDirect3DDevice9_SetVertexShader(device,NULL));IDirect3DVertexShader9_Release(shader);
 }
 for(UINT i=0;i<UMA_SHADER_PROFILE_COUNT;i++){
  const UmaShaderProfile *profile=&uma_shader_profiles[i];IDirect3DVertexShader9 *shader=NULL;
  CHECK(IDirect3DDevice9_CreateVertexShader(device,profile->words,&shader));CHECK(IDirect3DDevice9_SetVertexShader(device,shader));
  for(UINT row=0;row<4;row++)CHECK(IDirect3DDevice9_SetVertexShaderConstantF(device,profile->rows[row],constants[row],1));
  D3DMATRIX actual;CHECK(uma_camera_capture(device,&actual,NULL));
  for(int row=0;row<4;row++)for(int col=0;col<4;col++)assert(actual.m[row][col]==constants[col][row]*profile->signs[col]);
  IDirect3DVertexShader9 *same=NULL;CHECK(IDirect3DDevice9_GetVertexShader(device,&same));assert(same==shader);IDirect3DVertexShader9_Release(same);
  CHECK(IDirect3DDevice9_SetVertexShader(device,NULL));IDirect3DVertexShader9_Release(shader);
 }
 printf("PASS exact captured game shader profiles: %u programs; read-only camera extraction\n",(unsigned)UMA_SHADER_PROFILE_COUNT);
 D3DMATRIX world={0},view={0},projection={0},captured;
 for(int k=0;k<4;k++){world.m[k][k]=1;view.m[k][k]=1;projection.m[k][k]=1;}
 world.m[3][0]=2;view.m[0][0]=3;view.m[3][1]=4;projection.m[1][1]=5;
 CHECK(IDirect3DDevice9_SetTransform(device,D3DTS_WORLD,&world));CHECK(IDirect3DDevice9_SetTransform(device,D3DTS_VIEW,&view));CHECK(IDirect3DDevice9_SetTransform(device,D3DTS_PROJECTION,&projection));CHECK(uma_camera_capture(device,&captured,NULL));
 assert(captured.m[0][0]==3 && captured.m[1][1]==5 && captured.m[3][0]==6 && captured.m[3][1]==20);
 puts("PASS fixed-function and direct VS1.1/VS2 camera extraction; malformed and unsupported shaders rejected");return 0;
}
static int check_upload_identity(IDirect3DDevice9 *device,const UmaMotion *motion){
 UINT size=motion->vertices*sizeof(UmaVertex);IDirect3DVertexBuffer9 *candidate=NULL,*other=NULL,*managed=NULL;void *mapped=NULL;
 CHECK(IDirect3DDevice9_CreateVertexBuffer(device,size,D3DUSAGE_DYNAMIC|D3DUSAGE_WRITEONLY,0,D3DPOOL_DEFAULT,&candidate,NULL));
 CHECK(IDirect3DDevice9_CreateVertexBuffer(device,size,D3DUSAGE_DYNAMIC|D3DUSAGE_WRITEONLY,0,D3DPOOL_DEFAULT,&other,NULL));
 CHECK(IDirect3DDevice9_CreateVertexBuffer(device,size,0,0,D3DPOOL_MANAGED,&managed,NULL));
 assert(uma_upload_install(candidate,motion->rest,size));assert(!uma_upload_install(candidate,motion->rest,size));
 assert(!uma_upload_is_character(candidate) && !uma_upload_is_character(other));
 CHECK(IDirect3DVertexBuffer9_Lock(candidate,0,0,&mapped,D3DLOCK_DISCARD));memcpy(mapped,motion->rest,size);CHECK(IDirect3DVertexBuffer9_Unlock(candidate));assert(uma_upload_is_character(candidate));
 CHECK(IDirect3DVertexBuffer9_Lock(other,0,size,&mapped,D3DLOCK_DISCARD));memcpy(mapped,motion->rest,size);((BYTE*)mapped)[size-1]^=1;CHECK(IDirect3DVertexBuffer9_Unlock(other));assert(!uma_upload_is_character(other));
 CHECK(IDirect3DVertexBuffer9_Lock(other,0,0,&mapped,D3DLOCK_DISCARD));memcpy(mapped,motion->rest,size);((BYTE*)mapped)[24]^=127;CHECK(IDirect3DVertexBuffer9_Unlock(other));assert(uma_upload_is_character(other));
 CHECK(IDirect3DVertexBuffer9_Lock(candidate,4,4,&mapped,0));memset(mapped,0,4);assert(!uma_upload_is_character(candidate));CHECK(IDirect3DVertexBuffer9_Unlock(candidate));assert(!uma_upload_is_character(candidate));
 CHECK(IDirect3DVertexBuffer9_Lock(candidate,0,size,&mapped,D3DLOCK_DISCARD));memcpy(mapped,motion->rest,size);CHECK(IDirect3DVertexBuffer9_Unlock(candidate));assert(uma_upload_is_character(candidate));
 CHECK(IDirect3DVertexBuffer9_Lock(managed,0,size,&mapped,0));memcpy(mapped,motion->rest,size);CHECK(IDirect3DVertexBuffer9_Unlock(managed));assert(uma_upload_is_character(managed));
 CHECK(IDirect3DVertexBuffer9_Lock(managed,0,0,&mapped,D3DLOCK_READONLY));assert(!memcmp(mapped,motion->rest,size));CHECK(IDirect3DVertexBuffer9_Unlock(managed));assert(uma_upload_is_character(managed));
 void *second=NULL;
 CHECK(IDirect3DVertexBuffer9_Lock(managed,0,size,&mapped,0));memcpy(mapped,motion->rest,size);
 CHECK(IDirect3DVertexBuffer9_Lock(managed,0,size,&second,0));memcpy(second,motion->rest,size);
 CHECK(IDirect3DVertexBuffer9_Unlock(managed));assert(!uma_upload_is_character(managed));
 CHECK(IDirect3DVertexBuffer9_Unlock(managed));assert(!uma_upload_is_character(managed));
 CHECK(IDirect3DVertexBuffer9_Lock(candidate,0,0,&mapped,D3DLOCK_DISCARD));memset(mapped,0,size);CHECK(IDirect3DVertexBuffer9_Unlock(candidate));assert(!uma_upload_is_character(candidate));
 IDirect3DVertexBuffer9 *batched=NULL;CHECK(IDirect3DDevice9_CreateVertexBuffer(device,size+144,D3DUSAGE_DYNAMIC|D3DUSAGE_WRITEONLY,0,D3DPOOL_DEFAULT,&batched,NULL));
 CHECK(IDirect3DVertexBuffer9_Lock(batched,0,0,&mapped,D3DLOCK_DISCARD));memset(mapped,0,size+144);memcpy((BYTE*)mapped+72,motion->rest,size);CHECK(IDirect3DVertexBuffer9_Unlock(batched));
 assert(!uma_upload_is_character(batched) && uma_upload_matches_at(batched,72) && !uma_upload_matches_at(batched,36));
 CHECK(IDirect3DVertexBuffer9_Lock(batched,72,size,&mapped,0));memcpy(mapped,motion->rest,size);CHECK(IDirect3DVertexBuffer9_Unlock(batched));assert(uma_upload_matches_at(batched,72));
 CHECK(IDirect3DVertexBuffer9_Lock(batched,72,4,&mapped,0));memset(mapped,0,4);CHECK(IDirect3DVertexBuffer9_Unlock(batched));assert(!uma_upload_matches_at(batched,72));IDirect3DVertexBuffer9_Release(batched);
 IDirect3DVertexBuffer9_Release(managed);IDirect3DVertexBuffer9_Release(other);IDirect3DVertexBuffer9_Release(candidate);assert(uma_upload_remove());assert(!uma_upload_remove());
 puts("PASS full upload identity, one-byte impostor, partial/nested overwrite, READONLY, DISCARD and hook removal");return 0;
}
int main(void){
 freopen("modding/runtime/gpu-test/result.txt","w",stdout);freopen("modding/runtime/gpu-test/errors.txt","w",stderr);
 puts("START independent renderer test; not NFSU2");fflush(stdout);
 FILE *input=fopen("modding/runtime/kitasan.umab","rb");assert(input);UmaMotion motion={0};assert(uma_motion_load(input,&motion));fclose(input);
 HWND window=CreateWindowA("STATIC","Independent Kitasan renderer test",WS_POPUP,0,0,640,480,NULL,NULL,GetModuleHandle(NULL),NULL);assert(window);
 IDirect3D9 *api=Direct3DCreate9(D3D_SDK_VERSION);assert(api);
 D3DPRESENT_PARAMETERS pp={0};pp.Windowed=TRUE;pp.SwapEffect=D3DSWAPEFFECT_DISCARD;pp.hDeviceWindow=window;pp.BackBufferWidth=640;pp.BackBufferHeight=480;pp.BackBufferFormat=D3DFMT_A8R8G8B8;pp.EnableAutoDepthStencil=TRUE;pp.AutoDepthStencilFormat=D3DFMT_D24S8;
 IDirect3DDevice9 *device=NULL;CHECK(IDirect3D9_CreateDevice(api,0,D3DDEVTYPE_HAL,window,D3DCREATE_HARDWARE_VERTEXPROCESSING,&pp,&device));native_draw=(UmaDrawIndexed)(*(void***)device)[82];
 assert(check_upload_identity(device,&motion)==0);check_shader_bridge();assert(check_camera(device)==0);check_invalid_textures(device);
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
   CHECK(IDirect3DDevice9_Clear(device,0,NULL,D3DCLEAR_TARGET|D3DCLEAR_ZBUFFER,0xff252a32,1,0));CHECK(IDirect3DDevice9_BeginScene(device));CHECK(uma_d3d_draw(&renderer,&state,&combined,-1));check_restored(device,white,vb,ib,&original);
   CHECK(IDirect3DDevice9_DrawIndexedPrimitive(device,D3DPT_TRIANGLELIST,0,0,4,0,2));CHECK(IDirect3DDevice9_EndScene(device));
   DWORD *pixels=read_pixels(device);assert(pixels[8*640+8]==0xffffffff);UINT different=0,orange=0;DWORD hash=2166136261u;
   for(int y=20;y<480;y++)for(int x=0;x<640;x++){DWORD p=pixels[y*640+x];if(p!=0xff252a32)different++;if(p==0xffff8040)orange++;hash=(hash^p)*16777619u;}
   if(kind==0){assert(orange>1000 && orange==different);puts("PASS half-alpha texture produces opaque RGB without background blending");}
   if(kind==1){assert(different==0);puts("PASS zero-alpha texture is discarded");}
   if(kind==2){assert(different>1000);if(frame)assert(hash!=previous_hash);previous_hash=hash;char path[128];snprintf(path,sizeof(path),"modding/runtime/gpu-test/run-%d.ppm",frame);save_ppm(path,pixels);printf("PASS animated frame %d; %u non-background pixels; unrelated quad remains white\n",frame,different);}
   free(pixels);
  }
  if(kind==2){
   UmaMotionState invalid=state;invalid.idle_phase=NAN;CHECK(IDirect3DDevice9_BeginScene(device));assert(uma_d3d_draw(&renderer,&invalid,&combined,-1)==E_INVALIDARG);assert(!renderer.has_uploaded);CHECK(uma_d3d_draw(&renderer,&state,&combined,-1));CHECK(IDirect3DDevice9_EndScene(device));assert(renderer.has_uploaded);
   DWORD *recovered=read_pixels(device);DWORD recovered_hash=2166136261u;for(int y=20;y<480;y++)for(int x=0;x<640;x++)recovered_hash=(recovered_hash^recovered[y*640+x])*16777619u;assert(recovered_hash==previous_hash);free(recovered);puts("PASS invalid pose invalidates upload cache; repeated valid pose recovers identical GPU pixels");
  }
  fail_draw=1;CHECK(IDirect3DDevice9_BeginScene(device));assert(uma_d3d_draw(&renderer,&state,&combined,-1)==E_FAIL);check_restored(device,white,vb,ib,&original);CHECK(IDirect3DDevice9_EndScene(device));fail_draw=0;
  uma_d3d_close(&renderer);
 }
 assert(check_native_lighting(device,&motion,&combined)==0);
 CHECK(IDirect3DDevice9_Reset(device,&pp));input=fopen("modding/runtime/atlas.dds","rb");assert(input);CHECK(uma_d3d_open(&renderer,device,&motion,input,observed_draw));fclose(input);CHECK(IDirect3DDevice9_BeginScene(device));CHECK(uma_d3d_draw(&renderer,&state,&combined,-1));CHECK(IDirect3DDevice9_EndScene(device));uma_d3d_close(&renderer);
 assert(uma_motion_step(&state,1.f/60,6,0));uma_motion_free(&motion);IDirect3DVertexBuffer9_Release(vb);IDirect3DIndexBuffer9_Release(ib);IDirect3DPixelShader9_Release(white);IDirect3DDevice9_Release(device);IDirect3D9_Release(api);DestroyWindow(window);
 printf("PASS all renderer checks, failure restoration and device reset; %u intercepted draws. No game integration tested.\n",draws);return 0;
}
