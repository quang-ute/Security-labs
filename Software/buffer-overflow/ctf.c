#include <stdio.h>
#include <string.h>
#include <stdlib.h>
void myfunc(int p, int q)
{
	char filebuf[64];
	FILE *f = fopen("flag1.txt","r");
	if (f == NULL) {
		printf("flag1 is missing!\n");
		exit(0);
	}
	fgets(filebuf,64,f);

	printf("myfunc is reached");
	if (p!=0x04081211)
	{
		printf(", but you fail to get the flag");
		return;
	}
	if (q!=0x44644262)
	{
		printf(", but you fail to get the flag");
		return;
	}
	printf("You got the flag\n"); 
}
void vuln(char* s)
{
	char buf[100];
	strcpy(buf,s);
	puts(buf);
}
int main(int argc, char* argv[])
{
	vuln(argv[1]);
    return 0;
} 
