#include <assert.h>
#include <time.h>
#include "uma_secondary.h"
#include "uma_cloth_surface.h"
int main(int argc,char **argv){
 assert(argc==3);UmaMotion a={0};FILE *f=fopen(argv[1],"rb");assert(f && uma_motion_load(f,&a));fclose(f);UmaSecondary *c=calloc(1,sizeof(*c));UmaSecondaryState *s=calloc(1,sizeof(*s));assert(c && s);f=fopen(argv[2],"rb");assert(f && uma_secondary_load(f,&a,c));fclose(f);a.secondary_mask=c->mask;a.surface_mask=c->surface_mask;
 float *weights=calloc(a.vertices,sizeof(float));uint16_t *edges=malloc(a.indices*4),*selected=malloc(a.vertices*2);UmaVertex *full=malloc(a.vertices*36),*part=malloc(a.vertices*36),*base=malloc(a.vertices*36),*subset=malloc(a.vertices*36);assert(weights && edges && selected && full && part && base && subset);
 for(unsigned v=0;v<a.vertices;v++)for(int j=0;j<4;j++)if(c->surface_mask[a.skin[v].bone[j]])weights[v]+=a.skin[v].weight[j];
 unsigned count=uma_cloth_edges(&a,weights,edges),needed=uma_cloth_reference_vertices(&a,weights,selected);assert(count && needed && needed<a.vertices);float *lengths=malloc(count*4);assert(lengths);UmaMotionState state={0};float largest_position=0,largest_normal=0;double full_ticks=0,subset_ticks=0;
 for(unsigned frame=0;frame<180;frame++){
  float speed=frame>=30 && frame<120?12:0,accel[]={frame==120?-35:0,0,0};assert(uma_motion_step_timed(&state,1.f/60,speed,0,a.idle_seconds,a.run_seconds));assert(uma_secondary_step(c,s,&a,&state,1.f/60,speed,accel));assert(uma_motion_sample_secondary(&a,state.idle_phase,state.run_phase,state.run_blend,full,a.vertices*36,s->rotation));memcpy(part,full,a.vertices*36);memset(subset,255,a.vertices*36);
  for(unsigned step=0;step<2;step++){
   int optimized=(step+(frame&1))&1;clock_t begin=clock();
   if(optimized){assert(uma_cloth_project_subset(&a,&state,part,subset,weights,edges,count,lengths,selected,needed));subset_ticks+=clock()-begin;}
   else{assert(uma_cloth_project(&a,&state,full,base,weights,edges,count,lengths));full_ticks+=clock()-begin;}
  }
  for(unsigned v=0;v<a.vertices;v++)for(int k=0;k<3;k++){
   assert(isfinite(part[v].position[k]) && isfinite(part[v].normal[k]));largest_position=fmaxf(largest_position,fabsf(full[v].position[k]-part[v].position[k]));largest_normal=fmaxf(largest_normal,fabsf(full[v].normal[k]-part[v].normal[k]));
  }
 }
 printf("paired_same_frame full_surface_ms=%.4f subset_surface_ms=%.4f\n",full_ticks*1000/CLOCKS_PER_SEC/180,subset_ticks*1000/CLOCKS_PER_SEC/180);
 printf("frames180 reference_vertices=%u/%u maximum_position_delta=%.8f maximum_normal_delta=%.8f; poisoned unused baseline values never consumed\n",needed,a.vertices,largest_position,largest_normal);fflush(stdout);/* Omitting the uniform floor lift changes float rounding: allow <1 micron and <0.06 degree normal component error. */
 assert(largest_position<.000001f && largest_normal<.001f);
 free(lengths);free(subset);free(base);free(part);free(full);free(selected);free(edges);free(weights);free(s);free(c);uma_motion_free(&a);return 0;
}
