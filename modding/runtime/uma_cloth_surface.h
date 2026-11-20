#ifndef UMA_CLOTH_SURFACE_H
#define UMA_CLOTH_SURFACE_H
#include "uma_motion.h"
static inline uint32_t uma_cloth_edges(const UmaMotion *a,const float *weight,uint16_t *edges){
 uint32_t count=0;for(uint32_t t=0;t<a->indices;t+=3)for(int e=0;e<3;e++){uint16_t u=a->index[t+e],v=a->index[t+(e+1)%3];if(weight[u]+weight[v]>0){edges[count*2]=u;edges[count*2+1]=v;count++;}}
 return count;
}
/* Spring bones supply motion; surface constraints stop linked cape panels stretching apart. */
static inline int uma_cloth_project(const UmaMotion *a,const UmaMotionState *state,UmaVertex *pose,UmaVertex *base,const float *weight,const uint16_t *edges,uint32_t edge_count){
 if(!uma_motion_sample(a,state->idle_phase,state->run_phase,state->run_blend,base,(size_t)a->vertices*36))return 0;
 /* Dense skirt panels need more convergence than the existing cape meshes. */
 int iterations=16;if(a->surface_mask)for(unsigned b=0;b<a->bones;b++)if(a->surface_mask[b]==2){iterations=24;break;}
 for(int iteration=0;iteration<iterations;iteration++)for(uint32_t edge=0;edge<edge_count;edge++){
  uint16_t u=edges[edge*2],v=edges[edge*2+1];float mass=weight[u]+weight[v];if(mass<=0)continue;
  float delta[3],rest[3],length=0,original=0;
  for(int k=0;k<3;k++){delta[k]=pose[v].position[k]-pose[u].position[k];rest[k]=base[v].position[k]-base[u].position[k];length+=delta[k]*delta[k];original+=rest[k]*rest[k];}
  length=sqrtf(length);original=sqrtf(original);if(length<1e-7f || original<.001f)continue;
  float target=fminf(original*1.04f,fmaxf(original*.96f,length));float correction=.8f*(length-target)/(length*mass);
  for(int k=0;k<3;k++){pose[u].position[k]+=delta[k]*correction*weight[u];pose[v].position[k]-=delta[k]*correction*weight[v];}
 }
 for(uint32_t i=0;i<a->vertices;i++)if(weight[i]>0)memset(pose[i].normal,0,12);
 for(uint32_t t=0;t<a->indices;t+=3){
  uint16_t u=a->index[t],v=a->index[t+1],w=a->index[t+2];if(weight[u]+weight[v]+weight[w]<=0)continue;
  float x[3],y[3],normal[3];for(int k=0;k<3;k++){x[k]=pose[v].position[k]-pose[u].position[k];y[k]=pose[w].position[k]-pose[u].position[k];}
  for(int k=0;k<3;k++)normal[k]=x[(k+1)%3]*y[(k+2)%3]-x[(k+2)%3]*y[(k+1)%3];
  float dot=0;for(int k=0;k<3;k++)dot+=normal[k]*base[u].normal[k];if(dot<0)for(int k=0;k<3;k++)normal[k]*=-1;
  const uint16_t ids[]={u,v,w};for(int j=0;j<3;j++)if(weight[ids[j]]>0)for(int k=0;k<3;k++)pose[ids[j]].normal[k]+=normal[k];
 }
 for(uint32_t i=0;i<a->vertices;i++)if(weight[i]>0){float length=0;for(int k=0;k<3;k++)length+=pose[i].normal[k]*pose[i].normal[k];if(length<1e-12f)memcpy(pose[i].normal,base[i].normal,12);else for(int k=0;k<3;k++)pose[i].normal[k]/=sqrtf(length);}
 return 1;
}
#endif
