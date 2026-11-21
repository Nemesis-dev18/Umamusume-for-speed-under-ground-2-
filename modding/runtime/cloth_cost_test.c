#include <assert.h>
#include <time.h>
#include "uma_secondary.h"
#include "uma_cloth_surface.h"
int main(int argc,char **argv){
 int subset=argc==4 && !strcmp(argv[3],"subset");assert(argc==3 || subset);UmaMotion a={0};FILE *f=fopen(argv[1],"rb");assert(f && uma_motion_load(f,&a));fclose(f);UmaSecondary *c=calloc(1,sizeof(*c));UmaSecondaryState *s=calloc(1,sizeof(*s));assert(c && s);f=fopen(argv[2],"rb");assert(f && uma_secondary_load(f,&a,c));fclose(f);a.secondary_mask=c->mask;a.surface_mask=c->surface_mask;
 float *weights=calloc(a.vertices,sizeof(float));uint16_t *edges=malloc((size_t)a.indices*4);UmaVertex *pose=malloc((size_t)a.vertices*36),*base=malloc((size_t)a.vertices*36);assert(weights && edges && pose && base);
 for(unsigned v=0;v<a.vertices;v++)for(unsigned j=0;j<4;j++)if(c->surface_mask[a.skin[v].bone[j]])weights[v]+=a.skin[v].weight[j];
 unsigned count=uma_cloth_edges(&a,weights,edges);float *lengths=malloc((size_t)(count?count:1)*sizeof(float));assert(lengths);uint16_t *selected=malloc(a.vertices*2);assert(selected);unsigned selected_count=uma_cloth_reference_vertices(&a,weights,selected);assert(selected_count!=UINT32_MAX);UmaMotionState state={0};float accel[3]={0};double sample_ticks=0,projection_ticks=0,physics_ticks=0;
 for(unsigned frame=0;frame<180;frame++){
  assert(uma_motion_step_timed(&state,1.f/60,frame<120?12:0,0,a.idle_seconds,a.run_seconds));clock_t start=clock();assert(uma_secondary_step(c,s,&a,&state,1.f/60,frame<120?12:0,accel));physics_ticks+=clock()-start;
  start=clock();assert(uma_motion_sample_secondary(&a,state.idle_phase,state.run_phase,state.run_blend,pose,a.vertices*36,s->rotation));sample_ticks+=clock()-start;
  if(count){start=clock();assert(subset?uma_cloth_project_subset(&a,&state,pose,base,weights,edges,count,lengths,selected,selected_count):uma_cloth_project(&a,&state,pose,base,weights,edges,count,lengths));projection_ticks+=clock()-start;}
 }
 double factor=1000./CLOCKS_PER_SEC/180;printf("frames=180 active_edges=%u physics_ms=%.3f skin_ms=%.3f surface_ms=%.3f total_ms=%.3f\n",count,physics_ticks*factor,sample_ticks*factor,projection_ticks*factor,(physics_ticks+sample_ticks+projection_ticks)*factor);
 free(selected);free(lengths);free(weights);free(edges);free(pose);free(base);free(c);free(s);uma_motion_free(&a);return 0;
}
