#ifndef UMA_SCENE_SPEED_H
#define UMA_SCENE_SPEED_H
#include <math.h>
#include <string.h>
#include <float.h>
#include <stdint.h>
typedef struct {float m[4][4];} UmaMatrix;
typedef struct {uint32_t buffer,index,base,minimum,start,vertices,primitives,offset,pass,width,height;} UmaSceneKey;
typedef struct {UmaMatrix matrix;UmaSceneKey key;unsigned votes;int ambiguous;} UmaReference;
typedef struct {UmaReference reference[96];UmaMatrix body[16];UmaSceneKey previous_key;unsigned references,bodies,samples;float previous[3];int tracked;} UmaSceneSpeed;
static UmaMatrix uma_matrix_product(const UmaMatrix *a,const UmaMatrix *b){
 UmaMatrix result={0};for(int i=0;i<4;i++)for(int j=0;j<4;j++)for(int k=0;k<4;k++)result.m[i][j]+=a->m[i][k]*b->m[k][j];return result;
}
static int uma_matrix_inverse(const UmaMatrix *matrix,UmaMatrix *output){
 double work[4][8];
 for(int i=0;i<4;i++)for(int j=0;j<8;j++){double v=j<4?matrix->m[i][j]:(j-4==i);if(!isfinite(v))return 0;work[i][j]=v;}
 for(int c=0;c<4;c++){
  int pivot=c;for(int r=c+1;r<4;r++)if(fabs(work[r][c])>fabs(work[pivot][c]))pivot=r;
  if(fabs(work[pivot][c])<1e-10)return 0;
  if(pivot!=c)for(int j=0;j<8;j++){double tmp=work[c][j];work[c][j]=work[pivot][j];work[pivot][j]=tmp;}
  double factor=work[c][c];for(int j=0;j<8;j++)work[c][j]/=factor;
  for(int r=0;r<4;r++)if(r!=c){factor=work[r][c];for(int j=0;j<8;j++)work[r][j]-=factor*work[c][j];}
 }
 UmaMatrix inverse;for(int i=0;i<4;i++)for(int j=0;j<4;j++){double v=work[i][j+4];if(!isfinite(v) || fabs(v)>1e8)return 0;inverse.m[i][j]=(float)v;}
 *output=inverse;return 1;
}
/* Recover P from one body's WV and WVP so world-space scenery needs no WV constant. */
static int uma_inverse_projection(const UmaMatrix *worldview,const UmaMatrix *combined,UmaMatrix *inverse_projection){
 UmaMatrix inverse_worldview;if(!uma_matrix_inverse(worldview,&inverse_worldview))return 0;
 UmaMatrix projection=uma_matrix_product(&inverse_worldview,combined);return uma_matrix_inverse(&projection,inverse_projection);
}
static float uma_determinant(const UmaMatrix *a){return a->m[0][0]*(a->m[1][1]*a->m[2][2]-a->m[1][2]*a->m[2][1])-a->m[0][1]*(a->m[1][0]*a->m[2][2]-a->m[1][2]*a->m[2][0])+a->m[0][2]*(a->m[1][0]*a->m[2][1]-a->m[1][1]*a->m[2][0]);}
static int uma_rigid(const UmaMatrix *a){
 for(int r=0;r<4;r++)for(int c=0;c<4;c++)if(!isfinite(a->m[r][c]))return 0;
 for(int r=0;r<3;r++)for(int c=0;c<3;c++){float dot=0;for(int k=0;k<3;k++)dot+=a->m[r][k]*a->m[c][k];if(fabsf(dot-(r==c))>.02f)return 0;}
 return fabsf(a->m[0][3])+fabsf(a->m[1][3])+fabsf(a->m[2][3])+fabsf(a->m[3][3]-1)<.001f;
}
static int uma_relative_world(const UmaMatrix *body,const UmaMatrix *view,UmaMatrix *out){
 if(!uma_rigid(body) || !uma_rigid(view))return 0;
 UmaMatrix inverse={0},result={0};inverse.m[3][3]=1;
 for(int r=0;r<3;r++)for(int c=0;c<3;c++)inverse.m[r][c]=view->m[c][r];
 for(int c=0;c<3;c++)for(int k=0;k<3;k++)inverse.m[3][c]-=view->m[3][k]*inverse.m[k][c];
 for(int r=0;r<4;r++)for(int c=0;c<4;c++)for(int k=0;k<4;k++)result.m[r][c]+=body->m[r][k]*inverse.m[k][c];
 if(!uma_rigid(&result) || uma_determinant(&result)<.98f)return 0;
 *out=result;return 1;
}
static void uma_scene_reference(UmaSceneSpeed *scene,const UmaMatrix *matrix,const UmaSceneKey *key){
 if(!key || !key->buffer || !uma_rigid(matrix))return;
 if(scene->samples<96)scene->samples++;
 for(unsigned i=0;i<scene->references;i++){
  UmaReference *entry=&scene->reference[i];if(memcmp(&entry->key,key,sizeof(*key)))continue;
  for(int r=0;r<4;r++)for(int c=0;c<3;c++)if(fabsf(entry->matrix.m[r][c]-matrix->m[r][c])>.003f)entry->ambiguous=1;
  entry->votes++;return;
 }
 if(scene->references<96){UmaReference *entry=&scene->reference[scene->references++];entry->matrix=*matrix;entry->key=*key;entry->votes=1;entry->ambiguous=0;}
}
static void uma_scene_body(UmaSceneSpeed *scene,const UmaMatrix *matrix){if(scene->bodies<16 && uma_rigid(matrix))scene->body[scene->bodies++]=*matrix;}
/* Track one immutable scenery draw across frames; independent objects need not share a matrix. */
static int uma_scene_finish(UmaSceneSpeed *scene,float seconds,float *speed){
 int best=-1,valid=0,same=0;float distance=FLT_MAX;UmaMatrix chosen={0};
 if(!isfinite(seconds) || seconds<=0 || seconds>.25f || !scene->references || !scene->bodies)goto done;
 for(unsigned i=0;i<scene->references;i++){
  UmaReference *entry=&scene->reference[i];if(entry->ambiguous)continue;
  int compatible=0;for(unsigned j=0;j<scene->bodies;j++)if(uma_determinant(&entry->matrix)*uma_determinant(&scene->body[j])>.9f)compatible=1;
  if(!compatible)continue;
  if(scene->tracked && !memcmp(&entry->key,&scene->previous_key,sizeof(entry->key))){best=(int)i;same=1;break;}
  if(best<0 || entry->key.primitives>scene->reference[best].key.primitives)best=(int)i;
 }
 if(best<0)goto done;
 for(unsigned i=0;i<scene->bodies;i++){
  UmaMatrix world;if(!uma_relative_world(&scene->body[i],&scene->reference[best].matrix,&world))continue;
  float score=0;for(int k=0;k<3;k++){float delta=same?world.m[3][k]-scene->previous[k]:scene->body[i].m[3][k];score+=delta*delta;}
  if(score<distance){chosen=world;distance=score;valid=1;}
 }
 if(valid){
  float result=0;
  if(same){
   float forward=0;for(int k=0;k<3;k++)forward+=(chosen.m[3][k]-scene->previous[k])*chosen.m[0][k];
   result=sqrtf(distance)/seconds;if(result>120){valid=0;goto done;}if(forward<0)result=-result;
  }
  for(int k=0;k<3;k++)scene->previous[k]=chosen.m[3][k];
  scene->previous_key=scene->reference[best].key;*speed=result;
 }
done:
 scene->tracked=valid;scene->references=scene->bodies=scene->samples=0;return valid;
}
#endif
