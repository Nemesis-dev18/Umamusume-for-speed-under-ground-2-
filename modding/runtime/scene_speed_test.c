#include "uma_scene_speed.h"
#include "uma_wheels.h"
#include <assert.h>
#include <stdio.h>
static UmaMatrix identity(void){UmaMatrix m={0};for(int i=0;i<4;i++)m.m[i][i]=1;return m;}
static UmaMatrix multiply(UmaMatrix a,UmaMatrix b){UmaMatrix r={0};for(int i=0;i<4;i++)for(int j=0;j<4;j++)for(int k=0;k<4;k++)r.m[i][j]+=a.m[i][k]*b.m[k][j];return r;}
static const UmaSceneKey ground_key={.buffer=1,.index=1,.vertices=256,.primitives=128};
static void frame(UmaSceneSpeed *scene,UmaMatrix body,UmaMatrix view){for(int i=0;i<10;i++)uma_scene_reference(scene,&view,&ground_key);uma_scene_body(scene,&body);}
int main(void){
 UmaSceneSpeed scene={0};UmaMatrix view=identity(),body=identity(),world,wv;float speed=99;
 view.m[3][0]=-100;body.m[3][0]=5;wv=multiply(body,view);
 assert(uma_relative_world(&wv,&view,&world));assert(fabsf(world.m[3][0]-5)<1e-5f);
 frame(&scene,wv,view);assert(uma_scene_finish(&scene,.01f,&speed) && speed==0);
 float angle=.3f;view=identity();view.m[0][0]=cosf(angle);view.m[0][1]=sinf(angle);view.m[1][0]=-sinf(angle);view.m[1][1]=cosf(angle);view.m[3][0]=-120;view.m[3][1]=30;
 body.m[3][0]=5.1f;wv=multiply(body,view);frame(&scene,wv,view);assert(uma_scene_finish(&scene,.01f,&speed));assert(fabsf(speed-10)<.03f);
 view.m[3][0]=-200;wv=multiply(body,view);frame(&scene,wv,view);assert(uma_scene_finish(&scene,.01f,&speed));assert(fabsf(speed)<.03f);
 body.m[3][0]-=.05f;wv=multiply(body,view);frame(&scene,wv,view);assert(uma_scene_finish(&scene,.01f,&speed));assert(fabsf(speed+5)<.03f);
 body.m[3][0]+=100;wv=multiply(body,view);frame(&scene,wv,view);speed=7;assert(!uma_scene_finish(&scene,.01f,&speed) && speed==7 && !scene.tracked);
 frame(&scene,wv,view);assert(uma_scene_finish(&scene,.01f,&speed) && speed==0);
 UmaMatrix reflected=view;for(int k=0;k<3;k++)reflected.m[0][k]*=-1;
 assert(!uma_relative_world(&reflected,&view,&world));
 UmaMatrix scaled=view;scaled.m[0][0]*=2;assert(!uma_rigid(&scaled));
 scene=(UmaSceneSpeed){0};for(int i=0;i<3;i++)uma_scene_reference(&scene,&view,&ground_key);for(int i=0;i<3;i++)uma_scene_reference(&scene,&reflected,&ground_key);uma_scene_body(&scene,&wv);speed=42;assert(!uma_scene_finish(&scene,.01f,&speed) && speed==42);
 frame(&scene,wv,view);assert(!uma_scene_finish(&scene,.5f,&speed) && speed==42);
 for(int i=0;i<150;i++){uma_scene_reference(&scene,&view,&ground_key);}assert(scene.samples==96);uma_scene_body(&scene,&wv);assert(uma_scene_finish(&scene,.01f,&speed));
 /* The real capture had 32 groups with 6/7 votes: a majority cannot exist. */
 scene=(UmaSceneSpeed){0};body=identity();body.m[3][0]=20;view=identity();view.m[3][0]=-100;
 for(int f=0;f<4;f++){
  view.m[3][0]-=3;body.m[3][0]+=.1f;wv=multiply(body,view);
  for(int j=0;j<40;j++){
   int id=f&1?39-j:j;UmaSceneKey key=ground_key;key.buffer=10+id;key.primitives=100+id;
   UmaMatrix object=identity();object.m[3][0]=(float)id*15;object.m[3][1]=(float)id*4;UmaMatrix reference=multiply(object,view);
   uma_scene_reference(&scene,&reference,&key);
  }
  uma_scene_body(&scene,&wv);assert(uma_scene_finish(&scene,.01f,&speed));assert(f==0?speed==0:fabsf(speed-10)<.1f);
 }
 /* One draw key reused at two different instance transforms is ambiguous. */
 scene=(UmaSceneSpeed){0};uma_scene_reference(&scene,&view,&ground_key);UmaMatrix duplicate=view;duplicate.m[3][0]+=10;uma_scene_reference(&scene,&duplicate,&ground_key);uma_scene_body(&scene,&wv);assert(!uma_scene_finish(&scene,.01f,&speed));
 puts("PASS 40 distinct scenery anchors without any majority, reordered draws, moving camera and instanced-anchor rejection");
 UmaMatrix projection={0},inverse_projection,recovered,combined;projection.m[0][0]=2.5f;projection.m[1][1]=3.8f;projection.m[2][2]=1.001f;projection.m[2][3]=1;projection.m[3][2]=-.1001f;
 combined=multiply(wv,projection);assert(uma_inverse_projection(&wv,&combined,&inverse_projection));
 combined=multiply(view,projection);recovered=multiply(combined,inverse_projection);
 for(int i=0;i<4;i++)for(int j=0;j<4;j++)assert(fabsf(recovered.m[i][j]-view.m[i][j])<.004f);
 assert(uma_rigid(&recovered));scene=(UmaSceneSpeed){0};frame(&scene,wv,recovered);assert(uma_scene_finish(&scene,.016f,&speed) && speed==0);
 body.m[3][0]+=.16f;wv=multiply(body,view);frame(&scene,wv,recovered);assert(uma_scene_finish(&scene,.016f,&speed));assert(fabsf(speed-10)<.1f);
 UmaMatrix singular={0};assert(!uma_inverse_projection(&wv,&singular,&inverse_projection));singular.m[0][0]=NAN;assert(!uma_matrix_inverse(&singular,&recovered));
 UmaMatrix mount=identity();mount.m[3][0]=1.35f;mount.m[3][1]=.78f;mount.m[3][2]=.275f;
 UmaMatrix root=identity(),wheel=multiply(mount,view);assert(uma_corolla_wheel(&wheel,&view));
 root.m[3][0]=25;root=multiply(root,view);assert(!uma_corolla_wheel(&wheel,&root));
 wheel.m[0][0]*=.3f;assert(uma_corolla_wheel(&wheel,&view));
 mount.m[3][1]+=.2f;wheel=multiply(mount,view);assert(!uma_corolla_wheel(&wheel,&view));wheel.m[0][0]=NAN;assert(!uma_corolla_wheel(&wheel,&view));
 UmaVertexBounds baked={{1.35f,.58f,.075f},{1.35f,.98f,.475f}};
 assert(uma_corolla_wheel_bounds(&baked,&view,&view));baked.maximum[1]+=5;assert(!uma_corolla_wheel_bounds(&baked,&view,&view));
 float points[4][8]={{1.35f,.58f,.075f},{1.35f,.98f,.075f},{1.35f,.58f,.475f},{1.35f,.98f,.475f}};
 assert(uma_vertex_bounds(points,sizeof(points),4,32,0,&baked));assert(uma_corolla_wheel_bounds(&baked,&view,&view));
 assert(!uma_vertex_bounds(points,3*32+11,4,32,0,&baked));points[0][0]=NAN;assert(!uma_vertex_bounds(points,sizeof(points),4,32,0,&baked));
 /* A combined four-tire draw has no individual-wheel AABB center. */
 float tires[16][6]={0};for(int k=0;k<4;k++)for(int j=0;j<4;j++){
  tires[k*4+j][0]=(k<2?1.35f:-1.05f)+(j&1?.2f:-.2f);tires[k*4+j][1]=k&1?-.78f:.78f;tires[k*4+j][2]=.275f+(j&2?.2f:-.2f);
 }
 root=identity();assert(uma_corolla_tire_batch(tires,sizeof(tires),16,24,0,&root,&root));
 UmaMatrix suspension=root;suspension.m[3][2]=.2f;assert(uma_corolla_tire_batch(tires,sizeof(tires),16,24,0,&suspension,&root));
 UmaMatrix foreign=root;foreign.m[3][0]=10;assert(!uma_corolla_tire_batch(tires,sizeof(tires),16,24,0,&root,&foreign));
 tires[15][0]=0;assert(!uma_corolla_tire_batch(tires,sizeof(tires),16,24,0,&root,&root));tires[15][0]=NAN;assert(!uma_corolla_tire_batch(tires,sizeof(tires),16,24,0,&root,&root));
 assert(!uma_corolla_tire_batch(tires,10,16,24,0,&root,&root));
 UmaMatrix mirror=root;mirror.m[3][0]=.6322f;mirror.m[3][1]=.7031f;mirror.m[3][2]=.9397f;
 assert(uma_corolla_side_attachment(&mirror,&root));mirror.m[3][1]*=-1;assert(uma_corolla_side_attachment(&mirror,&root));assert(!uma_corolla_side_attachment(&mirror,&foreign));
 puts("PASS multi-tire batch, suspension travel, foreign actor and outlier rejection; symmetric side anchors");
 puts("PASS CPU-baked wheel center and radius; large mesh, truncated data and nonfinite vertices rejected");
 puts("PASS own tire mount, foreign car rejection, scaled tire and invalid matrix cases");
 puts("PASS scenery ViewProj recovery from body WV/WVP, moving body speed, singular and nonfinite matrices rejected");
 puts("PASS camera motion cancellation, translation speed, stop/reverse, teleport rejection, reflection/scale rejection, ambiguity and sample bounds; synthetic matrices only");return 0;
}
