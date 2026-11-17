#ifndef UMA_SECONDARY_H
#define UMA_SECONDARY_H
#include "uma_motion.h"
typedef struct {uint16_t bone,flags,first,count;float tip[3],hz,damping,gravity,radius,cone,wind,apply;} UmaSpring;
typedef struct {uint16_t bone0,bone1,kind,reserved;float a[3],b[3],radius;} UmaClothCollider;
typedef struct {uint32_t bones,nodes,colliders,refs;UmaSpring node[512];UmaClothCollider collider[128];uint16_t ref[4096];uint8_t mask[512];} UmaSecondary;
typedef struct {float tip[512][3],previous[512][3],rotation[512*4],remainder;uint32_t revision;int initialized;} UmaSecondaryState;
_Static_assert(sizeof(UmaSpring)==48,"UMAS spring layout");
_Static_assert(sizeof(UmaClothCollider)==36,"UMAS collider layout");
static int uma_secondary_load(FILE *file,const UmaMotion *asset,UmaSecondary *out){
 uint32_t h[6];UmaSecondary *c=calloc(1,sizeof(*c));if(!c)return 0;int valid=0;
 if(!file || !asset || !out || fread(h,4,6,file)!=6 || memcmp(h,"UMAS",4) || h[1]!=1 || h[2]!=asset->bones || !h[3] || h[3]>512 || h[4]>128 || h[5]>4096)goto done;
 c->bones=h[2];c->nodes=h[3];c->colliders=h[4];c->refs=h[5];
 if(fread(c->node,48,c->nodes,file)!=c->nodes || fread(c->collider,36,c->colliders,file)!=c->colliders || fread(c->ref,2,c->refs,file)!=c->refs)goto done;
 if((c->refs&1) && (fgetc(file)!=0 || fgetc(file)!=0))goto done;
 if(fgetc(file)!=EOF)goto done;
 for(unsigned i=0;i<c->nodes;i++){
  UmaSpring *n=c->node+i;float length=0;
  if(n->bone>=c->bones || n->flags || (i && n->bone<=c->node[i-1].bone) || (unsigned)n->first+n->count>c->refs)goto done;
  float values[10];memcpy(values,n->tip,sizeof(values));for(int k=0;k<10;k++)if(!isfinite(values[k]))goto done;
  for(int k=0;k<3;k++)length+=n->tip[k]*n->tip[k];
  if(length<1e-6f || length>.36f || n->hz<.1f || n->hz>10 || n->damping<.1f || n->damping>2 || n->gravity<0 || n->gravity>30 || n->radius<0 || n->radius>.2f || n->cone<.01f || n->cone>1.4f || n->wind<0 || n->wind>.1f || n->apply<0 || n->apply>1)goto done;
  c->mask[n->bone]=1;
 }
 for(unsigned i=0;i<c->bones;i++)if(asset->joint[i].parent>=0 && c->mask[asset->joint[i].parent])c->mask[i]=1;
 for(unsigned i=0;i<c->colliders;i++){
  UmaClothCollider *b=c->collider+i;if(b->bone0>=c->bones || b->bone1>=c->bones || b->kind>3 || b->reserved)goto done;
  float values[7];memcpy(values,b->a,sizeof(values));for(int k=0;k<7;k++)if(!isfinite(values[k]))goto done;
  if(b->radius<=0 || b->radius>2)goto done;
 }
 for(unsigned i=0;i<c->refs;i++)if(c->ref[i]>=c->colliders)goto done;
 *out=*c;valid=1;
 done:free(c);return valid;
}
static float uma_secondary_length(const float *v){return sqrtf(v[0]*v[0]+v[1]*v[1]+v[2]*v[2]);}
static void uma_secondary_point(const float *m,const float *p,float *out){for(int k=0;k<3;k++)out[k]=m[k*4+3]+m[k*4]*p[0]+m[k*4+1]*p[1]+m[k*4+2]*p[2];}
static void uma_secondary_reset(UmaSecondaryState *s,unsigned bones){memset(s,0,sizeof(*s));for(unsigned i=0;i<bones;i++)s->rotation[i*4+3]=1;}
static void uma_secondary_limit(float *p,const float *origin,const float *target,float length,float cone){
 float d[3],t[3],dot=0;for(int k=0;k<3;k++){d[k]=p[k]-origin[k];t[k]=(target[k]-origin[k])/length;}
 float l=uma_secondary_length(d);if(l<1e-6f){memcpy(p,target,12);return;}
 for(int k=0;k<3;k++){d[k]/=l;dot+=d[k]*t[k];}
 float minimum=cosf(cone);
 if(dot<minimum){float side[3];for(int k=0;k<3;k++)side[k]=d[k]-dot*t[k];l=uma_secondary_length(side);if(l<1e-6f){memcpy(p,target,12);return;}for(int k=0;k<3;k++)d[k]=minimum*t[k]+sinf(cone)*side[k]/l;}
 for(int k=0;k<3;k++)p[k]=origin[k]+d[k]*length;
}
static int uma_secondary_step(const UmaSecondary *c,UmaSecondaryState *s,const UmaMotion *asset,const UmaMotionState *pose,float dt,float speed,const float *acceleration){
 if(!c || !s || !asset || !pose || c->bones!=asset->bones || !isfinite(dt) || dt<0 || !isfinite(speed))return 0;
 for(int k=0;k<3;k++)if(!isfinite(acceleration[k]))return 0;
 if(!c->nodes)return 1;
 if(!s->initialized || dt>.1f){uma_secondary_reset(s,c->bones);s->initialized=1;float m[512*12];if(!uma_motion_matrices(asset,pose->idle_phase,pose->run_phase,pose->run_blend,NULL,m))return 0;for(unsigned i=0;i<c->nodes;i++){const UmaSpring *n=c->node+i;float p[3];for(int k=0;k<3;k++)p[k]=asset->joint[n->bone].rest[k]+n->tip[k];uma_secondary_point(m+n->bone*12,p,s->tip[i]);memcpy(s->previous[i],s->tip[i],12);}s->revision++;return 1;}
 s->remainder+=dt;const float h=1.f/120;
 for(int steps=0;s->remainder>=h && steps<12;steps++,s->remainder-=h){
  float matrices[512*12];if(!uma_motion_matrices(asset,pose->idle_phase,pose->run_phase,pose->run_blend,s->rotation,matrices))return 0;
  for(unsigned i=0;i<c->nodes;i++){
   const UmaSpring *n=c->node+i;const float *m=matrices+n->bone*12;float *q=s->rotation+n->bone*4,origin[3],target[3],base[9];
   uma_secondary_point(m,asset->joint[n->bone].rest,origin);
   float x=q[0],y=q[1],z=q[2],w=q[3];const float rot[]={1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w),2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w),2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)};
   for(int a=0;a<3;a++)for(int b=0;b<3;b++){base[a*3+b]=0;for(int k=0;k<3;k++)base[a*3+b]+=m[a*4+k]*rot[b*3+k];}
   for(int a=0;a<3;a++){target[a]=origin[a];for(int k=0;k<3;k++)target[a]+=base[a*3+k]*n->tip[k];}
   float length=uma_secondary_length(n->tip),omega=6.2831853f*n->hz,drag=expf(-2*n->damping*omega*h),next[3];
   for(int k=0;k<3;k++){float external=-fmaxf(-40,fminf(40,acceleration[k]));if(k==0)external-=fminf(8,n->wind*speed*fabsf(speed));if(k==2)external-=n->gravity;next[k]=s->tip[i][k]+(s->tip[i][k]-s->previous[i][k])*drag+(omega*omega*(target[k]-s->tip[i][k])+external)*h*h;}
   /* Keep every joint length and angular limit bounded, including after a teleport. */
   uma_secondary_limit(next,origin,target,length,n->cone);
   for(int iteration=0;iteration<3;iteration++){
    for(unsigned r=0;r<n->count;r++){
     const UmaClothCollider *b=c->collider+c->ref[n->first+r];float a[3],end[3],center[3],delta[3],ab[3],t=0,den=0;
     uma_secondary_point(matrices+b->bone0*12,b->a,a);uma_secondary_point(matrices+b->bone1*12,b->b,end);
     for(int k=0;k<3;k++){ab[k]=end[k]-a[k];den+=ab[k]*ab[k];t+=(next[k]-a[k])*ab[k];}
     t=(b->kind&2) && den>1e-8f?fmaxf(0,fminf(1,t/den)):0;
     for(int k=0;k<3;k++){center[k]=a[k]+t*ab[k];delta[k]=next[k]-center[k];}
     float distance=uma_secondary_length(delta),radius=(b->kind&1)?fmaxf(0,b->radius-n->radius):b->radius+n->radius;
     if(distance>1e-6f && ((b->kind&1)?distance>radius:distance<radius))for(int k=0;k<3;k++)next[k]=center[k]+delta[k]*radius/distance;
    }
    uma_secondary_limit(next,origin,target,length,n->cone);
   }
   memcpy(s->previous[i],s->tip[i],12);memcpy(s->tip[i],next,12);
   float local[3]={0},from[3],dot=0;for(int a=0;a<3;a++){from[a]=n->tip[a]/length;for(int k=0;k<3;k++)local[a]+=base[k*3+a]*(next[k]-origin[k])/length;dot+=from[a]*local[a];}
   float desired[4]={from[1]*local[2]-from[2]*local[1],from[2]*local[0]-from[0]*local[2],from[0]*local[1]-from[1]*local[0],1+dot};float norm=sqrtf(desired[0]*desired[0]+desired[1]*desired[1]+desired[2]*desired[2]+desired[3]*desired[3]);if(norm<1e-6f)return 0;
   for(int k=0;k<4;k++)desired[k]/=norm;
   const float identity[4]={0,0,0,1};uma_quaternion_mix(identity,desired,n->apply,q);
  }
  s->revision++;
 }
 return 1;
}
#endif
