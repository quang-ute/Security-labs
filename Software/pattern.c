#include <stdio.h>
#include <string.h>
int main(int argc, char* argv[])
{
    int	 pattern;
    char buffer[16];
    strcpy(buffer,argv[1]);
    if (pattern == 0x41614262)
	printf("Correct pattern\n");
    else
	printf("Incorrect pattern\n");
    return 0;
} 
