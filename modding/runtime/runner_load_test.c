#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
#include "uma_engine_profile.h"
unsigned char audio_engines[43*76],audio_duplicate[43*76],audio_mapping[33*48];
int main(int argc,char **argv){
 int ambiguous=argc>1 && !strcmp(argv[1],"--ambiguous-audio"),incompatible=argc>1 && !strcmp(argv[1],"--incompatible-audio");
 for(unsigned i=0;i<43;i++){memcpy(audio_engines+i*76+8,uma_engine_profile[i],4);memcpy(audio_engines+i*76+16,uma_engine_profile[i]+1,60);}
 memcpy(audio_mapping,uma_mapping_profile,sizeof(audio_mapping));if(ambiguous)memcpy(audio_duplicate,audio_engines,sizeof(audio_engines));if(incompatible)audio_engines[36]^=1;
 if(!SetCurrentDirectoryW(L"modding\\runtime\\runner-load-test\\scripts"))return 2;
 HMODULE module=LoadLibraryW(L"UmaRunner.asi");
 if(!module){printf("FAIL LoadLibrary=%lu\n",GetLastError());return 3;}
 /* Reproduce loading from scripts without restoring the working directory. */
 for(int i=0;i<100;i++){
  FILE *log=fopen("../modding/uma-runner.log","r");
  if(log){char line[512];int ready=0,audio=-1;while(fgets(line,sizeof(line),log)){if(strstr(line,"START native lighting runner installed=1"))ready=1;if(strstr(line,"AUDIO engineProfiles="))audio=strstr(line,"installed=1")?1:0;}fclose(log);if(ready){
   assert(audio==(ambiguous || incompatible?0:1));
   if(audio){for(unsigned j=0;j<4;j++){uint32_t value;memcpy(&value,audio_mapping+6*48+j*12,4);assert(value==3);}}
   else assert(!memcmp(audio_mapping,uma_mapping_profile,sizeof(audio_mapping)));
   puts("PASS DLL initialization, mutable-data audio profile selection/rejection and hook installation while CWD remains scripts");return 0;
  }}
  Sleep(50);
 }
 puts("FAIL no successful hook log after DLL initialization");return 4;
}
