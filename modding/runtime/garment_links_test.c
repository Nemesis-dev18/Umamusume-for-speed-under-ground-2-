#include <assert.h>
#include "uma_secondary.h"
static FILE *fixture(unsigned flags,int trailing,int invalid){
 FILE *f=tmpfile();assert(f);uint32_t h[]={0,1,4,1};memcpy(h,"UMAL",4);UmaGarmentLink pair={1,3,1,.5f,flags};if(invalid)pair.intensity=NAN;
 assert(fwrite(h,4,4,f)==4 && fwrite(&pair,16,1,f)==1);if(trailing)assert(fputc(0,f)!=EOF);rewind(f);return f;
}
int main(void){
 (void)uma_motion_load;(void)uma_motion_free;(void)uma_secondary_load;(void)uma_secondary_step;
 UmaJoint joints[4]={{.parent=-1},{.parent=0,.rest={0,0,-.1f}},{.parent=-1,.rest={1,0,0}},{.parent=2,.rest={1,0,-.1f}}};UmaMotion a={.bones=4,.joint=joints};UmaGarmentLinks links={0};FILE *f=fixture(0,0,0);assert(uma_garment_links_load(f,&a,&links));fclose(f);
 float m[48]={0},out[12];for(int b=0;b<4;b++)m[b*12]=m[b*12+5]=m[b*12+10]=1;
 assert(uma_garment_link_forces(&a,&links,m,out));for(int k=0;k<12;k++)assert(fabsf(out[k])<1e-7f);
 m[3*12+3]=.2f;assert(uma_garment_link_forces(&a,&links,m,out));assert(fabsf(out[3]-.1f)<1e-6f && fabsf(out[9]+.1f)<1e-6f);for(int k=0;k<3;k++)assert(fabsf(out[3+k]+out[9+k])<1e-7f);
 float identity[48];memcpy(identity,m,sizeof(m));m[3*12+3]=-1;assert(uma_garment_link_forces(&a,&links,m,out));for(int k=0;k<12;k++)assert(fabsf(out[k])<1e-7f);
 for(int b=0;b<4;b++){memset(m+b*12,0,48);m[b*12+1]=-1;m[b*12+4]=1;m[b*12+10]=1;m[b*12+3]=4;m[b*12+7]=-3;m[b*12+11]=2;}m[3*12+7]+=.2f;
 assert(uma_garment_link_forces(&a,&links,m,out));assert(fabsf(out[4]-.1f)<1e-6f && fabsf(out[10]+.1f)<1e-6f && fabsf(out[3])<1e-7f);
 m[12]=NAN;for(int k=0;k<12;k++)out[k]=123;assert(!uma_garment_link_forces(&a,&links,m,out));for(int k=0;k<12;k++)assert(out[k]==123);memcpy(m,identity,sizeof(m));
 for(unsigned flags=1;flags<=2;flags++){f=fixture(flags,0,0);UmaGarmentLinks saved=links;int parsed=uma_garment_links_load(f,&a,&links);fclose(f);if(flags==1){assert(parsed);for(int k=0;k<12;k++)out[k]=123;assert(!uma_garment_link_forces(&a,&links,m,out));for(int k=0;k<12;k++)assert(out[k]==123);}else assert(!parsed && !memcmp(&saved,&links,sizeof(links)));}
 f=fixture(0,1,0);assert(!uma_garment_links_load(f,&a,&links));fclose(f);f=fixture(0,0,1);assert(!uma_garment_links_load(f,&a,&links));fclose(f);
 UmaSecondary *secondary=calloc(1,sizeof(*secondary));assert(secondary);secondary->bones=4;secondary->nodes=2;secondary->node[0].bone=0;secondary->node[1].bone=2;secondary->node[0].tip[2]=secondary->node[1].tip[2]=-.1f;
 f=fixture(0,0,0);assert(uma_secondary_links_load(f,&a,secondary));fclose(f);assert(secondary->link_tip[0]==1 && secondary->link_tip[1]==3);secondary->node[1].tip[0]=.01f;UmaGarmentLinks saved=secondary->links;f=fixture(0,0,0);assert(!uma_secondary_links_load(f,&a,secondary));fclose(f);assert(!memcmp(&saved,&secondary->links,sizeof(saved)));
 free(secondary);puts("PASS UMAL rest/extension symmetry, child-tip mapping, fold/unknown flags, NaN/trailing rejection and atomic failure");return 0;
}
