#include <stdio.h>
#include <stdlib.h>
void main()
{
    char x[12];
    char* y = malloc(sizeof(char)*12);
    printf("address of x (on stack):0x%x\n",x);
    printf("address of y (on heap):0x%x\n",y);
}