#ifndef UMA_ENGINE_AUDIO_H
#define UMA_ENGINE_AUDIO_H
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include "uma_engine_profile.h"
#define UMA_ENGINE_BYTES (43u*76u)
#define UMA_MAPPING_BYTES (33u*48u)
typedef struct {unsigned char *engines,*mapping;unsigned char previous[76],replacement[76];uint32_t previous_ids[4];int active;} UmaEnginePatch;
static uint32_t uma_audio_word(const unsigned char *p){uint32_t v;memcpy(&v,p,4);return v;}
static int uma_engine_profile_matches(const unsigned char *p,size_t bytes){
 if(!p || bytes<UMA_ENGINE_BYTES)return 0;
 for(unsigned i=0;i<43;i++)if(uma_audio_word(p+i*76+8)!=uma_engine_profile[i][0] || memcmp(p+i*76+16,uma_engine_profile[i]+1,60))return 0;
 return 1;
}
static int uma_engine_apply(UmaEnginePatch *patch,unsigned char *engines,size_t engine_bytes,unsigned char *mapping,size_t mapping_bytes){
 if(!patch || patch->active || !uma_engine_profile_matches(engines,engine_bytes) || !mapping || mapping_bytes<UMA_MAPPING_BYTES || memcmp(mapping,uma_mapping_profile,UMA_MAPPING_BYTES))return 0;
 for(unsigned i=0;i<33;i++)for(unsigned j=0;j<4;j++)if(uma_audio_word(mapping+i*48+j*12)==3)return 0;
 patch->engines=engines;patch->mapping=mapping;memcpy(patch->previous,engines+3*76,76);memcpy(patch->replacement,engines+18*76,76);
 memset(patch->replacement+36,0,8);memcpy(engines+3*76,patch->replacement,76);
 for(unsigned i=0;i<4;i++){unsigned char *entry=mapping+6*48+i*12;patch->previous_ids[i]=uma_audio_word(entry);uint32_t value=3;memcpy(entry,&value,4);}
 patch->active=1;return 1;
}
static int uma_engine_restore(UmaEnginePatch *patch){
 if(!patch || !patch->active || memcmp(patch->engines+3*76,patch->replacement,76))return 0;
 for(unsigned i=0;i<4;i++)if(uma_audio_word(patch->mapping+6*48+i*12)!=3)return 0;
 memcpy(patch->engines+3*76,patch->previous,76);
 for(unsigned i=0;i<4;i++)memcpy(patch->mapping+6*48+i*12,&patch->previous_ids[i],4);
 memset(patch,0,sizeof(*patch));return 1;
}
#endif
