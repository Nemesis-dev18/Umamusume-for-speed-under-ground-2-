#ifndef UMA_GARMENT_LINKS_H
#define UMA_GARMENT_LINKS_H
#include "uma_motion.h"
typedef struct {uint16_t a,b;float distance,intensity;uint32_t flags;} UmaGarmentLink;
typedef struct {uint32_t bones,count;UmaGarmentLink pair[256];} UmaGarmentLinks;
_Static_assert(sizeof(UmaGarmentLink)==16,"UMAL link record");
static inline int uma_garment_links_load(FILE *file,const UmaMotion *asset,UmaGarmentLinks *out){
 uint32_t h[4];UmaGarmentLinks data={0};
 if(!file || !asset || !out || fread(h,4,4,file)!=4 || memcmp(h,"UMAL",4) || h[1]!=1 || !h[2] || h[2]>512 || h[2]!=asset->bones || h[3]>256)return 0;
 data.bones=h[2];data.count=h[3];if(fread(data.pair,16,data.count,file)!=data.count || fgetc(file)!=EOF)return 0;
 for(unsigned i=0;i<data.count;i++){
  const UmaGarmentLink *p=data.pair+i;
  if(p->a>=data.bones || p->b>=data.bones || p->a==p->b || !isfinite(p->distance) || p->distance<.0001f || p->distance>2 || !isfinite(p->intensity) || p->intensity<0 || p->intensity>1 || (p->flags&~1u))return 0;
 }
 *out=data;return 1;
}
/* Native-style distance correction; caller decides integration, not a Unity solver port. */
static inline int uma_garment_link_forces(const UmaMotion *asset,const UmaGarmentLinks *links,const float *matrices,float *out){
 if(!asset || !asset->joint || !links || !matrices || !out || !asset->bones || asset->bones>512 || links->bones!=asset->bones || links->count>256)return 0;
 float force[512*3]={0};
 for(unsigned i=0;i<links->count;i++){
  const UmaGarmentLink *p=links->pair+i;if(p->a>=asset->bones || p->b>=asset->bones || p->a==p->b || p->flags || !isfinite(p->distance) || p->distance<.0001f || p->distance>2 || !isfinite(p->intensity) || p->intensity<0 || p->intensity>1)return 0;
  unsigned ids[]={p->a,p->b};float point[2][3];
  for(int end=0;end<2;end++)for(int axis=0;axis<3;axis++){
   const float *m=matrices+ids[end]*12+axis*4,*rest=asset->joint[ids[end]].rest;point[end][axis]=m[3];for(int k=0;k<3;k++)point[end][axis]+=m[k]*rest[k];if(!isfinite(point[end][axis]))return 0;
  }
  float delta[3],length=0;for(int k=0;k<3;k++){delta[k]=point[1][k]-point[0][k];length+=delta[k]*delta[k];}length=sqrtf(length);if(length<1e-8f)continue;
  float gain=(length-p->distance)*p->intensity/length;
  for(int k=0;k<3;k++){float value=delta[k]*gain;force[p->a*3+k]+=value;force[p->b*3+k]-=value;if(!isfinite(force[p->a*3+k]) || !isfinite(force[p->b*3+k]))return 0;}
 }
 memcpy(out,force,(size_t)asset->bones*3*sizeof(float));return 1;
}
#endif
