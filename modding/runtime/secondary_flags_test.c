#include <assert.h>
#include "uma_secondary.h"
#include "uma_cloth_surface.h"
int main(void){
 (void)uma_motion_load;(void)uma_motion_free;(void)uma_secondary_step;
 UmaJoint joint={.parent=-1};UmaMotion asset={.bones=1,.joint=&joint};UmaSecondary *out=calloc(1,sizeof(*out));assert(out);
 const unsigned flags[]={256,257,768,1024};
 for(unsigned i=0;i<4;i++){
  uint32_t header[]={0,1,1,1,0,0};memcpy(header,"UMAS",4);UmaSpring node={.flags=flags[i],.tip={0,0,-.1f},.hz=2,.damping=1,.gravity=1,.cone=.2f,.apply=.7f};
  FILE *file=tmpfile();assert(file);assert(fwrite(header,4,6,file)==6 && fwrite(&node,48,1,file)==1);rewind(file);memset(out,0,sizeof(*out));int valid=uma_secondary_load(file,&asset,out);fclose(file);
  if(i==3){assert(!valid && !out->nodes);continue;}
  assert(valid && out->mask[0]);assert(out->surface_mask[0]==(i==1?1:i==2?2:0));assert(out->groups==(i==1?1u:0u));
 }
 uint16_t index[]={0,1,2,2,1,0},edges[12];float weight[]={1,1,1};UmaMotion triangle={.indices=6,.index=index};
 assert(uma_cloth_edges(&triangle,weight,edges)==3);const uint16_t expected[]={0,1,0,2,1,2};assert(!memcmp(edges,expected,sizeof(expected)));memset(weight,0,sizeof(weight));assert(!uma_cloth_edges(&triangle,weight,edges));
 free(out);puts("PASS legacy springs unchanged, cape groups unchanged, dense skirt surface independent of cape averaging, unknown flags rejected");return 0;
}
