#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
#include "uma_engine_profile.h"
unsigned char audio_engines[43*76],audio_duplicate[43*76],audio_mapping[33*48];
int main(void){
 for(unsigned i=0;i<43;i++){memcpy(audio_engines+i*76+8,uma_engine_profile[i],4);memcpy(audio_engines+i*76+16,uma_engine_profile[i]+1,60);}
 memcpy(audio_mapping,uma_mapping_profile,sizeof(audio_mapping));memcpy(audio_duplicate,audio_engines,sizeof(audio_engines));
 if(!SetCurrentDirectoryW(L"modding\\runtime\\runner-load-test\\scripts"))return 2;
 HMODULE module=LoadLibraryW(L"UmaRunner.asi");
 if(!module){printf("FAIL LoadLibrary=%lu\n",GetLastError());return 3;}
 /* Reproduce loading from scripts without restoring the working directory. */
 for(int i=0;i<100;i++){
  FILE *log=fopen("../modding/uma-runner.log","r");
  if(log){char line[512];int ready=0,audio=-1;while(fgets(line,sizeof(line),log)){if(strstr(line,"START native lighting runner installed=1"))ready=1;if(strstr(line,"AUDIO originalVariants="))audio=strstr(line,"installed=1")?1:0;}fclose(log);if(ready){
   assert(audio==1);assert(!memcmp(audio_engines,audio_duplicate,sizeof(audio_engines)));assert(!memcmp(audio_mapping,uma_mapping_profile,sizeof(audio_mapping)));
   puts("PASS DLL initialization, audio initialized without modifying main-image data and hook installation while CWD remains scripts");return 0;
  }}
  Sleep(50);
 }
 puts("FAIL no successful hook log after DLL initialization");return 4;
}
