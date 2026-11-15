#define COBJMACROS
#include <windows.h>
#include <mmsystem.h>
#include <stdio.h>
#include <stdint.h>
#include <wchar.h>
#include <assert.h>
static int force_failure;
static MMRESULT WINAPI test_write(HWAVEOUT output,LPWAVEHDR header,UINT bytes){return force_failure?MMSYSERR_ERROR:waveOutWrite(output,header,bytes);}
#define UMA_WAVE_WRITE test_write
#include "uma_audio_win.h"
int main(void){
 WCHAR root[4096];assert(GetCurrentDirectoryW(4096,root));
 unsigned char gain[52]={0};int16_t input[]={10000,-10000,30000,-30000},expected[]={15000,-15000,32767,-32768};memcpy(gain+44,input,8);uma_hoof_gain(gain,sizeof(gain));assert(!memcmp(gain+44,expected,8));
 assert(uma_hoof_schedule(.9f,.95f,1,6,.03f)==1);assert(uma_hoof_schedule(.4f,.45f,1,6,.03f)==2);assert(uma_hoof_schedule(.9f,.01f,1,6,.07f)==1);assert(uma_hoof_schedule(.95f,.9f,1,-6,.03f)==1);assert(!uma_hoof_schedule(0,.05f,1,6,.03f));
 assert(uma_audio_start(root,stdout));assert(uma_audio_active);
 uma_audio_step(.9f,.95f,1,6,.03f,stdout);assert(uma_hoof_played==1 && uma_audio_active);Sleep(100);
 uma_audio_step(.4f,.45f,1,6,.03f,stdout);assert(uma_hoof_played==2);assert((uma_hoof_header[0].dwFlags&WHDR_INQUEUE) && (uma_hoof_header[1].dwFlags&WHDR_INQUEUE));for(int wait=0;wait<40 && ((uma_hoof_header[0].dwFlags|uma_hoof_header[1].dwFlags)&WHDR_INQUEUE);wait++)Sleep(50);
 assert(!((uma_hoof_header[0].dwFlags|uma_hoof_header[1].dwFlags)&WHDR_INQUEUE));
 uma_audio_step(.1f,.2f,1,0,.03f,stdout);assert(uma_hoof_played==2);
 force_failure=1;uma_audio_step(.4f,.45f,1,6,.03f,stdout);assert(!uma_audio_active);assert(!uma_hoof_output[0] && !uma_hoof_output[1]);
 uma_audio_close();puts("PASS actual WinMM accepts original footsteps with overlapping left/right tails, idle silent, playback failure closes only own outputs; contact lead and gain saturation checked; synthetic host only");return 0;
}
