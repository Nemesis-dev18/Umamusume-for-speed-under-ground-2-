#ifndef UMA_CLOTH_SURFACE_H
#define UMA_CLOTH_SURFACE_H
#include "uma_motion.h"
static int uma_cloth_edge_compare(const void *a,const void *b){
 const uint16_t *x=a,*y=b;return x[0]!=y[0]?(x[0]>y[0]?1:-1):x[1]!=y[1]?(x[1]>y[1]?1:-1):0;
}
static inline uint32_t uma_cloth_edges(const UmaMotion *a,const float *weight,uint16_t *edges){
 uint32_t count=0;for(uint32_t t=0;t<a->indices;t+=3)for(int e=0;e<3;e++){uint16_t u=a->index[t+e],v=a->index[t+(e+1)%3];if(u!=v && weight[u]+weight[v]>0){edges[count*2]=u<v?u:v;edges[count*2+1]=u<v?v:u;count++;}}
 qsort(edges,count,4,uma_cloth_edge_compare);uint32_t unique=0;
 for(uint32_t edge=0;edge<count;edge++)if(!unique || edges[edge*2]!=edges[(unique-1)*2] || edges[edge*2+1]!=edges[(unique-1)*2+1]){edges[unique*2]=edges[edge*2];edges[unique*2+1]=edges[edge*2+1];unique++;}
 return unique;
}
static inline void uma_cloth_normals(const UmaMotion *a,UmaVertex *pose,const UmaVertex *base,const float *weight){
 for(uint32_t i=0;i<a->vertices;i++)if(weight[i]>0)memset(pose[i].normal,0,12);
 for(uint32_t t=0;t<a->indices;t+=3){
  uint16_t u=a->index[t],v=a->index[t+1],w=a->index[t+2];if(weight[u]+weight[v]+weight[w]<=0)continue;
  float x[3],y[3],normal[3];for(int k=0;k<3;k++){x[k]=pose[v].position[k]-pose[u].position[k];y[k]=pose[w].position[k]-pose[u].position[k];}
  for(int k=0;k<3;k++)normal[k]=x[(k+1)%3]*y[(k+2)%3]-x[(k+2)%3]*y[(k+1)%3];
  float dot=0;for(int k=0;k<3;k++)dot+=normal[k]*base[u].normal[k];if(dot<0)for(int k=0;k<3;k++)normal[k]*=-1;
  const uint16_t ids[]={u,v,w};for(int j=0;j<3;j++)if(weight[ids[j]]>0)for(int k=0;k<3;k++)pose[ids[j]].normal[k]+=normal[k];
 }
 for(uint32_t i=0;i<a->vertices;i++)if(weight[i]>0){float length=0;for(int k=0;k<3;k++)length+=pose[i].normal[k]*pose[i].normal[k];if(length<1e-12f)memcpy(pose[i].normal,base[i].normal,12);else for(int k=0;k<3;k++)pose[i].normal[k]/=sqrtf(length);}
}
/* Include boundary vertices too: their normals orient cloth triangles. */
static inline uint32_t uma_cloth_reference_vertices(const UmaMotion *a,const float *weight,uint16_t *output){
 uint8_t *needed=calloc(a->vertices,1);if(!needed)return UINT32_MAX;
 for(unsigned t=0;t<a->indices;t+=3){uint16_t u=a->index[t],v=a->index[t+1],w=a->index[t+2];if(weight[u]+weight[v]+weight[w]>0)needed[u]=needed[v]=needed[w]=1;}
 uint32_t count=0;for(unsigned v=0;v<a->vertices;v++)if(needed[v])output[count++]=(uint16_t)v;free(needed);return count;
}
static inline int uma_cloth_reference_subset(const UmaMotion *a,const UmaMotionState *state,UmaVertex *base,const uint16_t *vertices,uint32_t count){
 if(!a || !state || !base || !vertices || count>a->vertices)return 0;
 for(unsigned i=0;i<count;i++)if(vertices[i]>=a->vertices)return 0;
 float matrices[512*12];if(!uma_motion_matrices(a,state->idle_phase,state->run_phase,state->run_blend,NULL,matrices))return 0;
 for(unsigned i=0;i<count;i++){
  unsigned v=vertices[i];UmaVertex *p=base+v;*p=a->rest[v];memset(p->position,0,12);memset(p->normal,0,12);
  for(int j=0;j<4;j++){
   float weight=a->skin[v].weight[j];if(weight==0)continue;const float *matrix=matrices+a->skin[v].bone[j]*12;
   for(int axis=0;axis<3;axis++){const float *row=matrix+axis*4;float pp=row[3],nn=0;for(int k=0;k<3;k++){pp+=row[k]*a->rest[v].position[k];nn+=row[k]*a->rest[v].normal[k];}p->position[axis]+=pp*weight;p->normal[axis]+=nn*weight;}
  }
  float length=sqrtf(p->normal[0]*p->normal[0]+p->normal[1]*p->normal[1]+p->normal[2]*p->normal[2]);if(length<1e-8f){memcpy(p->normal,a->rest[v].normal,12);length=sqrtf(p->normal[0]*p->normal[0]+p->normal[1]*p->normal[1]+p->normal[2]*p->normal[2]);}for(int k=0;k<3;k++)p->normal[k]/=length;
 }
 /* A uniform support-plane lift cancels from every edge, so no whole-body floor pass is needed. */
 return 1;
}
/* Spring bones supply motion; surface constraints stop linked cape panels stretching apart. */
static inline int uma_cloth_solve(const UmaMotion *a,UmaVertex *pose,UmaVertex *base,const float *weight,const uint16_t *edges,uint32_t edge_count,float *lengths){
 if(!lengths)return 0;
 /* Reference lengths stay constant throughout one solve; most edges need no correction. */
 for(uint32_t edge=0;edge<edge_count;edge++){
  uint16_t u=edges[edge*2],v=edges[edge*2+1];float squared=0;
  for(int k=0;k<3;k++){float d=base[v].position[k]-base[u].position[k];squared+=d*d;}
  lengths[edge]=sqrtf(squared);
 }
 /* Dense skirt panels need more convergence than the existing cape meshes. */
 int iterations=16;if(a->surface_mask)for(unsigned b=0;b<a->bones;b++)if(a->surface_mask[b]==2){iterations=24;break;}
 for(int iteration=0;iteration<iterations;iteration++)for(uint32_t edge=0;edge<edge_count;edge++){
  uint16_t u=edges[edge*2],v=edges[edge*2+1];float mass=weight[u]+weight[v];if(mass<=0)continue;
  float delta[3],length=0,original=lengths[edge];if(original<.001f)continue;
  for(int k=0;k<3;k++){delta[k]=pose[v].position[k]-pose[u].position[k];length+=delta[k]*delta[k];}
  float squared=original*original;
  if(length>=squared*(.96f*.96f) && length<=squared*(1.04f*1.04f))continue;
  length=sqrtf(length);if(length<1e-7f)continue;
  float target=fminf(original*1.04f,fmaxf(original*.96f,length));float correction=.8f*(length-target)/(length*mass);
  for(int k=0;k<3;k++){pose[u].position[k]+=delta[k]*correction*weight[u];pose[v].position[k]-=delta[k]*correction*weight[v];}
 }
 uma_cloth_normals(a,pose,base,weight);
 return 1;
}
static inline int uma_cloth_project(const UmaMotion *a,const UmaMotionState *state,UmaVertex *pose,UmaVertex *base,const float *weight,const uint16_t *edges,uint32_t edge_count,float *lengths){
 if(!uma_motion_sample(a,state->idle_phase,state->run_phase,state->run_blend,base,(size_t)a->vertices*36))return 0;
 return uma_cloth_solve(a,pose,base,weight,edges,edge_count,lengths);
}
static inline int uma_cloth_project_subset(const UmaMotion *a,const UmaMotionState *state,UmaVertex *pose,UmaVertex *base,const float *weight,const uint16_t *edges,uint32_t edge_count,float *lengths,const uint16_t *vertices,uint32_t count){
 if(!uma_cloth_reference_subset(a,state,base,vertices,count))return 0;
 return uma_cloth_solve(a,pose,base,weight,edges,edge_count,lengths);
}
#endif
