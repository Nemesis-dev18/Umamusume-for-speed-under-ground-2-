#ifndef UMA_AUDIO_WIN_H
#define UMA_AUDIO_WIN_H
#include <mmsystem.h>
#include "uma_engine_audio.h"
#include "uma_hoof_schedule.h"
#ifndef UMA_WAVE_WRITE
#define UMA_WAVE_WRITE waveOutWrite
#endif
static UmaEnginePatch uma_engine_patch;
static unsigned char uma_hoof_wave[2][10][32768];
static DWORD uma_hoof_bytes[2][10];
static HWAVEOUT uma_hoof_output[2];
static WAVEHDR uma_hoof_header[2];
static unsigned uma_hoof_variant[2]={0,5};
static unsigned uma_hoof_played;
static inline void uma_hoof_output_close(void){
 for(int i=0;i<2;i++)if(uma_hoof_output[i]){
  waveOutReset(uma_hoof_output[i]);
  if(uma_hoof_header[i].dwFlags&WHDR_PREPARED)waveOutUnprepareHeader(uma_hoof_output[i],&uma_hoof_header[i],sizeof(WAVEHDR));
  waveOutClose(uma_hoof_output[i]);uma_hoof_output[i]=NULL;memset(&uma_hoof_header[i],0,sizeof(WAVEHDR));
 }
}
static inline int uma_hoof_load(const WCHAR *path,unsigned char *data){
 FILE *file=_wfopen(path,L"rb");if(!file)return 0;
 size_t bytes=fread(data,1,32768,file);int extra=fgetc(file);fclose(file);
 if(bytes<44 || ((bytes-44)&1) || extra!=EOF || memcmp(data,"RIFF",4) || uma_audio_word(data+4)!=bytes-8 || memcmp(data+8,"WAVEfmt ",8) || uma_audio_word(data+16)!=16 || memcmp(data+20,"\1\0\1\0",4) || uma_audio_word(data+24)!=22050 || uma_audio_word(data+28)!=44100 || memcmp(data+32,"\2\0\20\0data",8) || uma_audio_word(data+40)!=bytes-44)return 0;
 return (int)bytes;
}
static inline int uma_audio_start(const WCHAR *root,FILE *log){
 WCHAR path[4096];if(wcslen(root)>3900 || !waveOutGetNumDevs())return 0;
 for(int foot=0;foot<2;foot++)for(int variant=0;variant<10;variant++){
  swprintf(path,4096,L"%ls\\modding\\runtime\\hoof-%d-%d.wav",root,foot,variant);
  int bytes=uma_hoof_load(path,uma_hoof_wave[foot][variant]);if(!bytes){if(log){fprintf(log,"AUDIO missing or invalid original sample foot=%d variant=%d\n",foot,variant);fflush(log);}return 0;}uma_hoof_bytes[foot][variant]=(DWORD)bytes;
 }
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
 int profiles=engine_matches==1 && mapping_matches==1;
 WAVEFORMATEX format={WAVE_FORMAT_PCM,1,22050,44100,2,16,0};int outputs=profiles;
 for(int i=0;i<2 && outputs;i++)if(waveOutOpen(&uma_hoof_output[i],WAVE_MAPPER,&format,0,0,CALLBACK_NULL)!=MMSYSERR_NOERROR)outputs=0;
 int installed=outputs && uma_engine_apply(&uma_engine_patch,engines,UMA_ENGINE_BYTES,mapping,UMA_MAPPING_BYTES);
 if(!installed)uma_hoof_output_close();
 if(log){fprintf(log,"AUDIO engineProfiles=%u mappingProfiles=%u installed=%d; mutable data only; Corolla-only silent engine slot and hoof samples\n",engine_matches,mapping_matches,installed);fflush(log);}return installed;
}
static inline void uma_audio_step(float previous,float next,float blend,float speed,float seconds,FILE *log){
 if(!uma_engine_patch.active)return;
 unsigned events=uma_hoof_schedule(previous,next,blend,speed,seconds);
 for(unsigned foot=0;foot<2;foot++)if(events&(1u<<foot)){
  WAVEHDR *header=&uma_hoof_header[foot];MMRESULT result=MMSYSERR_NOERROR;
  if(header->dwFlags&WHDR_INQUEUE)continue;
  if(header->dwFlags&WHDR_PREPARED)result=waveOutUnprepareHeader(uma_hoof_output[foot],header,sizeof(*header));
  unsigned variant=uma_hoof_variant[foot];
  if(result==MMSYSERR_NOERROR){memset(header,0,sizeof(*header));header->lpData=(LPSTR)uma_hoof_wave[foot][variant]+44;header->dwBufferLength=uma_hoof_bytes[foot][variant]-44;}
  if(result==MMSYSERR_NOERROR)result=waveOutPrepareHeader(uma_hoof_output[foot],header,sizeof(*header));
  if(result==MMSYSERR_NOERROR)result=UMA_WAVE_WRITE(uma_hoof_output[foot],header,sizeof(*header));
  if(result!=MMSYSERR_NOERROR){
   uma_hoof_output_close();int restored=uma_engine_restore(&uma_engine_patch);if(log){fprintf(log,"AUDIO playback failed code=%u; original engine routing restored=%d\n",result,restored);fflush(log);}return;
  }
  uma_hoof_variant[foot]=(variant+7)%10;uma_hoof_played++;
 }
}
static inline void uma_audio_close(void){uma_hoof_output_close();if(uma_engine_patch.active)(void)uma_engine_restore(&uma_engine_patch);}
#endif
