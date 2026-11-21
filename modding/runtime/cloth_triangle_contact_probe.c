/* Diagnostic: vertex-only separation cannot detect a limb crossing a wide cloth triangle. */
#include <assert.h>
#include "uma_body_contact.h"
int main(void){
 UmaVertex pose[3]={0},before[3];float weights[3]={1,1,1};
 const float xy[3][2]={{-.2f,-.2f},{.2f,-.2f},{0,.2f}};
 UmaBodyCapsule limb={{0,0,-.2f},{0,0,.2f},.05f};
 for(unsigned i=0;i<3;i++){pose[i].position[0]=xy[i][0];pose[i].position[1]=xy[i][1];pose[i].normal[2]=1;float delta[3];assert(uma_body_distance(pose[i].position,&limb,delta)>.053f);}
 memcpy(before,pose,sizeof(pose));assert(uma_body_separate(pose,3,weights,&limb,1));
 assert(memcmp(before,pose,sizeof(pose))==0);
 /* Barycentric (1/4,1/4,1/2) lies inside the triangle, directly on the limb axis. */
 float center[3]={0},delta[3];for(int k=0;k<3;k++)center[k]=.25f*pose[0].position[k]+.25f*pose[1].position[k]+.5f*pose[2].position[k];
 assert(uma_body_distance(center,&limb,delta)<1e-7f);
 puts("REPRODUCED: all cloth vertices outside limb, triangle interior intersects; vertex projection leaves triangle unchanged. Diagnostic only, not a collision fix.");return 0;
}
