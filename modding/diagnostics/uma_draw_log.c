#define COBJMACROS
#include <windows.h>
#include <d3d9.h>
#include <stdio.h>
#include <wchar.h>

typedef HRESULT (WINAPI *DrawFn)(IDirect3DDevice9*,D3DPRIMITIVETYPE,INT,UINT,UINT,UINT,UINT);
typedef HRESULT (WINAPI *PresentFn)(IDirect3DDevice9*,const RECT*,const RECT*,HWND,const RGNDATA*);
static DrawFn original_draw;
static PresentFn original_present;
static CRITICAL_SECTION log_lock;
static FILE *draw_log;
static UINT frames,draws,characters,pair_count,metadata_window=~0u;
static UINT pair_vertices[256],pair_triangles[256];
static BOOL character_candidate(UINT vertices,UINT triangles){
#ifdef UMA_LOG_TEST
 return vertices==4 && triangles==2;
#else
 return vertices==14512 || triangles==16557;
#endif
}

static void metadata(IDirect3DDevice9 *device,INT base,UINT minimum,UINT start){
 IDirect3DVertexBuffer9 *buffer=NULL;UINT offset=0,stride=0;
 fprintf(draw_log,"DETAIL tick=%lu frame=%u base=%d min=%u start=%u",GetTickCount(),frames,base,minimum,start);
 if(SUCCEEDED(IDirect3DDevice9_GetStreamSource(device,0,&buffer,&offset,&stride)) && buffer){
  D3DVERTEXBUFFER_DESC d;if(SUCCEEDED(IDirect3DVertexBuffer9_GetDesc(buffer,&d)))fprintf(draw_log," streamOffset=%u stride=%u bufferBytes=%u",offset,stride,d.Size);
  IDirect3DVertexBuffer9_Release(buffer);
 }
 const D3DRENDERSTATETYPE names[]={D3DRS_CULLMODE,D3DRS_ALPHATESTENABLE,D3DRS_ALPHAFUNC,D3DRS_ALPHAREF,D3DRS_ALPHABLENDENABLE,D3DRS_ZENABLE,D3DRS_COLORWRITEENABLE};
 for(UINT i=0;i<sizeof(names)/sizeof(names[0]);i++){DWORD value;if(SUCCEEDED(IDirect3DDevice9_GetRenderState(device,names[i],&value)))fprintf(draw_log," state%u=%lu",names[i],value);}
 IDirect3DBaseTexture9 *texture=NULL;
 if(SUCCEEDED(IDirect3DDevice9_GetTexture(device,0,&texture)) && texture){
  if(IDirect3DBaseTexture9_GetType(texture)==D3DRTYPE_TEXTURE){D3DSURFACE_DESC d;if(SUCCEEDED(IDirect3DTexture9_GetLevelDesc((IDirect3DTexture9*)texture,0,&d)))fprintf(draw_log," texture0=%ux%u format=%u",d.Width,d.Height,d.Format);}
  IDirect3DBaseTexture9_Release(texture);
 }
 fputc('\n',draw_log);fflush(draw_log);
}
static HRESULT WINAPI logged_draw(IDirect3DDevice9 *device,D3DPRIMITIVETYPE type,INT base,UINT minimum,UINT vertices,UINT start,UINT triangles){
 EnterCriticalSection(&log_lock);draws++;
 BOOL candidate=type==D3DPT_TRIANGLELIST && character_candidate(vertices,triangles);
 if(candidate)characters++;
 if(draw_log){
  UINT i=0;while(i<pair_count && (pair_vertices[i]!=vertices || pair_triangles[i]!=triangles))i++;
  if(i==pair_count && pair_count<256){pair_vertices[pair_count]=vertices;pair_triangles[pair_count++]=triangles;fprintf(draw_log,"PAIR tick=%lu frame=%u vertices=%u primitives=%u type=%u candidate=%d\n",GetTickCount(),frames,vertices,triangles,type,candidate);fflush(draw_log);}
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
 const WCHAR suffix[]=L"\\modding\\uma-draw.log";
 if(wcslen(path)+wcslen(suffix)>=4096)return 1;
 wcscat(path,suffix);draw_log=_wfopen(path,L"a");if(!draw_log)return 1;
 fputs("START draw-only diagnostics; no executable addresses; no shader/state changes\n",draw_log);fflush(draw_log);
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
