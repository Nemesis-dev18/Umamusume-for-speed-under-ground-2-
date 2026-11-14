#include "uma_motion.h"
#include <assert.h>
#include <time.h>
static void reject(const unsigned char *bytes,size_t count){
 const char *path="modding/runtime/test-build/malformed-motion.tmp";
 FILE *f=fopen(path,"w+b");assert(f);assert(fwrite(bytes,1,count,f)==count);rewind(f);
 UmaMotion a={0};a.vertices=17;UmaMotion before=a;assert(!uma_motion_load(f,&a));assert(!memcmp(&a,&before,sizeof(a)));
 fclose(f);assert(remove(path)==0);
}
int main(void){
 FILE *f=fopen("modding/runtime/kitasan.umab","rb");assert(f);UmaMotion a={0};assert(uma_motion_load(f,&a));fclose(f);
 assert(a.vertices==14512 && a.bones==282 && a.idle_frames==32 && a.run_frames==48);
 size_t bytes=(size_t)a.vertices*36;UmaVertex *out=malloc(bytes);assert(out);memset(out,0xa5,bytes);
 assert(!uma_motion_sample(&a,0,0,0,out,bytes-1));for(size_t i=0;i<bytes;i++)assert(((unsigned char*)out)[i]==0xa5);
 assert(!uma_motion_sample(&a,NAN,0,0,out,bytes));assert(!uma_motion_sample(&a,0,0,2,out,bytes));assert(!uma_motion_sample(&a,0,0,0,a.rest,bytes));
 FILE *reference=fopen("modding/runtime/test-build/reference.bin","rb");assert(reference);uint32_t cases=0;assert(fread(&cases,4,1,reference)==1);assert(cases==6);
 float *expected=malloc((size_t)a.vertices*24);assert(expected);float max_error=0;
 for(uint32_t sample=0;sample<cases;sample++){
  float parameters[3];assert(fread(parameters,4,3,reference)==3);assert(fread(expected,24,a.vertices,reference)==a.vertices);
  assert(uma_motion_sample(&a,parameters[0],parameters[1],parameters[2],out,bytes));
  for(uint32_t i=0;i<a.vertices;i++){
   for(int k=0;k<6;k++){
    float value=k<3?out[i].position[k]:out[i].normal[k-3];float error=fabsf(value-expected[i*6+k]);if(error>max_error)max_error=error;assert(error<3e-5f);assert(isfinite(value));
   }
   assert(!memcmp((unsigned char*)&out[i]+24,(unsigned char*)&a.rest[i]+24,12));
   float n=0;for(int k=0;k<3;k++)n+=out[i].normal[k]*out[i].normal[k];assert(fabsf(n-1)<1e-5f);
  }
 }
 assert(fgetc(reference)==EOF);fclose(reference);free(expected);
 UmaMotionState state={0};
 for(int i=0;i<60;i++)assert(uma_motion_step(&state,1.f/60,6,0));
 assert(state.run_blend>.99f);
 UmaMotionState paused=state;assert(uma_motion_step(&state,.1f,6,1));assert(!memcmp(&paused,&state,sizeof(state)));
 for(int i=0;i<120;i++)assert(uma_motion_step(&state,1.f/60,0,0));
 assert(state.run_blend<1e-4f);
 paused=state;assert(!uma_motion_step(&state,NAN,0,0));assert(!memcmp(&paused,&state,sizeof(state)));
 UmaMotionState at30={0},at60={0};
 for(int i=0;i<30;i++)assert(uma_motion_step(&at30,1.f/30,6,0));
 for(int i=0;i<60;i++)assert(uma_motion_step(&at60,1.f/60,6,0));
 assert(fabsf(at30.run_blend-at60.run_blend)<1e-5f);assert(fabsf(at30.run_phase-at60.run_phase)<1e-4f);
 float floor_min=0;
 for(int level=0;level<5;level++)for(int frame=0;frame<48;frame++){
  assert(uma_motion_sample(&a,frame/160.f,frame/48.f,level/4.f,out,bytes));
  for(uint32_t i=0;i<a.vertices;i++){if(out[i].position[2]<floor_min)floor_min=out[i].position[2];assert(out[i].position[2]>=-.000101f);}
 }
 clock_t begin=clock();
 for(int i=0;i<100;i++){assert(uma_motion_step(&state,1.f/60,6,0));assert(uma_motion_sample(&a,state.idle_phase,state.run_phase,state.run_blend,out,bytes));}
 double sample_ms=(double)(clock()-begin)*1000/CLOCKS_PER_SEC/100;
 f=fopen("modding/runtime/kitasan.umab","rb");assert(f);size_t length=a.memory_bytes+32;unsigned char *original=malloc(length+1),*bad=malloc(length+1);assert(original && bad);assert(fread(original,1,length,f)==length);fclose(f);
 reject(original,31);reject(original,40);
 memcpy(bad,original,length);bad[4]=3;reject(bad,length);
 memcpy(bad,original,length);memset(bad+8,0,4);reject(bad,length);
 memcpy(bad,original,length);uint16_t invalid_bone=65535;memcpy(bad+32+(size_t)a.vertices*36,&invalid_bone,2);reject(bad,length);
 memcpy(bad,original,length);float invalid_weight=-1;memcpy(bad+32+(size_t)a.vertices*36+8,&invalid_weight,4);reject(bad,length);
 memcpy(bad,original,length);uint16_t invalid_index=(uint16_t)a.vertices;memcpy(bad+32+(size_t)a.vertices*60+(size_t)a.bones*16,&invalid_index,2);reject(bad,length);
 memcpy(bad,original,length);size_t first_matrix=(size_t)((unsigned char*)a.idle-a.memory)+32;float invalid_matrix=NAN;memcpy(bad+first_matrix,&invalid_matrix,4);reject(bad,length);
 memcpy(bad,original,length);bad[length]=0;reject(bad,length+1);
 printf("PASS: six Python-reference poses, max error %.9g; UV/colour preservation; transitions, pause, invalid inputs, alias rejection and nine malformed packages. 240 grounded transition poses; CPU sample %.3f ms (standalone, not game FPS).\n",max_error,sample_ms);
 free(original);free(bad);free(out);uma_motion_free(&a);return 0;
}
