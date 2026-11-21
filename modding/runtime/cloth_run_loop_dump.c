#include <assert.h>
#include "uma_motion.h"
int main(int argc,char **argv){
 assert(argc==3);UmaMotion a={0};FILE *f=fopen(argv[1],"rb");assert(f && uma_motion_load(f,&a));assert(!fclose(f));UmaVertex *pose=malloc(a.vertices*36);assert(pose);
 for(unsigned frame=0;frame<a.run_frames;frame++){
  assert(uma_motion_sample(&a,0,(float)frame/a.run_frames,1,pose,a.vertices*36));
  char path[4096];int n=snprintf(path,sizeof(path),"%s/run-%03u.umap",argv[2],frame);assert(n>0 && (size_t)n<sizeof(path));f=fopen(path,"wb");assert(f);uint32_t header[]={0,1,a.vertices};memcpy(header,"UMAP",4);assert(fwrite(header,4,3,f)==3 && fwrite(pose,36,a.vertices,f)==a.vertices && !fclose(f));
 }
 printf("PASS %u full run poses, cycle %.9g seconds, no secondary spring deformation\n",a.run_frames,a.run_seconds);free(pose);uma_motion_free(&a);return 0;
}
