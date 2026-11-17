#include "uma_motion.h"
#include <assert.h>
int main(int argc,char **argv){
 assert(argc==2);FILE *f=fopen(argv[1],"rb");assert(f);UmaMotion asset={0};assert(uma_motion_load(f,&asset));fclose(f);
 UmaVertex *vertices=malloc((size_t)asset.vertices*sizeof(*vertices));assert(vertices);
 for(int clip=0;clip<2;clip++)for(int frame=0;frame<4;frame++){
  assert(uma_motion_sample(&asset,frame*.25f,frame*.25f,(float)clip,vertices,(size_t)asset.vertices*sizeof(*vertices)));
  float low[3],high[3];memcpy(low,vertices[0].position,sizeof(low));memcpy(high,low,sizeof(high));
  for(uint32_t i=1;i<asset.vertices;i++)for(int k=0;k<3;k++){low[k]=fminf(low[k],vertices[i].position[k]);high[k]=fmaxf(high[k],vertices[i].position[k]);}
  printf("%s %.2f min %.6f %.6f %.6f max %.6f %.6f %.6f\n",clip?"run":"idle",frame*.25f,low[0],low[1],low[2],high[0],high[1],high[2]);
 }
 free(vertices);uma_motion_free(&asset);return 0;
}
