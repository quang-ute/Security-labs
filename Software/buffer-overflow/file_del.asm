; delete dummyfile in nasm

section .text
global _start
_start:
    jmp short ender
starter:
    mov eax,10
    mov ebx,_filename
    int 0x80
_exit:
    mov eax,1
    int 0x80

ender:
    call starter
_filename:
    db 'dummyfile',0