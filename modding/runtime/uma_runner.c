#define COBJMACROS
#include <windows.h>
#include <d3d9.h>
#include <wchar.h>
#include "uma_d3d.h"
#include "uma_secondary.h"
#include "uma_upload.h"
#include "uma_scene_speed.h"
#include "uma_wheels.h"
#include "uma_audio_win.h"
#include "uma_selection_capture.h"
#include "uma_effects.h"
typedef HRESULT (WINAPI *RunnerPresent)(IDirect3DDevice9*,const RECT*,const RECT*,HWND,const RGNDATA*);
typedef HRESULT (WINAPI *RunnerReset)(IDirect3DDevice9*,D3DPRESENT_PARAMETERS*);
typedef HRESULT (WINAPI *RunnerPrimitive)(IDirect3DDevice9*,D3DPRIMITIVETYPE,UINT,UINT);
typedef HRESULT (WINAPI *RunnerPrimitiveUP)(IDirect3DDevice9*,D3DPRIMITIVETYPE,UINT,const void*,UINT);
typedef HRESULT (WINAPI *RunnerIndexedUP)(IDirect3DDevice9*,D3DPRIMITIVETYPE,UINT,UINT,UINT,const void*,D3DFORMAT,const void*,UINT);
static RunnerPrimitive runner_original_primitive;
static RunnerPrimitiveUP runner_original_primitive_up;
static RunnerIndexedUP runner_original_indexed_up;
static UmaDrawIndexed runner_original_draw;
static RunnerPresent runner_original_present;
static RunnerReset runner_original_reset;
static void **runner_table;
static CRITICAL_SECTION runner_lock;
typedef struct {UmaMotion motion;UmaD3D renderer;WCHAR atlas[4096];UmaMotionState idle;UmaVertex carrier[6];UmaAnchors anchors;UmaSecondary secondary;UmaBodyContacts contacts;} RunnerModel;
static RunnerModel runner_models[9];
static unsigned runner_model_count=1;
static int runner_fleet_carriers;
#define runner_motion runner_models[0].motion
#define runner_renderer runner_models[0].renderer
#define runner_atlas runner_models[0].atlas
#define runner_idle_state runner_models[0].idle
static UmaD3D *runner_active_renderer=&runner_models[0].renderer;
static UmaMotionState runner_state;
typedef struct {UmaMatrix world,view;UmaMotionState state;float velocity[3],speed,up[3],heading[3];unsigned seen,model;int used,up_valid;UmaSecondaryState secondary;} RunnerActor;
static RunnerActor runner_actors[16];
static UmaSceneKey runner_actor_anchor;
static UmaMatrix runner_previous_anchor;
static UmaReference runner_previous_references[96];
static unsigned runner_previous_reference_count;
static int runner_actor_world_valid;
static float runner_tracking_gap;
static UmaSceneSpeed runner_scene;
static FILE *runner_log;
static ULONGLONG runner_last_tick;
static unsigned runner_frames,runner_candidates,runner_owned,runner_replaced,runner_shader_failures;
static unsigned runner_hidden_wheels,runner_tire_candidates,runner_camera_reports;
static struct {UINT vertices,primitives,shader;const char *method;int match,racing;} runner_wheel_reports[96];
static int runner_speed_valid;
static float runner_speed;
static unsigned runner_last_owned,runner_projected_references;
static UmaMatrix runner_inverse_projection;
static int runner_projection_valid;
static float runner_frame_seconds=1.f/60;
static float runner_road_up[3];static int runner_road_up_valid;
static void runner_close_renderers(void){for(unsigned i=0;i<9;i++)uma_d3d_close(&runner_models[i].renderer);runner_active_renderer=&runner_models[0].renderer;}
static void runner_free_models(void){runner_close_renderers();for(unsigned i=0;i<9;i++){uma_motion_free(&runner_models[i].motion);memset(&runner_models[i].secondary,0,sizeof(runner_models[i].secondary));memset(&runner_models[i].contacts,0,sizeof(runner_models[i].contacts));}runner_model_count=1;runner_fleet_carriers=0;}
static const void *runner_input_vertices(const RunnerModel *model){return runner_fleet_carriers?(const void*)model->carrier:(const void*)model->motion.rest;}
static UINT runner_input_count(const RunnerModel *model){return runner_fleet_carriers?6:model->motion.vertices;}
static UINT runner_input_triangles(const RunnerModel *model){return runner_fleet_carriers?2:model->motion.indices/3;}
static const UmaAnchors *runner_anchors(unsigned model){return model<runner_model_count?(runner_fleet_carriers?&runner_models[model].anchors:&uma_corolla_anchors):NULL;}
static inline int runner_load_models(const WCHAR *root,int fleet){
 static const unsigned ids[]={1068,1052,1032,1062,1015,1006,1058,9001,1067};WCHAR path[4096];
 if(!root || wcslen(root)>3900)return 0;
 for(unsigned i=0;i<9;i++)if(runner_models[i].motion.memory)return 0;
 unsigned count=fleet?7:1;
 if(fleet){swprintf(path,4096,L"%ls\\modding\\runtime\\fleet\\9001\\model.umab",root);if(GetFileAttributesW(path)!=INVALID_FILE_ATTRIBUTES)count=8;}
 if(fleet && count==8){swprintf(path,4096,L"%ls\\modding\\runtime\\fleet\\1067\\model.umab",root);if(GetFileAttributesW(path)!=INVALID_FILE_ATTRIBUTES)count=9;}
 for(unsigned i=0;i<count;i++){
  if(fleet)swprintf(path,4096,L"%ls\\modding\\runtime\\fleet\\%u\\model.umab",root,ids[i]);else swprintf(path,4096,L"%ls\\modding\\runtime\\kitasan.umab",root);
  FILE *asset=_wfopen(path,L"rb");if(!asset){runner_free_models();return 0;}int loaded=uma_motion_load(asset,&runner_models[i].motion);fclose(asset);if(!loaded){runner_free_models();return 0;}
  if(fleet){
   swprintf(path,4096,L"%ls\\modding\\runtime\\fleet\\%u\\secondary.bin",root,ids[i]);
   FILE *physics=_wfopen(path,L"rb");if(physics){int valid=uma_secondary_load(physics,&runner_models[i].motion,&runner_models[i].secondary);fclose(physics);if(!valid){runner_free_models();return 0;}runner_models[i].motion.secondary_mask=runner_models[i].secondary.mask;runner_models[i].motion.surface_mask=runner_models[i].secondary.surface_mask;}
  }
  if(fleet){
   swprintf(path,4096,L"%ls\\modding\\runtime\\fleet\\%u\\body.umac",root,ids[i]);FILE *contacts=_wfopen(path,L"rb");
   if(contacts){int valid=uma_body_load(contacts,&runner_models[i].motion,&runner_models[i].contacts);fclose(contacts);if(!valid){runner_free_models();return 0;}runner_models[i].motion.body_contacts=&runner_models[i].contacts;}
  }
  if(fleet)swprintf(runner_models[i].atlas,4096,L"%ls\\modding\\runtime\\fleet\\%u\\atlas.dds",root,ids[i]);else swprintf(runner_models[i].atlas,4096,L"%ls\\modding\\runtime\\atlas.dds",root);
  FILE *texture=_wfopen(runner_models[i].atlas,L"rb");if(!texture){runner_free_models();return 0;}fclose(texture);
  if(fleet){
   swprintf(path,4096,L"%ls\\modding\\runtime\\fleet\\%u\\anchors.bin",root,ids[i]);FILE *anchors=_wfopen(path,L"rb");if(!anchors){runner_free_models();return 0;}int valid=fread(&runner_models[i].anchors,1,72,anchors)==72 && fgetc(anchors)==EOF;fclose(anchors);
   for(int a=0;a<6;a++)for(int k=0;k<3;k++){float v=a<4?runner_models[i].anchors.wheel[a][k]:runner_models[i].anchors.side[a-4][k];if(!isfinite(v) || fabsf(v)>4)valid=0;}
   if(!valid){runner_free_models();return 0;}
  }
  const float positions[6][3]={{0,0,0},{0,.25f,0},{0,.5f,0},{0,0,0},{0,0,1},{0,0,2}};
  for(unsigned v=0;v<6;v++){UmaVertex *vertex=&runner_models[i].carrier[v];memset(vertex,0,sizeof(*vertex));memcpy(vertex->position,positions[v],12);vertex->normal[0]=1;memset(vertex->bgra,255,4);vertex->uv[0]=(ids[i]+v*17)/4096.f;vertex->uv[1]=(ids[i]+v*29)/8192.f;}
 }
 runner_model_count=count;runner_fleet_carriers=fleet;return 1;
}
static int runner_camera_change(UmaMatrix *output){
 static unsigned frame=UINT32_MAX,index;static UmaSceneKey key;static UmaMatrix matrix,change;static int cached;
 if(frame!=runner_frames){frame=runner_frames;cached=0;}
 if(cached && runner_previous_reference_count && index<runner_scene.references){
  const UmaReference *entry=&runner_scene.reference[index];
  if(!entry->ambiguous && !memcmp(&entry->key,&key,sizeof(key)) && !memcmp(&entry->matrix,&matrix,sizeof(matrix))){*output=change;return 1;}
 }
 cached=0;
 for(unsigned now=0;now<runner_scene.references;now++)for(unsigned old=0;old<runner_previous_reference_count;old++){
  const UmaReference *a=&runner_scene.reference[now],*b=&runner_previous_references[old];UmaMatrix inverse;
  if(a->ambiguous || b->ambiguous || memcmp(&a->key,&b->key,sizeof(a->key)) || !uma_matrix_inverse(&b->matrix,&inverse))continue;
  change=uma_matrix_product(&inverse,&a->matrix);if(!uma_rigid(&change) || uma_determinant(&change)<.98f)continue;
  index=now;key=a->key;matrix=a->matrix;cached=1;*output=change;return 1;
 }
 return 0;
}
static float runner_view_score(const UmaMatrix *a,const UmaMatrix *b){
 float score=0;for(int k=0;k<3;k++){float d=a->m[3][k]-b->m[3][k];score+=d*d;}
 for(int r=0;r<3;r++)for(int c=0;c<3;c++){float d=a->m[r][c]-b->m[r][c];score+=.0625f*d*d;}
 return score;
}
static UmaMotionState *runner_actor_pose_model(const UmaMatrix *view,unsigned model){
 if(model>=runner_model_count)return NULL;
 float radius=fmaxf(4,120*runner_frame_seconds+.25f);int best=-1;float distance=radius*radius;UmaMatrix camera;int rebased=runner_camera_change(&camera);
 for(int i=0;i<16;i++)if(runner_actors[i].used && runner_actors[i].model==model && runner_frames-runner_actors[i].seen<3){
  UmaMatrix predicted=rebased?uma_matrix_product(&runner_actors[i].view,&camera):runner_actors[i].view;
  float score=fminf(runner_view_score(view,&runner_actors[i].view),runner_view_score(view,&predicted));
  /* Owned reflected draws reuse the actor pose; only tracker updates reject mirrored bodies. */
  if(score<distance){best=i;distance=score;}
 }
 if(best<0 && runner_log){
  static unsigned reports,frame=UINT32_MAX;int moving=0;
  for(int i=0;i<16;i++)if(runner_actors[i].used && fabsf(runner_actors[i].speed)>.5f)moving=1;
  if(moving && reports<512 && frame!=runner_frames){
   frame=runner_frames;reports++;fprintf(runner_log,"POSE_UNMATCHED frame=%u model=%u determinant=%.4f rebased=%d origin=%.4f,%.4f,%.4f",runner_frames,model,uma_determinant(view),rebased,view->m[3][0],view->m[3][1],view->m[3][2]);
   for(int i=0;i<16;i++)if(runner_actors[i].used && runner_actors[i].model==model){
    UmaMatrix predicted=rebased?uma_matrix_product(&runner_actors[i].view,&camera):runner_actors[i].view;float score=0,raw=0,orientation=0;
    for(int k=0;k<3;k++){float d=view->m[3][k]-predicted.m[3][k],r=view->m[3][k]-runner_actors[i].view.m[3][k];score+=d*d;raw+=r*r;orientation+=view->m[0][k]*predicted.m[0][k];}
    fprintf(runner_log," actor=%d age=%u speed=%.3f distance=%.3f rawDistance=%.3f direction=%.3f determinant=%.3f",i,runner_frames-runner_actors[i].seen,runner_actors[i].speed,sqrtf(score),sqrtf(raw),orientation,uma_determinant(&runner_actors[i].view));
   }
   fputc('\n',runner_log);fflush(runner_log);
  }
 }
 return best>=0?&runner_actors[best].state:&runner_models[model].idle;
}
static inline UmaMotionState *runner_actor_pose(const UmaMatrix *view){return runner_actor_pose_model(view,0);}
/* shortcut: coherent scenery +Z estimates visual up; replace with native gravity if scene axes disagree. */
static int runner_reference_up(const UmaReference *refs,unsigned count,const UmaMatrix *anchor,float output[3]){
 int best=-1;unsigned best_votes=0,eligible=0;
 for(unsigned i=0;i<count;i++)if(!refs[i].ambiguous && uma_determinant(&refs[i].matrix)*uma_determinant(anchor)>.9f){
  eligible++;unsigned votes=0;
  for(unsigned j=0;j<count;j++)if(!refs[j].ambiguous && uma_determinant(&refs[j].matrix)*uma_determinant(anchor)>.9f){float dot=0;for(int k=0;k<3;k++)dot+=refs[i].matrix.m[2][k]*refs[j].matrix.m[2][k];if(dot>.98f)votes++;}
  if(votes>best_votes){best=(int)i;best_votes=votes;}
 }
 if(best<0 || best_votes<3 || best_votes*5<eligible*3)return 0;
 float length=0;for(int k=0;k<3;k++){output[k]=0;for(int c=0;c<3;c++)output[k]+=refs[best].matrix.m[2][c]*anchor->m[k][c];length+=output[k]*output[k];}
 if(length<1e-6f)return 0;
 length=sqrtf(length);for(int k=0;k<3;k++)output[k]/=length;
 return 1;
}
/* Associate actors in one immutable scenery coordinate frame, independent of draw order. */
/* shortcut: overlapping identical actors can be ambiguous; add native instance IDs before per-actor customization. */
static RunnerActor *runner_actor_update_models(const UmaMatrix *bodies,const unsigned *models,unsigned count,float seconds,const UmaMatrix *camera){
 if(count>16 || (count && !bodies) || !isfinite(seconds) || seconds<=0 || seconds>.25f)return NULL;
 for(unsigned j=0;j<count;j++)if(models && models[j]>=runner_model_count)return NULL;
 int handoff=!runner_scene.anchor_valid || !runner_actor_world_valid;
 runner_tracking_gap=runner_scene.anchor_valid?0:runner_tracking_gap+seconds;
 if(runner_scene.anchor_valid && memcmp(&runner_actor_anchor,&runner_scene.anchor_key,sizeof(runner_actor_anchor))){
  int rebased=0;UmaMatrix change,inverse;
  if(camera && runner_actor_world_valid && uma_matrix_inverse(&runner_scene.anchor,&inverse)){
   UmaMatrix previous=uma_matrix_product(&runner_previous_anchor,camera);change=uma_matrix_product(&previous,&inverse);rebased=uma_rigid(&change) && uma_determinant(&change)>.98f;
  }
  for(unsigned i=0;!rebased && runner_actor_world_valid && i<runner_previous_reference_count;i++){
   UmaReference *reference=&runner_previous_references[i];
   if(reference->ambiguous || memcmp(&reference->key,&runner_scene.anchor_key,sizeof(reference->key)) || !uma_matrix_inverse(&reference->matrix,&inverse))continue;
   change=uma_matrix_product(&runner_previous_anchor,&inverse);rebased=uma_rigid(&change) && uma_determinant(&change)>.98f;
  }
  if(rebased)for(int actor=0;actor<16;actor++)if(runner_actors[actor].used){
   runner_actors[actor].world=uma_matrix_product(&runner_actors[actor].world,&change);
   float velocity[3]={0},up[3]={0},heading[3]={0};
   for(int r=0;r<3;r++)for(int c=0;c<3;c++){velocity[c]+=runner_actors[actor].velocity[r]*change.m[r][c];up[c]+=runner_actors[actor].up[r]*change.m[r][c];heading[c]+=runner_actors[actor].heading[r]*change.m[r][c];}
   memcpy(runner_actors[actor].velocity,velocity,sizeof(velocity));memcpy(runner_actors[actor].up,up,sizeof(up));memcpy(runner_actors[actor].heading,heading,sizeof(heading));
  }
  if(!rebased){handoff=1;for(int i=0;i<16;i++)runner_actors[i].up_valid=0;}
  runner_actor_anchor=runner_scene.anchor_key;
 }
 UmaMatrix world[16];int assignment[16],taken[16]={0};
 for(unsigned j=0;j<count;j++){assignment[j]=-1;if(!runner_scene.anchor_valid)world[j]=bodies[j];else if(!uma_relative_world(&bodies[j],&runner_scene.anchor,&world[j]))taken[j]=1;}
 int used[16]={0};float limit=120*seconds+.25f;
 for(unsigned pair=0;pair<count;pair++){
  int actor=-1,body=-1;float best=limit*limit;
  for(int i=0;i<16;i++)if(runner_actors[i].used && !used[i] && runner_frames-runner_actors[i].seen<=2){
   for(unsigned j=0;j<count;j++)if(!taken[j] && runner_actors[i].model==(models?models[j]:0)){
    const UmaMatrix *current=handoff?&bodies[j]:&world[j],*previous=handoff?&runner_actors[i].view:&runner_actors[i].world;
    float distance=0;for(int k=0;k<3;k++){float d=current->m[3][k]-previous->m[3][k]-(handoff?0:runner_actors[i].velocity[k]*seconds);distance+=d*d;}
    if(uma_determinant(current)*uma_determinant(previous)>0 && distance<best){best=distance;actor=i;body=(int)j;}
   }
  }
  if(actor<0)break;
  assignment[body]=actor;used[actor]=taken[body]=1;
 }
 for(unsigned j=0;j<count;j++)if(!taken[j]){
  for(int i=0;i<16;i++)if(!used[i] && (!runner_actors[i].used || runner_frames-runner_actors[i].seen>2)){
   memset(&runner_actors[i],0,sizeof(runner_actors[i]));assignment[j]=i;used[i]=taken[j]=1;break;
  }
 }
 RunnerActor *primary=NULL;float nearest=FLT_MAX;
 for(unsigned j=0;j<count;j++)if(assignment[j]>=0){
  RunnerActor *actor=&runner_actors[assignment[j]];float forward=0,lateral=0,previous_speed=actor->speed;
  if(!handoff && actor->used && runner_frames-actor->seen==1){
   for(int k=0;k<3;k++){actor->velocity[k]=(world[j].m[3][k]-actor->world.m[3][k])/seconds;forward+=actor->velocity[k]*world[j].m[0][k];lateral+=actor->velocity[k]*world[j].m[1][k];}
   float speed=hypotf(forward,lateral);if(speed<=120)actor->speed=speed>.35f?(forward<0?-speed:speed):0;
  }else{if(!actor->used || runner_tracking_gap>.2f)actor->speed=0;memset(actor->velocity,0,sizeof(actor->velocity));}
  if(runner_scene.anchor_valid && runner_road_up_valid){memcpy(actor->up,runner_road_up,sizeof(actor->up));if(!actor->up_valid)memcpy(actor->heading,world[j].m[0],sizeof(actor->heading));actor->up_valid=1;}
  if(runner_scene.anchor_valid && !actor->up_valid){memcpy(actor->up,world[j].m[2],sizeof(actor->up));memcpy(actor->heading,world[j].m[0],sizeof(actor->heading));actor->up_valid=1;}
  if(runner_scene.anchor_valid && actor->up_valid){
   float alignment=0,dot=0,length=0,heading[3];for(int k=0;k<3;k++){alignment+=world[j].m[2][k]*actor->up[k];dot+=world[j].m[0][k]*actor->up[k];}
   for(int k=0;k<3;k++){heading[k]=world[j].m[0][k]-dot*actor->up[k];length+=heading[k]*heading[k];}
   if(alignment>.707f && length>.01f){length=sqrtf(length);for(int k=0;k<3;k++)actor->heading[k]=heading[k]/length;}
  }
  actor->world=world[j];actor->view=bodies[j];actor->seen=runner_frames;actor->used=1;actor->model=models?models[j]:0;
  const UmaMotion *motion=&runner_models[actor->model].motion;
  uma_motion_step_timed(&actor->state,seconds,actor->speed,0,motion->idle_seconds>0?motion->idle_seconds:2.f,motion->run_seconds>0?motion->run_seconds:.6f);
  if(runner_models[actor->model].secondary.nodes){float acceleration[3]={seconds>0?(actor->speed-previous_speed)/seconds:0,0,0};if(!uma_secondary_step(&runner_models[actor->model].secondary,&actor->secondary,motion,&actor->state,seconds,actor->speed,acceleration))memset(&actor->secondary,0,sizeof(actor->secondary));}
  float distance=0;for(int k=0;k<3;k++)distance+=bodies[j].m[3][k]*bodies[j].m[3][k];
  if(distance<nearest){nearest=distance;primary=actor;}
 }
 for(int i=0;i<16;i++)if(!used[i] && runner_frames-runner_actors[i].seen>2)runner_actors[i].used=0;
 runner_actor_world_valid=runner_scene.anchor_valid;
 return primary;
}
static inline RunnerActor *runner_actor_update(const UmaMatrix *bodies,unsigned count,float seconds,const UmaMatrix *camera){return runner_actor_update_models(bodies,NULL,count,seconds,camera);}
/* Keep the character upright in the initial road frame instead of inheriting car roll. */
/* shortcut: no fall/recovery clip yet; a crash keeps the existing gait with an upright root. */
static int runner_actor_root_view(const UmaMotionState *state,const UmaMatrix *view,float rotation[9]){
 if(!runner_scene.anchor_valid)return 0;
 for(int actor=0;actor<16;actor++)if(state==&runner_actors[actor].state && runner_actors[actor].up_valid){
  const RunnerActor *a=&runner_actors[actor];UmaMatrix body=a->world;
  if(view){UmaMatrix reference=runner_scene.anchor,camera,current;
   if(runner_camera_change(&camera)){UmaMatrix predicted=uma_matrix_product(&a->view,&camera);if(runner_view_score(view,&predicted)<runner_view_score(view,&a->view))reference=uma_matrix_product(&reference,&camera);}
   if(uma_relative_world(view,&reference,&current))body=current;
  }
  float forward[3],left[3],dot=0,length=0;
  for(int k=0;k<3;k++)dot+=a->heading[k]*a->up[k];
  for(int k=0;k<3;k++){forward[k]=a->heading[k]-dot*a->up[k];length+=forward[k]*forward[k];}
  if(length<.01f){
   dot=0;length=0;for(int k=0;k<3;k++)dot+=body.m[0][k]*a->up[k];
   for(int k=0;k<3;k++){forward[k]=body.m[0][k]-dot*a->up[k];length+=forward[k]*forward[k];}
   if(length<.01f){length=0;for(int k=0;k<3;k++){forward[k]=body.m[1][(k+1)%3]*a->up[(k+2)%3]-body.m[1][(k+2)%3]*a->up[(k+1)%3];length+=forward[k]*forward[k];}}
  }
  if(length<.01f)return 0;
  length=sqrtf(length);for(int k=0;k<3;k++)forward[k]/=length;
  for(int k=0;k<3;k++)left[k]=a->up[(k+1)%3]*forward[(k+2)%3]-a->up[(k+2)%3]*forward[(k+1)%3];
  for(int r=0;r<3;r++)for(int c=0;c<3;c++){
   rotation[r*3+c]=0;for(int k=0;k<3;k++)rotation[r*3+c]+=(r==0?forward[k]:(r==1?left[k]:a->up[k]))*body.m[c][k];
  }
  return 1;
 }
 return 0;
}
static inline int runner_actor_root(const UmaMotionState *state,float rotation[9]){return runner_actor_root_view(state,NULL,rotation);}
static int runner_combined(IDirect3DDevice9 *device,const UmaShaderEntry *entry,UmaMatrix *output){
 if(!entry || entry->worldviewproj<0)return 0;
 float rows[4][4];if(FAILED(IDirect3DDevice9_GetVertexShaderConstantF(device,(UINT)entry->worldviewproj,&rows[0][0],4)))return 0;
 for(int r=0;r<4;r++)for(int c=0;c<4;c++){if(!isfinite(rows[c][r]))return 0;output->m[r][c]=rows[c][r];}
 return 1;
}
static int runner_worldview(IDirect3DDevice9 *device,const UmaShaderEntry *entry,UmaMatrix *output){
 UmaMatrix matrix={0};matrix.m[3][3]=1;
 if(entry){
  if(entry->worldview<0){
   UmaMatrix combined;if(!entry->reference || !runner_projection_valid || !runner_combined(device,entry,&combined))return 0;
   matrix=uma_matrix_product(&combined,&runner_inverse_projection);if(!uma_rigid(&matrix))return 0;
   *output=matrix;runner_projected_references++;return 1;
  }
  float rows[3][4];if(FAILED(IDirect3DDevice9_GetVertexShaderConstantF(device,(UINT)entry->worldview,&rows[0][0],3)))return 0;
  for(int r=0;r<4;r++)for(int c=0;c<3;c++)matrix.m[r][c]=rows[c][r];
 }else{
  D3DMATRIX world,view;if(FAILED(IDirect3DDevice9_GetTransform(device,D3DTS_WORLD,&world)) || FAILED(IDirect3DDevice9_GetTransform(device,D3DTS_VIEW,&view)))return 0;
  memset(&matrix,0,sizeof(matrix));for(int r=0;r<4;r++)for(int c=0;c<4;c++)for(int k=0;k<4;k++)matrix.m[r][c]+=world.m[r][k]*view.m[k][c];
 }
 for(int r=0;r<4;r++)for(int c=0;c<4;c++)if(!isfinite(matrix.m[r][c]))return 0;
 *output=matrix;return 1;
}
typedef struct {float saved[16];int reg,active;} RunnerHeadlightScope;
static unsigned runner_hidden_headlights;
static void runner_headlight_begin(IDirect3DDevice9 *device,RunnerHeadlightScope *scope){
 HRESULT result;UmaShaderEntry *entry=uma_shader_get(&runner_active_renderer->shaders,device,&result);
 if(FAILED(result) || !entry || entry->headlight<0 || FAILED(IDirect3DDevice9_GetVertexShaderConstantF(device,(UINT)entry->headlight,scope->saved,4)))return;
 /* A negative projector depth samples the zero end of the native clip ramp; base scene lighting is untouched. */
 float off[16]={0};off[15]=-100;
 if(SUCCEEDED(IDirect3DDevice9_SetVertexShaderConstantF(device,(UINT)entry->headlight,off,4))){scope->reg=entry->headlight;scope->active=1;runner_hidden_headlights++;}
}
static int runner_fixed_combined(IDirect3DDevice9 *device,D3DMATRIX *combined){
 D3DMATRIX projection;UmaMatrix worldview;if(!runner_worldview(device,NULL,&worldview) || FAILED(IDirect3DDevice9_GetTransform(device,D3DTS_PROJECTION,&projection)))return 0;
 memset(combined,0,sizeof(*combined));for(int r=0;r<4;r++)for(int c=0;c<4;c++)for(int k=0;k<4;k++)combined->m[r][c]+=worldview.m[r][k]*projection.m[k][c];return 1;
}
static const GUID runner_resource_guid={0x9e814763,0xa906,0x47ba,{0xa9,0x63,0x9b,0x11,0x65,0x67,0x3d,0x54}};
static DWORD runner_next_resource;
static DWORD runner_resource_id(IDirect3DResource9 *resource){
 DWORD id=0,size=sizeof(id);if(!resource)return 0;
 if(SUCCEEDED(IDirect3DResource9_GetPrivateData(resource,&runner_resource_guid,&id,&size)) && size==sizeof(id) && id)return id;
 if(runner_next_resource==UINT32_MAX)return 0;
 id=++runner_next_resource;if(FAILED(IDirect3DResource9_SetPrivateData(resource,&runner_resource_guid,&id,sizeof(id),0)))return 0;return id;
}
static void runner_reference(IDirect3DDevice9 *device,IDirect3DVertexBuffer9 *vb,INT base,UINT minimum,UINT vertices,UINT start,UINT triangles,UINT offset,const UmaMatrix *worldview){
 DWORD zwrite=0,blend=1;D3DVERTEXBUFFER_DESC descriptor;
 if(vertices<64 || triangles<24 || FAILED(IDirect3DVertexBuffer9_GetDesc(vb,&descriptor)) || (descriptor.Usage&D3DUSAGE_DYNAMIC))return;
 if(FAILED(IDirect3DDevice9_GetRenderState(device,D3DRS_ZWRITEENABLE,&zwrite)) || !zwrite || FAILED(IDirect3DDevice9_GetRenderState(device,D3DRS_ALPHABLENDENABLE,&blend)) || blend)return;
 IDirect3DIndexBuffer9 *indices=NULL;D3DVIEWPORT9 viewport;if(FAILED(IDirect3DDevice9_GetIndices(device,&indices)) || !indices)return;
 UmaSceneKey key={0};key.buffer=runner_resource_id((IDirect3DResource9*)vb);key.index=runner_resource_id((IDirect3DResource9*)indices);IDirect3DIndexBuffer9_Release(indices);
 if(!key.buffer || !key.index || FAILED(IDirect3DDevice9_GetViewport(device,&viewport)))return;
 key.base=(UINT)base;key.minimum=minimum;key.vertices=vertices;key.start=start;key.primitives=triangles;key.offset=offset;key.pass=uma_determinant(worldview)<0;key.width=viewport.Width;key.height=viewport.Height;
 uma_scene_reference(&runner_scene,worldview,&key);
}
static int runner_position_offset(IDirect3DDevice9 *device,UINT stride,UINT *position){
 IDirect3DVertexDeclaration9 *declaration=NULL;D3DVERTEXELEMENT9 elements[65];UINT number=65;int found=0;
 if(FAILED(IDirect3DDevice9_GetVertexDeclaration(device,&declaration)) || !declaration)return 0;
 HRESULT result=IDirect3DVertexDeclaration9_GetDeclaration(declaration,elements,&number);IDirect3DVertexDeclaration9_Release(declaration);
 if(FAILED(result) || number>65 || stride<12 || stride>256)return 0;
 for(UINT i=0;i<number;i++)if(elements[i].Stream==0 && elements[i].Usage==D3DDECLUSAGE_POSITION && elements[i].UsageIndex==0 && elements[i].Type==D3DDECLTYPE_FLOAT3 && elements[i].Offset<=stride-12){*position=elements[i].Offset;found=1;}
 return found;
}
static int runner_readable(const void *data,size_t bytes){
 if(!data || !bytes || bytes>4*1024*1024 || (uintptr_t)data>UINTPTR_MAX-bytes)return 0;
 uintptr_t at=(uintptr_t)data,end=at+bytes;
 for(unsigned region=0;at<end && region<16;region++){
  MEMORY_BASIC_INFORMATION info;if(!VirtualQuery((const void*)at,&info,sizeof(info)) || info.State!=MEM_COMMIT || (info.Protect&(PAGE_GUARD|PAGE_NOACCESS)))return 0;
  DWORD protection=info.Protect&255;if(protection!=PAGE_READONLY && protection!=PAGE_READWRITE && protection!=PAGE_WRITECOPY)return 0;
  uintptr_t next=(uintptr_t)info.BaseAddress+info.RegionSize;if(next<=at)return 0;at=next;
 }
 return at>=end;
}
/* Crash cameras may draw wheels before the character body in the current pass. */
static unsigned runner_wheel_bodies(UmaMatrix bodies[32],unsigned models[32]){
 unsigned count=0;for(unsigned i=0;i<runner_scene.bodies && count<32;i++){bodies[count]=runner_scene.body[i];models[count++]=runner_scene.body_model[i];}
 UmaMatrix camera;int rebased=runner_camera_change(&camera);
 for(int i=0;i<16 && count<32;i++)if(runner_actors[i].used && runner_frames-runner_actors[i].seen<=2 && runner_actors[i].model<runner_model_count){
  bodies[count]=rebased?uma_matrix_product(&runner_actors[i].view,&camera):runner_actors[i].view;models[count++]=runner_actors[i].model;
 }
 return count;
}
static int runner_vertex_wheels(IDirect3DDevice9 *device,UINT vertices,const void *data,UINT stride,UINT first,const UmaMatrix *worldview,UmaVertexBounds *decoded){
 UINT position=0;UmaUploadSnapshot snapshot;const BYTE *points=data;size_t bytes=(size_t)vertices*stride;
 if(!data){
  IDirect3DVertexBuffer9 *buffer=NULL;UINT offset=0;DWORD size=sizeof(snapshot);
  if(FAILED(IDirect3DDevice9_GetStreamSource(device,0,&buffer,&offset,&stride)) || !buffer)return 0;
  HRESULT result=IDirect3DVertexBuffer9_GetPrivateData(buffer,&uma_bounds_guid,&snapshot,&size);IDirect3DVertexBuffer9_Release(buffer);
  uint64_t begin=(uint64_t)offset+(uint64_t)first*stride;
  if(FAILED(result) || size<8 || snapshot.bytes>sizeof(snapshot.data) || size!=8+snapshot.bytes || begin<snapshot.offset || begin-snapshot.offset>snapshot.bytes)return 0;
  UINT skip=(UINT)(begin-snapshot.offset);points=snapshot.data+skip;bytes=snapshot.bytes-skip;
 }else if(!runner_readable(data,bytes))return 0;
 if(!runner_position_offset(device,stride,&position))return 0;
 UmaVertexBounds bounds;if(!uma_vertex_bounds(points,bytes,vertices,stride,position,&bounds))return 0;
 *decoded=bounds;
 UmaMatrix bodies[32];unsigned models[32],count=runner_wheel_bodies(bodies,models);
 for(unsigned i=0;i<count;i++)if(uma_model_wheel_bounds(&bounds,worldview,bodies+i,runner_anchors(models[i])) || uma_model_tire_batch(points,bytes,vertices,stride,position,worldview,bodies+i,runner_anchors(models[i])))return 1;
 return 0;
}
static int runner_root_attachment(IDirect3DDevice9 *device,const UmaShaderEntry *entry,const UmaMatrix *worldview,UINT vertices){
 if(!entry || entry->diffuse_min<0 || vertices<4 || vertices>4096)return 0;
 IDirect3DVertexBuffer9 *buffer=NULL;UINT offset=0,stride=0;
 if(FAILED(IDirect3DDevice9_GetStreamSource(device,0,&buffer,&offset,&stride)) || !buffer)return 0;
 IDirect3DVertexBuffer9_Release(buffer);if(stride!=36)return 0;
 UmaMatrix bodies[32];unsigned models[32],count=runner_wheel_bodies(bodies,models);
 for(unsigned i=0;i<count;i++){
  int equal=1;for(int r=0;r<4;r++)for(int c=0;c<3;c++)if(fabsf(worldview->m[r][c]-bodies[i].m[r][c])>.001f)equal=0;
  if(equal)return 1;
 }
 return 0;
}
static int runner_wheel_draw(IDirect3DDevice9 *device,D3DPRIMITIVETYPE type,UINT vertices,UINT triangles,const char *method,const void *data,UINT stride,UINT first){
 if(type<D3DPT_TRIANGLELIST || type>D3DPT_TRIANGLEFAN || vertices<4 || vertices>4096 || triangles<2 || triangles>2048 || runner_active_renderer->device!=device || runner_frames-runner_last_owned>=3 )return 0;
 DWORD depth=0;if(FAILED(IDirect3DDevice9_GetRenderState(device,D3DRS_ZENABLE,&depth)) || !depth)return 0;
 HRESULT status;UmaShaderEntry *entry=uma_shader_get(&runner_active_renderer->shaders,device,&status);UmaMatrix worldview;if(FAILED(status) || !runner_worldview(device,entry,&worldview))return 0;
 UmaMatrix bodies[32];unsigned models[32],count=runner_wheel_bodies(bodies,models);
 int match=runner_root_attachment(device,entry,&worldview,vertices);for(unsigned i=0;!match && i<count;i++)if(uma_model_wheel(&worldview,bodies+i,runner_anchors(models[i])) || (entry && entry->diffuse_min>=0 && uma_model_side_attachment(&worldview,bodies+i,runner_anchors(models[i])))){match=1;break;}
 UmaVertexBounds decoded={{NAN,NAN,NAN},{NAN,NAN,NAN}};
 /* Detailed rims may use displaced child transforms, not the body origin. */
 int nearby=vertices<=32;
 for(unsigned i=0;!nearby && i<count;i++){float distance=0;for(int k=0;k<3;k++){float d=worldview.m[3][k]-bodies[i].m[3][k];distance+=d*d;}if(distance<16.f)nearby=1;}
 if(!match && nearby && vertices<=1024)match=runner_vertex_wheels(device,vertices,data,stride,first,&worldview,&decoded);
 if(runner_log && runner_tire_candidates<96){
  UINT shader=entry?entry->bytes:0;int known=0,racing=runner_scene.bodies>2;
  for(unsigned i=0;i<runner_tire_candidates;i++)if(runner_wheel_reports[i].vertices==vertices && runner_wheel_reports[i].primitives==triangles && runner_wheel_reports[i].shader==shader && runner_wheel_reports[i].method==method && runner_wheel_reports[i].match==match && runner_wheel_reports[i].racing==racing)known=1;
  if(!known){
   unsigned i=runner_tire_candidates++;runner_wheel_reports[i].vertices=vertices;runner_wheel_reports[i].primitives=triangles;runner_wheel_reports[i].shader=shader;runner_wheel_reports[i].method=method;runner_wheel_reports[i].match=match;runner_wheel_reports[i].racing=racing;
   fprintf(runner_log,"WHEEL method=%s frame=%u vertices=%u primitives=%u shaderBytes=%u match=%d bodies=%u origin=%.4f,%.4f,%.4f rawBounds=%.4f,%.4f,%.4f:%.4f,%.4f,%.4f\n",method,runner_frames,vertices,triangles,shader,match,runner_scene.bodies,worldview.m[3][0],worldview.m[3][1],worldview.m[3][2],decoded.minimum[0],decoded.minimum[1],decoded.minimum[2],decoded.maximum[0],decoded.maximum[1],decoded.maximum[2]);fflush(runner_log);
  }
 }
 if(match)runner_hidden_wheels++;
 return match;
}
static UINT runner_primitive_vertices(D3DPRIMITIVETYPE type,UINT count){
 if(count>2048)return 0;
 return type==D3DPT_TRIANGLELIST?count*3:((type==D3DPT_TRIANGLESTRIP || type==D3DPT_TRIANGLEFAN)?count+2:0);
}
static HRESULT WINAPI runner_primitive(IDirect3DDevice9 *device,D3DPRIMITIVETYPE type,UINT start,UINT count){
 EnterCriticalSection(&runner_lock);int capture=uma_selection_before(device);int hide=uma_effect_draw(device) || runner_wheel_draw(device,type,runner_primitive_vertices(type,count),count,"DP",NULL,0,start);LeaveCriticalSection(&runner_lock);
 HRESULT result=hide?S_OK:runner_original_primitive(device,type,start,count);
 if(capture){EnterCriticalSection(&runner_lock);uma_selection_after(device,capture,"DP",runner_primitive_vertices(type,count),count);LeaveCriticalSection(&runner_lock);}return result;
}
static HRESULT WINAPI runner_primitive_up(IDirect3DDevice9 *device,D3DPRIMITIVETYPE type,UINT count,const void *vertices,UINT stride){
 EnterCriticalSection(&runner_lock);int capture=uma_selection_before(device);int hide=uma_effect_draw(device) || (vertices && stride && runner_wheel_draw(device,type,runner_primitive_vertices(type,count),count,"DPUP",vertices,stride,0));LeaveCriticalSection(&runner_lock);
 HRESULT result=hide?IDirect3DDevice9_SetStreamSource(device,0,NULL,0,0):runner_original_primitive_up(device,type,count,vertices,stride);
 if(capture){EnterCriticalSection(&runner_lock);uma_selection_after(device,capture,"DPUP",runner_primitive_vertices(type,count),count);LeaveCriticalSection(&runner_lock);}return result;
}
static HRESULT WINAPI runner_indexed_up(IDirect3DDevice9 *device,D3DPRIMITIVETYPE type,UINT minimum,UINT vertices,UINT count,const void *indices,D3DFORMAT format,const void *data,UINT stride){
 EnterCriticalSection(&runner_lock);int capture=uma_selection_before(device);int hide=uma_effect_draw(device) || (data && indices && stride && runner_wheel_draw(device,type,vertices,count,"DIPUP",minimum?NULL:data,stride,minimum));LeaveCriticalSection(&runner_lock);
 HRESULT result;
 if(hide){result=IDirect3DDevice9_SetStreamSource(device,0,NULL,0,0);HRESULT cleared=IDirect3DDevice9_SetIndices(device,NULL);if(SUCCEEDED(result))result=cleared;}
 else result=runner_original_indexed_up(device,type,minimum,vertices,count,indices,format,data,stride);
 if(capture){EnterCriticalSection(&runner_lock);uma_selection_after(device,capture,"DIPUP",vertices,count);LeaveCriticalSection(&runner_lock);}return result;
}
static HRESULT WINAPI runner_draw(IDirect3DDevice9 *device,D3DPRIMITIVETYPE type,INT base,UINT minimum,UINT vertices,UINT start,UINT triangles){
 HRESULT result=E_FAIL;int replaced=0;EnterCriticalSection(&runner_lock);int capture=uma_selection_before(device);
 if(uma_effect_draw(device)){LeaveCriticalSection(&runner_lock);return S_OK;}
 int candidate=0;for(unsigned i=0;i<runner_model_count;i++)if(type==D3DPT_TRIANGLELIST && vertices==runner_input_count(&runner_models[i]) && triangles==runner_input_triangles(&runner_models[i]))candidate=1;
 if(candidate)runner_candidates++;
 if(candidate || (runner_active_renderer->device==device && runner_frames-runner_last_owned<3 && (runner_scene.references<96 || (vertices<=4096 && type==D3DPT_TRIANGLELIST) || (runner_scene.tracked && vertices==runner_scene.previous_key.vertices && triangles==runner_scene.previous_key.primitives)))){
  IDirect3DVertexBuffer9 *vb=NULL;UINT offset=0,stride=0;
  if(SUCCEEDED(IDirect3DDevice9_GetStreamSource(device,0,&vb,&offset,&stride)) && vb){
   int64_t first=(int64_t)base+minimum;uint64_t byte_offset=first>=0?(uint64_t)offset+(uint64_t)first*stride:UINT64_MAX;
   UINT model=0;int owned=candidate && stride==36 && byte_offset<=UINT_MAX && uma_upload_model_at(vb,(UINT)byte_offset,&model) && model<runner_model_count && vertices==runner_input_count(&runner_models[model]) && triangles==runner_input_triangles(&runner_models[model]);DWORD depth=0;
   if(SUCCEEDED(IDirect3DDevice9_GetRenderState(device,D3DRS_ZENABLE,&depth)) && depth && (owned || stride==24 || (stride>0 && vertices<=4096))){
    if(owned){
     runner_owned++;runner_last_owned=runner_frames;
     if(runner_active_renderer->device && runner_active_renderer->device!=device)runner_close_renderers();
     runner_active_renderer=&runner_models[model].renderer;
     if(!runner_active_renderer->device){FILE *texture=_wfopen(runner_models[model].atlas,L"rb");if(texture){result=uma_d3d_open(runner_active_renderer,device,&runner_models[model].motion,texture,runner_original_draw);fclose(texture);if(SUCCEEDED(result)){result=uma_d3d_materials_load(runner_active_renderer,runner_models[model].atlas);if(FAILED(result))uma_d3d_close(runner_active_renderer);}}}
    }
    if(runner_active_renderer->device==device){
     HRESULT shader_status;UmaShaderEntry *entry=uma_shader_get(&runner_active_renderer->shaders,device,&shader_status);UmaMatrix worldview;int have_worldview=0;
     if(owned && SUCCEEDED(shader_status) && entry && entry->worldview>=0){
      UmaMatrix combined;if(runner_worldview(device,entry,&worldview) && runner_combined(device,entry,&combined))runner_projection_valid=uma_inverse_projection(&worldview,&combined,&runner_inverse_projection);
     }
     if(SUCCEEDED(shader_status) && runner_worldview(device,entry,&worldview)){
      have_worldview=1;
      if(owned)uma_scene_body_model(&runner_scene,&worldview,model);
      else if(stride==24 && entry && entry->reference)runner_reference(device,vb,base,minimum,vertices,start,triangles,offset,&worldview);
      else if(stride==24 && !entry){DWORD fvf=0;if(SUCCEEDED(IDirect3DDevice9_GetFVF(device,&fvf)) && (fvf&D3DFVF_POSITION_MASK)==D3DFVF_XYZ)runner_reference(device,vb,base,minimum,vertices,start,triangles,offset,&worldview);}
     }
     if(!owned && runner_wheel_draw(device,type,vertices,triangles,"DIP",NULL,0,(UINT)(base+minimum))){replaced=1;result=S_OK;}
     if(owned){
      DWORD color=0;IDirect3DDevice9_GetRenderState(device,D3DRS_COLORWRITEENABLE,&color);
      D3DMATRIX combined={0};int transform=entry?1:runner_fixed_combined(device,&combined);
      if(runner_log && runner_owned<=8){fprintf(runner_log,"OWNED frame=%u base=%d min=%u start=%u offset=%u stride=%u color=%lu shaderBytes=%u supported=%d\n",runner_frames,base,minimum,start,offset,stride,(unsigned long)color,entry?entry->bytes:0,entry?entry->supported:0);fflush(runner_log);}
      if(SUCCEEDED(shader_status) && transform && ((color&7)==7 || color==0)){UmaMotionState *pose=have_worldview?runner_actor_pose_model(&worldview,model):&runner_models[model].idle;float root[9];const float *correction=runner_actor_root_view(pose,have_worldview?&worldview:NULL,root)?root:NULL;
       if(runner_log && runner_frames%120==0 && have_worldview){
        float up[3]={0};for(int c=0;c<3;c++)for(int k=0;k<3;k++)up[c]+=(correction?correction[6+k]:(k==2?1.f:0.f))*worldview.m[k][c];
        fprintf(runner_log,"VISUAL frame=%u model=%u idleFallback=%d corrected=%d color=%lu upView=%.5f,%.5f,%.5f originView=%.5f,%.5f,%.5f\n",runner_frames,model,pose==&runner_models[model].idle,correction!=NULL,(unsigned long)color,up[0],up[1],up[2],worldview.m[3][0],worldview.m[3][1],worldview.m[3][2]);
       }
       runner_active_renderer->secondary=NULL;runner_active_renderer->secondary_revision=0;
       for(int i=0;i<16;i++)if(pose==&runner_actors[i].state && runner_actors[i].secondary.initialized){runner_active_renderer->secondary=runner_actors[i].secondary.rotation;runner_active_renderer->secondary_revision=runner_actors[i].secondary.revision;break;}
       runner_active_renderer->spark_draw=runner_original_primitive_up;
       result=uma_d3d_draw(runner_active_renderer,pose,&combined,0,correction);if(SUCCEEDED(result)){replaced=1;runner_replaced++;}else {runner_shader_failures++;if(runner_log && runner_shader_failures<=8){fprintf(runner_log,"DRAW_FAILURE hr=%08lx shaderBytes=%u supported=%d color=%lu base=%d min=%u start=%u stride=%u\n",(unsigned long)result,entry?entry->bytes:0,entry?entry->supported:0,(unsigned long)color,base,minimum,start,stride);fflush(runner_log);}}}
     }
    }
   }
   IDirect3DVertexBuffer9_Release(vb);
  }
 }
 RunnerHeadlightScope headlight={0};if(!replaced)runner_headlight_begin(device,&headlight);
 LeaveCriticalSection(&runner_lock);if(!replaced)result=runner_original_draw(device,type,base,minimum,vertices,start,triangles);
 if(headlight.active){HRESULT restored=IDirect3DDevice9_SetVertexShaderConstantF(device,(UINT)headlight.reg,headlight.saved,4);if(SUCCEEDED(result) && FAILED(restored))result=restored;}
 if(capture){EnterCriticalSection(&runner_lock);uma_selection_after(device,capture,"DIP",vertices,triangles);LeaveCriticalSection(&runner_lock);}return result;
}
static HRESULT WINAPI runner_present(IDirect3DDevice9 *device,const RECT *source,const RECT *destination,HWND window,const RGNDATA *dirty){
 EnterCriticalSection(&runner_lock);ULONGLONG tick=GetTickCount64();float seconds=runner_last_tick?(float)(tick-runner_last_tick)*.001f:0;runner_last_tick=tick;
 if(seconds>0 && seconds<=.25f)runner_frame_seconds=seconds;
 unsigned references=runner_scene.samples,bodies=runner_scene.bodies,groups=runner_scene.references,best_votes=0,second_votes=0;
 for(unsigned i=0;i<groups;i++){unsigned votes=runner_scene.reference[i].votes;if(votes>best_votes){second_votes=best_votes;best_votes=votes;}else if(votes>second_votes)second_votes=votes;}
 if(runner_log && runner_frames%120==119 && references && bodies && runner_camera_reports<12){
  runner_camera_reports++;fprintf(runner_log,"CAMERA frame=%u groups=%u best=%u second=%u inverseProjection=",runner_frames,groups,best_votes,second_votes);
  for(int i=0;i<4;i++)for(int j=0;j<4;j++)fprintf(runner_log,"%.6g,",runner_inverse_projection.m[i][j]);
  fputc('\n',runner_log);
  for(unsigned i=0;i<groups && i<4;i++){fprintf(runner_log,"REF votes=%u ",runner_scene.reference[i].votes);for(int r=0;r<4;r++)for(int c=0;c<3;c++)fprintf(runner_log,"%.6g,",runner_scene.reference[i].matrix.m[r][c]);fputc('\n',runner_log);}
  fprintf(runner_log,"BODY ");for(int r=0;r<4;r++)for(int c=0;c<3;c++)fprintf(runner_log,"%.6g,",runner_scene.body[0].m[r][c]);fputc('\n',runner_log);
 }
 uma_selection_finish(device,bodies);
 UmaMatrix actor_bodies[16];memcpy(actor_bodies,runner_scene.body,bodies*sizeof(*actor_bodies));
 unsigned actor_models[16];memcpy(actor_models,runner_scene.body_model,bodies*sizeof(*actor_models));
 UmaReference current_references[96];unsigned current_reference_count=runner_scene.references;memcpy(current_references,runner_scene.reference,current_reference_count*sizeof(*current_references));
 UmaMatrix camera_change;int camera_valid=runner_camera_change(&camera_change);
 runner_speed_valid=uma_scene_finish(&runner_scene,seconds,&runner_speed);
 runner_road_up_valid=runner_scene.anchor_valid && runner_reference_up(current_references,current_reference_count,&runner_scene.anchor,runner_road_up);
 float previous_phase=runner_state.run_phase;RunnerActor *primary=runner_actor_update_models(actor_bodies,actor_models,bodies,seconds,camera_valid?&camera_change:NULL);
 if(runner_scene.anchor_valid){runner_previous_anchor=runner_scene.anchor;runner_previous_reference_count=current_reference_count;memcpy(runner_previous_references,current_references,current_reference_count*sizeof(*current_references));}
 runner_speed_valid=primary!=NULL;runner_speed=primary?primary->speed:0;
 if(seconds>0 && seconds<=.25f){
  for(unsigned i=0;i<runner_model_count;i++){const UmaMotion *motion=&runner_models[i].motion;uma_motion_step_timed(&runner_models[i].idle,seconds,0,0,motion->idle_seconds,motion->run_seconds);}
  if(primary)runner_state=primary->state;else uma_motion_step(&runner_state,seconds,0,0);
  uma_audio_step(previous_phase,runner_state.run_phase,runner_state.run_blend,runner_speed_valid?runner_speed:0,seconds,runner_log);
 }
 runner_frames++;
 if(runner_log && runner_frames%120==0){
  fprintf(runner_log,"FRAME %u candidates=%u owned=%u replaced=%u shaderFailures=%u references=%u bodies=%u graphicsSpeedValid=%d graphicsSpeed=%.4f blend=%.4f projectionValid=%d recoveredSceneRefs=%u hiddenWheels=%u groups=%u best=%u second=%u hoofPlayed=%u audioActive=%d hiddenEffects=%u hiddenHeadlights=%u effectReads=%u effectCacheHits=%u\n",runner_frames,runner_candidates,runner_owned,runner_replaced,runner_shader_failures,references,bodies,runner_speed_valid,runner_speed,runner_state.run_blend,runner_projection_valid,runner_projected_references,runner_hidden_wheels,groups,best_votes,second_votes,uma_hoof_played,uma_audio_active,uma_effects_hidden,runner_hidden_headlights,uma_effect_reads,uma_effect_cache_hits);fflush(runner_log);
#ifdef UMA_PROFILE
  LARGE_INTEGER frequency;if(QueryPerformanceFrequency(&frequency) && frequency.QuadPart>0){
   double ms=1000.0/frequency.QuadPart;
   fprintf(runner_log,"PROFILE frame=%u draws=%u uploads=%u skinMs=%.3f uploadMs=%.3f drawMs=%.3f\n",runner_frames,uma_profile_draws,uma_profile_uploads,uma_profile_skin_ticks*ms,uma_profile_upload_ticks*ms,uma_profile_draw_ticks*ms);
  }
  uma_profile_draws=uma_profile_uploads=0;uma_profile_skin_ticks=uma_profile_upload_ticks=uma_profile_draw_ticks=0;
#endif
  for(unsigned m=0;m<runner_model_count;m++)if(runner_models[m].renderer.device)fprintf(runner_log,"SPARK model=%u draws=%u contacts=%u,%u blend=%.3f skinSamples=%u\n",m,runner_models[m].renderer.spark_draws,runner_models[m].renderer.spark_contacts[0],runner_models[m].renderer.spark_contacts[1],runner_models[m].renderer.uploaded.run_blend,runner_models[m].renderer.skin_samples);
  fprintf(runner_log,"ROAD_UP valid=%d local=%.5f,%.5f,%.5f\n",runner_road_up_valid,runner_road_up[0],runner_road_up[1],runner_road_up[2]);
  for(int i=0;i<16;i++)if(runner_actors[i].used && runner_frames-runner_actors[i].seen<=2)fprintf(runner_log,"ACTOR slot=%d model=%u speed=%.4f blend=%.4f position=%.4f,%.4f,%.4f\n",i,runner_actors[i].model,runner_actors[i].speed,runner_actors[i].state.run_blend,runner_actors[i].world.m[3][0],runner_actors[i].world.m[3][1],runner_actors[i].world.m[3][2]);
  if(ftell(runner_log)>2*1024*1024){fclose(runner_log);runner_log=NULL;}
 }
 LeaveCriticalSection(&runner_lock);return runner_original_present(device,source,destination,window,dirty);
}
static HRESULT WINAPI runner_reset(IDirect3DDevice9 *device,D3DPRESENT_PARAMETERS *parameters){
 EnterCriticalSection(&runner_lock);uma_selection_release();runner_close_renderers();memset(&runner_scene,0,sizeof(runner_scene));memset(runner_actors,0,sizeof(runner_actors));runner_state=(UmaMotionState){0};for(unsigned i=0;i<9;i++)runner_models[i].idle=(UmaMotionState){0};runner_last_tick=0;runner_projection_valid=0;runner_actor_world_valid=0;runner_tracking_gap=0;runner_road_up_valid=0;runner_previous_reference_count=0;LeaveCriticalSection(&runner_lock);
 return runner_original_reset(device,parameters);
}
static int runner_install(IDirect3DDevice9 *device){
 (void)uma_upload_is_character;
 if(runner_table)return 0;
 IDirect3DVertexBuffer9 *sample=NULL;HRESULT result=IDirect3DDevice9_CreateVertexBuffer(device,36,D3DUSAGE_DYNAMIC|D3DUSAGE_WRITEONLY,0,D3DPOOL_DEFAULT,&sample,NULL);if(FAILED(result))return 0;
 int observed=uma_upload_install(sample,runner_input_vertices(&runner_models[0]),runner_input_count(&runner_models[0])*36);IDirect3DVertexBuffer9_Release(sample);if(!observed)return 0;
 for(unsigned i=1;i<runner_model_count;i++)if(!uma_upload_add_model(runner_input_vertices(&runner_models[i]),runner_input_count(&runner_models[i])*36,i)){uma_upload_remove();return 0;}
 void **table=*(void***)device;DWORD protection;
 if(!VirtualProtect(table+16,(84-16+1)*sizeof(void*),PAGE_READWRITE,&protection)){uma_upload_remove();return 0;}
 runner_original_primitive=(RunnerPrimitive)table[81];runner_original_primitive_up=(RunnerPrimitiveUP)table[83];runner_original_indexed_up=(RunnerIndexedUP)table[84];runner_original_draw=(UmaDrawIndexed)table[82];runner_original_present=(RunnerPresent)table[17];runner_original_reset=(RunnerReset)table[16];runner_table=table;
 InterlockedExchangePointer(table+81,(void*)runner_primitive);InterlockedExchangePointer(table+83,(void*)runner_primitive_up);InterlockedExchangePointer(table+84,(void*)runner_indexed_up);InterlockedExchangePointer(table+82,(void*)runner_draw);InterlockedExchangePointer(table+17,(void*)runner_present);InterlockedExchangePointer(table+16,(void*)runner_reset);
 DWORD ignored;VirtualProtect(table+16,(84-16+1)*sizeof(void*),protection,&ignored);return 1;
}
/* Rotate full logs before opening so new sessions retain their diagnostic budget. */
static inline FILE *runner_open_log(const WCHAR *root){
 WCHAR path[4096],archive[4096];WIN32_FILE_ATTRIBUTE_DATA info;
 if(!root || wcslen(root)>3800)return NULL;
 swprintf(path,4096,L"%ls\\modding\\uma-runner.log",root);
 if(GetFileAttributesExW(path,GetFileExInfoStandard,&info) && (info.nFileSizeHigh || info.nFileSizeLow>=2*1024*1024)){
  swprintf(archive,4096,L"%ls\\modding\\uma-runner-%lu-%llu.log",root,(unsigned long)GetCurrentProcessId(),(unsigned long long)GetTickCount64());
  if(!MoveFileW(path,archive))return NULL;
 }
 return _wfopen(path,L"a");
}
#ifdef UMA_RUNNER_TEST
static int runner_remove(void){
 if(!runner_table)return 0;
 void **table=runner_table;DWORD protection;
 if(table[81]!=(void*)runner_primitive || table[83]!=(void*)runner_primitive_up || table[84]!=(void*)runner_indexed_up || table[82]!=(void*)runner_draw || table[17]!=(void*)runner_present || table[16]!=(void*)runner_reset || !VirtualProtect(table+16,(84-16+1)*sizeof(void*),PAGE_READWRITE,&protection))return 0;
 uma_audio_close();uma_selection_release();runner_close_renderers();InterlockedExchangePointer(table+81,(void*)runner_original_primitive);InterlockedExchangePointer(table+83,(void*)runner_original_primitive_up);InterlockedExchangePointer(table+84,(void*)runner_original_indexed_up);InterlockedExchangePointer(table+82,(void*)runner_original_draw);InterlockedExchangePointer(table+17,(void*)runner_original_present);InterlockedExchangePointer(table+16,(void*)runner_original_reset);
 DWORD ignored;VirtualProtect(table+16,(84-16+1)*sizeof(void*),protection,&ignored);runner_table=NULL;uma_effects_remove();return uma_upload_remove();
}
#else
static DWORD WINAPI runner_start(void *module){
 InitializeCriticalSection(&runner_lock);WCHAR root[4096],path[4096];DWORD length=GetModuleFileNameW((HMODULE)module,root,4096);if(!length || length>=4096)return 1;
 WCHAR *last=wcsrchr(root,L'\\');if(!last)return 1;*last=0;last=wcsrchr(root,L'\\');if(!last || _wcsicmp(last+1,L"scripts"))return 1;*last=0;if(wcslen(root)>3900)return 1;
 runner_log=runner_open_log(root);
 wcscpy(path,root);wcscat(path,L"\\modding\\selection-trace.request");
 if(GetFileAttributesW(path)!=INVALID_FILE_ATTRIBUTES){
  wcscpy(uma_selection.folder,root);wcscat(uma_selection.folder,L"\\modding\\diagnostics\\selection-capture");
  CreateDirectoryW(uma_selection.folder,NULL);
  swprintf(path,4096,L"%ls\\trace.log",uma_selection.folder);uma_selection.log=_wfopen(path,L"w");uma_selection.enabled=uma_selection.log!=NULL;
 }
 swprintf(path,4096,L"%ls\\modding\\runtime\\fleet.enabled",root);int fleet=GetFileAttributesW(path)!=INVALID_FILE_ATTRIBUTES;
 if(!runner_load_models(root,fleet)){if(runner_log){fprintf(runner_log,"MODEL_LOAD_FAILED fleet=%d\n",fleet);fflush(runner_log);}return 1;}
 HWND window=CreateWindowA("STATIC","Uma renderer initialization",WS_POPUP,0,0,16,16,NULL,NULL,GetModuleHandle(NULL),NULL);IDirect3D9 *api=Direct3DCreate9(D3D_SDK_VERSION);IDirect3DDevice9 *device=NULL;
 D3DPRESENT_PARAMETERS pp={0};pp.Windowed=TRUE;pp.SwapEffect=D3DSWAPEFFECT_DISCARD;pp.hDeviceWindow=window;pp.BackBufferWidth=16;pp.BackBufferHeight=16;pp.BackBufferFormat=D3DFMT_A8R8G8B8;
 HRESULT result=window && api?IDirect3D9_CreateDevice(api,0,D3DDEVTYPE_HAL,window,D3DCREATE_SOFTWARE_VERTEXPROCESSING,&pp,&device):E_FAIL;
 int textures_valid=SUCCEEDED(result);
 for(unsigned i=0;textures_valid && i<runner_model_count;i++){FILE *texture=_wfopen(runner_models[i].atlas,L"rb");IDirect3DTexture9 *decoded=NULL;textures_valid=texture && SUCCEEDED(uma_texture_load(device,texture,&decoded));if(texture)fclose(texture);if(decoded)IDirect3DTexture9_Release(decoded);}
 int installed=textures_valid && runner_install(device);
 if(installed){(void)uma_audio_start(root,runner_log);int effects=uma_effects_load(root);if(runner_log){fprintf(runner_log,"EFFECTS exact source textures ready=%d profiles=%u\n",effects,uma_effect_count);fflush(runner_log);}}
 if(runner_log){fprintf(runner_log,"START native lighting runner installed=%d; graphics-derived speed uncalibrated; independent actor gait, spatial association; models=%u\n",installed,runner_model_count);fflush(runner_log);}
 if(device){IDirect3DDevice9_Release(device);}if(api){IDirect3D9_Release(api);}if(window){DestroyWindow(window);}
 if(!installed){runner_free_models();}return installed?0:1;
}
BOOL WINAPI DllMain(HINSTANCE instance,DWORD reason,LPVOID reserved){(void)reserved;if(reason==DLL_PROCESS_ATTACH){DisableThreadLibraryCalls(instance);HANDLE thread=CreateThread(NULL,0,runner_start,instance,0,NULL);if(thread)CloseHandle(thread);}return TRUE;}
#endif
