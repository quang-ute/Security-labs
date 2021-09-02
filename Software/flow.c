#include <stdio.h>
#include <string.h>
void change()
{
	printf("code flow has been modified\n");
}
int main(int argc, char* argv[])
{
	char buffer[16];
	strcpy(buffer,argv[1]);
	return 0;
}