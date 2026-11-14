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
typedef struct {void *pointer;UINT bytes,depth;} UmaPendingUpload;
static BOOL uma_upload_is_character(IDirect3DVertexBuffer9 *buffer){
 DWORD identity=0,size=sizeof(identity);
 return buffer && SUCCEEDED(IDirect3DVertexBuffer9_GetPrivateData(buffer,&uma_identity_guid,&identity,&size)) && size==sizeof(identity) && identity==0x554d4132;
}
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
 if(SUCCEEDED(IDirect3DVertexBuffer9_GetDesc(buffer,&descriptor)) && descriptor.Size==uma_upload_bytes){
  pending.pointer=(!(flags&D3DLOCK_READONLY) && data && *data && !offset && (!bytes || bytes==descriptor.Size))?*data:NULL;
  pending.bytes=descriptor.Size;pending.depth=1;
  IDirect3DVertexBuffer9_SetPrivateData(buffer,&uma_pending_guid,&pending,sizeof(pending),0);
 }
 return result;
}
static HRESULT WINAPI uma_observe_unlock(IDirect3DVertexBuffer9 *buffer){
 UmaPendingUpload pending={0};DWORD bytes=sizeof(pending);
 BOOL tracked=SUCCEEDED(IDirect3DVertexBuffer9_GetPrivateData(buffer,&uma_pending_guid,&pending,&bytes)) && bytes==sizeof(pending);
 BOOL matches=tracked && pending.depth==1 && pending.pointer && pending.bytes==uma_upload_bytes && !memcmp(pending.pointer,uma_upload_expected,pending.bytes);
 if(tracked && pending.depth>1){pending.depth--;pending.pointer=NULL;IDirect3DVertexBuffer9_SetPrivateData(buffer,&uma_pending_guid,&pending,sizeof(pending),0);}
 else IDirect3DVertexBuffer9_FreePrivateData(buffer,&uma_pending_guid);
 HRESULT result=uma_native_unlock(buffer);
 if(SUCCEEDED(result) && matches){DWORD identity=0x554d4132;IDirect3DVertexBuffer9_SetPrivateData(buffer,&uma_identity_guid,&identity,sizeof(identity),0);}
 return result;
}
/* Install only before uploads; expected bytes must remain alive until removal. */
static BOOL uma_upload_install(IDirect3DVertexBuffer9 *sample,const void *expected,UINT bytes){
 if(uma_upload_table || !sample || !expected || !bytes || bytes>4*1024*1024)return FALSE;
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
