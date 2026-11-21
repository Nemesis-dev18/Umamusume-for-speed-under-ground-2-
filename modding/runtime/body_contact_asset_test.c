#include <assert.h>
#include "uma_secondary.h"
#include "uma_body_contact.h"
#include "uma_body_render.h"
typedef struct {uint16_t a,b;float radius;} ContactBones;
static unsigned penetrations(const UmaVertex *pose,unsigned vertices,const float *weight,const UmaBodyCapsule *caps,unsigned count){
 unsigned total=0;for(unsigned v=0;v<vertices;v++)if(weight[v]>=.5f)for(unsigned c=0;c<count;c++){float delta[3];if(uma_body_distance(pose[v].position,caps+c,delta)<caps[c].radius-.001f){total++;break;}}return total;
}
int main(int argc,char **argv){
 assert(argc==5 || argc==6 || (argc==7 && !strcmp(argv[6],"surface-probe")));UmaMotion a={0};FILE *f=fopen(argv[1],"rb");assert(f && uma_motion_load(f,&a));fclose(f);UmaSecondary *c=calloc(1,sizeof(*c));UmaSecondaryState *s=calloc(1,sizeof(*s));assert(c && s);f=fopen(argv[2],"rb");assert(f && uma_secondary_load(f,&a,c));fclose(f);a.secondary_mask=c->mask;
 uint8_t mask[512]={0};f=fopen(argv[3],"rb");assert(f && fread(mask,1,a.bones,f)==a.bones && fgetc(f)==EOF);fclose(f);ContactBones bones[16];f=fopen(argv[4],"rb");assert(f);size_t count=fread(bones,sizeof(*bones),16,f);assert(count && fgetc(f)==EOF);fclose(f);for(unsigned k=0;k<count;k++)assert(bones[k].a<a.bones && bones[k].b<a.bones);
 float *weight=calloc(a.vertices,sizeof(float));UmaVertex *pose=malloc(a.vertices*36),*original=malloc(a.vertices*36);assert(weight && pose && original);for(unsigned v=0;v<a.vertices;v++)for(unsigned j=0;j<4;j++)if(mask[a.skin[v].bone[j]])weight[v]+=a.skin[v].weight[j];UmaBodyContacts contacts={0};if(argc>=6){f=fopen(argv[5],"rb");assert(f && uma_body_load(f,&a,&contacts));fclose(f);assert(!memcmp(mask,contacts.mask,a.bones));a.body_contacts=&contacts;}
 UmaMotionState state={0};float accel[3]={0};unsigned before=0,after=0,frames=0;float largest=0,edge_delta=0;unsigned edge_x=0,edge_y=0,edge_frame=0;float edge_before[2][3]={{0}},edge_after[2][3]={{0}};UmaBodyCapsule edge_caps[16];
 for(unsigned frame=0;frame<360;frame++){
  float speed=frame<240?12:0;assert(uma_motion_step_timed(&state,1.f/60,speed,0,a.idle_seconds,a.run_seconds));assert(uma_secondary_step(c,s,&a,&state,1.f/60,speed,accel));assert(uma_motion_sample_secondary(&a,state.idle_phase,state.run_phase,state.run_blend,pose,a.vertices*36,s->rotation));memcpy(original,pose,a.vertices*36);
  float m[512*12];assert(uma_motion_matrices(&a,state.idle_phase,state.run_phase,state.run_blend,s->rotation,m));float shift[3]={0};for(int axis=0;axis<3;axis++){float raw=0;for(unsigned j=0;j<4;j++){const float *row=m+a.skin[0].bone[j]*12+axis*4;raw+=a.skin[0].weight[j]*(row[3]+row[0]*a.rest[0].position[0]+row[1]*a.rest[0].position[1]+row[2]*a.rest[0].position[2]);}shift[axis]=pose[0].position[axis]-raw;}
  UmaBodyCapsule caps[16];for(unsigned k=0;k<count;k++){uma_secondary_point(m+bones[k].a*12,a.joint[bones[k].a].rest,caps[k].a);uma_secondary_point(m+bones[k].b*12,a.joint[bones[k].b].rest,caps[k].b);caps[k].radius=bones[k].radius;for(int axis=0;axis<3;axis++){caps[k].a[axis]+=shift[axis];caps[k].b[axis]+=shift[axis];}}
  unsigned b=penetrations(pose,a.vertices,weight,caps,(unsigned)count);if(argc>=6)assert(uma_body_render(&a,&state,s->rotation,pose,original,weight));else assert(uma_body_separate(pose,a.vertices,weight,caps,(unsigned)count));if(argc==7)for(unsigned pass=0;pass<12;pass++){
   for(unsigned t=0;t<a.indices;t+=3)for(unsigned e=0;e<3;e++){
    unsigned x=a.index[t+e],y=a.index[t+(e+1)%3];float wx=weight[x]>=.5f?weight[x]:0,wy=weight[y]>=.5f?weight[y]:0;if(wx+wy<=0)continue;
    float delta[3],old=0,now=0;for(int axis=0;axis<3;axis++){float b=original[y].position[axis]-original[x].position[axis];old+=b*b;delta[axis]=pose[y].position[axis]-pose[x].position[axis];now+=delta[axis]*delta[axis];}
    if(old<1e-6f || now<1e-12f || (now>=old*.81f && now<=old*1.21f))continue;
    old=sqrtf(old);now=sqrtf(now);float target=fminf(old*1.1f,fmaxf(old*.9f,now)),correction=.8f*(now-target)/(now*(wx+wy));
    for(int axis=0;axis<3;axis++){pose[x].position[axis]+=delta[axis]*correction*wx;pose[y].position[axis]-=delta[axis]*correction*wy;}
   }
   assert(uma_body_separate(pose,a.vertices,weight,caps,(unsigned)count));
  }
  if(argc==7)uma_cloth_normals(&a,pose,original,weight);
  unsigned d=penetrations(pose,a.vertices,weight,caps,(unsigned)count);before+=b;after+=d;frames+=b>0;
  for(unsigned t=0;t<a.indices;t+=3)for(unsigned e=0;e<3;e++){
   unsigned x=a.index[t+e],y=a.index[t+(e+1)%3];if(weight[x]<.5f && weight[y]<.5f)continue;
   float old=0,now=0;for(int axis=0;axis<3;axis++){float d=original[x].position[axis]-original[y].position[axis],n=pose[x].position[axis]-pose[y].position[axis];old+=d*d;now+=n*n;}
   float change=fabsf(sqrtf(now)-sqrtf(old));if(change>edge_delta){edge_delta=change;edge_x=x;edge_y=y;edge_frame=frame;memcpy(edge_before[0],original[x].position,12);memcpy(edge_before[1],original[y].position,12);memcpy(edge_after[0],pose[x].position,12);memcpy(edge_after[1],pose[y].position,12);memcpy(edge_caps,caps,count*sizeof(*caps));}
  }
  for(unsigned v=0;v<a.vertices;v++){if(weight[v]==0)assert(!memcmp(pose+v,original+v,36));float normal=0;for(int axis=0;axis<3;axis++)normal+=pose[v].normal[axis]*pose[v].normal[axis];assert(fabsf(normal-1)<.001f);for(int axis=0;axis<3;axis++){assert(isfinite(pose[v].position[axis]) && fabsf(pose[v].position[axis])<4);largest=fmaxf(largest,fabsf(pose[v].position[axis]-original[v].position[axis]));}}
 }
 printf("worst_frame=%u\n",edge_frame);for(unsigned v=0;v<2;v++){printf("edge_endpoint=%u before=%.4f,%.4f,%.4f after=%.4f,%.4f,%.4f\n",v,edge_before[v][0],edge_before[v][1],edge_before[v][2],edge_after[v][0],edge_after[v][1],edge_after[v][2]);for(unsigned k=0;k<count;k++){float delta[3],d=uma_body_distance(edge_before[v],edge_caps+k,delta);if(d<edge_caps[k].radius)printf("capsule=%u before_distance=%.4f radius=%.4f\n",k,d,edge_caps[k].radius);}}
 printf("worst_edge=%u,%u garment_weights=%.4f,%.4f\n",edge_x,edge_y,weight[edge_x],weight[edge_y]);
 printf("frames=360 penetrating_frames=%u before_proxy_contacts=%u after_proxy_contacts=%u largest_axis_correction=%.5f largest_edge_length_change=%.5f; normals and pinned skin checked; live gameplay not validated\n",frames,before,after,largest,edge_delta);assert(before>0 && after<before/10);free(weight);free(pose);free(original);free(c);free(s);uma_motion_free(&a);return 0;
}
