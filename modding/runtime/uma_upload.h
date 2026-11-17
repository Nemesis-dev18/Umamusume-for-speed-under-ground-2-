#ifndef UMA_UPLOAD_H
#define UMA_UPLOAD_H
#define COBJMACROS
#include <windows.h>
#include <d3d9.h>
#include <string.h>
#include "uma_vertex_bounds.h"
/* Observe CPU uploads, never read back a WRITEONLY GPU buffer. */
typedef HRESULT (WINAPI *UmaVertexLock)(IDirect3DVertexBuffer9*,UINT,UINT,void**,DWORD);
typedef HRESULT (WINAPI *UmaVertexUnlock)(IDirect3DVertexBuffer9*);
static const GUID uma_pending_guid={0x6c2a3341,0x3f91,0x4fe7,{0xa0,0xd1,0x32,0xb4,0x71,0xc2,0xe8,0x16}};
static const GUID uma_identity_guid={0xd79bb88d,0x7a42,0x4d21,{0xa2,0x03,0x54,0x37,0x99,0xcd,0x0f,0xe1}};
static UmaVertexLock uma_native_lock;
static UmaVertexUnlock uma_native_unlock;
static void **uma_upload_table;
typedef struct {const void *expected;UINT bytes,model;} UmaUploadModel;
static UmaUploadModel uma_upload_models[8];
static UINT uma_upload_model_count;
typedef struct {void *pointer;UINT bytes,offset,depth;BOOL whole;} UmaPendingUpload;
/* Retain only bounded CPU upload bytes; decode the actual declaration/range at draw time. */
typedef struct {UINT offset,bytes;BYTE data[131072];} UmaUploadSnapshot;
static const GUID uma_bounds_guid={0x0fd3a417,0x882b,0x45a9,{0xaf,0x28,0x41,0x3e,0x3f,0xd2,0xe8,0x56}};
static inline int uma_upload_bounds(IDirect3DVertexBuffer9 *buffer,UINT offset,UINT vertices,UINT stride,UINT position,UmaVertexBounds *output){
 UmaUploadSnapshot snapshot;DWORD size=sizeof(snapshot);
 if(!buffer || FAILED(IDirect3DVertexBuffer9_GetPrivateData(buffer,&uma_bounds_guid,&snapshot,&size)) || size<8 || snapshot.bytes>sizeof(snapshot.data) || size!=8+snapshot.bytes || offset<snapshot.offset || offset-snapshot.offset>snapshot.bytes)return 0;
 UINT first=offset-snapshot.offset;return uma_vertex_bounds(snapshot.data+first,snapshot.bytes-first,vertices,stride,position,output);
}
typedef struct {UINT count,offsets[16],models[16];} UmaUploadIdentity;
static BOOL uma_upload_model_at(IDirect3DVertexBuffer9 *buffer,UINT offset,UINT *model){
 UmaUploadIdentity identity={0};DWORD size=sizeof(identity);
 if(!buffer || FAILED(IDirect3DVertexBuffer9_GetPrivateData(buffer,&uma_identity_guid,&identity,&size)) || size!=sizeof(identity) || identity.count>16)return FALSE;
 for(UINT i=0;i<identity.count;i++)if(identity.offsets[i]==offset){if(model)*model=identity.models[i];return TRUE;}
 return FALSE;
}
static BOOL uma_upload_matches_at(IDirect3DVertexBuffer9 *buffer,UINT offset){return uma_upload_model_at(buffer,offset,NULL);}
static BOOL uma_upload_is_character(IDirect3DVertexBuffer9 *buffer){return uma_upload_matches_at(buffer,0);}
static HRESULT WINAPI uma_observe_lock(IDirect3DVertexBuffer9 *buffer,UINT offset,UINT bytes,void **data,DWORD flags){
 HRESULT result=uma_native_lock(buffer,offset,bytes,data,flags);if(FAILED(result))return result;
 UmaPendingUpload pending={0};DWORD pending_bytes=sizeof(pending);
 BOOL nested=SUCCEEDED(IDirect3DVertexBuffer9_GetPrivateData(buffer,&uma_pending_guid,&pending,&pending_bytes)) && pending_bytes==sizeof(pending);
 if(!(flags&D3DLOCK_READONLY)){IDirect3DVertexBuffer9_FreePrivateData(buffer,&uma_identity_guid);IDirect3DVertexBuffer9_FreePrivateData(buffer,&uma_bounds_guid);}
 if(nested){
  pending.pointer=NULL;pending.depth++;
  IDirect3DVertexBuffer9_SetPrivateData(buffer,&uma_pending_guid,&pending,sizeof(pending),0);return result;
 }
 D3DVERTEXBUFFER_DESC descriptor;
 if(SUCCEEDED(IDirect3DVertexBuffer9_GetDesc(buffer,&descriptor)) && descriptor.Size<=16*1024*1024 && offset<=descriptor.Size && (!bytes || bytes<=descriptor.Size-offset)){
  pending.pointer=(!(flags&D3DLOCK_READONLY) && data && *data)?*data:NULL;
  pending.bytes=bytes?bytes:descriptor.Size-offset;pending.offset=offset;pending.depth=1;pending.whole=offset==0 && pending.bytes==descriptor.Size;
  IDirect3DVertexBuffer9_SetPrivateData(buffer,&uma_pending_guid,&pending,sizeof(pending),0);
 }
 return result;
}
static int uma_upload_geometry_equal(const void *mapped,const UmaUploadModel *profile){
 const BYTE *actual=mapped,*expected=profile->expected;
 if(!memcmp(actual,expected,profile->bytes))return 1;
 /* Runtime paint/color updates do not change the identity of the mesh. */
 for(UINT at=0;at<profile->bytes;at+=36)if(memcmp(actual+at,expected+at,24) || memcmp(actual+at+28,expected+at+28,8))return 0;
 return 1;
}
/* Register before uploads; all borrowed profile bytes must remain alive until removal. */
static inline BOOL uma_upload_add_model(const void *expected,UINT bytes,UINT model){
 if(!uma_upload_table || !expected || !bytes || bytes%36 || bytes>4*1024*1024 || uma_upload_model_count>=8)return FALSE;
 UmaUploadModel profile={expected,bytes,model};
 for(UINT i=0;i<uma_upload_model_count;i++)if(uma_upload_models[i].model==model || (uma_upload_models[i].bytes==bytes && uma_upload_geometry_equal(uma_upload_models[i].expected,&profile)))return FALSE;
 uma_upload_models[uma_upload_model_count++]=profile;return TRUE;
}
static HRESULT WINAPI uma_observe_unlock(IDirect3DVertexBuffer9 *buffer){
 UmaPendingUpload pending={0};DWORD bytes=sizeof(pending);
 BOOL tracked=SUCCEEDED(IDirect3DVertexBuffer9_GetPrivateData(buffer,&uma_pending_guid,&pending,&bytes)) && bytes==sizeof(pending);
 UmaUploadIdentity identity={0};UmaUploadSnapshot snapshot;snapshot.bytes=0;
 if(tracked && pending.depth==1 && pending.pointer && pending.bytes>=12 && pending.bytes<=sizeof(snapshot.data)){
  snapshot.offset=pending.offset;snapshot.bytes=pending.bytes;memcpy(snapshot.data,pending.pointer,pending.bytes);
 }
 int shared=uma_upload_model_count>1;for(UINT p=1;shared && p<uma_upload_model_count;p++)if(uma_upload_models[p].bytes!=uma_upload_models[0].bytes || memcmp(uma_upload_models[p].expected,uma_upload_models[0].expected,24))shared=0;
 if(tracked && pending.depth==1 && pending.pointer && shared && pending.bytes>=uma_upload_models[0].bytes){
  const BYTE *mapped=pending.pointer,*prefix=uma_upload_models[0].expected;UINT length=uma_upload_models[0].bytes;
  /* Fleet carriers share position/normal prefix; scan the upload once, then resolve its model. */
  for(UINT at=0;at<=pending.bytes-length && identity.count<16;at+=4){
   if(memcmp(mapped+at,prefix,24))continue;
   for(UINT p=0;p<uma_upload_model_count;p++){
    const UmaUploadModel *profile=&uma_upload_models[p];const BYTE *expected=profile->expected;
    if(!memcmp(mapped+at+28,expected+28,8) && uma_upload_geometry_equal(mapped+at,profile)){
     identity.offsets[identity.count]=pending.offset+at;identity.models[identity.count++]=profile->model;at+=length-4;break;
    }
   }
  }
 }
 if(tracked && pending.depth==1 && pending.pointer && !shared)for(UINT p=0;p<uma_upload_model_count;p++){
  const UmaUploadModel *profile=&uma_upload_models[p];const BYTE *mapped=pending.pointer,*expected=profile->expected;
  if(pending.bytes<profile->bytes)continue;
  for(UINT at=0;at<=pending.bytes-profile->bytes && identity.count<16;at+=4){
   if(!memcmp(mapped+at,expected,24) && !memcmp(mapped+at+28,expected+28,8) && uma_upload_geometry_equal(mapped+at,profile)){
    identity.offsets[identity.count]=pending.offset+at;identity.models[identity.count++]=profile->model;at+=profile->bytes-4;
   }
  }
 }
 if(tracked && pending.depth>1){pending.depth--;pending.pointer=NULL;IDirect3DVertexBuffer9_SetPrivateData(buffer,&uma_pending_guid,&pending,sizeof(pending),0);}
 else IDirect3DVertexBuffer9_FreePrivateData(buffer,&uma_pending_guid);
 HRESULT result=uma_native_unlock(buffer);
 if(SUCCEEDED(result) && snapshot.bytes)IDirect3DVertexBuffer9_SetPrivateData(buffer,&uma_bounds_guid,&snapshot,8+snapshot.bytes,0);
 if(SUCCEEDED(result) && identity.count)IDirect3DVertexBuffer9_SetPrivateData(buffer,&uma_identity_guid,&identity,sizeof(identity),0);
 return result;
}
/* Install only before uploads; expected bytes must remain alive until removal. */
static BOOL uma_upload_install(IDirect3DVertexBuffer9 *sample,const void *expected,UINT bytes){
 if(uma_upload_table || !sample || !expected || !bytes || bytes%36 || bytes>4*1024*1024)return FALSE;
 void **table=*(void***)sample;DWORD protection;
 if(!VirtualProtect(table+11,2*sizeof(void*),PAGE_READWRITE,&protection))return FALSE;
 uma_native_lock=(UmaVertexLock)table[11];uma_native_unlock=(UmaVertexUnlock)table[12];
 uma_upload_table=table;uma_upload_models[0]=(UmaUploadModel){expected,bytes,0};uma_upload_model_count=1;
 InterlockedExchangePointer(table+11,(void*)uma_observe_lock);InterlockedExchangePointer(table+12,(void*)uma_observe_unlock);
 DWORD ignored;VirtualProtect(table+11,2*sizeof(void*),protection,&ignored);return TRUE;
}
/* Caller must stop uploads and release/clear observed buffers before removal. */
static BOOL uma_upload_remove(void){
 if(!uma_upload_table)return FALSE;
 void **table=uma_upload_table;DWORD protection;
 if(table[11]!=(void*)uma_observe_lock || table[12]!=(void*)uma_observe_unlock || !VirtualProtect(table+11,2*sizeof(void*),PAGE_READWRITE,&protection))return FALSE;
 InterlockedExchangePointer(table+11,(void*)uma_native_lock);InterlockedExchangePointer(table+12,(void*)uma_native_unlock);
 DWORD ignored;VirtualProtect(table+11,2*sizeof(void*),protection,&ignored);
 uma_upload_table=NULL;memset(uma_upload_models,0,sizeof(uma_upload_models));uma_upload_model_count=0;return TRUE;
}
#endif
