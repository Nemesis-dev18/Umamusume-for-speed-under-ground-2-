#ifndef UMA_SHADER_BRIDGE_H
#define UMA_SHADER_BRIDGE_H
/* GPU shader objects only. The original program is never modified. */
typedef struct {IDirect3DVertexShader9 *original,*clone;DWORD *code;UINT bytes,declaration_at,used_inputs;int uv,worldview,worldviewproj,headlight,diffuse_min,diffuse_range;BOOL reference,supported,declare_uv;} UmaShaderEntry;
typedef struct {UmaShaderEntry entries[32];unsigned next;} UmaShaderCache;
static void uma_shader_entry_clear(UmaShaderEntry *entry){if(entry->original)IDirect3DVertexShader9_Release(entry->original);if(entry->clone)IDirect3DVertexShader9_Release(entry->clone);free(entry->code);memset(entry,0,sizeof(*entry));}
static void uma_shader_cache_clear(UmaShaderCache *cache){for(unsigned i=0;i<32;i++)uma_shader_entry_clear(&cache->entries[i]);cache->next=0;}
static unsigned uma_shader_type(DWORD token){return ((token>>28)&7)|((token>>8)&24);}
static int uma_shader_length(unsigned op){
 switch(op){case 0:return 0;case 1:case 6:case 7:case 14:case 15:case 16:case 19:case 31:case 78:case 79:return 2;case 2:case 3:case 5:case 8:case 9:case 10:case 11:case 12:case 13:case 17:case 20:case 21:case 22:case 23:case 24:return 3;case 4:case 18:return 4;case 81:return 5;default:return -1;}
}
static void uma_shader_ctab(UmaShaderEntry *entry,const DWORD *comment,UINT words){
 if(words<8 || comment[0]!=0x42415443)return;
 const BYTE *data=(const BYTE*)(comment+1);size_t bytes=(size_t)(words-1)*4;DWORD number=uma_le32(data+12),info=uma_le32(data+16);
 if(uma_le32(data)!=28 || number>256 || info>bytes || number*20>bytes-info)return;
 for(DWORD i=0;i<number;i++){
  const BYTE *record=data+info+i*20;DWORD name=uma_le32(record);WORD kind,reg,count;memcpy(&kind,record+4,2);memcpy(&reg,record+6,2);memcpy(&count,record+8,2);
  if(name>bytes || kind!=2)continue;
  if(count==4 && reg<=252 && bytes-name>=sizeof("HeadlightWVP") && !memcmp(data+name,"HeadlightWVP",sizeof("HeadlightWVP")))entry->headlight=reg;
  if(count==4 && reg<=252 && bytes-name>=sizeof("WorldViewProj") && !memcmp(data+name,"WorldViewProj",sizeof("WorldViewProj")))entry->worldviewproj=reg;
  if(count==3 && reg<=253 && bytes-name>=sizeof("WorldView") && !memcmp(data+name,"WorldView",sizeof("WorldView")))entry->worldview=reg;
  if(count==1 && reg<=255 && bytes-name>=sizeof("DiffuseMin") && !memcmp(data+name,"DiffuseMin",sizeof("DiffuseMin")))entry->diffuse_min=reg;
  if(count==1 && reg<=255 && bytes-name>=sizeof("DiffuseRange") && !memcmp(data+name,"DiffuseRange",sizeof("DiffuseRange")))entry->diffuse_range=reg;
 }
}
static void uma_shader_input_flags(DWORD token,const unsigned input[16],unsigned temp[32][4],const unsigned address[4],unsigned out[4]){
 unsigned kind=uma_shader_type(token),index=token&2047;
 for(unsigned c=0;c<4;c++){
  unsigned swizzle=(token>>(16+2*c))&3,value=0;
  if(kind==0)value=index<32?temp[index][swizzle]:4;
  else if(kind==1)value=index<16?input[index]:4;
  else if(kind!=2)value=4;
  if(token&0x2000)value|=address[0]|address[1]|address[2]|address[3];
  out[c]=value;
 }
}
static void uma_shader_parse(UmaShaderEntry *entry){
 entry->uv=-1;entry->worldview=entry->worldviewproj=entry->headlight=-1;entry->diffuse_min=entry->diffuse_range=-1;if(entry->bytes<8 || entry->code[0]!=0xfffe0101)return;
 UINT words=entry->bytes/4,at=1;int canonical=1;unsigned input[16],temp[32][4]={{0}},address[4]={0},position[4]={0};for(unsigned i=0;i<16;i++)input[i]=4;
 while(at<words){
  DWORD instruction=entry->code[at++];unsigned op=instruction&65535;
  if(op==65535){unsigned flags=position[0]|position[1]|position[2]|position[3];if(entry->uv<0){for(int i=15;i>=0;i--)if(!(entry->used_inputs&(1u<<i))){entry->uv=i;entry->declare_uv=TRUE;break;}}entry->supported=instruction==65535 && at==words && canonical && entry->uv>=0 && (flags&1) && !(flags&2);return;}
  if(op==65534){UINT n=(instruction>>16)&32767;if(n>words-at)return;uma_shader_ctab(entry,entry->code+at,n);at+=n;continue;}
  int length=uma_shader_length(op);if(length<0 || instruction!=op || (UINT)length>words-at)return;
  const DWORD *args=entry->code+at;at+=(UINT)length;if(!length)continue;
  if(op==31){
   unsigned reg=args[1]&2047,usage=args[0]&0xf001f;if(uma_shader_type(args[1])!=1 || reg>=16)return;
   input[reg]=(usage==0)?1:((usage&31)==5?2:4);
   entry->used_inputs|=1u<<reg;if(usage!=0 && usage!=3 && usage!=5 && usage!=10)canonical=0;
   if(usage==5){entry->uv=(int)reg;}if(usage==10 && reg==1){entry->reference=TRUE;}continue;
  }
  if(op==81)continue;
  if(!entry->declaration_at)entry->declaration_at=at-(UINT)length-1;
  unsigned result[4]={0},flags[3][4]={{0}};
  for(int source=1;source<length;source++)uma_shader_input_flags(args[source],input,temp,address,flags[source-1]);
  for(unsigned c=0;c<4;c++){
   if(op==1)result[c]=flags[0][c];
   else for(int source=0;source<length-1;source++)for(unsigned k=0;k<4;k++)result[c]|=flags[source][k];
  }
  unsigned kind=uma_shader_type(args[0]),index=args[0]&2047,mask=(args[0]>>16)&15;unsigned *dest=NULL;
  if(kind==0 && index<32)dest=temp[index];else if(kind==3 && index==0)dest=address;else if(kind==4 && index==0)dest=position;
  if(dest)for(unsigned c=0;c<4;c++)if(mask&(1u<<c))dest[c]=result[c];
 }
}
static UmaShaderEntry *uma_shader_get(UmaShaderCache *cache,IDirect3DDevice9 *device,HRESULT *status){
 IDirect3DVertexShader9 *shader=NULL;*status=IDirect3DDevice9_GetVertexShader(device,&shader);if(FAILED(*status) || !shader)return NULL;
 for(unsigned i=0;i<32;i++)if(cache->entries[i].original==shader){IDirect3DVertexShader9_Release(shader);return &cache->entries[i];}
 UmaShaderEntry entry={0};entry.original=shader;UINT capacity=0;*status=IDirect3DVertexShader9_GetFunction(shader,NULL,&capacity);
 if(FAILED(*status) || capacity<8 || capacity>65536 || capacity%4){uma_shader_entry_clear(&entry);*status=E_FAIL;return NULL;}
 entry.code=malloc(capacity);if(!entry.code){uma_shader_entry_clear(&entry);*status=E_OUTOFMEMORY;return NULL;}
 entry.bytes=capacity;*status=IDirect3DVertexShader9_GetFunction(shader,entry.code,&entry.bytes);
 if(FAILED(*status) || entry.bytes>capacity || entry.bytes<8 || entry.bytes%4){uma_shader_entry_clear(&entry);*status=E_FAIL;return NULL;}
 uma_shader_parse(&entry);unsigned slot=cache->next++%32;uma_shader_entry_clear(&cache->entries[slot]);cache->entries[slot]=entry;return &cache->entries[slot];
}
static HRESULT uma_shader_clone(IDirect3DDevice9 *device,UmaShaderEntry *entry){
 if(!entry || !entry->supported)return E_FAIL;
 if(entry->clone)return S_OK;
 DWORD *code=malloc(entry->bytes+(entry->declare_uv?24:12));if(!code)return E_OUTOFMEMORY;UINT at=entry->bytes/4-1;
 if(entry->declare_uv){UINT insertion=entry->declaration_at;memcpy(code,entry->code,insertion*4);code[insertion]=31;code[insertion+1]=0x80000005;code[insertion+2]=0x900f0000|(DWORD)entry->uv;memcpy(code+insertion+3,entry->code+insertion,(at-insertion)*4);at+=3;}
 else memcpy(code,entry->code,entry->bytes-4);
 code[at++]=1;code[at++]=0xe00f0000;code[at++]=0x90e40000|(DWORD)entry->uv;code[at]=0xffff;
 HRESULT result=IDirect3DDevice9_CreateVertexShader(device,code,&entry->clone);free(code);return result;
}
#endif
