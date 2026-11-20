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
static inline unsigned uma_spark_mesh(float phase,float feet[2][3],const unsigned counts[2],const float *root,UmaVertex output[24]){
 unsigned vertices=0;
 for(int side=0;side<2;side++)if(counts[side])for(int i=0;i<4;i++){
  float age=uma_fraction(phase*7+i*.237f+side*.37f),width=.006f*(1-age)+.002f;
  float center[]={feet[side][0]-.16f*age,feet[side][1]+(i-1.5f)*.025f*age,feet[side][2]+.008f+.06f*sinf(age*3.14159265f)};
  for(int v=0;v<3;v++){
   UmaVertex *point=output+vertices++;memset(point,0,sizeof(*point));float p[]={center[0]+(v==0?-.025f:(v==1?.015f:0)),center[1]+(v==0?-width:(v==1?width:0)),center[2]+(v==2?width*2:0)};
   if(root){for(int c=0;c<3;c++)for(int k=0;k<3;k++)point->position[c]+=p[k]*root[k*3+c];}else memcpy(point->position,p,12);
   point->normal[2]=1;memset(point->bgra,255,4);
  }
 }
 return vertices;
}
#endif
