Design a 2-hour hands-on practice:

## [Objectives]()

By completing this lab, you will be able to:

- Understand the fundamental security principle of process memory isolation in Linux.
- Demonstrate that a process cannot directly read the memory of another process using standard file I/O on /proc/[PID]/mem.
- Explain *why* the kernel blocks this direct access.
- Contrast the failed direct access with successful, sanctioned methods for inspecting process memory, such as using a
  debugger (gdb) or the process_vm_readv system call.
- Any other demonstration that you can suggest.
