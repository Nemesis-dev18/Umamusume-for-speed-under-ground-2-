#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>
int main(void){
 if(!SetCurrentDirectoryW(L"modding\\diagnostics\\pipeline-load-test\\scripts"))return 2;
 HMODULE module=LoadLibraryW(L"UmaPipelineProbe.asi");
 if(!module){printf("FAIL LoadLibrary=%lu\n",GetLastError());return 3;}
 /* Reproduce loading from scripts without restoring the working directory. */
 for(int i=0;i<100;i++){
  FILE *log=fopen("../modding/uma-pipeline.log","r");
  if(log){char line[512];int ready=0;while(fgets(line,sizeof(line),log))if(strstr(line,"HOOK installed=1"))ready=1;fclose(log);if(ready){puts("PASS DLL initialization and hook installation while CWD remains scripts");return 0;}}
  Sleep(50);
 }
 puts("FAIL no successful hook log after DLL initialization");return 4;
}
