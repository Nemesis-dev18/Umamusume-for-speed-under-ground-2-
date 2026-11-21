#include <assert.h>
#include "uma_motion.h"
int main(int argc,char **argv){
 assert(argc==3);UmaMotion a={0};FILE *f=fopen(argv[1],"rb");assert(f && uma_motion_load(f,&a));assert(!fclose(f));UmaVertex *pose=malloc(a.vertices*36);assert(pose);
 for(unsigned frame=0;frame<a.run_frames;frame++){
  assert(uma_motion_sample(&a,0,(float)frame/a.run_frames,1,pose,a.vertices*36));
  float matrices[512*12],joints[512*3],shift[3]={0};assert(uma_motion_matrices(&a,0,(float)frame/a.run_frames,1,NULL,matrices));
  for(int axis=0;axis<3;axis++){float raw=0;for(unsigned j=0;j<4;j++){const float *m=matrices+a.skin[0].bone[j]*12;raw+=a.skin[0].weight[j]*(m[axis*4+3]+m[axis*4]*a.rest[0].position[0]+m[axis*4+1]*a.rest[0].position[1]+m[axis*4+2]*a.rest[0].position[2]);}shift[axis]=pose[0].position[axis]-raw;}
  for(unsigned b=0;b<a.bones;b++)for(int axis=0;axis<3;axis++){const float *m=matrices+b*12;joints[b*3+axis]=shift[axis]+m[axis*4+3]+m[axis*4]*a.joint[b].rest[0]+m[axis*4+1]*a.joint[b].rest[1]+m[axis*4+2]*a.joint[b].rest[2];assert(isfinite(joints[b*3+axis]));}
  char joint_path[4096];int jn=snprintf(joint_path,sizeof(joint_path),"%s/run-%03u.umaj",argv[2],frame);assert(jn>0 && (size_t)jn<sizeof(joint_path));f=fopen(joint_path,"wb");assert(f);uint32_t jheader[]={0,1,a.bones};memcpy(jheader,"UMAJ",4);assert(fwrite(jheader,4,3,f)==3 && fwrite(joints,12,a.bones,f)==a.bones && !fclose(f));
  for(unsigned b=0;b<a.bones;b++)for(int axis=0;axis<3;axis++)matrices[b*12+axis*4+3]+=shift[axis];
  char matrix_path[4096];int mn=snprintf(matrix_path,sizeof(matrix_path),"%s/run-%03u.umax",argv[2],frame);assert(mn>0 && (size_t)mn<sizeof(matrix_path));f=fopen(matrix_path,"wb");assert(f);uint32_t mheader[]={0,1,a.bones};memcpy(mheader,"UMAX",4);assert(fwrite(mheader,4,3,f)==3 && fwrite(matrices,48,a.bones,f)==a.bones && !fclose(f));
  char path[4096];int n=snprintf(path,sizeof(path),"%s/run-%03u.umap",argv[2],frame);assert(n>0 && (size_t)n<sizeof(path));f=fopen(path,"wb");assert(f);uint32_t header[]={0,1,a.vertices};memcpy(header,"UMAP",4);assert(fwrite(header,4,3,f)==3 && fwrite(pose,36,a.vertices,f)==a.vertices && !fclose(f));
 }
 printf("PASS %u full run poses, cycle %.9g seconds, no secondary spring deformation\n",a.run_frames,a.run_seconds);free(pose);uma_motion_free(&a);return 0;
}
