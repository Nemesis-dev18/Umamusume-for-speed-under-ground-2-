#include <assert.h>
#include "uma_secondary.h"
int main(int argc,char **argv){
 assert(argc==4);UmaMotion a={0};FILE *f=fopen(argv[1],"rb");assert(f && uma_motion_load(f,&a));fclose(f);UmaSecondary *c=calloc(1,sizeof(*c)),*baseline=calloc(1,sizeof(*baseline));UmaSecondaryState *s=calloc(1,sizeof(*s)),*reference=calloc(1,sizeof(*reference));assert(c && baseline && s && reference);
 f=fopen(argv[2],"rb");assert(f && uma_secondary_load(f,&a,c));fclose(f);*baseline=*c;UmaGarmentLinks links={0};f=fopen(argv[3],"rb");assert(f && uma_garment_links_load(f,&a,&links));rewind(f);unsigned fold=0;for(unsigned i=0;i<links.count;i++)fold+=!!links.pair[i].flags;int attached=uma_secondary_links_load(f,&a,c);fclose(f);
 if(fold){assert(!attached && !c->links.count);printf("PASS source links=%u fold=%u preserved; unsupported fold mode rejected without changing secondary data\n",links.count,fold);free(reference);free(s);free(baseline);free(c);uma_motion_free(&a);return 0;}
 assert(attached);a.secondary_mask=c->mask;a.surface_mask=c->surface_mask;UmaVertex *vertices=malloc(a.vertices*36);assert(vertices);UmaMotionState pose={0};
 for(unsigned frame=0;frame<360;frame++){
  float speed=frame>=30 && frame<300?12:0,accel[]={frame==300?-35:0,0,0};assert(uma_motion_step_timed(&pose,1.f/60,speed,0,a.idle_seconds,a.run_seconds));assert(uma_secondary_step(c,s,&a,&pose,1.f/60,speed,accel));
  if(!links.count){assert(uma_secondary_step(baseline,reference,&a,&pose,1.f/60,speed,accel));assert(!memcmp(s,reference,sizeof(*s)));}
  for(unsigned b=0;b<a.bones;b++){float norm=0;for(int k=0;k<4;k++){float value=s->rotation[b*4+k];assert(isfinite(value));norm+=value*value;}assert(fabsf(norm-1)<.001f);}
  if(frame%30==0){assert(uma_motion_sample_secondary(&a,pose.idle_phase,pose.run_phase,pose.run_blend,vertices,a.vertices*36,s->rotation));for(unsigned v=0;v<a.vertices;v++)for(int k=0;k<3;k++)assert(isfinite(vertices[v].position[k]) && isfinite(vertices[v].normal[k]));}
 }
 printf("PASS links=%u frames360 finite quaternion/skin; %s; no gameplay or appearance acceptance\n",links.count,links.count?"native endpoint maps valid":"zero-link state bitwise matches baseline");free(vertices);free(reference);free(s);free(baseline);free(c);uma_motion_free(&a);return 0;
}
