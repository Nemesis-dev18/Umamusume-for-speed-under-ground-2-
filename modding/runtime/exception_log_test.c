#include <windows.h>
#include <assert.h>
#include <stdio.h>
#include <string.h>
static LONG CALLBACK resume_test(EXCEPTION_POINTERS *e){return e->ExceptionRecord->ExceptionCode==EXCEPTION_INT_DIVIDE_BY_ZERO?EXCEPTION_CONTINUE_EXECUTION:EXCEPTION_CONTINUE_SEARCH;}
int main(void){
 DeleteFileW(L"modding\\uma-exception.log");
 HMODULE module=LoadLibraryW(L"modding\\runtime\\UmaExceptionLog.asi");assert(module);
 PVOID resume=AddVectoredExceptionHandler(0,resume_test);assert(resume);
 RaiseException(EXCEPTION_INT_DIVIDE_BY_ZERO,0,0,NULL);
 RemoveVectoredExceptionHandler(resume);FreeLibrary(module);
 FILE *file=fopen("modding/uma-exception.log","rb");assert(file);char text[2048]={0};fread(text,1,sizeof(text)-1,file);fclose(file);
 assert(strstr(text,"code=c0000094") && strstr(text,"module="));puts("PASS exception observed without suppressing it; independent test resumes and logger unloads");return 0;
}
