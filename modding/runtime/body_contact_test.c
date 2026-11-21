#include <assert.h>
#include "uma_body_contact.h"
int main(void){
 (void)uma_motion_load;(void)uma_motion_free;
 UmaVertex p[4]={0};p[0].position[0]=.02f;p[1].position[0]=.02f;p[2].position[2]=.5f;p[3].position[0]=1;for(int v=0;v<4;v++)p[v].normal[0]=1;
 UmaVertex original[4];memcpy(original,p,sizeof(p));float weight[]={1,0,1,1};UmaBodyCapsule caps[2]={{{0,0,0},{0,0,0},.1f},{{0,0,.3f},{0,0,.7f},.08f}};
 assert(uma_body_separate(p,4,weight,caps,2));float delta[3];assert(uma_body_distance(p[0].position,caps,delta)>=.1029f);assert(uma_body_distance(p[2].position,caps+1,delta)>=.0829f);assert(!memcmp(p+1,original+1,sizeof(*p)) && !memcmp(p+3,original+3,sizeof(*p)));
 memcpy(original,p,sizeof(p));caps[1].radius=NAN;assert(!uma_body_separate(p,4,weight,caps,2) && !memcmp(p,original,sizeof(p)));caps[1].radius=.08f;weight[3]=2;assert(!uma_body_separate(p,4,weight,caps,2) && !memcmp(p,original,sizeof(p)));
 UmaMotion asset={.bones=1,.vertices=1};UmaBodyContacts contacts;
 for(unsigned bad=0;bad<9;bad++){
  uint32_t h[5]={0,1,1,1,1};memcpy(h,"UMAC",4);unsigned char mask[4]={1,0,0,0};UmaBodyBones bone={0,0,.1f};if(bad==1)h[1]=2;if(bad==2)h[2]=513;if(bad==3)h[4]=17;if(bad==4)mask[0]=2;if(bad==5)mask[1]=1;if(bad==6)bone.a=1;if(bad==7)bone.radius=NAN;
  FILE *file=tmpfile();assert(file);assert(fwrite(h,4,5,file)==5 && fwrite(mask,1,4,file)==4 && fwrite(&bone,8,1,file)==1);if(bad==8)fputc(1,file);rewind(file);memset(&contacts,0,sizeof(contacts));int valid=uma_body_load(file,&asset,&contacts);fclose(file);if(!bad)assert(valid && contacts.count==1 && contacts.mask[0]);else assert(!valid && !contacts.count);
 }
 puts("PASS sphere/capsule garment separation, axial-center fallback, pinned skin/remote points unchanged; invalid data rejected before mutation; UMAC malformed input rejected atomically");return 0;
}
