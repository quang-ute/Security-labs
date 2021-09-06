#include<stdio.h>
#include<string.h>
int main(int argc, char* argv[])
{
	char buf[64];
 	if (argc==1)
		printf("missing argument\n");
 	else
 		strcpy(buf,argv[1]);
 	//printf("buf: 0x%x\n",(unsigned int)buf);
  	return 0;
}
