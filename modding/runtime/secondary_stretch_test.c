#include <assert.h>
#include "uma_secondary.h"
#include "uma_cloth_surface.h"
int main(int argc,char **argv){
 assert(argc==4);UmaMotion a={0};FILE *f=fopen(argv[1],"rb");assert(f && uma_motion_load(f,&a));fclose(f);UmaSecondary *c=calloc(1,sizeof(*c));UmaSecondaryState *s=calloc(1,sizeof(*s));assert(c && s);f=fopen(argv[2],"rb");assert(f && uma_secondary_load(f,&a,c));fclose(f);a.secondary_mask=c->mask;a.surface_mask=c->surface_mask;
 unsigned char mask[512]={0};f=fopen(argv[3],"rb");assert(f && fread(mask,1,a.bones,f)==a.bones && fgetc(f)==EOF);fclose(f);
 float *weight=calloc(a.vertices,sizeof(float));assert(weight);for(unsigned i=0;i<a.vertices;i++)for(int j=0;j<4;j++)if(mask[a.skin[i].bone[j]])weight[i]+=a.skin[i].weight[j];
 uint16_t *edges=malloc(a.indices*4);assert(edges);uint32_t edge_count=uma_cloth_edges(&a,weight,edges);assert(edge_count);float *lengths=malloc((size_t)edge_count*sizeof(float));assert(lengths);
 UmaVertex *reference=malloc(a.vertices*36);assert(reference);
 UmaVertex *base=malloc(a.vertices*36),*cloth=malloc(a.vertices*36);assert(base && cloth);UmaMotionState p={0};float acceleration[3]={0},maximum=0;unsigned checked=0,over10=0,over25=0,over50=0;
 for(int frame=0;frame<600;frame++){
  float speed=frame%200<100?12:0;acceleration[0]=frame%200==100?-35:0;assert(uma_motion_step_timed(&p,1.f/60,speed,0,a.idle_seconds,a.run_seconds));assert(uma_secondary_step(c,s,&a,&p,1.f/60,speed,acceleration));if(frame%4)continue;
  assert(uma_motion_sample(&a,p.idle_phase,p.run_phase,p.run_blend,base,a.vertices*36));assert(uma_motion_sample_secondary(&a,p.idle_phase,p.run_phase,p.run_blend,cloth,a.vertices*36,s->rotation));
  assert(uma_cloth_project(&a,&p,cloth,reference,weight,edges,edge_count,lengths));
  for(unsigned t=0;t<a.indices;t+=3)for(int e=0;e<3;e++){
   unsigned u=a.index[t+e],v=a.index[t+(e+1)%3];float wu=0,wv=0;
   for(int j=0;j<4;j++){if(mask[a.skin[u].bone[j]])wu+=a.skin[u].weight[j];if(mask[a.skin[v].bone[j]])wv+=a.skin[v].weight[j];}if(wu<.5f || wv<.5f)continue;
   float b[3],d[3];for(int k=0;k<3;k++){b[k]=base[u].position[k]-base[v].position[k];d[k]=cloth[u].position[k]-cloth[v].position[k];}float before=uma_secondary_length(b);if(before<.005f)continue;
   float change=fabsf(uma_secondary_length(d)/before-1);assert(isfinite(change));maximum=fmaxf(change,maximum);checked++;if(change>.1f)over10++;if(change>.25f)over25++;if(change>.5f)over50++;
  }
 }
 printf("edges=%u absolute_length_change_max=%.5f fraction_over_10pct=%.5f fraction_over_25pct=%.5f fraction_over_50pct=%.5f\n",checked,maximum,(float)over10/checked,(float)over25/checked,(float)over50/checked);fflush(stdout);assert(checked && maximum<.2f && over25==0);
 free(lengths);free(edges);free(weight);free(reference);free(base);free(cloth);free(c);free(s);uma_motion_free(&a);return 0;
}
