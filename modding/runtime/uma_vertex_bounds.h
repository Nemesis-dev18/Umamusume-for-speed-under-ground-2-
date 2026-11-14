#ifndef UMA_VERTEX_BOUNDS_H
#define UMA_VERTEX_BOUNDS_H
#include <math.h>
#include <stddef.h>
#include <string.h>
typedef struct {float minimum[3],maximum[3];} UmaVertexBounds;
static inline int uma_vertex_bounds(const void *data,size_t bytes,unsigned count,unsigned stride,unsigned position,UmaVertexBounds *output){
 if(!data || !count || count>4096 || stride<12 || stride>256 || position>stride-12 || bytes>4*1024*1024 || (size_t)(count-1)*stride+position+12>bytes)return 0;
 UmaVertexBounds result;
 for(unsigned i=0;i<count;i++){
  float point[3];memcpy(point,(const unsigned char*)data+(size_t)i*stride+position,12);
  for(int c=0;c<3;c++){if(!isfinite(point[c]) || fabsf(point[c])>1e6f)return 0;if(!i || point[c]<result.minimum[c])result.minimum[c]=point[c];if(!i || point[c]>result.maximum[c])result.maximum[c]=point[c];}
 }
 *output=result;return 1;
}
#endif
