#ifndef UMA_CAMERA_H
#define UMA_CAMERA_H
#define COBJMACROS
#include <windows.h>
#include <d3d9.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
#include "uma_shader_profiles.h"
/* shortcut: accepts only a direct v0-to-oPos matrix shader; extend from captured shader evidence. */
static int uma_camera_constant(const DWORD *code,size_t count,UINT *base){
 if(!code || !base || count<2 || (code[0]!=0xfffe0101 && code[0]!=0xfffe0200))return 0;
 BOOL version2=code[0]==0xfffe0200;UINT matrix=0;int found=0;
 for(size_t at=1;at<count;){
  DWORD instruction=code[at++],op=instruction&0xffff;size_t length;
  if(op==D3DSIO_END){if(instruction!=0xffff || at!=count || !found)return 0;*base=matrix;return 1;}
  if(op==D3DSIO_COMMENT){size_t n=(instruction>>16)&0x7fff;if(n>count-at)return 0;at+=n;continue;}
  if(op==D3DSIO_MOV)length=2;
  else if(op==D3DSIO_M4x4)length=3;
  else if(version2 && op==D3DSIO_DCL)length=2;
  else return 0;
  if(instruction!=(op | (version2?(DWORD)length<<24:0)) || length>count-at)return 0;
  DWORD destination=code[at];
  if(op==D3DSIO_DCL){
   /* Only a declaration of an input register can be ignored. */
   if((code[at+1]&0xfffff800)!=0x900f0000 || (code[at+1]&0x7ff)>15)return 0;
  }else if(op==D3DSIO_M4x4){
   if(found || destination!=0xc00f0000 || code[at+1]!=0x90e40000 || (code[at+2]&0xfffff800)!=0xa0e40000 || (code[at+2]&0x7ff)>252)return 0;
   matrix=code[at+2]&0x7ff;found=1;
  }else{
   DWORD reg=destination&0x7ff,type=destination&0xf0001800,source=code[at+1];
   if(!(destination&0xf0000) || (destination&0x0ff0e000) || !((type==0xe0000000 && reg<8) || (type==0xd0000000 && reg<2)))return 0;
   if((source&0xfffff800)!=0x90e40000 && (source&0xfffff800)!=0xa0e40000)return 0;
   if((source&0x7ff)>((source&0xf0000000)==0x90000000?15u:255u))return 0;
  }
  at+=length;
 }
 return 0;
}
static int uma_camera_finite(const D3DMATRIX *matrix){
 for(int row=0;row<4;row++)for(int col=0;col<4;col++)if(!isfinite(matrix->m[row][col]))return 0;
 return 1;
}
static HRESULT uma_camera_capture(IDirect3DDevice9 *device,D3DMATRIX *output){
 if(!device || !output)return E_INVALIDARG;
 IDirect3DVertexShader9 *shader=NULL;HRESULT result=IDirect3DDevice9_GetVertexShader(device,&shader);if(FAILED(result))return result;
 D3DMATRIX combined={0};
 if(shader){
  UINT bytes=0;DWORD *code=NULL;UINT base=0;
  result=IDirect3DVertexShader9_GetFunction(shader,NULL,&bytes);
  if(FAILED(result) || bytes<8 || bytes>65536 || bytes%4){IDirect3DVertexShader9_Release(shader);return E_FAIL;}
  code=malloc(bytes);if(!code){IDirect3DVertexShader9_Release(shader);return E_OUTOFMEMORY;}
  result=IDirect3DVertexShader9_GetFunction(shader,code,&bytes);IDirect3DVertexShader9_Release(shader);
  const UmaShaderProfile *profile=NULL;
  if(SUCCEEDED(result))for(UINT i=0;i<UMA_SHADER_PROFILE_COUNT;i++)if(bytes==uma_shader_profiles[i].bytes && !memcmp(code,uma_shader_profiles[i].words,bytes)){profile=&uma_shader_profiles[i];break;}
  int supported=profile || (SUCCEEDED(result) && uma_camera_constant(code,bytes/4,&base));free(code);if(!supported)return E_FAIL;
  float constants[4][4];
  if(profile){for(UINT i=0;i<4;i++){result=IDirect3DDevice9_GetVertexShaderConstantF(device,profile->rows[i],constants[i],1);if(FAILED(result))return result;for(UINT k=0;k<4;k++)constants[i][k]*=profile->signs[i];}}
  else{result=IDirect3DDevice9_GetVertexShaderConstantF(device,base,&constants[0][0],4);if(FAILED(result))return result;}
  for(int row=0;row<4;row++)for(int col=0;col<4;col++)combined.m[row][col]=constants[col][row];
 }else{
  D3DMATRIX world,view,projection,temp={0};
  result=IDirect3DDevice9_GetTransform(device,D3DTS_WORLD,&world);if(FAILED(result))return result;
  result=IDirect3DDevice9_GetTransform(device,D3DTS_VIEW,&view);if(FAILED(result))return result;
  result=IDirect3DDevice9_GetTransform(device,D3DTS_PROJECTION,&projection);if(FAILED(result))return result;
  for(int r=0;r<4;r++)for(int c=0;c<4;c++)for(int k=0;k<4;k++)temp.m[r][c]+=world.m[r][k]*view.m[k][c];
  for(int r=0;r<4;r++)for(int c=0;c<4;c++)for(int k=0;k<4;k++)combined.m[r][c]+=temp.m[r][k]*projection.m[k][c];
 }
 if(!uma_camera_finite(&combined))return E_FAIL;
 *output=combined;return S_OK;
}
#endif
