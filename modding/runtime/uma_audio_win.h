#ifndef UMA_AUDIO_WIN_H
#define UMA_AUDIO_WIN_H
#include <mmsystem.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include "uma_hoof_schedule.h"
#ifndef UMA_WAVE_WRITE
#define UMA_WAVE_WRITE waveOutWrite
#endif
static int uma_audio_active;
static inline uint32_t uma_audio_word(const unsigned char *p){uint32_t value;memcpy(&value,p,4);return value;}
static unsigned char uma_hoof_wave[2][10][32768];
static DWORD uma_hoof_bytes[2][10];
static HWAVEOUT uma_hoof_output[2];
static WAVEHDR uma_hoof_header[2];
static unsigned uma_hoof_variant[2]={0,5};
static unsigned uma_hoof_played;
static inline void uma_hoof_output_close(void){
 uma_audio_active=0;
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
/* Raise only the footsteps by 3.5 dB; original decoded files remain intact. */
static inline void uma_hoof_gain(unsigned char *data,size_t bytes){
 for(size_t at=44;at+1<bytes;at+=2){int16_t sample;memcpy(&sample,data+at,2);int value=(int)sample*3/2;if(value>32767)value=32767;if(value< -32768)value=-32768;sample=(int16_t)value;memcpy(data+at,&sample,2);}
}
static inline int uma_audio_start(const WCHAR *root,FILE *log){
 WCHAR path[4096];if(wcslen(root)>3900 || !waveOutGetNumDevs())return 0;
 for(int foot=0;foot<2;foot++)for(int variant=0;variant<10;variant++){
  swprintf(path,4096,L"%ls\\modding\\runtime\\hoof-%d-%d.wav",root,foot,variant);
  int bytes=uma_hoof_load(path,uma_hoof_wave[foot][variant]);if(!bytes){if(log){fprintf(log,"AUDIO missing or invalid original sample foot=%d variant=%d\n",foot,variant);fflush(log);}return 0;}uma_hoof_bytes[foot][variant]=(DWORD)bytes;uma_hoof_gain(uma_hoof_wave[foot][variant],(size_t)bytes);
 }
 WAVEFORMATEX format={WAVE_FORMAT_PCM,1,22050,44100,2,16,0};int outputs=1;
 for(int i=0;i<2 && outputs;i++)if(waveOutOpen(&uma_hoof_output[i],WAVE_MAPPER,&format,0,0,CALLBACK_NULL)!=MMSYSERR_NOERROR)outputs=0;
 if(!outputs)uma_hoof_output_close();else uma_audio_active=1;
 if(log){fprintf(log,"AUDIO originalVariants=20 outputStreams=2 installed=%d; sample playback only, no game data patch\n",uma_audio_active);fflush(log);}return uma_audio_active;
}
static inline void uma_audio_step(float previous,float next,float blend,float speed,float seconds,FILE *log){
 if(!uma_audio_active)return;
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
   uma_hoof_output_close();if(log){fprintf(log,"AUDIO playback failed code=%u; own outputs stopped\n",result);fflush(log);}return;
  }
  uma_hoof_variant[foot]=(variant+7)%10;uma_hoof_played++;
 }
}
static inline void uma_audio_close(void){uma_hoof_output_close();}
#endif
