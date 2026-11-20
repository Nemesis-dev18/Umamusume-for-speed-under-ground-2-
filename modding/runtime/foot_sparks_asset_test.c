#include <assert.h>
#include "uma_secondary.h"
#include "uma_foot_sparks.h"
int main(int argc,char **argv){
 assert(argc==3);UmaMotion a={0};FILE *f=fopen(argv[1],"rb");assert(f && uma_motion_load(f,&a));fclose(f);UmaSecondary *cloth=calloc(1,sizeof(*cloth));f=fopen(argv[2],"rb");assert(f && uma_secondary_load(f,&a,cloth));fclose(f);a.secondary_mask=cloth->mask;
 UmaVertex *pose=malloc(a.vertices*36);assert(pose);unsigned frames=0;
 for(int i=0;i<96;i++){
  assert(uma_motion_sample(&a,0,i/96.f,1,pose,a.vertices*36));float feet[2][3];unsigned count[2];uma_spark_contacts(&a,pose,feet,count);frames+=count[0] || count[1];UmaVertex sparks[24];unsigned n=uma_spark_mesh(i/96.f,feet,count,NULL,sparks);assert(n<=24 && n%3==0);for(unsigned v=0;v<n;v++)for(int k=0;k<3;k++)assert(isfinite(sparks[v].position[k]));
 }
 assert(frames>0 && frames<96);printf("PASS contact frames=%u/96 %s\n",frames,argv[1]);free(pose);free(cloth);uma_motion_free(&a);return 0;
}
