#include <assert.h>
#include <time.h>
#include "uma_secondary.h"
int main(int argc,char **argv){
 assert(argc==3 || argc==4);UmaMotion a={0};FILE *f=fopen(argv[1],"rb");assert(f && uma_motion_load(f,&a));fclose(f);
 UmaSecondary *c=calloc(1,sizeof(*c));UmaSecondaryState *s=calloc(1,sizeof(*s));f=fopen(argv[2],"rb");assert(f);int valid=uma_secondary_load(f,&a,c);fclose(f);if(argc==4){free(c);free(s);uma_motion_free(&a);return valid?0:2;}assert(valid);a.secondary_mask=c->mask;
 UmaVertex *v=malloc(a.vertices*sizeof(*v));UmaMotionState p={0};float accel[3]={0};clock_t start=clock();float moved=0,maximum=0;
 for(int frame=0;frame<3600;frame++){
  float dt=frame%79==0?1.f/25:1.f/60;float speed=frame%600<300?10:0;accel[0]=frame%600==300?-35:0;
  assert(uma_motion_step_timed(&p,dt,speed,0,a.idle_seconds,a.run_seconds));assert(uma_secondary_step(c,s,&a,&p,dt,speed,accel));
  for(unsigned b=0;b<a.bones;b++){float *q=s->rotation+b*4,n=0;for(int k=0;k<4;k++){assert(isfinite(q[k]));n+=q[k]*q[k];}assert(fabsf(n-1)<1e-4f);moved+=fabsf(q[0])+fabsf(q[1])+fabsf(q[2]);}
  if(frame%60==0){assert(uma_motion_sample_secondary(&a,p.idle_phase,p.run_phase,p.run_blend,v,a.vertices*36,s->rotation));for(unsigned i=0;i<a.vertices;i++)for(int k=0;k<3;k++){assert(isfinite(v[i].position[k]) && fabsf(v[i].position[k])<2.25f);maximum=fmaxf(maximum,fabsf(v[i].position[k]));}}
 }
 assert(moved>1);assert(!uma_secondary_step(c,s,&a,&p,-1,0,accel));assert(uma_secondary_step(c,s,&a,&p,1,0,accel));
 unsigned revision=s->revision;assert(uma_secondary_step(c,s,&a,&p,0,0,accel));assert(revision==s->revision);
 printf("bones=%u springs=%u 3600_frames_cpu_seconds=%.4f motion=%.1f max_absolute_vertex=%.3f\n",a.bones,c->nodes,(double)(clock()-start)/CLOCKS_PER_SEC,moved,maximum);
 free(v);free(c);free(s);uma_motion_free(&a);return 0;
}
