#define COBJMACROS
#include <windows.h>
#include <d3d9.h>
#include <wchar.h>
#include "uma_d3d.h"
#include "uma_upload.h"
#include "uma_scene_speed.h"
typedef HRESULT (WINAPI *RunnerPresent)(IDirect3DDevice9*,const RECT*,const RECT*,HWND,const RGNDATA*);
typedef HRESULT (WINAPI *RunnerReset)(IDirect3DDevice9*,D3DPRESENT_PARAMETERS*);
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
static int runner_speed_valid;
static float runner_speed;
static unsigned runner_last_owned;
static int runner_worldview(IDirect3DDevice9 *device,const UmaShaderEntry *entry,UmaMatrix *output){
 UmaMatrix matrix={0};matrix.m[3][3]=1;
 if(entry){
  if(entry->worldview<0)return 0;
  float rows[3][4];if(FAILED(IDirect3DDevice9_GetVertexShaderConstantF(device,(UINT)entry->worldview,&rows[0][0],3)))return 0;
  for(int r=0;r<4;r++)for(int c=0;c<3;c++)matrix.m[r][c]=rows[c][r];
 }else{
  D3DMATRIX world,view;if(FAILED(IDirect3DDevice9_GetTransform(device,D3DTS_WORLD,&world)) || FAILED(IDirect3DDevice9_GetTransform(device,D3DTS_VIEW,&view)))return 0;
  memset(&matrix,0,sizeof(matrix));for(int r=0;r<4;r++)for(int c=0;c<4;c++)for(int k=0;k<4;k++)matrix.m[r][c]+=world.m[r][k]*view.m[k][c];
 }
 if(!uma_rigid(&matrix))return 0;
 *output=matrix;return 1;
}
static int runner_fixed_combined(IDirect3DDevice9 *device,D3DMATRIX *combined){
 D3DMATRIX projection;UmaMatrix worldview;if(!runner_worldview(device,NULL,&worldview) || FAILED(IDirect3DDevice9_GetTransform(device,D3DTS_PROJECTION,&projection)))return 0;
 memset(combined,0,sizeof(*combined));for(int r=0;r<4;r++)for(int c=0;c<4;c++)for(int k=0;k<4;k++)combined->m[r][c]+=worldview.m[r][k]*projection.m[k][c];return 1;
}
static HRESULT WINAPI runner_draw(IDirect3DDevice9 *device,D3DPRIMITIVETYPE type,INT base,UINT minimum,UINT vertices,UINT start,UINT triangles){
 HRESULT result=E_FAIL;int replaced=0;EnterCriticalSection(&runner_lock);
 int candidate=type==D3DPT_TRIANGLELIST && vertices==runner_motion.vertices && triangles==runner_motion.indices/3;
 if(candidate)runner_candidates++;
 if(candidate || (runner_renderer.device==device && runner_frames-runner_last_owned<3 && runner_scene.samples<96)){
  IDirect3DVertexBuffer9 *vb=NULL;UINT offset=0,stride=0;
  if(SUCCEEDED(IDirect3DDevice9_GetStreamSource(device,0,&vb,&offset,&stride)) && vb){
   int64_t first=(int64_t)base+minimum;uint64_t byte_offset=first>=0?(uint64_t)offset+(uint64_t)first*stride:UINT64_MAX;
   int owned=candidate && stride==36 && byte_offset<=UINT_MAX && uma_upload_matches_at(vb,(UINT)byte_offset);DWORD depth=0;
   if(SUCCEEDED(IDirect3DDevice9_GetRenderState(device,D3DRS_ZENABLE,&depth)) && depth && (owned || stride==24)){
    if(owned){
     runner_owned++;runner_last_owned=runner_frames;
     if(runner_renderer.device && runner_renderer.device!=device)uma_d3d_close(&runner_renderer);
     if(!runner_renderer.device){FILE *texture=_wfopen(runner_atlas,L"rb");if(texture){result=uma_d3d_open(&runner_renderer,device,&runner_motion,texture,runner_original_draw);fclose(texture);}}
    }
    if(runner_renderer.device==device){
     HRESULT shader_status;UmaShaderEntry *entry=uma_shader_get(&runner_renderer.shaders,device,&shader_status);UmaMatrix worldview;
     if(SUCCEEDED(shader_status) && runner_worldview(device,entry,&worldview)){
      if(owned)uma_scene_body(&runner_scene,&worldview);
      else if(entry && entry->reference)uma_scene_reference(&runner_scene,&worldview);
      else if(!entry){DWORD fvf=0;if(SUCCEEDED(IDirect3DDevice9_GetFVF(device,&fvf)) && (fvf&D3DFVF_POSITION_MASK)==D3DFVF_XYZ)uma_scene_reference(&runner_scene,&worldview);}
     }
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
 unsigned references=runner_scene.samples,bodies=runner_scene.bodies;
 runner_speed_valid=uma_scene_finish(&runner_scene,seconds,&runner_speed);
 if(seconds>0 && seconds<=.1f)uma_motion_step(&runner_state,seconds,runner_speed_valid?runner_speed:0,0);
 runner_frames++;
 if(runner_log && runner_frames%120==0){
  fprintf(runner_log,"FRAME %u candidates=%u owned=%u replaced=%u shaderFailures=%u references=%u bodies=%u graphicsSpeedValid=%d graphicsSpeed=%.4f blend=%.4f\n",runner_frames,runner_candidates,runner_owned,runner_replaced,runner_shader_failures,references,bodies,runner_speed_valid,runner_speed,runner_state.run_blend);fflush(runner_log);
  if(ftell(runner_log)>2*1024*1024){fclose(runner_log);runner_log=NULL;}
 }
 LeaveCriticalSection(&runner_lock);return runner_original_present(device,source,destination,window,dirty);
}
static HRESULT WINAPI runner_reset(IDirect3DDevice9 *device,D3DPRESENT_PARAMETERS *parameters){
 EnterCriticalSection(&runner_lock);uma_d3d_close(&runner_renderer);memset(&runner_scene,0,sizeof(runner_scene));runner_last_tick=0;LeaveCriticalSection(&runner_lock);
 return runner_original_reset(device,parameters);
}
static int runner_install(IDirect3DDevice9 *device){
 (void)uma_upload_is_character;
 if(runner_table)return 0;
 IDirect3DVertexBuffer9 *sample=NULL;HRESULT result=IDirect3DDevice9_CreateVertexBuffer(device,36,D3DUSAGE_DYNAMIC|D3DUSAGE_WRITEONLY,0,D3DPOOL_DEFAULT,&sample,NULL);if(FAILED(result))return 0;
 int observed=uma_upload_install(sample,runner_motion.rest,runner_motion.vertices*36);IDirect3DVertexBuffer9_Release(sample);if(!observed)return 0;
 void **table=*(void***)device;DWORD protection;
 if(!VirtualProtect(table+16,(82-16+1)*sizeof(void*),PAGE_READWRITE,&protection)){uma_upload_remove();return 0;}
 runner_original_draw=(UmaDrawIndexed)table[82];runner_original_present=(RunnerPresent)table[17];runner_original_reset=(RunnerReset)table[16];runner_table=table;
 InterlockedExchangePointer(table+82,(void*)runner_draw);InterlockedExchangePointer(table+17,(void*)runner_present);InterlockedExchangePointer(table+16,(void*)runner_reset);
 DWORD ignored;VirtualProtect(table+16,(82-16+1)*sizeof(void*),protection,&ignored);return 1;
}
#ifdef UMA_RUNNER_TEST
static int runner_remove(void){
 if(!runner_table)return 0;
 void **table=runner_table;DWORD protection;
 if(table[82]!=(void*)runner_draw || table[17]!=(void*)runner_present || table[16]!=(void*)runner_reset || !VirtualProtect(table+16,(82-16+1)*sizeof(void*),PAGE_READWRITE,&protection))return 0;
 uma_d3d_close(&runner_renderer);InterlockedExchangePointer(table+82,(void*)runner_original_draw);InterlockedExchangePointer(table+17,(void*)runner_original_present);InterlockedExchangePointer(table+16,(void*)runner_original_reset);
 DWORD ignored;VirtualProtect(table+16,(82-16+1)*sizeof(void*),protection,&ignored);runner_table=NULL;return uma_upload_remove();
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
 if(runner_log){fprintf(runner_log,"START native lighting runner installed=%d; graphics-derived speed uncalibrated; shared motion state for Corolla instances\n",installed);fflush(runner_log);}
 if(device){IDirect3DDevice9_Release(device);}if(api){IDirect3D9_Release(api);}if(window){DestroyWindow(window);}
 if(!installed){uma_motion_free(&runner_motion);}return installed?0:1;
}
BOOL WINAPI DllMain(HINSTANCE instance,DWORD reason,LPVOID reserved){(void)reserved;if(reason==DLL_PROCESS_ATTACH){DisableThreadLibraryCalls(instance);HANDLE thread=CreateThread(NULL,0,runner_start,instance,0,NULL);if(thread)CloseHandle(thread);}return TRUE;}
#endif
