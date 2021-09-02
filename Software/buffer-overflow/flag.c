#include <stdio.h>
#include <string.h>
int main(int argc, char* argv[])
{
    int	 flag=0;
    char buffer[16];
    strcpy(buffer,argv[1]);
    if (flag!=0)
	printf("Modified\n");
    else
	printf("Try again\n");
    return 0;
} 
