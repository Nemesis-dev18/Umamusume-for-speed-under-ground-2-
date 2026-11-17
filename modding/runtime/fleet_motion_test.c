#include "uma_motion.h"
#include <assert.h>
static void reject_durations(const char *path){
 FILE *f=fopen(path,"rb");assert(f);assert(!fseek(f,0,SEEK_END));long size=ftell(f);assert(size>40);rewind(f);unsigned char *bytes=malloc((size_t)size);assert(bytes);assert(fread(bytes,1,(size_t)size,f)==(size_t)size);fclose(f);unsigned char original[8];memcpy(original,bytes+32,8);
 for(int kind=0;kind<5;kind++){
  memcpy(bytes+32,original,8);float value=kind==1?NAN:(kind==2?61:0);if(kind==4)value=INFINITY;memcpy(bytes+(kind>=3?36:32),&value,4);
  f=tmpfile();assert(f);assert(fwrite(bytes,1,(size_t)size,f)==(size_t)size);rewind(f);UmaMotion rejected={0};rejected.vertices=33;UmaMotion before=rejected;assert(!uma_motion_load(f,&rejected));assert(!memcmp(&before,&rejected,sizeof(before)));fclose(f);
 }
 free(bytes);
}
int main(int argc,char **argv){
 assert(argc==3);FILE *f=fopen(argv[1],"rb");assert(f);UmaMotion asset={0};assert(uma_motion_load(f,&asset));fclose(f);
 reject_durations(argv[1]);
 UmaMotionState state={0};for(int n=0;n<4;n++)assert(uma_motion_step_timed(&state,.25f,6,0,asset.idle_seconds,asset.run_seconds));
 assert(fabsf(state.idle_phase-uma_fraction(1.f/asset.idle_seconds))<1e-5f);assert(fabsf(state.run_phase-uma_fraction(1.f/asset.run_seconds))<1e-5f);
 UmaMotionState before=state;assert(!uma_motion_step_timed(&state,.1f,6,0,NAN,.6f));assert(!memcmp(&before,&state,sizeof(state)));
 FILE *reference=fopen(argv[2],"rb");assert(reference);uint32_t vertices,cases;
 assert(fread(&vertices,4,1,reference)==1 && vertices==asset.vertices);assert(fread(&cases,4,1,reference)==1 && cases>=6);
 UmaVertex *output=malloc((size_t)vertices*36);float *expected=malloc((size_t)vertices*24);assert(output && expected);float max_error=0;
 for(uint32_t c=0;c<cases;c++){
  float phase[3];assert(fread(phase,4,3,reference)==3);assert(fread(expected,24,vertices,reference)==vertices);
  assert(uma_motion_sample(&asset,phase[0],phase[1],phase[2],output,(size_t)vertices*36));
  for(uint32_t i=0;i<vertices;i++)for(int k=0;k<6;k++){
   float value=k<3?output[i].position[k]:output[i].normal[k-3],error=fabsf(value-expected[i*6+k]);
   if(error>max_error)max_error=error;
   if(!isfinite(value) || !isfinite(expected[i*6+k]) || error>7e-5f){fprintf(stderr,"case=%u vertex=%u component=%d got=%g expected=%g error=%g\n",c,i,k,value,expected[i*6+k],error);return 1;}
  }
 }
 assert(fgetc(reference)==EOF);fclose(reference);free(expected);free(output);uma_motion_free(&asset);printf("maximum_skin_error=%g\n",max_error);return 0;
}
