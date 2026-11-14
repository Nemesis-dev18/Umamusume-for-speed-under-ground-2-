#include "uma_engine_audio.h"
#include <assert.h>
#include "uma_hoof_schedule.h"
#include <stdio.h>
int main(void){
 unsigned char engine[UMA_ENGINE_BYTES]={0},mapping[UMA_MAPPING_BYTES],original_engine[UMA_ENGINE_BYTES],original_mapping[UMA_MAPPING_BYTES];
 for(unsigned i=0;i<43;i++){uint32_t pointer=0x12340000+i*100;memcpy(engine+i*76,&pointer,4);memcpy(engine+i*76+8,uma_engine_profile[i],4);memcpy(engine+i*76+16,uma_engine_profile[i]+1,60);}
 memcpy(mapping,uma_mapping_profile,sizeof(mapping));memcpy(original_engine,engine,sizeof(engine));memcpy(original_mapping,mapping,sizeof(mapping));UmaEnginePatch patch={0};
 assert(!uma_engine_apply(&patch,engine,UMA_ENGINE_BYTES-1,mapping,sizeof(mapping)));
 mapping[0]^=1;assert(!uma_engine_apply(&patch,engine,sizeof(engine),mapping,sizeof(mapping)));mapping[0]^=1;
 engine[36]^=1;assert(!uma_engine_apply(&patch,engine,sizeof(engine),mapping,sizeof(mapping)));engine[36]^=1;
 assert(uma_engine_apply(&patch,engine,sizeof(engine),mapping,sizeof(mapping)));
 assert(uma_audio_word(engine+3*76+36)==0 && uma_audio_word(engine+3*76+40)==0);
 for(unsigned i=0;i<sizeof(engine);i++)if(i<3*76 || i>=4*76)assert(engine[i]==original_engine[i]);
 for(unsigned i=0;i<33;i++)for(unsigned j=0;j<12;j++)assert(uma_audio_word(mapping+i*48+j*4)==(i==6 && j%3==0?3:uma_audio_word(original_mapping+i*48+j*4)));
 assert(!uma_engine_apply(&patch,engine,sizeof(engine),mapping,sizeof(mapping)));
 mapping[6*48]=99;assert(!uma_engine_restore(&patch));mapping[6*48]=3;
 assert(uma_engine_restore(&patch));assert(!memcmp(engine,original_engine,sizeof(engine)) && !memcmp(mapping,original_mapping,sizeof(mapping)));
 assert(uma_hoof_schedule(0,.05f,1,10,.03f)==1);assert(uma_hoof_schedule(.5f,.55f,1,10,.03f)==2);
 assert(uma_hoof_schedule(.9f,.05f,1,10,.09f)==1);assert(uma_hoof_schedule(.1f,0,1,-10,.06f)==1);
 assert(!uma_hoof_schedule(0,.05f,1,0,.03f));assert(!uma_hoof_schedule(0,.05f,0,10,.03f));assert(!uma_hoof_schedule(NAN,.05f,1,10,.03f));
 puts("PASS contact-phase hoof scheduler, wrap/reverse, stop, idle and invalid time/phase rejection");
 puts("PASS strict 43-engine/33-mapping profile, malformed/altered data rejection, Corolla-only routing and exact restoration; synthetic data only");return 0;
}
