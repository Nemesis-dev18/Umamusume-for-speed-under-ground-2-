#ifndef UMA_D3D_H
#define UMA_D3D_H
#define COBJMACROS
#include <windows.h>
#include <d3d9.h>
#include <wchar.h>
#include "uma_motion.h"
#include "uma_cloth_surface.h"
#include "uma_foot_sparks.h"
#include "uma_resource_tags.h"
#include "uma_shader_bridge.h"

#ifdef UMA_PROFILE
static LONGLONG uma_profile_skin_ticks,uma_profile_upload_ticks,uma_profile_draw_ticks;
static unsigned uma_profile_uploads,uma_profile_draws;
static LONGLONG uma_profile_now(void){LARGE_INTEGER t;QueryPerformanceCounter(&t);return t.QuadPart;}
#endif

typedef HRESULT (WINAPI *UmaDrawSparks)(IDirect3DDevice9*,D3DPRIMITIVETYPE,UINT,const void*,UINT);
typedef HRESULT (WINAPI *UmaDrawIndexed)(IDirect3DDevice9*,D3DPRIMITIVETYPE,INT,UINT,UINT,UINT,UINT);
typedef struct {
 IDirect3DDevice9 *device;IDirect3DVertexBuffer9 *vertices;IDirect3DIndexBuffer9 *indices;
 IDirect3DTexture9 *texture;IDirect3DVertexDeclaration9 *declaration;IDirect3DPixelShader9 *shader,*native_shader;UmaShaderCache shaders;
 IDirect3DPixelShader9 *spark_shader;UmaDrawSparks spark_draw;float spark_feet[2][3];unsigned spark_contacts[2];
 IDirect3DTexture9 *material_textures[16];unsigned material_texture_count,batch_count;
 struct {uint32_t first,count,texture,visible;} batch[64];
 IDirect3DStateBlock9 *saved;UmaVertex *pose,*local_pose,*surface_base;unsigned skin_samples;float *surface_weight;uint16_t *surface_edges;uint32_t surface_edge_count;
 const UmaMotion *motion;UmaDrawIndexed draw;UmaMotionState uploaded;float uploaded_root[9];int has_uploaded,uploaded_root_valid;const float *secondary,*uploaded_secondary;uint32_t secondary_revision,uploaded_secondary_revision;
} UmaD3D;
static void uma_d3d_close(UmaD3D *renderer){
 if(!renderer)return;
 if(renderer->saved)IDirect3DStateBlock9_Release(renderer->saved);
 if(renderer->shader)IDirect3DPixelShader9_Release(renderer->shader);
 if(renderer->spark_shader)IDirect3DPixelShader9_Release(renderer->spark_shader);
 if(renderer->native_shader)IDirect3DPixelShader9_Release(renderer->native_shader);
 uma_shader_cache_clear(&renderer->shaders);
 for(unsigned i=0;i<16;i++)if(renderer->material_textures[i])IDirect3DTexture9_Release(renderer->material_textures[i]);
 if(renderer->texture)IDirect3DTexture9_Release(renderer->texture);
 if(renderer->declaration)IDirect3DVertexDeclaration9_Release(renderer->declaration);
 if(renderer->indices)IDirect3DIndexBuffer9_Release(renderer->indices);
 if(renderer->vertices)IDirect3DVertexBuffer9_Release(renderer->vertices);
 if(renderer->device)IDirect3DDevice9_Release(renderer->device);
 free(renderer->pose);free(renderer->local_pose);free(renderer->surface_base);free(renderer->surface_weight);free(renderer->surface_edges);
 memset(renderer,0,sizeof(*renderer));
}
static HRESULT uma_texture_load(IDirect3DDevice9 *device,FILE *file,IDirect3DTexture9 **output){
 unsigned char h[128];
 if(!file || !output || fread(h,1,128,file)!=128 || memcmp(h,"DDS ",4) || uma_le32(h+4)!=124 || uma_le32(h+76)!=32 || uma_le32(h+112) || uma_le32(h+24)>1 || (uma_le32(h+8)&0x1007)!=0x1007)return E_INVALIDARG;
 UINT width=uma_le32(h+16),height=uma_le32(h+12),levels=uma_le32(h+28);
 DWORD pf=uma_le32(h+80);BOOL compressed=(pf&4) && uma_le32(h+84)==D3DFMT_DXT5;
 BOOL bgra=(pf&0x41)==0x41 && !uma_le32(h+84) && uma_le32(h+88)==32 && uma_le32(h+92)==0xff0000 && uma_le32(h+96)==0xff00 && uma_le32(h+100)==0xff && uma_le32(h+104)==0xff000000;
 if(!compressed && !bgra)return E_INVALIDARG;
 if(!width || !height || width>4096 || height>4096 || (width&(width-1)) || (height&(height-1)) || !levels || levels>13)return E_INVALIDARG;
 UINT w=width,hh=height,count=0;size_t total=0;
 do{total+=compressed?(size_t)((w+3)/4)*((hh+3)/4)*16:(size_t)w*hh*4;count++;if(w==1 && hh==1)break;w=w>1?w/2:1;hh=hh>1?hh/2:1;}while(count<=13);
 if(total>32*1024*1024 || count!=levels)return E_INVALIDARG;
 IDirect3DTexture9 *texture=NULL;HRESULT result=IDirect3DDevice9_CreateTexture(device,width,height,levels,0,compressed?D3DFMT_DXT5:D3DFMT_A8R8G8B8,D3DPOOL_MANAGED,&texture,NULL);
 if(FAILED(result))return result;
 w=width;hh=height;
 for(UINT level=0;level<levels;level++){
  D3DLOCKED_RECT locked;result=IDirect3DTexture9_LockRect(texture,level,&locked,NULL,0);if(FAILED(result))goto invalid;
  UINT row_bytes=compressed?((w+3)/4)*16:w*4,rows=compressed?(hh+3)/4:hh;
  BOOL complete=locked.Pitch>=(INT)row_bytes;
  if(complete)for(UINT row=0;row<rows;row++)if(fread((BYTE*)locked.pBits+(size_t)row*locked.Pitch,1,row_bytes,file)!=row_bytes){complete=FALSE;break;}
  result=IDirect3DTexture9_UnlockRect(texture,level);if(FAILED(result) || !complete){result=E_FAIL;goto invalid;}
  w=w>1?w/2:1;hh=hh>1?hh/2:1;
 }
 if(fgetc(file)!=EOF){result=E_INVALIDARG;goto invalid;}
 *output=texture;return S_OK;
invalid:
 IDirect3DTexture9_Release(texture);return result;
}
/* Optional native material ranges; old atlas models keep their single draw. */
static inline HRESULT uma_d3d_materials_load(UmaD3D *r,const WCHAR *atlas){
 if(!r || !r->device || !atlas || wcslen(atlas)>3800 || r->batch_count)return E_INVALIDARG;
 WCHAR folder[4096],path[4096];wcscpy(folder,atlas);WCHAR *end=wcsrchr(folder,L'\\');if(!end)end=wcsrchr(folder,L'/');if(!end)return E_INVALIDARG;*end=0;
 swprintf(path,4096,L"%ls\\materials.bin",folder);FILE *file=_wfopen(path,L"rb");
 if(!file){DWORD attributes=GetFileAttributesW(path);return attributes==INVALID_FILE_ATTRIBUTES && GetLastError()==ERROR_FILE_NOT_FOUND?S_FALSE:E_FAIL;}
 uint32_t h[4];HRESULT result=E_INVALIDARG;
 if(fread(h,4,4,file)!=4 || memcmp(h,"UMAM",4) || h[1]!=1 || !h[2] || h[2]>64 || !h[3] || h[3]>16)goto done;
 if(fread(r->batch,16,h[2],file)!=h[2] || fgetc(file)!=EOF)goto done;
 uint32_t next=0;
 for(unsigned i=0;i<h[2];i++){
  if(r->batch[i].first!=next || r->batch[i].count%3 || r->batch[i].count>r->motion->indices-next || r->batch[i].texture>=h[3] || r->batch[i].visible>1)goto done;
  next+=r->batch[i].count;
 }
 if(next!=r->motion->indices)goto done;
 for(unsigned i=0;i<h[3];i++){
  swprintf(path,4096,L"%ls\\material-%02u.dds",folder,i);FILE *texture=_wfopen(path,L"rb");if(!texture){result=E_FAIL;goto done;}
  result=uma_texture_load(r->device,texture,&r->material_textures[i]);fclose(texture);if(FAILED(result))goto done;
 }
 r->batch_count=h[2];r->material_texture_count=h[3];result=S_OK;
done:
 fclose(file);
 if(FAILED(result)){for(unsigned i=0;i<16;i++)if(r->material_textures[i]){IDirect3DTexture9_Release(r->material_textures[i]);r->material_textures[i]=NULL;}r->batch_count=r->material_texture_count=0;}
 return result;
}
/* Called with a zero-initialized renderer; all partial resources are released on failure. */
static HRESULT uma_d3d_open(UmaD3D *output,IDirect3DDevice9 *device,const UmaMotion *motion,FILE *texture,UmaDrawIndexed draw){
 if(!output || output->device || !device || !motion || !motion->memory || !draw)return E_INVALIDARG;
 UmaD3D r={0};r.device=device;r.motion=motion;r.draw=draw;IDirect3DDevice9_AddRef(device);
 HRESULT result=E_OUTOFMEMORY;r.pose=malloc((size_t)motion->vertices*sizeof(*r.pose));r.local_pose=malloc((size_t)motion->vertices*sizeof(*r.local_pose));if(!r.pose || !r.local_pose)goto invalid;
 if(motion->surface_mask){
  unsigned count=0;for(unsigned b=0;b<motion->bones;b++)count+=!!motion->surface_mask[b];
  if(count){
   r.surface_base=malloc((size_t)motion->vertices*sizeof(*r.surface_base));r.surface_weight=calloc(motion->vertices,sizeof(*r.surface_weight));if(!r.surface_base || !r.surface_weight)goto invalid;
   for(unsigned v=0;v<motion->vertices;v++)for(int j=0;j<4;j++)if(motion->surface_mask[motion->skin[v].bone[j]])r.surface_weight[v]+=motion->skin[v].weight[j];
   r.surface_edges=malloc((size_t)motion->indices*4);if(!r.surface_edges)goto invalid;r.surface_edge_count=uma_cloth_edges(motion,r.surface_weight,r.surface_edges);
  }
 }
 result=IDirect3DDevice9_CreateVertexBuffer(device,motion->vertices*36,D3DUSAGE_DYNAMIC|D3DUSAGE_WRITEONLY,0,D3DPOOL_DEFAULT,&r.vertices,NULL);if(FAILED(result))goto invalid;
 DWORD owned=1;result=IDirect3DVertexBuffer9_SetPrivateData(r.vertices,&uma_renderer_buffer_guid,&owned,sizeof(owned),0);if(FAILED(result))goto invalid;
 result=IDirect3DDevice9_CreateIndexBuffer(device,motion->indices*2,0,D3DFMT_INDEX16,D3DPOOL_MANAGED,&r.indices,NULL);if(FAILED(result))goto invalid;
 void *indices=NULL;result=IDirect3DIndexBuffer9_Lock(r.indices,0,motion->indices*2,&indices,0);if(FAILED(result))goto invalid;
 memcpy(indices,motion->index,motion->indices*2);result=IDirect3DIndexBuffer9_Unlock(r.indices);if(FAILED(result))goto invalid;
 result=uma_texture_load(device,texture,&r.texture);if(FAILED(result))goto invalid;
 static const DWORD code[]={0xffff0101,0x42,0xb00f0000,0x1,0x800f0000,0xb0e40000,0xffff};
 result=IDirect3DDevice9_CreatePixelShader(device,code,&r.shader);if(FAILED(result))goto invalid;
 /* Car shaders halve diffuse; the new diffuse-only pass restores that scale. */
 static const DWORD lit[]={0xffff0101,0x42,0xb00f0000,5,0x810f0000,0xb0e40000,0x90e40000,1,0x80080000,0xb0ff0000,0xffff};
 result=IDirect3DDevice9_CreatePixelShader(device,lit,&r.native_shader);if(FAILED(result))goto invalid;
 static const DWORD spark_code[]={0xffff0101,0x51,0xa00f0000,0x3f800000,0x3f333333,0x3dcccccd,0x3f800000,0x1,0x800f0000,0xa0e40000,0xffff};
 result=IDirect3DDevice9_CreatePixelShader(device,spark_code,&r.spark_shader);if(FAILED(result))goto invalid;
 static const D3DVERTEXELEMENT9 elements[]={{0,0,D3DDECLTYPE_FLOAT3,0,D3DDECLUSAGE_POSITION,0},{0,12,D3DDECLTYPE_FLOAT3,0,D3DDECLUSAGE_NORMAL,0},{0,24,D3DDECLTYPE_D3DCOLOR,0,D3DDECLUSAGE_COLOR,0},{0,28,D3DDECLTYPE_FLOAT2,0,D3DDECLUSAGE_TEXCOORD,0},D3DDECL_END()};
 result=IDirect3DDevice9_CreateVertexDeclaration(device,elements,&r.declaration);if(FAILED(result))goto invalid;
 *output=r;return S_OK;
invalid:
 uma_d3d_close(&r);return result;
}
/* Caller supplies the camera/object transform and invokes this inside its scene. */
static HRESULT uma_d3d_draw(UmaD3D *r,const UmaMotionState *state,const D3DMATRIX *combined,int use_native,const float *root){
 if(!r || !r->device || !state || (use_native!=-1 && use_native!=0))return E_INVALIDARG;
#ifdef UMA_PROFILE
 LONGLONG profile_start=uma_profile_now();
#endif
 HRESULT result=S_OK;UmaShaderEntry *entry=NULL;int native=use_native==0;DWORD incoming_color=7;IDirect3DDevice9_GetRenderState(r->device,D3DRS_COLORWRITEENABLE,&incoming_color);int depth_only=incoming_color==0;
 if(native){entry=uma_shader_get(&r->shaders,r->device,&result);if(FAILED(result))return result;if(entry){result=uma_shader_clone(r->device,entry);if(FAILED(result))return result;}else native=0;}
 if(!native){if(!combined)return E_INVALIDARG;for(int row=0;row<4;row++)for(int column=0;column<4;column++)if(!isfinite(combined->m[row][column]) || fabsf(combined->m[row][column])>1e6)return E_INVALIDARG;}

 if(root)for(int r=0;r<3;r++)for(int c=0;c<3;c++){
  float dot=0;for(int k=0;k<3;k++){if(!isfinite(root[r*3+k]))return E_INVALIDARG;dot+=root[r*3+k]*root[c*3+k];}
  if(fabsf(dot-(r==c))>.02f)return E_INVALIDARG;
 }
 /* Root-only reflection/camera changes reuse the unrotated skin and garment solution. */
 int pose_changed=!r->has_uploaded || r->secondary!=r->uploaded_secondary || r->secondary_revision!=r->uploaded_secondary_revision || state->idle_phase!=r->uploaded.idle_phase || state->run_phase!=r->uploaded.run_phase || state->run_blend!=r->uploaded.run_blend;
 if(pose_changed || (!!root)!=r->uploaded_root_valid || (root && memcmp(root,r->uploaded_root,sizeof(r->uploaded_root)))){
  r->has_uploaded=0;
#ifdef UMA_PROFILE
  LONGLONG profile_upload=uma_profile_now();
#endif
  int sampled=1;
  if(pose_changed){
#ifdef UMA_PROFILE
   LONGLONG profile_skin=uma_profile_now();
#endif
   sampled=uma_motion_sample_secondary(r->motion,state->idle_phase,state->run_phase,state->run_blend,r->local_pose,(size_t)r->motion->vertices*36,r->secondary);
   if(sampled && r->secondary && r->surface_base)sampled=uma_cloth_project(r->motion,state,r->local_pose,r->surface_base,r->surface_weight,r->surface_edges,r->surface_edge_count);
   if(sampled && r->spark_draw)uma_spark_contacts(r->motion,r->local_pose,r->spark_feet,r->spark_contacts);
   if(sampled)r->skin_samples++;
#ifdef UMA_PROFILE
   uma_profile_skin_ticks+=uma_profile_now()-profile_skin;
#endif
  }
  if(sampled)memcpy(r->pose,r->local_pose,(size_t)r->motion->vertices*36);
  if(sampled && root)for(uint32_t i=0;i<r->motion->vertices;i++){
   UmaVertex *vertex=r->pose+i;float position[3]={0},normal[3]={0};
   for(int c=0;c<3;c++)for(int k=0;k<3;k++){position[c]+=vertex->position[k]*root[k*3+c];normal[c]+=vertex->normal[k]*root[k*3+c];}
   memcpy(vertex->position,position,sizeof(position));memcpy(vertex->normal,normal,sizeof(normal));
  }
  if(!sampled)return E_INVALIDARG;
  void *mapped=NULL;result=IDirect3DVertexBuffer9_Lock(r->vertices,0,r->motion->vertices*36,&mapped,D3DLOCK_DISCARD);if(FAILED(result))return result;
  memcpy(mapped,r->pose,(size_t)r->motion->vertices*sizeof(*r->pose));
  result=IDirect3DVertexBuffer9_Unlock(r->vertices);if(FAILED(result))return result;
  r->uploaded_root_valid=root!=NULL;if(root)memcpy(r->uploaded_root,root,sizeof(r->uploaded_root));
  r->uploaded=*state;r->uploaded_secondary=r->secondary;r->uploaded_secondary_revision=r->secondary_revision;r->has_uploaded=1;
#ifdef UMA_PROFILE
  uma_profile_upload_ticks+=uma_profile_now()-profile_upload;uma_profile_uploads++;
#endif
 }
 if(!r->saved){result=IDirect3DDevice9_CreateStateBlock(r->device,D3DSBT_ALL,&r->saved);if(FAILED(result))return result;}
 result=IDirect3DStateBlock9_Capture(r->saved);if(FAILED(result))return result;
 #define UMA_SET(call) do{result=(call);if(FAILED(result))goto restore;}while(0)
 D3DMATRIX identity={0};for(int i=0;i<4;i++)identity.m[i][i]=1;
 if(!native){UMA_SET(IDirect3DDevice9_SetVertexShader(r->device,NULL));UMA_SET(IDirect3DDevice9_SetFVF(r->device,D3DFVF_XYZ|D3DFVF_NORMAL|D3DFVF_DIFFUSE|D3DFVF_TEX1));}
 if(native){
  UMA_SET(IDirect3DDevice9_SetVertexShader(r->device,entry->clone));
  UMA_SET(IDirect3DDevice9_SetVertexDeclaration(r->device,r->declaration));
  /* Keep the costume colors independent of the car paint color. */
  for(int i=0;i<2;i++){int reg=i?entry->diffuse_range:entry->diffuse_min;if(reg>=0){float value[4];UMA_SET(IDirect3DDevice9_GetVertexShaderConstantF(r->device,(UINT)reg,value,1));for(int c=0;c<3;c++)value[c]=i?0:1;UMA_SET(IDirect3DDevice9_SetVertexShaderConstantF(r->device,(UINT)reg,value,1));}}
 }
 UMA_SET(IDirect3DDevice9_SetPixelShader(r->device,native && !depth_only?r->native_shader:r->shader));
 UMA_SET(IDirect3DDevice9_SetStreamSource(r->device,0,r->vertices,0,36));UMA_SET(IDirect3DDevice9_SetStreamSourceFreq(r->device,0,1));UMA_SET(IDirect3DDevice9_SetIndices(r->device,r->indices));
 if(!native){UMA_SET(IDirect3DDevice9_SetTransform(r->device,D3DTS_WORLD,&identity));UMA_SET(IDirect3DDevice9_SetTransform(r->device,D3DTS_VIEW,&identity));UMA_SET(IDirect3DDevice9_SetTransform(r->device,D3DTS_PROJECTION,combined));}
 UINT stage=0;
 UMA_SET(IDirect3DDevice9_SetTexture(r->device,stage,(IDirect3DBaseTexture9*)r->texture));
 UMA_SET(IDirect3DDevice9_SetTextureStageState(r->device,0,D3DTSS_TEXCOORDINDEX,0));UMA_SET(IDirect3DDevice9_SetTextureStageState(r->device,0,D3DTSS_TEXTURETRANSFORMFLAGS,D3DTTFF_DISABLE));
 const D3DSAMPLERSTATETYPE sampler_names[]={D3DSAMP_MINFILTER,D3DSAMP_MAGFILTER,D3DSAMP_MIPFILTER,D3DSAMP_ADDRESSU,D3DSAMP_ADDRESSV,D3DSAMP_SRGBTEXTURE};
 const DWORD sampler_values[]={D3DTEXF_LINEAR,D3DTEXF_LINEAR,D3DTEXF_LINEAR,D3DTADDRESS_CLAMP,D3DTADDRESS_CLAMP,FALSE};
 for(int i=0;i<6;i++)UMA_SET(IDirect3DDevice9_SetSamplerState(r->device,stage,sampler_names[i],sampler_values[i]));
 const D3DRENDERSTATETYPE names[]={D3DRS_LIGHTING,D3DRS_CULLMODE,D3DRS_ALPHATESTENABLE,D3DRS_ALPHAFUNC,D3DRS_ALPHAREF,D3DRS_ALPHABLENDENABLE,D3DRS_SEPARATEALPHABLENDENABLE,D3DRS_ZENABLE,D3DRS_ZWRITEENABLE,D3DRS_ZFUNC,D3DRS_FOGENABLE,D3DRS_STENCILENABLE,D3DRS_SCISSORTESTENABLE,D3DRS_CLIPPLANEENABLE,D3DRS_COLORWRITEENABLE,D3DRS_FILLMODE,D3DRS_SRGBWRITEENABLE,D3DRS_DEPTHBIAS,D3DRS_SLOPESCALEDEPTHBIAS};
 const DWORD values[]={FALSE,D3DCULL_NONE,TRUE,D3DCMP_GREATER,32,FALSE,FALSE,D3DZB_TRUE,TRUE,D3DCMP_LESSEQUAL,FALSE,FALSE,FALSE,0,7,D3DFILL_SOLID,FALSE,0,0};
 for(UINT i=0;i<sizeof(names)/sizeof(names[0]);i++){if(native && (names[i]==D3DRS_STENCILENABLE || names[i]==D3DRS_SCISSORTESTENABLE || names[i]==D3DRS_CLIPPLANEENABLE || names[i]==D3DRS_FOGENABLE || (depth_only && names[i]==D3DRS_ZWRITEENABLE)))continue;UMA_SET(IDirect3DDevice9_SetRenderState(r->device,names[i],depth_only && names[i]==D3DRS_COLORWRITEENABLE?0:values[i]));}
 if(r->batch_count){
  UMA_SET(IDirect3DDevice9_SetSamplerState(r->device,0,D3DSAMP_ADDRESSU,D3DTADDRESS_WRAP));
  UMA_SET(IDirect3DDevice9_SetSamplerState(r->device,0,D3DSAMP_ADDRESSV,D3DTADDRESS_WRAP));
  for(unsigned i=0;i<r->batch_count;i++)if(r->batch[i].visible && r->batch[i].count){
   UMA_SET(IDirect3DDevice9_SetTexture(r->device,0,(IDirect3DBaseTexture9*)r->material_textures[r->batch[i].texture]));
   UMA_SET(r->draw(r->device,D3DPT_TRIANGLELIST,0,0,r->motion->vertices,r->batch[i].first,r->batch[i].count/3));
  }
 }else result=r->draw(r->device,D3DPT_TRIANGLELIST,0,0,r->motion->vertices,0,r->motion->indices/3);
 if(SUCCEEDED(result) && !depth_only && state->run_blend>.6f && r->spark_draw){
  UmaVertex sparks[24];unsigned count=uma_spark_mesh(state->run_phase,r->spark_feet,r->spark_contacts,root,sparks);
  if(count){
   UMA_SET(IDirect3DDevice9_SetPixelShader(r->device,r->spark_shader));
   UMA_SET(IDirect3DDevice9_SetRenderState(r->device,D3DRS_ALPHATESTENABLE,FALSE));
   UMA_SET(IDirect3DDevice9_SetRenderState(r->device,D3DRS_ALPHABLENDENABLE,TRUE));
   UMA_SET(IDirect3DDevice9_SetRenderState(r->device,D3DRS_SRCBLEND,D3DBLEND_ONE));
   UMA_SET(IDirect3DDevice9_SetRenderState(r->device,D3DRS_DESTBLEND,D3DBLEND_ONE));
   UMA_SET(IDirect3DDevice9_SetRenderState(r->device,D3DRS_ZWRITEENABLE,FALSE));
   UMA_SET(r->spark_draw(r->device,D3DPT_TRIANGLELIST,count/3,sparks,36));
  }
 }
restore:
 {HRESULT restored=IDirect3DStateBlock9_Apply(r->saved);if(SUCCEEDED(result) && FAILED(restored))result=restored;}
 #undef UMA_SET
#ifdef UMA_PROFILE
 uma_profile_draw_ticks+=uma_profile_now()-profile_start;uma_profile_draws++;
#endif
 return result;
}
#endif
