#define COBJMACROS
#include <windows.h>
#include <d3d9.h>
#include <stdio.h>
#include <wchar.h>
#include <stdlib.h>

typedef HRESULT (WINAPI *DrawFn)(IDirect3DDevice9*,D3DPRIMITIVETYPE,INT,UINT,UINT,UINT,UINT);
typedef HRESULT (WINAPI *PresentFn)(IDirect3DDevice9*,const RECT*,const RECT*,HWND,const RGNDATA*);
static DrawFn original_draw;
static PresentFn original_present;
static CRITICAL_SECTION log_lock;
static FILE *draw_log;
static UINT frames,draws,characters,pair_count,metadata_window=~0u;
static UINT pair_vertices[256],pair_triangles[256];
static UINT pair_shaders[256];
static IDirect3DVertexShader9 *known_shaders[64];
static UINT known_shader_count;
static BOOL shader_limit_noted;
static BOOL character_candidate(UINT vertices,UINT triangles){
#ifdef UMA_LOG_TEST
 return vertices==4 && triangles==2;
#else
 return vertices==14512 || triangles==16557;
#endif
}

/* Retain at most 64 shader objects so pointer reuse cannot disguise a new program. */
static UINT record_shader(IDirect3DDevice9 *device){
 IDirect3DVertexShader9 *shader=NULL;
 if(FAILED(IDirect3DDevice9_GetVertexShader(device,&shader)))return ~0u;
 if(!shader)return 0;
 for(UINT i=0;i<known_shader_count;i++)if(known_shaders[i]==shader){IDirect3DVertexShader9_Release(shader);return i+1;}
 if(known_shader_count==64){if(!shader_limit_noted && draw_log){fputs("SHADER_LIMIT 64; no additional programs captured\n",draw_log);shader_limit_noted=TRUE;}IDirect3DVertexShader9_Release(shader);return ~0u;}
 UINT bytes=0;HRESULT result=IDirect3DVertexShader9_GetFunction(shader,NULL,&bytes);
 if(FAILED(result) || bytes<8 || bytes>16384 || bytes%4){IDirect3DVertexShader9_Release(shader);return ~0u;}
 DWORD *code=malloc(bytes);if(!code){IDirect3DVertexShader9_Release(shader);return ~0u;}
 UINT capacity=bytes;result=IDirect3DVertexShader9_GetFunction(shader,code,&bytes);
 if(FAILED(result) || bytes>capacity || bytes%4){free(code);IDirect3DVertexShader9_Release(shader);return ~0u;}
 UINT id=++known_shader_count;known_shaders[id-1]=shader;
 if(draw_log){fprintf(draw_log,"VS id=%u bytes=%u words=",id,bytes);for(UINT i=0;i<bytes/4;i++)fprintf(draw_log,"%08lx%s",(unsigned long)code[i],i+1==bytes/4?"\n":" ");fflush(draw_log);}
 free(code);return id;
}
static void record_constants(IDirect3DDevice9 *device){
 if(!draw_log)return;
 D3DCAPS9 caps;float constants[256][4];
 if(SUCCEEDED(IDirect3DDevice9_GetDeviceCaps(device,&caps))){UINT count=caps.MaxVertexShaderConst<256?caps.MaxVertexShaderConst:256;
  if(count && SUCCEEDED(IDirect3DDevice9_GetVertexShaderConstantF(device,0,&constants[0][0],count))){
   fprintf(draw_log,"VS_CONSTANTS frame=%u count=%u",frames,count);
   for(UINT i=0;i<count;i++){fprintf(draw_log," c%u=%.9g,%.9g,%.9g,%.9g",i,constants[i][0],constants[i][1],constants[i][2],constants[i][3]);}fputc('\n',draw_log);
  }
 }
 const D3DTRANSFORMSTATETYPE names[]={D3DTS_WORLD,D3DTS_VIEW,D3DTS_PROJECTION};
 for(UINT i=0;i<3;i++){D3DMATRIX m;if(SUCCEEDED(IDirect3DDevice9_GetTransform(device,names[i],&m))){fprintf(draw_log,"FF_MATRIX frame=%u type=%u",frames,names[i]);for(int r=0;r<4;r++)for(int c=0;c<4;c++)fprintf(draw_log," %.9g",m.m[r][c]);fputc('\n',draw_log);}}
}
static void metadata(IDirect3DDevice9 *device,INT base,UINT minimum,UINT start){
 IDirect3DVertexBuffer9 *buffer=NULL;UINT offset=0,stride=0;
 fprintf(draw_log,"DETAIL tick=%lu frame=%u base=%d min=%u start=%u shader=%u",GetTickCount(),frames,base,minimum,start,record_shader(device));
 if(SUCCEEDED(IDirect3DDevice9_GetStreamSource(device,0,&buffer,&offset,&stride)) && buffer){
  D3DVERTEXBUFFER_DESC d;if(SUCCEEDED(IDirect3DVertexBuffer9_GetDesc(buffer,&d)))fprintf(draw_log," streamOffset=%u stride=%u bufferBytes=%u",offset,stride,d.Size);
  IDirect3DVertexBuffer9_Release(buffer);
 }
 const D3DRENDERSTATETYPE names[]={D3DRS_CULLMODE,D3DRS_ALPHATESTENABLE,D3DRS_ALPHAFUNC,D3DRS_ALPHAREF,D3DRS_ALPHABLENDENABLE,D3DRS_ZENABLE,D3DRS_COLORWRITEENABLE};
 for(UINT i=0;i<sizeof(names)/sizeof(names[0]);i++){DWORD value;if(SUCCEEDED(IDirect3DDevice9_GetRenderState(device,names[i],&value)))fprintf(draw_log," state%u=%lu",names[i],value);}
 for(UINT sampler=0;sampler<8;sampler++){
 IDirect3DBaseTexture9 *texture=NULL;
 if(SUCCEEDED(IDirect3DDevice9_GetTexture(device,sampler,&texture)) && texture){
  if(IDirect3DBaseTexture9_GetType(texture)==D3DRTYPE_TEXTURE){D3DSURFACE_DESC d;if(SUCCEEDED(IDirect3DTexture9_GetLevelDesc((IDirect3DTexture9*)texture,0,&d)))fprintf(draw_log," texture%u=%ux%u format=%u",sampler,d.Width,d.Height,d.Format);}
  IDirect3DBaseTexture9_Release(texture);
 }
 }
 fputc('\n',draw_log);record_constants(device);fflush(draw_log);
}
static HRESULT WINAPI logged_draw(IDirect3DDevice9 *device,D3DPRIMITIVETYPE type,INT base,UINT minimum,UINT vertices,UINT start,UINT triangles){
 EnterCriticalSection(&log_lock);draws++;
 if(draw_log && ftell(draw_log)>=8*1024*1024){fputs("LOG_LIMIT reached; capture stopped, rendering unchanged\n",draw_log);fclose(draw_log);draw_log=NULL;}
 BOOL candidate=type==D3DPT_TRIANGLELIST && character_candidate(vertices,triangles);
 if(candidate)characters++;
 if(draw_log){
  UINT shader=record_shader(device);
  UINT i=0;while(i<pair_count && (pair_vertices[i]!=vertices || pair_triangles[i]!=triangles || pair_shaders[i]!=shader))i++;
  if(i==pair_count && pair_count<256){pair_vertices[pair_count]=vertices;pair_triangles[pair_count]=triangles;pair_shaders[pair_count++]=shader;fprintf(draw_log,"PAIR tick=%lu frame=%u vertices=%u primitives=%u type=%u candidate=%d shader=%u\n",GetTickCount(),frames,vertices,triangles,type,candidate,shader);metadata(device,base,minimum,start);fflush(draw_log);}
  if(candidate && metadata_window!=frames/120){metadata_window=frames/120;metadata(device,base,minimum,start);}
 }
 LeaveCriticalSection(&log_lock);
 return original_draw(device,type,base,minimum,vertices,start,triangles);
}
static HRESULT WINAPI logged_present(IDirect3DDevice9 *device,const RECT *source,const RECT *destination,HWND window,const RGNDATA *dirty){
 EnterCriticalSection(&log_lock);frames++;
 if(draw_log && frames%120==0){fprintf(draw_log,"SUMMARY tick=%lu frame=%u draws=%u characterCandidates=%u\n",GetTickCount(),frames,draws,characters);fflush(draw_log);draws=characters=0;}
 LeaveCriticalSection(&log_lock);
 return original_present(device,source,destination,window,dirty);
}
static BOOL install_hooks(IDirect3DDevice9 *device){
 void **table=*(void***)device;DWORD protection;
 if(original_draw)return FALSE;
 if(!VirtualProtect(table+17,(82-17+1)*sizeof(void*),PAGE_READWRITE,&protection))return FALSE;
 original_draw=(DrawFn)table[82];original_present=(PresentFn)table[17];
 InterlockedExchangePointer(table+82,(void*)logged_draw);InterlockedExchangePointer(table+17,(void*)logged_present);
 DWORD ignored;VirtualProtect(table+17,(82-17+1)*sizeof(void*),protection,&ignored);return TRUE;
}
#ifndef UMA_LOG_TEST
static DWORD WINAPI start_logging(void *module){
 InitializeCriticalSection(&log_lock);
 WCHAR path[4096];DWORD length=GetModuleFileNameW((HMODULE)module,path,4096);
 if(!length || length>=4096)return 1;
 WCHAR *last=wcsrchr(path,L'\\');if(!last)return 1;*last=0;
 last=wcsrchr(path,L'\\');if(!last || _wcsicmp(last+1,L"scripts"))return 1;*last=0;
 const WCHAR suffix[]=L"\\modding\\uma-pipeline.log";
 if(wcslen(path)+wcslen(suffix)>=4096)return 1;
 wcscat(path,suffix);draw_log=_wfopen(path,L"a");if(!draw_log)return 1;
 fputs("START pipeline diagnostics; GPU shader object reads only; no executable reads or rendering changes\n",draw_log);fflush(draw_log);
 HWND window=CreateWindowA("STATIC","Uma graphics probe",WS_POPUP,0,0,16,16,NULL,NULL,GetModuleHandle(NULL),NULL);
 IDirect3D9 *api=Direct3DCreate9(D3D_SDK_VERSION);IDirect3DDevice9 *device=NULL;
 D3DPRESENT_PARAMETERS pp={0};pp.Windowed=TRUE;pp.SwapEffect=D3DSWAPEFFECT_DISCARD;pp.hDeviceWindow=window;pp.BackBufferWidth=16;pp.BackBufferHeight=16;pp.BackBufferFormat=D3DFMT_A8R8G8B8;
 HRESULT result=window && api?IDirect3D9_CreateDevice(api,0,D3DDEVTYPE_HAL,window,D3DCREATE_SOFTWARE_VERTEXPROCESSING,&pp,&device):E_FAIL;
 BOOL installed=SUCCEEDED(result) && install_hooks(device);
 fprintf(draw_log,"HOOK installed=%d deviceHR=%08lx\n",installed,(unsigned long)result);fflush(draw_log);
 if(device)IDirect3DDevice9_Release(device);
 if(api)IDirect3D9_Release(api);
 if(window)DestroyWindow(window);
 return installed?0:1;
}
BOOL WINAPI DllMain(HINSTANCE instance,DWORD reason,LPVOID reserved){
 (void)reserved;
 if(reason==DLL_PROCESS_ATTACH){DisableThreadLibraryCalls(instance);HANDLE thread=CreateThread(NULL,0,start_logging,instance,0,NULL);if(thread)CloseHandle(thread);}
 return TRUE;
}
#endif
