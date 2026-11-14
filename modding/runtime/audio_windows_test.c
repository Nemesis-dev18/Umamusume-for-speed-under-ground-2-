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
unsigned char test_engines[UMA_ENGINE_BYTES],test_mapping[UMA_MAPPING_BYTES];
int main(void){
 for(unsigned i=0;i<43;i++){memcpy(test_engines+i*76+8,uma_engine_profile[i],4);memcpy(test_engines+i*76+16,uma_engine_profile[i]+1,60);}
 memcpy(test_mapping,uma_mapping_profile,sizeof(test_mapping));WCHAR root[4096];assert(GetCurrentDirectoryW(4096,root));
 assert(uma_audio_start(root,stdout));assert(uma_engine_patch.active);
 uma_audio_step(0,.05f,1,6,.03f,stdout);assert(uma_hoof_played==1 && uma_engine_patch.active);Sleep(100);
 uma_audio_step(.5f,.55f,1,6,.03f,stdout);assert(uma_hoof_played==2);assert((uma_hoof_header[0].dwFlags&WHDR_INQUEUE) && (uma_hoof_header[1].dwFlags&WHDR_INQUEUE));for(int wait=0;wait<40 && ((uma_hoof_header[0].dwFlags|uma_hoof_header[1].dwFlags)&WHDR_INQUEUE);wait++)Sleep(50);
 assert(!((uma_hoof_header[0].dwFlags|uma_hoof_header[1].dwFlags)&WHDR_INQUEUE));
 uma_audio_step(.1f,.2f,1,0,.03f,stdout);assert(uma_hoof_played==2);
 force_failure=1;uma_audio_step(.5f,.55f,1,6,.03f,stdout);assert(!uma_engine_patch.active);assert(!memcmp(test_mapping,uma_mapping_profile,sizeof(test_mapping)));
 uma_audio_close();puts("PASS actual WinMM accepts original footsteps with overlapping left/right tails, idle silent, playback failure restores native engine mapping; synthetic host only");return 0;
}
