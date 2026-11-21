#ifndef UMA_BODY_RENDER_H
#define UMA_BODY_RENDER_H
#include "uma_body_contact.h"
#include "uma_cloth_surface.h"
static inline int uma_body_render(const UmaMotion *a,const UmaMotionState *state,const float *secondary,UmaVertex *pose,UmaVertex *base,const float *weight){
 const UmaBodyContacts *c=a->body_contacts;if(!c || !c->count || c->count>16 || c->bones!=a->bones || c->vertices!=a->vertices)return 0;
 float matrices[512*12];if(!uma_motion_matrices(a,state->idle_phase,state->run_phase,state->run_blend,secondary,matrices))return 0;
 float shift[3]={0};for(int axis=0;axis<3;axis++){float raw=0;for(unsigned j=0;j<4;j++){const float *row=matrices+a->skin[0].bone[j]*12+axis*4;raw+=a->skin[0].weight[j]*(row[3]+row[0]*a->rest[0].position[0]+row[1]*a->rest[0].position[1]+row[2]*a->rest[0].position[2]);}shift[axis]=pose[0].position[axis]-raw;}
 UmaBodyCapsule caps[16];for(unsigned i=0;i<c->count;i++){
  const UmaBodyBones *b=c->capsule+i;const float *p[]={a->joint[b->a].rest,a->joint[b->b].rest},*m[]={matrices+b->a*12,matrices+b->b*12};float *q[]={caps[i].a,caps[i].b};caps[i].radius=b->radius;
  for(int end=0;end<2;end++)for(int axis=0;axis<3;axis++)q[end][axis]=shift[axis]+m[end][axis*4+3]+m[end][axis*4]*p[end][0]+m[end][axis*4+1]*p[end][1]+m[end][axis*4+2]*p[end][2];
 }
 memcpy(base,pose,(size_t)a->vertices*36);if(!uma_body_separate(pose,a->vertices,weight,caps,c->count))return 0;uma_cloth_normals(a,pose,base,weight);return 1;
}
#endif
