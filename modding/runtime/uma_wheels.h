#ifndef UMA_WHEELS_H
#define UMA_WHEELS_H
/* The tire object may contain rotation/scale; its origin is the wheel mount. */
static int uma_corolla_wheel(const UmaMatrix *wheel,const UmaMatrix *body){
 if(!uma_rigid(body))return 0;
 for(int i=0;i<4;i++)for(int j=0;j<4;j++)if(!isfinite(wheel->m[i][j]))return 0;
 float point[3]={0};for(int i=0;i<3;i++)for(int j=0;j<3;j++)point[i]+=(wheel->m[3][j]-body->m[3][j])*body->m[i][j];
 return (fabsf(point[0]-1.35f)<.06f || fabsf(point[0]+1.05f)<.06f) && fabsf(fabsf(point[1])-.78f)<.06f && fabsf(point[2]-.275f)<.12f;
}
#endif
