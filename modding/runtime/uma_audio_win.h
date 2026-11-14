#ifndef UMA_AUDIO_WIN_H
#define UMA_AUDIO_WIN_H
#include <mmsystem.h>
#include "uma_engine_audio.h"
#include "uma_hoof_schedule.h"
#ifndef UMA_PLAY_SOUND
#define UMA_PLAY_SOUND PlaySoundW
#endif
static UmaEnginePatch uma_engine_patch;
static unsigned char uma_hoof_wave[2][16384];
static unsigned uma_hoof_played;
static inline int uma_hoof_load(const WCHAR *path,unsigned char *data){
 FILE *file=_wfopen(path,L"rb");if(!file)return 0;
 size_t bytes=fread(data,1,16384,file);int extra=fgetc(file);fclose(file);
 if(bytes<44 || extra!=EOF || memcmp(data,"RIFF",4) || uma_audio_word(data+4)!=bytes-8 || memcmp(data+8,"WAVEfmt ",8) || uma_audio_word(data+16)!=16 || memcmp(data+20,"\1\0\1\0",4) || uma_audio_word(data+24)!=22050 || uma_audio_word(data+28)!=44100 || memcmp(data+32,"\2\0\20\0data",8) || uma_audio_word(data+40)!=bytes-44)return 0;
 return 1;
}
static inline int uma_audio_start(const WCHAR *root,FILE *log){
 WCHAR path[4096];if(wcslen(root)>3900 || !waveOutGetNumDevs())return 0;
 for(int i=0;i<2;i++){swprintf(path,4096,L"%ls\\modding\\runtime\\hoof-%d.wav",root,i);if(!uma_hoof_load(path,uma_hoof_wave[i]))return 0;}
 unsigned char *image=(unsigned char*)GetModuleHandleW(NULL),*engines=NULL,*mapping=NULL;unsigned engine_matches=0,mapping_matches=0;uintptr_t at=(uintptr_t)image;
 for(unsigned region=0;region<512;region++){
  MEMORY_BASIC_INFORMATION info;if(!VirtualQuery((void*)at,&info,sizeof(info)) || info.AllocationBase!=image)break;
  uintptr_t end=(uintptr_t)info.BaseAddress+info.RegionSize;if(end<=at)break;
  /* Only mutable data pages of the main image; no instruction pages or executable-file reads. */
  if(info.State==MEM_COMMIT && !(info.Protect&PAGE_GUARD) && ((info.Protect&255)==PAGE_READWRITE || (info.Protect&255)==PAGE_WRITECOPY)){
   unsigned char *begin=(unsigned char*)info.BaseAddress;
   for(size_t i=0;i+UMA_ENGINE_BYTES<=info.RegionSize;i+=4)if(uma_audio_word(begin+i+8)==uma_engine_profile[0][0] && !memcmp(begin+i+16,uma_engine_profile[0]+1,60) && uma_engine_profile_matches(begin+i,info.RegionSize-i)){engines=begin+i;engine_matches++;}
   for(size_t i=0;i+UMA_MAPPING_BYTES<=info.RegionSize;i+=4)if(!memcmp(begin+i,uma_mapping_profile[0],48) && !memcmp(begin+i,uma_mapping_profile,UMA_MAPPING_BYTES)){mapping=begin+i;mapping_matches++;}
  }
  at=end;
 }
 int installed=engine_matches==1 && mapping_matches==1 && uma_engine_apply(&uma_engine_patch,engines,UMA_ENGINE_BYTES,mapping,UMA_MAPPING_BYTES);
 if(log){fprintf(log,"AUDIO engineProfiles=%u mappingProfiles=%u installed=%d; mutable data only; Corolla-only silent engine slot and hoof samples\n",engine_matches,mapping_matches,installed);fflush(log);}return installed;
}
static inline void uma_audio_step(float previous,float next,float blend,float speed,float seconds,FILE *log){
 if(!uma_engine_patch.active)return;
 unsigned events=uma_hoof_schedule(previous,next,blend,speed,seconds);
 for(unsigned i=0;i<2;i++)if(events&(1u<<i)){
  if(!UMA_PLAY_SOUND((LPCWSTR)uma_hoof_wave[i],NULL,SND_MEMORY|SND_ASYNC|SND_NODEFAULT)){
   int restored=uma_engine_restore(&uma_engine_patch);if(log){fprintf(log,"AUDIO playback failed; original engine routing restored=%d\n",restored);fflush(log);}return;
  }
  uma_hoof_played++;
 }
}
static inline void uma_audio_close(void){PlaySoundW(NULL,NULL,0);if(uma_engine_patch.active)(void)uma_engine_restore(&uma_engine_patch);}
#endif
