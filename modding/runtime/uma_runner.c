#define COBJMACROS
#include <windows.h>
#include <d3d9.h>
#include <wchar.h>
#include "uma_d3d.h"
#include "uma_upload.h"
#include "uma_scene_speed.h"
#include "uma_wheels.h"
#include "uma_audio_win.h"
typedef HRESULT (WINAPI *RunnerPresent)(IDirect3DDevice9*,const RECT*,const RECT*,HWND,const RGNDATA*);
typedef HRESULT (WINAPI *RunnerReset)(IDirect3DDevice9*,D3DPRESENT_PARAMETERS*);
typedef HRESULT (WINAPI *RunnerPrimitive)(IDirect3DDevice9*,D3DPRIMITIVETYPE,UINT,UINT);
typedef HRESULT (WINAPI *RunnerPrimitiveUP)(IDirect3DDevice9*,D3DPRIMITIVETYPE,UINT,const void*,UINT);
typedef HRESULT (WINAPI *RunnerIndexedUP)(IDirect3DDevice9*,D3DPRIMITIVETYPE,UINT,UINT,UINT,const void*,D3DFORMAT,const void*,UINT);
static RunnerPrimitive runner_original_primitive;
static RunnerPrimitiveUP runner_original_primitive_up;
static RunnerIndexedUP runner_original_indexed_up;
static UmaDrawIndexed runner_original_draw;
static RunnerPresent runner_original_present;
static RunnerReset runner_original_reset;
static void **runner_table;
static CRITICAL_SECTION runner_lock;
static UmaMotion runner_motion;
/* shortcut: Corolla instances share gait; use per-instance tracking before supporting multiple character actors. */
static UmaMotionState runner_state;
static UmaD3D runner_renderer;
static UmaSceneSpeed runner_scene;
static WCHAR runner_atlas[4096];
static FILE *runner_log;
static ULONGLONG runner_last_tick;
static unsigned runner_frames,runner_candidates,runner_owned,runner_replaced,runner_shader_failures;
static unsigned runner_hidden_wheels,runner_tire_candidates,runner_camera_reports;
static struct {UINT vertices,primitives,shader;const char *method;int match,racing;} runner_wheel_reports[96];
static int runner_speed_valid;
static float runner_speed;
static unsigned runner_last_owned,runner_projected_references;
static UmaMatrix runner_inverse_projection;
static int runner_projection_valid;
static int runner_combined(IDirect3DDevice9 *device,const UmaShaderEntry *entry,UmaMatrix *output){
 if(!entry || entry->worldviewproj<0)return 0;
 float rows[4][4];if(FAILED(IDirect3DDevice9_GetVertexShaderConstantF(device,(UINT)entry->worldviewproj,&rows[0][0],4)))return 0;
 for(int r=0;r<4;r++)for(int c=0;c<4;c++){if(!isfinite(rows[c][r]))return 0;output->m[r][c]=rows[c][r];}
 return 1;
}
static int runner_worldview(IDirect3DDevice9 *device,const UmaShaderEntry *entry,UmaMatrix *output){
 UmaMatrix matrix={0};matrix.m[3][3]=1;
 if(entry){
  if(entry->worldview<0){
   UmaMatrix combined;if(!entry->reference || !runner_projection_valid || !runner_combined(device,entry,&combined))return 0;
   matrix=uma_matrix_product(&combined,&runner_inverse_projection);if(!uma_rigid(&matrix))return 0;
   *output=matrix;runner_projected_references++;return 1;
  }
  float rows[3][4];if(FAILED(IDirect3DDevice9_GetVertexShaderConstantF(device,(UINT)entry->worldview,&rows[0][0],3)))return 0;
  for(int r=0;r<4;r++)for(int c=0;c<3;c++)matrix.m[r][c]=rows[c][r];
 }else{
  D3DMATRIX world,view;if(FAILED(IDirect3DDevice9_GetTransform(device,D3DTS_WORLD,&world)) || FAILED(IDirect3DDevice9_GetTransform(device,D3DTS_VIEW,&view)))return 0;
  memset(&matrix,0,sizeof(matrix));for(int r=0;r<4;r++)for(int c=0;c<4;c++)for(int k=0;k<4;k++)matrix.m[r][c]+=world.m[r][k]*view.m[k][c];
 }
 for(int r=0;r<4;r++)for(int c=0;c<4;c++)if(!isfinite(matrix.m[r][c]))return 0;
 *output=matrix;return 1;
}
static int runner_fixed_combined(IDirect3DDevice9 *device,D3DMATRIX *combined){
 D3DMATRIX projection;UmaMatrix worldview;if(!runner_worldview(device,NULL,&worldview) || FAILED(IDirect3DDevice9_GetTransform(device,D3DTS_PROJECTION,&projection)))return 0;
 memset(combined,0,sizeof(*combined));for(int r=0;r<4;r++)for(int c=0;c<4;c++)for(int k=0;k<4;k++)combined->m[r][c]+=worldview.m[r][k]*projection.m[k][c];return 1;
}
static const GUID runner_resource_guid={0x9e814763,0xa906,0x47ba,{0xa9,0x63,0x9b,0x11,0x65,0x67,0x3d,0x54}};
static DWORD runner_next_resource;
static DWORD runner_resource_id(IDirect3DResource9 *resource){
 DWORD id=0,size=sizeof(id);if(!resource)return 0;
 if(SUCCEEDED(IDirect3DResource9_GetPrivateData(resource,&runner_resource_guid,&id,&size)) && size==sizeof(id) && id)return id;
 if(runner_next_resource==UINT32_MAX)return 0;
 id=++runner_next_resource;if(FAILED(IDirect3DResource9_SetPrivateData(resource,&runner_resource_guid,&id,sizeof(id),0)))return 0;return id;
}
static void runner_reference(IDirect3DDevice9 *device,IDirect3DVertexBuffer9 *vb,INT base,UINT minimum,UINT vertices,UINT start,UINT triangles,UINT offset,const UmaMatrix *worldview){
 DWORD zwrite=0,blend=1;D3DVERTEXBUFFER_DESC descriptor;
 if(vertices<64 || triangles<24 || FAILED(IDirect3DVertexBuffer9_GetDesc(vb,&descriptor)) || (descriptor.Usage&D3DUSAGE_DYNAMIC))return;
 if(FAILED(IDirect3DDevice9_GetRenderState(device,D3DRS_ZWRITEENABLE,&zwrite)) || !zwrite || FAILED(IDirect3DDevice9_GetRenderState(device,D3DRS_ALPHABLENDENABLE,&blend)) || blend)return;
 IDirect3DIndexBuffer9 *indices=NULL;D3DVIEWPORT9 viewport;if(FAILED(IDirect3DDevice9_GetIndices(device,&indices)) || !indices)return;
 UmaSceneKey key={0};key.buffer=runner_resource_id((IDirect3DResource9*)vb);key.index=runner_resource_id((IDirect3DResource9*)indices);IDirect3DIndexBuffer9_Release(indices);
 if(!key.buffer || !key.index || FAILED(IDirect3DDevice9_GetViewport(device,&viewport)))return;
 key.base=(UINT)base;key.minimum=minimum;key.vertices=vertices;key.start=start;key.primitives=triangles;key.offset=offset;key.pass=uma_determinant(worldview)<0;key.width=viewport.Width;key.height=viewport.Height;
 uma_scene_reference(&runner_scene,worldview,&key);
}
static int runner_position_offset(IDirect3DDevice9 *device,UINT stride,UINT *position){
 IDirect3DVertexDeclaration9 *declaration=NULL;D3DVERTEXELEMENT9 elements[65];UINT number=65;int found=0;
 if(FAILED(IDirect3DDevice9_GetVertexDeclaration(device,&declaration)) || !declaration)return 0;
 HRESULT result=IDirect3DVertexDeclaration9_GetDeclaration(declaration,elements,&number);IDirect3DVertexDeclaration9_Release(declaration);
 if(FAILED(result) || number>65 || stride<12 || stride>256)return 0;
 for(UINT i=0;i<number;i++)if(elements[i].Stream==0 && elements[i].Usage==D3DDECLUSAGE_POSITION && elements[i].UsageIndex==0 && elements[i].Type==D3DDECLTYPE_FLOAT3 && elements[i].Offset<=stride-12){*position=elements[i].Offset;found=1;}
 return found;
}
static int runner_readable(const void *data,size_t bytes){
 if(!data || !bytes || bytes>4*1024*1024 || (uintptr_t)data>UINTPTR_MAX-bytes)return 0;
 uintptr_t at=(uintptr_t)data,end=at+bytes;
 for(unsigned region=0;at<end && region<16;region++){
  MEMORY_BASIC_INFORMATION info;if(!VirtualQuery((const void*)at,&info,sizeof(info)) || info.State!=MEM_COMMIT || (info.Protect&(PAGE_GUARD|PAGE_NOACCESS)))return 0;
  DWORD protection=info.Protect&255;if(protection!=PAGE_READONLY && protection!=PAGE_READWRITE && protection!=PAGE_WRITECOPY)return 0;
  uintptr_t next=(uintptr_t)info.BaseAddress+info.RegionSize;if(next<=at)return 0;at=next;
 }
 return at>=end;
}
static int runner_vertex_wheels(IDirect3DDevice9 *device,UINT vertices,const void *data,UINT stride,UINT first,const UmaMatrix *worldview,UmaVertexBounds *decoded){
 UINT position=0;UmaUploadSnapshot snapshot;const BYTE *points=data;size_t bytes=(size_t)vertices*stride;
 if(!data){
  IDirect3DVertexBuffer9 *buffer=NULL;UINT offset=0;DWORD size=sizeof(snapshot);
  if(FAILED(IDirect3DDevice9_GetStreamSource(device,0,&buffer,&offset,&stride)) || !buffer)return 0;
  HRESULT result=IDirect3DVertexBuffer9_GetPrivateData(buffer,&uma_bounds_guid,&snapshot,&size);IDirect3DVertexBuffer9_Release(buffer);
  uint64_t begin=(uint64_t)offset+(uint64_t)first*stride;
  if(FAILED(result) || size<8 || snapshot.bytes>sizeof(snapshot.data) || size!=8+snapshot.bytes || begin<snapshot.offset || begin-snapshot.offset>snapshot.bytes)return 0;
  UINT skip=(UINT)(begin-snapshot.offset);points=snapshot.data+skip;bytes=snapshot.bytes-skip;
 }else if(!runner_readable(data,bytes))return 0;
 if(!runner_position_offset(device,stride,&position))return 0;
 UmaVertexBounds bounds;if(!uma_vertex_bounds(points,bytes,vertices,stride,position,&bounds))return 0;
 *decoded=bounds;
 for(unsigned i=0;i<runner_scene.bodies;i++)if(uma_corolla_wheel_bounds(&bounds,worldview,&runner_scene.body[i]) || uma_corolla_tire_batch(points,bytes,vertices,stride,position,worldview,&runner_scene.body[i]))return 1;
 return 0;
}
static int runner_root_attachment(IDirect3DDevice9 *device,const UmaShaderEntry *entry,const UmaMatrix *worldview,UINT vertices){
 if(!entry || entry->diffuse_min<0 || vertices<4 || vertices>4096)return 0;
 IDirect3DVertexBuffer9 *buffer=NULL;UINT offset=0,stride=0;
 if(FAILED(IDirect3DDevice9_GetStreamSource(device,0,&buffer,&offset,&stride)) || !buffer)return 0;
 IDirect3DVertexBuffer9_Release(buffer);if(stride!=36)return 0;
 for(unsigned i=0;i<runner_scene.bodies;i++){
  int equal=1;for(int r=0;r<4;r++)for(int c=0;c<3;c++)if(fabsf(worldview->m[r][c]-runner_scene.body[i].m[r][c])>.001f)equal=0;
  if(equal)return 1;
 }
 return 0;
}
static int runner_wheel_draw(IDirect3DDevice9 *device,D3DPRIMITIVETYPE type,UINT vertices,UINT triangles,const char *method,const void *data,UINT stride,UINT first){
 if(type<D3DPT_TRIANGLELIST || type>D3DPT_TRIANGLEFAN || vertices<4 || vertices>4096 || triangles<2 || triangles>2048 || runner_renderer.device!=device || runner_frames-runner_last_owned>=3 || !runner_scene.bodies)return 0;
 DWORD depth=0;if(FAILED(IDirect3DDevice9_GetRenderState(device,D3DRS_ZENABLE,&depth)) || !depth)return 0;
 HRESULT status;UmaShaderEntry *entry=uma_shader_get(&runner_renderer.shaders,device,&status);UmaMatrix worldview;if(FAILED(status) || !runner_worldview(device,entry,&worldview))return 0;
 int match=runner_root_attachment(device,entry,&worldview,vertices);for(unsigned i=0;!match && i<runner_scene.bodies;i++)if(uma_corolla_wheel(&worldview,&runner_scene.body[i]) || (entry && entry->diffuse_min>=0 && uma_corolla_side_attachment(&worldview,&runner_scene.body[i]))){match=1;break;}
 UmaVertexBounds decoded={{NAN,NAN,NAN},{NAN,NAN,NAN}};
 if(!match)match=runner_vertex_wheels(device,vertices,data,stride,first,&worldview,&decoded);
 if(runner_log && runner_tire_candidates<96){
  UINT shader=entry?entry->bytes:0;int known=0,racing=runner_scene.bodies>2;
  for(unsigned i=0;i<runner_tire_candidates;i++)if(runner_wheel_reports[i].vertices==vertices && runner_wheel_reports[i].primitives==triangles && runner_wheel_reports[i].shader==shader && runner_wheel_reports[i].method==method && runner_wheel_reports[i].match==match && runner_wheel_reports[i].racing==racing)known=1;
  if(!known){
   unsigned i=runner_tire_candidates++;runner_wheel_reports[i].vertices=vertices;runner_wheel_reports[i].primitives=triangles;runner_wheel_reports[i].shader=shader;runner_wheel_reports[i].method=method;runner_wheel_reports[i].match=match;runner_wheel_reports[i].racing=racing;
   fprintf(runner_log,"WHEEL method=%s frame=%u vertices=%u primitives=%u shaderBytes=%u match=%d bodies=%u origin=%.4f,%.4f,%.4f rawBounds=%.4f,%.4f,%.4f:%.4f,%.4f,%.4f\n",method,runner_frames,vertices,triangles,shader,match,runner_scene.bodies,worldview.m[3][0],worldview.m[3][1],worldview.m[3][2],decoded.minimum[0],decoded.minimum[1],decoded.minimum[2],decoded.maximum[0],decoded.maximum[1],decoded.maximum[2]);fflush(runner_log);
  }
 }
 if(match)runner_hidden_wheels++;
 return match;
}
static UINT runner_primitive_vertices(D3DPRIMITIVETYPE type,UINT count){
 if(count>2048)return 0;
 return type==D3DPT_TRIANGLELIST?count*3:((type==D3DPT_TRIANGLESTRIP || type==D3DPT_TRIANGLEFAN)?count+2:0);
}
static HRESULT WINAPI runner_primitive(IDirect3DDevice9 *device,D3DPRIMITIVETYPE type,UINT start,UINT count){
 EnterCriticalSection(&runner_lock);int hide=runner_wheel_draw(device,type,runner_primitive_vertices(type,count),count,"DP",NULL,0,start);LeaveCriticalSection(&runner_lock);
 return hide?S_OK:runner_original_primitive(device,type,start,count);
}
static HRESULT WINAPI runner_primitive_up(IDirect3DDevice9 *device,D3DPRIMITIVETYPE type,UINT count,const void *vertices,UINT stride){
 EnterCriticalSection(&runner_lock);int hide=vertices && stride && runner_wheel_draw(device,type,runner_primitive_vertices(type,count),count,"DPUP",vertices,stride,0);LeaveCriticalSection(&runner_lock);
 if(hide)return IDirect3DDevice9_SetStreamSource(device,0,NULL,0,0);
 return runner_original_primitive_up(device,type,count,vertices,stride);
}
static HRESULT WINAPI runner_indexed_up(IDirect3DDevice9 *device,D3DPRIMITIVETYPE type,UINT minimum,UINT vertices,UINT count,const void *indices,D3DFORMAT format,const void *data,UINT stride){
 EnterCriticalSection(&runner_lock);int hide=data && indices && stride && runner_wheel_draw(device,type,vertices,count,"DIPUP",minimum?NULL:data,stride,minimum);LeaveCriticalSection(&runner_lock);
 if(hide){HRESULT result=IDirect3DDevice9_SetStreamSource(device,0,NULL,0,0);HRESULT cleared=IDirect3DDevice9_SetIndices(device,NULL);return FAILED(result)?result:cleared;}
 return runner_original_indexed_up(device,type,minimum,vertices,count,indices,format,data,stride);
}
static HRESULT WINAPI runner_draw(IDirect3DDevice9 *device,D3DPRIMITIVETYPE type,INT base,UINT minimum,UINT vertices,UINT start,UINT triangles){
 HRESULT result=E_FAIL;int replaced=0;EnterCriticalSection(&runner_lock);
 int candidate=type==D3DPT_TRIANGLELIST && vertices==runner_motion.vertices && triangles==runner_motion.indices/3;
 if(candidate)runner_candidates++;
 if(candidate || (runner_renderer.device==device && runner_frames-runner_last_owned<3 && (runner_scene.references<96 || (vertices<=4096 && type==D3DPT_TRIANGLELIST) || (runner_scene.tracked && vertices==runner_scene.previous_key.vertices && triangles==runner_scene.previous_key.primitives)))){
  IDirect3DVertexBuffer9 *vb=NULL;UINT offset=0,stride=0;
  if(SUCCEEDED(IDirect3DDevice9_GetStreamSource(device,0,&vb,&offset,&stride)) && vb){
   int64_t first=(int64_t)base+minimum;uint64_t byte_offset=first>=0?(uint64_t)offset+(uint64_t)first*stride:UINT64_MAX;
   int owned=candidate && stride==36 && byte_offset<=UINT_MAX && uma_upload_matches_at(vb,(UINT)byte_offset);DWORD depth=0;
   if(SUCCEEDED(IDirect3DDevice9_GetRenderState(device,D3DRS_ZENABLE,&depth)) && depth && (owned || stride==24 || (stride>0 && vertices<=4096))){
    if(owned){
     runner_owned++;runner_last_owned=runner_frames;
     if(runner_renderer.device && runner_renderer.device!=device)uma_d3d_close(&runner_renderer);
     if(!runner_renderer.device){FILE *texture=_wfopen(runner_atlas,L"rb");if(texture){result=uma_d3d_open(&runner_renderer,device,&runner_motion,texture,runner_original_draw);fclose(texture);}}
    }
    if(runner_renderer.device==device){
     HRESULT shader_status;UmaShaderEntry *entry=uma_shader_get(&runner_renderer.shaders,device,&shader_status);UmaMatrix worldview;
     if(owned && SUCCEEDED(shader_status) && entry && entry->worldview>=0){
      UmaMatrix combined;if(runner_worldview(device,entry,&worldview) && runner_combined(device,entry,&combined))runner_projection_valid=uma_inverse_projection(&worldview,&combined,&runner_inverse_projection);
     }
     if(SUCCEEDED(shader_status) && runner_worldview(device,entry,&worldview)){
      if(owned)uma_scene_body(&runner_scene,&worldview);
      else if(stride==24 && entry && entry->reference)runner_reference(device,vb,base,minimum,vertices,start,triangles,offset,&worldview);
      else if(stride==24 && !entry){DWORD fvf=0;if(SUCCEEDED(IDirect3DDevice9_GetFVF(device,&fvf)) && (fvf&D3DFVF_POSITION_MASK)==D3DFVF_XYZ)runner_reference(device,vb,base,minimum,vertices,start,triangles,offset,&worldview);}
     }
     if(!owned && runner_wheel_draw(device,type,vertices,triangles,"DIP",NULL,0,(UINT)(base+minimum))){replaced=1;result=S_OK;}
     if(owned){
      DWORD color=0;IDirect3DDevice9_GetRenderState(device,D3DRS_COLORWRITEENABLE,&color);
      D3DMATRIX combined={0};int transform=entry?1:runner_fixed_combined(device,&combined);
      if(runner_log && runner_owned<=8){fprintf(runner_log,"OWNED frame=%u base=%d min=%u start=%u offset=%u stride=%u color=%lu shaderBytes=%u supported=%d\n",runner_frames,base,minimum,start,offset,stride,(unsigned long)color,entry?entry->bytes:0,entry?entry->supported:0);fflush(runner_log);}
      if(SUCCEEDED(shader_status) && transform && ((color&7)==7 || color==0)){result=uma_d3d_draw(&runner_renderer,&runner_state,&combined,0);if(SUCCEEDED(result)){replaced=1;runner_replaced++;}else {runner_shader_failures++;if(runner_log && runner_shader_failures<=8){fprintf(runner_log,"DRAW_FAILURE hr=%08lx shaderBytes=%u supported=%d color=%lu base=%d min=%u start=%u stride=%u\n",(unsigned long)result,entry?entry->bytes:0,entry?entry->supported:0,(unsigned long)color,base,minimum,start,stride);fflush(runner_log);}}}
     }
    }
   }
   IDirect3DVertexBuffer9_Release(vb);
  }
 }
 LeaveCriticalSection(&runner_lock);if(replaced)return result;
 return runner_original_draw(device,type,base,minimum,vertices,start,triangles);
}
static HRESULT WINAPI runner_present(IDirect3DDevice9 *device,const RECT *source,const RECT *destination,HWND window,const RGNDATA *dirty){
 EnterCriticalSection(&runner_lock);ULONGLONG tick=GetTickCount64();float seconds=runner_last_tick?(float)(tick-runner_last_tick)*.001f:0;runner_last_tick=tick;
 unsigned references=runner_scene.samples,bodies=runner_scene.bodies,groups=runner_scene.references,best_votes=0,second_votes=0;
 for(unsigned i=0;i<groups;i++){unsigned votes=runner_scene.reference[i].votes;if(votes>best_votes){second_votes=best_votes;best_votes=votes;}else if(votes>second_votes)second_votes=votes;}
 if(runner_log && runner_frames%120==119 && references && bodies && runner_camera_reports<12){
  runner_camera_reports++;fprintf(runner_log,"CAMERA frame=%u groups=%u best=%u second=%u inverseProjection=",runner_frames,groups,best_votes,second_votes);
  for(int i=0;i<4;i++)for(int j=0;j<4;j++)fprintf(runner_log,"%.6g,",runner_inverse_projection.m[i][j]);
  fputc('\n',runner_log);
  for(unsigned i=0;i<groups && i<4;i++){fprintf(runner_log,"REF votes=%u ",runner_scene.reference[i].votes);for(int r=0;r<4;r++)for(int c=0;c<3;c++)fprintf(runner_log,"%.6g,",runner_scene.reference[i].matrix.m[r][c]);fputc('\n',runner_log);}
  fprintf(runner_log,"BODY ");for(int r=0;r<4;r++)for(int c=0;c<3;c++)fprintf(runner_log,"%.6g,",runner_scene.body[0].m[r][c]);fputc('\n',runner_log);
 }
 runner_speed_valid=uma_scene_finish(&runner_scene,seconds,&runner_speed);
 if(seconds>0 && seconds<=.1f){
  float previous_phase=runner_state.run_phase;uma_motion_step(&runner_state,seconds,runner_speed_valid?runner_speed:0,0);
  uma_audio_step(previous_phase,runner_state.run_phase,runner_state.run_blend,runner_speed_valid?runner_speed:0,seconds,runner_log);
 }
 runner_frames++;
 if(runner_log && runner_frames%120==0){
  fprintf(runner_log,"FRAME %u candidates=%u owned=%u replaced=%u shaderFailures=%u references=%u bodies=%u graphicsSpeedValid=%d graphicsSpeed=%.4f blend=%.4f projectionValid=%d recoveredSceneRefs=%u hiddenWheels=%u groups=%u best=%u second=%u hoofPlayed=%u audioActive=%d\n",runner_frames,runner_candidates,runner_owned,runner_replaced,runner_shader_failures,references,bodies,runner_speed_valid,runner_speed,runner_state.run_blend,runner_projection_valid,runner_projected_references,runner_hidden_wheels,groups,best_votes,second_votes,uma_hoof_played,uma_engine_patch.active);fflush(runner_log);
  if(ftell(runner_log)>2*1024*1024){fclose(runner_log);runner_log=NULL;}
 }
 LeaveCriticalSection(&runner_lock);return runner_original_present(device,source,destination,window,dirty);
}
static HRESULT WINAPI runner_reset(IDirect3DDevice9 *device,D3DPRESENT_PARAMETERS *parameters){
 EnterCriticalSection(&runner_lock);uma_d3d_close(&runner_renderer);memset(&runner_scene,0,sizeof(runner_scene));runner_last_tick=0;runner_projection_valid=0;LeaveCriticalSection(&runner_lock);
 return runner_original_reset(device,parameters);
}
static int runner_install(IDirect3DDevice9 *device){
 (void)uma_upload_is_character;
 if(runner_table)return 0;
 IDirect3DVertexBuffer9 *sample=NULL;HRESULT result=IDirect3DDevice9_CreateVertexBuffer(device,36,D3DUSAGE_DYNAMIC|D3DUSAGE_WRITEONLY,0,D3DPOOL_DEFAULT,&sample,NULL);if(FAILED(result))return 0;
 int observed=uma_upload_install(sample,runner_motion.rest,runner_motion.vertices*36);IDirect3DVertexBuffer9_Release(sample);if(!observed)return 0;
 void **table=*(void***)device;DWORD protection;
 if(!VirtualProtect(table+16,(84-16+1)*sizeof(void*),PAGE_READWRITE,&protection)){uma_upload_remove();return 0;}
 runner_original_primitive=(RunnerPrimitive)table[81];runner_original_primitive_up=(RunnerPrimitiveUP)table[83];runner_original_indexed_up=(RunnerIndexedUP)table[84];runner_original_draw=(UmaDrawIndexed)table[82];runner_original_present=(RunnerPresent)table[17];runner_original_reset=(RunnerReset)table[16];runner_table=table;
 InterlockedExchangePointer(table+81,(void*)runner_primitive);InterlockedExchangePointer(table+83,(void*)runner_primitive_up);InterlockedExchangePointer(table+84,(void*)runner_indexed_up);InterlockedExchangePointer(table+82,(void*)runner_draw);InterlockedExchangePointer(table+17,(void*)runner_present);InterlockedExchangePointer(table+16,(void*)runner_reset);
 DWORD ignored;VirtualProtect(table+16,(84-16+1)*sizeof(void*),protection,&ignored);return 1;
}
#ifdef UMA_RUNNER_TEST
static int runner_remove(void){
 if(!runner_table)return 0;
 void **table=runner_table;DWORD protection;
 if(table[81]!=(void*)runner_primitive || table[83]!=(void*)runner_primitive_up || table[84]!=(void*)runner_indexed_up || table[82]!=(void*)runner_draw || table[17]!=(void*)runner_present || table[16]!=(void*)runner_reset || !VirtualProtect(table+16,(84-16+1)*sizeof(void*),PAGE_READWRITE,&protection))return 0;
 uma_audio_close();uma_d3d_close(&runner_renderer);InterlockedExchangePointer(table+81,(void*)runner_original_primitive);InterlockedExchangePointer(table+83,(void*)runner_original_primitive_up);InterlockedExchangePointer(table+84,(void*)runner_original_indexed_up);InterlockedExchangePointer(table+82,(void*)runner_original_draw);InterlockedExchangePointer(table+17,(void*)runner_original_present);InterlockedExchangePointer(table+16,(void*)runner_original_reset);
 DWORD ignored;VirtualProtect(table+16,(84-16+1)*sizeof(void*),protection,&ignored);runner_table=NULL;return uma_upload_remove();
}
#else
static DWORD WINAPI runner_start(void *module){
 InitializeCriticalSection(&runner_lock);WCHAR root[4096],path[4096];DWORD length=GetModuleFileNameW((HMODULE)module,root,4096);if(!length || length>=4096)return 1;
 WCHAR *last=wcsrchr(root,L'\\');if(!last)return 1;*last=0;last=wcsrchr(root,L'\\');if(!last || _wcsicmp(last+1,L"scripts"))return 1;*last=0;if(wcslen(root)>3900)return 1;
 wcscpy(path,root);wcscat(path,L"\\modding\\uma-runner.log");runner_log=_wfopen(path,L"a");
 wcscpy(path,root);wcscat(path,L"\\modding\\runtime\\kitasan.umab");FILE *asset=_wfopen(path,L"rb");if(!asset)return 1;int loaded=uma_motion_load(asset,&runner_motion);fclose(asset);if(!loaded)return 1;
 wcscpy(runner_atlas,root);wcscat(runner_atlas,L"\\modding\\runtime\\atlas.dds");
 HWND window=CreateWindowA("STATIC","Uma renderer initialization",WS_POPUP,0,0,16,16,NULL,NULL,GetModuleHandle(NULL),NULL);IDirect3D9 *api=Direct3DCreate9(D3D_SDK_VERSION);IDirect3DDevice9 *device=NULL;
 D3DPRESENT_PARAMETERS pp={0};pp.Windowed=TRUE;pp.SwapEffect=D3DSWAPEFFECT_DISCARD;pp.hDeviceWindow=window;pp.BackBufferWidth=16;pp.BackBufferHeight=16;pp.BackBufferFormat=D3DFMT_A8R8G8B8;
 HRESULT result=window && api?IDirect3D9_CreateDevice(api,0,D3DDEVTYPE_HAL,window,D3DCREATE_SOFTWARE_VERTEXPROCESSING,&pp,&device):E_FAIL;
 int installed=SUCCEEDED(result) && runner_install(device);
 if(installed)(void)uma_audio_start(root,runner_log);
 if(runner_log){fprintf(runner_log,"START native lighting runner installed=%d; graphics-derived speed uncalibrated; shared motion state for Corolla instances\n",installed);fflush(runner_log);}
 if(device){IDirect3DDevice9_Release(device);}if(api){IDirect3D9_Release(api);}if(window){DestroyWindow(window);}
 if(!installed){uma_motion_free(&runner_motion);}return installed?0:1;
}
BOOL WINAPI DllMain(HINSTANCE instance,DWORD reason,LPVOID reserved){(void)reserved;if(reason==DLL_PROCESS_ATTACH){DisableThreadLibraryCalls(instance);HANDLE thread=CreateThread(NULL,0,runner_start,instance,0,NULL);if(thread)CloseHandle(thread);}return TRUE;}
#endif
