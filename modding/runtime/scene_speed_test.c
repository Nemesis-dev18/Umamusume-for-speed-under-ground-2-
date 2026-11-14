#include "uma_scene_speed.h"
#include <assert.h>
#include <stdio.h>
static UmaMatrix identity(void){UmaMatrix m={0};for(int i=0;i<4;i++)m.m[i][i]=1;return m;}
static UmaMatrix multiply(UmaMatrix a,UmaMatrix b){UmaMatrix r={0};for(int i=0;i<4;i++)for(int j=0;j<4;j++)for(int k=0;k<4;k++)r.m[i][j]+=a.m[i][k]*b.m[k][j];return r;}
static void frame(UmaSceneSpeed *scene,UmaMatrix body,UmaMatrix view){for(int i=0;i<10;i++)uma_scene_reference(scene,&view);uma_scene_body(scene,&body);}
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
 scene=(UmaSceneSpeed){0};for(int i=0;i<3;i++)uma_scene_reference(&scene,&view);for(int i=0;i<3;i++)uma_scene_reference(&scene,&reflected);uma_scene_body(&scene,&wv);speed=42;assert(!uma_scene_finish(&scene,.01f,&speed) && speed==42);
 frame(&scene,wv,view);assert(!uma_scene_finish(&scene,.5f,&speed) && speed==42);
 for(int i=0;i<150;i++){uma_scene_reference(&scene,&view);}assert(scene.samples==96);uma_scene_body(&scene,&wv);assert(uma_scene_finish(&scene,.01f,&speed));
 puts("PASS camera motion cancellation, translation speed, stop/reverse, teleport rejection, reflection/scale rejection, ambiguity and sample bounds; synthetic matrices only");return 0;
}
