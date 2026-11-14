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
#endif
