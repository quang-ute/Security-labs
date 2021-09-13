#include<stdio.h>
void fmtstr()
{
	char input[80];
	int	var = 0x55667788;

	printf("Enter a string:");
	fgets(input, sizeof(input),stdin);
	printf(input);
	
}
void main(int argc, char* argv[])
{
	fmtstr();
}
