#include <assert.h>
#include "uma_secondary.h"
#include "uma_cloth_surface.h"
static void snapshot(const char *folder,const char *name,const UmaMotion *a,const UmaVertex *pose){
 char path[4096];int n=snprintf(path,sizeof(path),"%s/%s.umap",folder,name);assert(n>0 && (size_t)n<sizeof(path));FILE *f=fopen(path,"wb");assert(f);uint32_t h[]={0,1,a->vertices};memcpy(h,"UMAP",4);assert(fwrite(h,4,3,f)==3);
 for(unsigned v=0;v<a->vertices;v++)for(int k=0;k<3;k++)assert(isfinite(pose[v].position[k]) && isfinite(pose[v].normal[k]));
 assert(fwrite(pose,36,a->vertices,f)==a->vertices && !fclose(f));
}
int main(int argc,char **argv){
 assert(argc==4);UmaMotion a={0};FILE *f=fopen(argv[1],"rb");assert(f && uma_motion_load(f,&a));fclose(f);UmaSecondary *c=calloc(1,sizeof(*c));UmaSecondaryState *s=calloc(1,sizeof(*s));assert(c && s);f=fopen(argv[2],"rb");assert(f && uma_secondary_load(f,&a,c));fclose(f);a.secondary_mask=c->mask;a.surface_mask=c->surface_mask;
 UmaVertex *pose=malloc(a.vertices*36),*base=malloc(a.vertices*36);float *weight=calloc(a.vertices,sizeof(float));uint16_t *edges=malloc(a.indices*4);assert(pose && base && weight && edges);
 for(unsigned v=0;v<a.vertices;v++)for(int j=0;j<4;j++)if(c->surface_mask[a.skin[v].bone[j]])weight[v]+=a.skin[v].weight[j];
 unsigned count=uma_cloth_edges(&a,weight,edges);float *lengths=malloc((count?count:1)*sizeof(float));assert(lengths);snapshot(argv[3],"rest",&a,a.rest);UmaMotionState state={0};unsigned written=1;
 for(unsigned frame=0;frame<180;frame++){
  float speed=frame>=30 && frame<120?12:0,accel[]={frame==120?-35:0,0,0};assert(uma_motion_step_timed(&state,1.f/60,speed,0,a.idle_seconds,a.run_seconds));assert(uma_secondary_step(c,s,&a,&state,1.f/60,speed,accel));
  if(frame%30 && frame!=179)continue;
  assert(uma_motion_sample_secondary(&a,state.idle_phase,state.run_phase,state.run_blend,pose,a.vertices*36,s->rotation));if(count)assert(uma_cloth_project(&a,&state,pose,base,weight,edges,count,lengths));char name[24];snprintf(name,sizeof(name),"frame-%03u",frame);snapshot(argv[3],name,&a,pose);written++;
 }
 printf("PASS %u finite runtime pose snapshots, same skin/spring/surface sampling path; no game integration\n",written);free(lengths);free(edges);free(weight);free(base);free(pose);free(s);free(c);uma_motion_free(&a);return 0;
}
