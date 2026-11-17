#ifndef UMA_MOTION_H
#define UMA_MOTION_H
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

typedef struct {float position[3],normal[3];uint8_t bgra[4];float uv[2];} UmaVertex;
typedef struct {uint16_t bone[4];float weight[4];} UmaSkin;
typedef struct {int16_t parent;uint16_t reserved;float rest[3];} UmaJoint;
typedef struct {
 uint32_t vertices,indices,bones,idle_frames,run_frames;
 float idle_seconds,run_seconds;
 size_t memory_bytes;unsigned char *memory;
 UmaVertex *rest;UmaSkin *skin;UmaJoint *joint;uint16_t *index;float *idle,*run;
} UmaMotion;
typedef struct {float idle_phase,run_phase,run_blend;} UmaMotionState;
_Static_assert(sizeof(UmaVertex)==36,"Game-compatible vertex stride");
_Static_assert(sizeof(UmaSkin)==24,"Packed skin stride");
_Static_assert(sizeof(UmaJoint)==16,"Joint metadata stride");
static uint32_t uma_le32(const unsigned char *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static void uma_motion_free(UmaMotion *asset){if(asset){free(asset->memory);memset(asset,0,sizeof(*asset));}}
/* Caller zero-initializes asset; a failed load leaves it unchanged. */
static int uma_motion_load(FILE *file,UmaMotion *asset){
 unsigned char h[32];uint16_t endian=1;UmaMotion a={0};
 if(!file || !asset || asset->memory || *(unsigned char*)&endian!=1 || fread(h,1,32,file)!=32 || memcmp(h,"UMAB",4) || (uma_le32(h+4)!=2 && uma_le32(h+4)!=3) || uma_le32(h+28))return 0;
 a.idle_seconds=2.f;a.run_seconds=.6f;
 if(uma_le32(h+4)==3){float durations[2];if(fread(durations,4,2,file)!=2)return 0;a.idle_seconds=durations[0];a.run_seconds=durations[1];}
 if(!isfinite(a.idle_seconds) || !isfinite(a.run_seconds) || a.idle_seconds<.05f || a.idle_seconds>60 || a.run_seconds<.05f || a.run_seconds>60)return 0;
 a.vertices=uma_le32(h+8);a.indices=uma_le32(h+12);a.bones=uma_le32(h+16);a.idle_frames=uma_le32(h+20);a.run_frames=uma_le32(h+24);
 if(!a.vertices || a.vertices>65535 || !a.indices || a.indices>786432 || a.indices%3 || !a.bones || a.bones>512 || a.idle_frames<2 || a.idle_frames>128 || a.run_frames<2 || a.run_frames>128)return 0;
 size_t index_bytes=((size_t)a.indices*2+3)&~(size_t)3;
 size_t matrix_floats=(size_t)(a.idle_frames+a.run_frames)*a.bones*7;
 a.memory_bytes=(size_t)a.vertices*(36+24)+(size_t)a.bones*16+index_bytes+matrix_floats*4;
 a.memory=(unsigned char*)malloc(a.memory_bytes);if(!a.memory)return 0;
 if(fread(a.memory,1,a.memory_bytes,file)!=a.memory_bytes || fgetc(file)!=EOF)goto invalid;
 a.rest=(UmaVertex*)a.memory;a.skin=(UmaSkin*)(a.memory+(size_t)a.vertices*36);
 a.joint=(UmaJoint*)((unsigned char*)a.skin+(size_t)a.vertices*24);
 a.index=(uint16_t*)((unsigned char*)a.joint+(size_t)a.bones*16);
 a.idle=(float*)((unsigned char*)a.index+index_bytes);a.run=a.idle+(size_t)a.idle_frames*a.bones*7;
 for(size_t i=(size_t)a.indices*2;i<index_bytes;i++)if(((unsigned char*)a.index)[i])goto invalid;
 for(uint32_t i=0;i<a.vertices;i++){
  float normal=0,total=0;
  for(int j=0;j<3;j++){
   if(!isfinite(a.rest[i].position[j]) || fabsf(a.rest[i].position[j])>10000 || !isfinite(a.rest[i].normal[j]))goto invalid;
   normal+=a.rest[i].normal[j]*a.rest[i].normal[j];
  }
  if(!isfinite(normal) || normal<1e-12f)goto invalid;
  for(int j=0;j<2;j++)if(!isfinite(a.rest[i].uv[j]) || fabsf(a.rest[i].uv[j])>10000)goto invalid;
  for(int j=0;j<4;j++){
   float w=a.skin[i].weight[j];if(a.skin[i].bone[j]>=a.bones || !isfinite(w) || w<0 || w>1)goto invalid;total+=w;
  }
  if(fabsf(total-1)>1e-4f)goto invalid;
 }
 for(uint32_t i=0;i<a.bones;i++){
  if(a.joint[i].reserved || a.joint[i].parent< -1 || a.joint[i].parent>=(int)i)goto invalid;
  for(int j=0;j<3;j++)if(!isfinite(a.joint[i].rest[j]) || fabsf(a.joint[i].rest[j])>10)goto invalid;
 }
 for(uint32_t i=0;i<a.indices;i++)if(a.index[i]>=a.vertices)goto invalid;
 for(size_t i=0;i<matrix_floats;i++)if(!isfinite(a.idle[i]) || fabsf(a.idle[i])>10)goto invalid;
 for(size_t i=0;i<matrix_floats;i+=7){
  float length=0;for(int k=0;k<4;k++)length+=a.idle[i+k]*a.idle[i+k];
  if(fabsf(length-1)>1e-3f)goto invalid;
 }
 *asset=a;return 1;
invalid:
 free(a.memory);return 0;
}
static float uma_fraction(float phase){return phase-floorf(phase);}
static void uma_frame(float phase,uint32_t count,uint32_t *a,uint32_t *b,float *t){float f=uma_fraction(phase)*count;*a=(uint32_t)f;*b=(*a+1)%count;*t=f-*a;}
static void uma_quaternion_mix(const float *a,const float *b,float amount,float *out){
 float dot=0;for(int k=0;k<4;k++)dot+=a[k]*b[k];float sign=dot<0?-1:1,length=0;
 for(int k=0;k<4;k++){out[k]=a[k]+(sign*b[k]-a[k])*amount;length+=out[k]*out[k];}
 length=sqrtf(length);for(int k=0;k<4;k++)out[k]/=length;
}
static void uma_local_pose(const float *clip,size_t stride,uint32_t a,uint32_t b,float t,uint32_t bone,float *out){
 const float *first=clip+(size_t)a*stride+(size_t)bone*7,*second=clip+(size_t)b*stride+(size_t)bone*7;
 uma_quaternion_mix(first,second,t,out);
 for(int k=4;k<7;k++)out[k]=first[k]+(second[k]-first[k])*t;
}
static int uma_motion_sample(const UmaMotion *asset,float idle_phase,float run_phase,float blend,UmaVertex *output,size_t output_bytes){
 if(!asset || !asset->memory || !output || !isfinite(idle_phase) || !isfinite(run_phase) || !isfinite(blend) || blend<0 || blend>1)return 0;
 size_t bytes=(size_t)asset->vertices*36;
 uintptr_t dst=(uintptr_t)output,src=(uintptr_t)asset->memory;
 if(output_bytes<bytes || dst>UINTPTR_MAX-bytes || (dst<src+asset->memory_bytes && dst+bytes>src))return 0;
 uint32_t ia,ib,ra,rb;float it,rt;
 uma_frame(idle_phase,asset->idle_frames,&ia,&ib,&it);uma_frame(run_phase,asset->run_frames,&ra,&rb,&rt);
 float mixed[512*12],positions[512*3];size_t stride=(size_t)asset->bones*7;
 for(uint32_t bone=0;bone<asset->bones;bone++){
  float idle[7],run[7],pose[7];
  uma_local_pose(asset->idle,stride,ia,ib,it,bone,idle);uma_local_pose(asset->run,stride,ra,rb,rt,bone,run);
  uma_quaternion_mix(idle,run,blend,pose);
  for(int k=4;k<7;k++)pose[k]=idle[k]+(run[k]-idle[k])*blend;
  float x=pose[0],y=pose[1],z=pose[2],w=pose[3];
  const float local[]={1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w),2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w),2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)};
  int parent=asset->joint[bone].parent;float *world=mixed+(size_t)bone*12;
  for(int axis=0;axis<3;axis++){
   if(parent<0){for(int k=0;k<3;k++)world[axis*4+k]=local[axis*3+k];positions[bone*3+axis]=asset->joint[bone].rest[axis]+pose[4+axis];}
   else{
    const float *p=mixed+(size_t)parent*12;float value=positions[parent*3+axis];
    for(int k=0;k<3;k++)value+=p[axis*4+k]*(asset->joint[bone].rest[k]-asset->joint[parent].rest[k]+pose[4+k]);
    positions[bone*3+axis]=value;
    for(int k=0;k<3;k++){float r=0;for(int j=0;j<3;j++)r+=p[axis*4+j]*local[j*3+k];world[axis*4+k]=r;}
   }
   float offset=positions[bone*3+axis];for(int k=0;k<3;k++)offset-=world[axis*4+k]*asset->joint[bone].rest[k];world[axis*4+3]=offset;
  }
 }
 memcpy(output,asset->rest,bytes);
 for(uint32_t i=0;i<asset->vertices;i++){
  float p[3]={0},n[3]={0};
  for(int j=0;j<4;j++){
   float weight=asset->skin[i].weight[j];if(weight==0)continue;
   const float *matrix=mixed+(size_t)asset->skin[i].bone[j]*12;
   for(int axis=0;axis<3;axis++){
    const float *row=matrix+axis*4;float pp=row[3],nn=0;
    for(int k=0;k<3;k++){pp+=row[k]*asset->rest[i].position[k];nn+=row[k]*asset->rest[i].normal[k];}
    p[axis]+=pp*weight;n[axis]+=nn*weight;
   }
  }
  float length=sqrtf(n[0]*n[0]+n[1]*n[1]+n[2]*n[2]);
  if(length<1e-8f){memcpy(n,asset->rest[i].normal,12);length=sqrtf(n[0]*n[0]+n[1]*n[1]+n[2]*n[2]);}
  for(int axis=0;axis<3;axis++){output[i].position[axis]=p[axis];output[i].normal[axis]=n[axis]/length;}
 }
 // Keep the whole model above its local support plane during clip transitions.
 float lowest=output[0].position[2];for(uint32_t i=1;i<asset->vertices;i++)if(output[i].position[2]<lowest)lowest=output[i].position[2];
 if(lowest<-.0001f){float rise=-.0001f-lowest;for(uint32_t i=0;i<asset->vertices;i++)output[i].position[2]+=rise;}
 return 1;
}
/* Speed/paused are explicit inputs; this code does not inspect game memory. */
static inline int uma_motion_step_timed(UmaMotionState *state,float seconds,float speed_mps,int paused,float idle_seconds,float run_seconds){
 if(!state || !isfinite(seconds) || seconds<0 || seconds>.25f || !isfinite(speed_mps) || !isfinite(state->idle_phase) || !isfinite(state->run_phase) || !isfinite(state->run_blend) || state->run_blend<0 || state->run_blend>1 || !isfinite(idle_seconds) || idle_seconds<.05f || idle_seconds>60 || !isfinite(run_seconds) || run_seconds<.05f || run_seconds>60)return 0;
 if(paused)return 1;
 float speed=fminf(fabsf(speed_mps),100),target=fminf(fmaxf((speed-.2f)/2.8f,0),1);
 state->run_blend+=(target-state->run_blend)*(1-expf(-seconds/.15f));
 state->idle_phase=uma_fraction(state->idle_phase+seconds/idle_seconds);
 /* Original race loop lasts 0.6 seconds; avoid the earlier rapid small-step cadence. */
 float cadence=1.f/run_seconds;
 state->run_phase=uma_fraction(state->run_phase+(speed_mps<0?-1:1)*seconds*cadence);
 return 1;
}
static inline int uma_motion_step(UmaMotionState *state,float seconds,float speed_mps,int paused){return uma_motion_step_timed(state,seconds,speed_mps,paused,2.f,.6f);}
#endif
