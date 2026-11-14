#ifndef UMA_UPLOAD_H
#define UMA_UPLOAD_H
#define COBJMACROS
#include <windows.h>
#include <d3d9.h>
#include <string.h>
/* Observe CPU uploads, never read back a WRITEONLY GPU buffer. */
typedef HRESULT (WINAPI *UmaVertexLock)(IDirect3DVertexBuffer9*,UINT,UINT,void**,DWORD);
typedef HRESULT (WINAPI *UmaVertexUnlock)(IDirect3DVertexBuffer9*);
static const GUID uma_pending_guid={0x6c2a3341,0x3f91,0x4fe7,{0xa0,0xd1,0x32,0xb4,0x71,0xc2,0xe8,0x16}};
static const GUID uma_identity_guid={0xd79bb88d,0x7a42,0x4d21,{0xa2,0x03,0x54,0x37,0x99,0xcd,0x0f,0xe1}};
static UmaVertexLock uma_native_lock;
static UmaVertexUnlock uma_native_unlock;
static void **uma_upload_table;
static const void *uma_upload_expected;
static UINT uma_upload_bytes;
typedef struct {void *pointer;UINT bytes,offset,depth;} UmaPendingUpload;
typedef struct {UINT count,offsets[16];} UmaUploadIdentity;
static BOOL uma_upload_matches_at(IDirect3DVertexBuffer9 *buffer,UINT offset){
 UmaUploadIdentity identity={0};DWORD size=sizeof(identity);
 if(!buffer || FAILED(IDirect3DVertexBuffer9_GetPrivateData(buffer,&uma_identity_guid,&identity,&size)) || size!=sizeof(identity) || identity.count>16)return FALSE;
 for(UINT i=0;i<identity.count;i++)if(identity.offsets[i]==offset)return TRUE;
 return FALSE;
}
static BOOL uma_upload_is_character(IDirect3DVertexBuffer9 *buffer){return uma_upload_matches_at(buffer,0);}
static HRESULT WINAPI uma_observe_lock(IDirect3DVertexBuffer9 *buffer,UINT offset,UINT bytes,void **data,DWORD flags){
 HRESULT result=uma_native_lock(buffer,offset,bytes,data,flags);if(FAILED(result))return result;
 UmaPendingUpload pending={0};DWORD pending_bytes=sizeof(pending);
 BOOL nested=SUCCEEDED(IDirect3DVertexBuffer9_GetPrivateData(buffer,&uma_pending_guid,&pending,&pending_bytes)) && pending_bytes==sizeof(pending);
 if(!(flags&D3DLOCK_READONLY))IDirect3DVertexBuffer9_FreePrivateData(buffer,&uma_identity_guid);
 if(nested){
  pending.pointer=NULL;pending.depth++;
  IDirect3DVertexBuffer9_SetPrivateData(buffer,&uma_pending_guid,&pending,sizeof(pending),0);return result;
 }
 D3DVERTEXBUFFER_DESC descriptor;
 if(SUCCEEDED(IDirect3DVertexBuffer9_GetDesc(buffer,&descriptor)) && descriptor.Size<=16*1024*1024 && offset<=descriptor.Size && (!bytes || bytes<=descriptor.Size-offset)){
  pending.pointer=(!(flags&D3DLOCK_READONLY) && data && *data)?*data:NULL;
  pending.bytes=bytes?bytes:descriptor.Size-offset;pending.offset=offset;pending.depth=1;
  IDirect3DVertexBuffer9_SetPrivateData(buffer,&uma_pending_guid,&pending,sizeof(pending),0);
 }
 return result;
}
static int uma_upload_geometry_equal(const void *mapped){
 const BYTE *actual=mapped,*expected=uma_upload_expected;
 if(!memcmp(actual,expected,uma_upload_bytes))return 1;
 /* Runtime paint/color updates do not change the identity of the mesh. */
 for(UINT at=0;at<uma_upload_bytes;at+=36)if(memcmp(actual+at,expected+at,24) || memcmp(actual+at+28,expected+at+28,8))return 0;
 return 1;
}
static HRESULT WINAPI uma_observe_unlock(IDirect3DVertexBuffer9 *buffer){
 UmaPendingUpload pending={0};DWORD bytes=sizeof(pending);
 BOOL tracked=SUCCEEDED(IDirect3DVertexBuffer9_GetPrivateData(buffer,&uma_pending_guid,&pending,&bytes)) && bytes==sizeof(pending);
 UmaUploadIdentity identity={0};
 if(tracked && pending.depth==1 && pending.pointer && pending.bytes>=uma_upload_bytes){
  const BYTE *mapped=pending.pointer,*expected=uma_upload_expected;
  for(UINT at=0;at<=pending.bytes-uma_upload_bytes && identity.count<16;at+=4){
   if(!memcmp(mapped+at,expected,24) && !memcmp(mapped+at+28,expected+28,8) && uma_upload_geometry_equal(mapped+at)){
    identity.offsets[identity.count++]=pending.offset+at;at+=uma_upload_bytes-4;
   }
  }
 }
 if(tracked && pending.depth>1){pending.depth--;pending.pointer=NULL;IDirect3DVertexBuffer9_SetPrivateData(buffer,&uma_pending_guid,&pending,sizeof(pending),0);}
 else IDirect3DVertexBuffer9_FreePrivateData(buffer,&uma_pending_guid);
 HRESULT result=uma_native_unlock(buffer);
 if(SUCCEEDED(result) && identity.count)IDirect3DVertexBuffer9_SetPrivateData(buffer,&uma_identity_guid,&identity,sizeof(identity),0);
 return result;
}
/* Install only before uploads; expected bytes must remain alive until removal. */
static BOOL uma_upload_install(IDirect3DVertexBuffer9 *sample,const void *expected,UINT bytes){
 if(uma_upload_table || !sample || !expected || !bytes || bytes%36 || bytes>4*1024*1024)return FALSE;
 void **table=*(void***)sample;DWORD protection;
 if(!VirtualProtect(table+11,2*sizeof(void*),PAGE_READWRITE,&protection))return FALSE;
 uma_native_lock=(UmaVertexLock)table[11];uma_native_unlock=(UmaVertexUnlock)table[12];
 uma_upload_expected=expected;uma_upload_bytes=bytes;uma_upload_table=table;
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
 uma_upload_table=NULL;uma_upload_expected=NULL;uma_upload_bytes=0;return TRUE;
}
#endif
