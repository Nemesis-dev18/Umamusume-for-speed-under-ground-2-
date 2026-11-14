#ifndef UMA_HOOF_SCHEDULE_H
#define UMA_HOOF_SCHEDULE_H
#include <math.h>
static inline unsigned uma_hoof_schedule(float previous,float next,float blend,float speed,float seconds){
 if(!isfinite(previous) || !isfinite(next) || !isfinite(blend) || !isfinite(speed) || !isfinite(seconds) || previous<0 || previous>=1 || next<0 || next>=1 || blend<.7f || fabsf(speed)<.7f || seconds<=0 || seconds>.1f)return 0;
 float distance=speed<0?previous-next:next-previous;if(distance<0)distance+=1;if(distance>.25f)return 0;
 unsigned events=0;for(unsigned foot=0;foot<2;foot++){
  float contact=1.f/30+foot*.5f,delta=speed<0?previous-contact:contact-previous;if(delta<0)delta+=1;
  if(delta>0 && delta<=distance)events|=1u<<foot;
 }
 return events;
}
#endif
