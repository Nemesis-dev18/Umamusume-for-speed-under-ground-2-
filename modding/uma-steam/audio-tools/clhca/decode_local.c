#include "clhca.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <errno.h>
int main(int argc,char **argv){
 if(argc!=4)return 2;
 char *end=NULL;errno=0;unsigned long long key=strtoull(argv[2],&end,16);if(errno || !end || *end)return 2;
 FILE *input=fopen(argv[1],"rb");if(!input)return 3;
 if(fseek(input,0,SEEK_END))return 3;
 long length=ftell(input);rewind(input);if(length<8 || length>16000000)return 3;
 unsigned char *bytes=malloc((size_t)length);if(!bytes || fread(bytes,1,(size_t)length,input)!=(size_t)length)return 3;fclose(input);
 int header=clHCA_isOurFile(bytes,(unsigned)length);if(header<8 || header>length)return 4;
 clHCA *decoder=clHCA_new();if(!decoder)return 4;clHCA_SetKey(decoder,key);
 if(clHCA_DecodeHeader(decoder,bytes,(unsigned)header)<0)return 4;
 clHCA_stInfo info;if(clHCA_getInfo(decoder,&info)<0 || !info.channelCount || info.channelCount>8 || info.samplesPerBlock!=1024 || info.samplingRate<8000 || info.samplingRate>192000 || !info.blockSize || (uint64_t)info.headerSize+(uint64_t)info.blockCount*info.blockSize>(uint64_t)length)return 4;
 uint64_t total=(uint64_t)info.blockCount*1024;if((uint64_t)info.encoderDelay+info.encoderPadding>=total)return 4;
 unsigned checked=0;for(unsigned b=0;b<info.blockCount && b<16;b++){
  unsigned char *copy=malloc(info.blockSize);if(!copy)return 4;memcpy(copy,bytes+info.headerSize+b*info.blockSize,info.blockSize);int score=clHCA_TestBlock(decoder,copy,info.blockSize);free(copy);if(score<0)return 5;if(score>0)checked++;
 }
 if(info.encryptionEnabled && !checked)return 5;
 clHCA_DecodeReset(decoder);
 FILE *output=fopen(argv[3],"wb");if(!output)return 6;short samples[1024*8];uint64_t written=0;
 for(unsigned b=0;b<info.blockCount;b++){
  if(clHCA_DecodeBlock(decoder,bytes+info.headerSize+b*info.blockSize,info.blockSize)<0)return 7;
  clHCA_ReadSamples16(decoder,samples);
  uint64_t begin=(uint64_t)b*1024,low=begin<info.encoderDelay?info.encoderDelay-begin:0,high=1024;
  if(begin>=total-info.encoderPadding)high=0;else if(begin+high>total-info.encoderPadding)high=total-info.encoderPadding-begin;
  if(high>low && low<1024){size_t count=(size_t)(high-low)*info.channelCount;if(fwrite(samples+low*info.channelCount,2,count,output)!=count)return 6;written+=high-low;}
 }
 fclose(output);free(bytes);clHCA_delete(decoder);printf("{\"rate\":%u,\"channels\":%u,\"frames\":%llu,\"key_validation_blocks\":%u}\n",info.samplingRate,info.channelCount,(unsigned long long)written,checked);return 0;
}
