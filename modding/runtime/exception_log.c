#include <windows.h>
#include <stdio.h>
#include <wchar.h>
static HANDLE output=INVALID_HANDLE_VALUE;
static PVOID handler;
static LONG events;
static LONG CALLBACK record_exception(EXCEPTION_POINTERS *exception){
 DWORD code=exception->ExceptionRecord->ExceptionCode;
 if(code!=EXCEPTION_ACCESS_VIOLATION && code!=EXCEPTION_STACK_OVERFLOW && code!=EXCEPTION_ILLEGAL_INSTRUCTION && code!=EXCEPTION_INT_DIVIDE_BY_ZERO)return EXCEPTION_CONTINUE_SEARCH;
 if(InterlockedIncrement(&events)>16)return EXCEPTION_CONTINUE_SEARCH;
 HMODULE module=NULL;char name[256]={0},line[512];DWORD written=0;
 GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,(LPCSTR)exception->ExceptionRecord->ExceptionAddress,&module);
 if(module)GetModuleFileNameA(module,name,sizeof(name));
 int size=snprintf(line,sizeof(line),"EXCEPTION code=%08lx eip=%08lx esp=%08lx module=%s offset=%08lx\r\n",(unsigned long)code,(unsigned long)exception->ContextRecord->Eip,(unsigned long)exception->ContextRecord->Esp,name,(unsigned long)((ULONG_PTR)exception->ExceptionRecord->ExceptionAddress-(ULONG_PTR)module));
 if(size>0 && size<(int)sizeof(line) && output!=INVALID_HANDLE_VALUE){WriteFile(output,line,(DWORD)size,&written,NULL);FlushFileBuffers(output);}
 return EXCEPTION_CONTINUE_SEARCH;
}
BOOL WINAPI DllMain(HINSTANCE module,DWORD reason,LPVOID reserved){
 (void)reserved;
 if(reason==DLL_PROCESS_ATTACH){
  WCHAR path[4096];DWORD length=GetModuleFileNameW(module,path,4096);if(!length || length>=3900)return TRUE;
  WCHAR *last=wcsrchr(path,L'\\');if(!last)return TRUE;*last=0;last=wcsrchr(path,L'\\');if(!last)return TRUE;
  if(!_wcsicmp(last+1,L"runtime")){*last=0;last=wcsrchr(path,L'\\');if(!last || _wcsicmp(last+1,L"modding"))return TRUE;}
  else if(_wcsicmp(last+1,L"scripts"))return TRUE;
  *last=0;wcscat(path,L"\\modding\\uma-exception.log");
  output=CreateFileW(path,GENERIC_WRITE,FILE_SHARE_READ,NULL,OPEN_ALWAYS,FILE_ATTRIBUTE_NORMAL,NULL);
  if(output!=INVALID_HANDLE_VALUE){SetFilePointer(output,0,NULL,FILE_END);DWORD written;const char text[]="EXCEPTION LOGGER attached; observe only\r\n";WriteFile(output,text,sizeof(text)-1,&written,NULL);handler=AddVectoredExceptionHandler(1,record_exception);}
 }else if(reason==DLL_PROCESS_DETACH){if(handler)RemoveVectoredExceptionHandler(handler);if(output!=INVALID_HANDLE_VALUE)CloseHandle(output);}
 return TRUE;
}
