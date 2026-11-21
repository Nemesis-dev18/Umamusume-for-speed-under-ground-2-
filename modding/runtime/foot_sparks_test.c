#include <assert.h>
#include "uma_foot_sparks.h"
int main(void){
 (void)uma_motion_load;(void)uma_motion_free;
 UmaMotion m={0};m.vertices=4;UmaVertex vertices[4]={0};UmaSkin skin[4]={0};uint8_t mask[]={0,1};m.skin=skin;m.secondary_mask=mask;
 vertices[0].position[1]=-.1f;vertices[1].position[1]=.1f;vertices[2].position[1]=1;vertices[3].position[2]=1;
 for(int i=0;i<4;i++)skin[i].weight[0]=1;
 skin[2].bone[0]=1;
 float feet[2][3];unsigned counts[2];uma_spark_contacts(&m,vertices,feet,counts);assert(counts[0]==1 && counts[1]==1);assert(fabsf(feet[1][1]-.1f)<1e-6f);
 UmaVertex sparks[48];float root[]={0,1,0,-1,0,0,0,0,1};assert(uma_spark_mesh(.25f,feet,counts,root,NULL,sparks)==48);
 for(int i=0;i<48;i++)for(int k=0;k<3;k++)assert(isfinite(sparks[i].position[k]) && fabsf(sparks[i].position[k])<.75f);
 for(int i=0;i<48;i++)assert(sparks[i].uv[0]>0 && sparks[i].uv[0]<1 && sparks[i].uv[1]>0 && sparks[i].uv[1]<1);
 float facing[]={1,0,0,0,0,1};assert(uma_spark_mesh(.125f,feet,counts,root,facing,sparks)==48);
 for(int q=0;q<8;q++){
  UmaVertex *p=sparks+q*6;assert(p[1].position[0]>p[0].position[0] && fabsf(p[1].position[1]-p[0].position[1])<1e-6f && fabsf(p[1].position[2]-p[0].position[2])<1e-6f);
  assert(p[2].position[2]>p[0].position[2] && fabsf(p[2].position[0]-p[0].position[0])<1e-6f);
  unsigned column=(unsigned)(p[0].uv[0]*4),row=(unsigned)(p[0].uv[1]*2);assert(column<4 && row<2);
  for(int v=0;v<6;v++)assert((unsigned)(p[v].uv[0]*4)==column && (unsigned)(p[v].uv[1]*2)==row);
 }
 vertices[0].position[2]=vertices[1].position[2]=.25f;uma_spark_contacts(&m,vertices,feet,counts);assert(!counts[0] && !counts[1]);assert(!uma_spark_mesh(0,feet,counts,NULL,NULL,sparks));
 puts("PASS sole contact sparks: both feet, no garment/tail contact, raised feet suppressed, finite corrected mesh, camera-facing axes independent of root correction, atlas cells isolated");return 0;
}
