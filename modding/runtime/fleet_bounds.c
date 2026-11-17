#include "uma_motion.h"
#include <assert.h>
int main(int argc,char **argv){
 assert(argc==2);FILE *f=fopen(argv[1],"rb");assert(f);UmaMotion asset={0};assert(uma_motion_load(f,&asset));fclose(f);UmaVertex *vertices=malloc((size_t)asset.vertices*36);assert(vertices);float maximum=4.f;
 for(int blend=0;blend<=4;blend++)for(int frame=0;frame<96;frame++){
  assert(uma_motion_sample(&asset,frame/96.f,((frame*5)%96)/96.f,blend/4.f,vertices,(size_t)asset.vertices*36));
  for(uint32_t i=0;i<asset.vertices;i++){float radius=0;for(int k=0;k<3;k++)radius+=vertices[i].position[k]*vertices[i].position[k];assert(isfinite(radius));if(radius>maximum)maximum=radius;}
 }
 float radius=ceilf((sqrtf(maximum)+.25f)*16)/16;assert(radius<4);float bounds[]={-radius,-radius,-radius,radius,radius,radius};assert(fwrite(bounds,4,6,stdout)==6);fprintf(stderr,"480 sampled poses, 0.25m margin; rotation-invariant radius=%.4f\n",radius);free(vertices);uma_motion_free(&asset);return 0;
}
