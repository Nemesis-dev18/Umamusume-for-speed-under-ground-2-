#ifndef UMA_FOOT_SPARKS_H
#define UMA_FOOT_SPARKS_H
#include "uma_motion.h"
static inline int uma_spark_cloth(const UmaMotion *motion,unsigned i){
 if(motion->secondary_mask)for(int j=0;j<4;j++)if(motion->skin[i].weight[j]>0 && motion->secondary_mask[motion->skin[i].bone[j]])return 1;
 return 0;
}
/* Cosmetic contact sparks: use uncorrected shoe soles, never car light or tire emitters. */
static inline void uma_spark_contacts(const UmaMotion *motion,const UmaVertex *pose,float feet[2][3],unsigned counts[2]){
 memset(feet,0,6*sizeof(float));counts[0]=counts[1]=0;float low=10000;
 for(unsigned i=0;i<motion->vertices;i++){
  if(!uma_spark_cloth(motion,i) && pose[i].position[2]<low)low=pose[i].position[2];
 }
 if(low>.05f || low<-.05f)return;
 for(unsigned i=0;i<motion->vertices;i++)if(!uma_spark_cloth(motion,i) && pose[i].position[2]<=low+.018f && fabsf(pose[i].position[1])>.025f){
  unsigned side=pose[i].position[1]>0;counts[side]++;for(int k=0;k<3;k++)feet[side][k]+=pose[i].position[k];
 }
 for(int side=0;side<2;side++)if(counts[side])for(int k=0;k<3;k++)feet[side][k]/=counts[side];
}
static inline unsigned uma_spark_mesh(float phase,float feet[2][3],const unsigned counts[2],const float *root,const float *facing,UmaVertex output[48]){
 unsigned vertices=0;const float axes[]={0,1,0,0,0,1};if(!facing)facing=axes;
 for(int side=0;side<2;side++)if(counts[side])for(int i=0;i<4;i++){
  float age=uma_fraction(phase*2+i*.237f+side*.37f),width=.09f*(1-age)+.025f;
  float local[]={feet[side][0]-.5f*age,feet[side][1]+(side?1.f:-1.f)*(.05f+.08f*age),feet[side][2]+.05f+.06f*sinf(age*3.14159265f)},center[3]={0};
  if(root){for(int c=0;c<3;c++)for(int k=0;k<3;k++)center[c]+=local[k]*root[k*3+c];}else memcpy(center,local,12);
  unsigned frame=(unsigned)(age*8);if(frame>7)frame=7;
  for(int v=0;v<6;v++){
   static const unsigned corners[]={0,1,2,2,1,3};unsigned corner=corners[v];UmaVertex *point=output+vertices++;memset(point,0,sizeof(*point));
   for(int k=0;k<3;k++)point->position[k]=center[k]+facing[k]*((corner&1)?width:-width)+facing[3+k]*((corner&2)?width:-width);
   point->uv[0]=((frame%4)+((corner&1)?.9921875f:.0078125f))/4;
   point->uv[1]=((frame/4)+((corner&2)?.0078125f:.9921875f))/2;
   point->normal[2]=1;memset(point->bgra,255,4);
  }
 }
 return vertices;
}
#endif
