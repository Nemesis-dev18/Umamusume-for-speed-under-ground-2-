#ifndef UMA_RESOURCE_TAGS_H
#define UMA_RESOURCE_TAGS_H
#include <windows.h>
#include <d3d9.h>
static const GUID uma_renderer_buffer_guid={0xe28b4783,0xb102,0x46fb,{0x85,0x7a,0xde,0x91,0x62,0x47,0x10,0x3c}};
static inline BOOL uma_private_renderer_buffer(IDirect3DVertexBuffer9 *buffer){
 DWORD value=0,bytes=sizeof(value);
 return SUCCEEDED(IDirect3DVertexBuffer9_GetPrivateData(buffer,&uma_renderer_buffer_guid,&value,&bytes)) && bytes==sizeof(value) && value==1;
}
#endif
