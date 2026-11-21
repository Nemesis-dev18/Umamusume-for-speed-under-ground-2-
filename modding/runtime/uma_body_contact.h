#ifndef UMA_BODY_CONTACT_H
#define UMA_BODY_CONTACT_H
#include "uma_motion.h"
typedef struct {float a[3],b[3],radius;} UmaBodyCapsule;
static inline float uma_body_distance(const float *point,const UmaBodyCapsule *c,float *delta){
 float line[3],t=0,length=0;
 for(int k=0;k<3;k++){line[k]=c->b[k]-c->a[k];length+=line[k]*line[k];t+=(point[k]-c->a[k])*line[k];}
 t=length>1e-10f?fminf(1,fmaxf(0,t/length)):0;float squared=0;
 for(int k=0;k<3;k++){delta[k]=point[k]-c->a[k]-line[k]*t;squared+=delta[k]*delta[k];}
 return sqrtf(squared);
}
/* Only garment vertices move; skin and remote vertices remain unchanged. */
static inline int uma_body_separate(UmaVertex *pose,unsigned vertices,const float *weight,const UmaBodyCapsule *caps,unsigned count){
 if(!pose || !weight || !caps || !vertices || vertices>65535 || !count || count>16)return 0;
 for(unsigned c=0;c<count;c++){
  if(!isfinite(caps[c].radius) || caps[c].radius<=0 || caps[c].radius>1)return 0;
  for(int k=0;k<3;k++)if(!isfinite(caps[c].a[k]) || !isfinite(caps[c].b[k]))return 0;
 }
 for(unsigned v=0;v<vertices;v++){
  if(!isfinite(weight[v]) || weight[v]<0 || weight[v]>1.0001f)return 0;
  for(int k=0;k<3;k++)if(!isfinite(pose[v].position[k]) || !isfinite(pose[v].normal[k]))return 0;
 }
 for(unsigned v=0;v<vertices;v++)if(weight[v]>=.5f)for(unsigned pass=0;pass<4;pass++){
  int moved=0;for(unsigned c=0;c<count;c++){
  float delta[3],distance=uma_body_distance(pose[v].position,caps+c,delta),radius=caps[c].radius+.003f;
  if(distance>=radius)continue;
  if(distance<1e-7f){float n=0;for(int k=0;k<3;k++)n+=pose[v].normal[k]*pose[v].normal[k];if(n<1e-10f){delta[0]=1;delta[1]=delta[2]=0;}else for(int k=0;k<3;k++)delta[k]=pose[v].normal[k]/sqrtf(n);distance=0;}
  else for(int k=0;k<3;k++)delta[k]/=distance;
  for(int k=0;k<3;k++)pose[v].position[k]+=delta[k]*(radius-distance);
  moved=1;
  }if(!moved)break;
 }
 return 1;
}
typedef struct {uint16_t a,b;float radius;} UmaBodyBones;
typedef struct UmaBodyContacts {uint32_t bones,vertices,count;uint8_t mask[512];UmaBodyBones capsule[16];} UmaBodyContacts;
_Static_assert(sizeof(UmaBodyBones)==8,"Body contact record layout");
static inline int uma_body_load(FILE *file,const UmaMotion *asset,UmaBodyContacts *output){
 uint32_t h[5];UmaBodyContacts c={0};
 if(!file || !asset || !output || fread(h,4,5,file)!=5 || memcmp(h,"UMAC",4) || h[1]!=1 || !h[2] || h[2]>512 || !h[3] || h[3]>65535 || h[2]!=asset->bones || h[3]!=asset->vertices || !h[4] || h[4]>16)return 0;
 c.bones=h[2];c.vertices=h[3];c.count=h[4];if(fread(c.mask,1,c.bones,file)!=c.bones)return 0;
 for(unsigned i=0;i<c.bones;i++)if(c.mask[i]>1)return 0;
 for(unsigned i=0;i<((-c.bones)&3);i++)if(fgetc(file)!=0)return 0;
 if(fread(c.capsule,8,c.count,file)!=c.count || fgetc(file)!=EOF)return 0;
 for(unsigned i=0;i<c.count;i++)if(c.capsule[i].a>=c.bones || c.capsule[i].b>=c.bones || !isfinite(c.capsule[i].radius) || c.capsule[i].radius<.005f || c.capsule[i].radius>.3f)return 0;
 *output=c;return 1;
}
#endif
