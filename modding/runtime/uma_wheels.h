#ifndef UMA_WHEELS_H
#define UMA_WHEELS_H
#include "uma_vertex_bounds.h"
/* The tire object may contain rotation/scale; its origin is the wheel mount. */
static int uma_corolla_wheel(const UmaMatrix *wheel,const UmaMatrix *body){
 if(!uma_rigid(body))return 0;
 for(int i=0;i<4;i++)for(int j=0;j<4;j++)if(!isfinite(wheel->m[i][j]))return 0;
 float point[3]={0};for(int i=0;i<3;i++)for(int j=0;j<3;j++)point[i]+=(wheel->m[3][j]-body->m[3][j])*body->m[i][j];
 return (fabsf(point[0]-1.35f)<.06f || fabsf(point[0]+1.05f)<.06f) && fabsf(fabsf(point[1])-.78f)<.06f && fabsf(point[2]-.275f)<.12f;
}
static int uma_corolla_wheel_bounds(const UmaVertexBounds *bounds,const UmaMatrix *object,const UmaMatrix *body){
 UmaMatrix center=*object;float half[3];
 for(int i=0;i<3;i++){float p=(bounds->minimum[i]+bounds->maximum[i])*.5f;half[i]=(bounds->maximum[i]-bounds->minimum[i])*.5f;for(int j=0;j<3;j++)center.m[3][j]+=p*object->m[i][j];}
 if(!uma_corolla_wheel(&center,body))return 0;
 float largest=0;
 for(int axis=0;axis<3;axis++){float extent=0;for(int i=0;i<3;i++){float rotation=0;for(int j=0;j<3;j++)rotation+=object->m[i][j]*body->m[axis][j];extent+=fabsf(rotation)*half[i];}if(extent>largest)largest=extent;}
 return largest>=.12f && largest<=.75f;
}
/* Batches may contain several tires; their combined center is not a wheel mount. */
static int uma_corolla_tire_batch(const void *data,size_t bytes,unsigned count,unsigned stride,unsigned position,const UmaMatrix *object,const UmaMatrix *body){
 UmaVertexBounds checked;if(count<4 || !uma_vertex_bounds(data,bytes,count,stride,position,&checked) || !uma_rigid(body))return 0;
 for(int r=0;r<4;r++)for(int c=0;c<4;c++)if(!isfinite(object->m[r][c]))return 0;
 float low[4][3]={{0}},high[4][3]={{0}};unsigned occupied[4]={0};
 for(unsigned v=0;v<count;v++){
  float input[3],world[3],point[3]={0};memcpy(input,(const unsigned char*)data+(size_t)v*stride+position,12);
  for(int j=0;j<3;j++){world[j]=object->m[3][j]-body->m[3][j];for(int i=0;i<3;i++)world[j]+=input[i]*object->m[i][j];}
  for(int i=0;i<3;i++)for(int j=0;j<3;j++)point[i]+=world[j]*body->m[i][j];
  int mount=-1;for(int k=0;k<4;k++){
   float x=k<2?1.35f:-1.05f,y=k&1?-.78f:.78f;
   if(fabsf(point[0]-x)<=.45f && fabsf(point[1]-y)<=.35f && fabsf(point[2]-.275f)<=.55f){mount=k;break;}
  }
  if(mount<0)return 0;
  for(int i=0;i<3;i++){if(!occupied[mount] || point[i]<low[mount][i])low[mount][i]=point[i];if(!occupied[mount] || point[i]>high[mount][i])high[mount][i]=point[i];}occupied[mount]++;
 }
 int surface=0;for(int k=0;k<4;k++)if(occupied[k]){
  float extent=0;for(int i=0;i<3;i++)if(high[k][i]-low[k][i]>extent)extent=high[k][i]-low[k][i];
  if(occupied[k]<4 || extent<.18f)return 0;
  surface=1;
 }
 return surface;
}
/* Symmetric body anchors 0x0ee87ec4/0x9b971511 in this Corolla resource. */
static int uma_corolla_side_attachment(const UmaMatrix *object,const UmaMatrix *body){
 if(!uma_rigid(body))return 0;
 float point[3]={0};for(int i=0;i<3;i++)for(int j=0;j<3;j++){if(!isfinite(object->m[3][j]))return 0;point[i]+=(object->m[3][j]-body->m[3][j])*body->m[i][j];}
 return fabsf(point[0]-.6322f)<.04f && fabsf(fabsf(point[1])-.7031f)<.04f && fabsf(point[2]-.9397f)<.04f;
}
#endif
