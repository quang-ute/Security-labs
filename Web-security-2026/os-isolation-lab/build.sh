#!/usr/bin/env bash
# Build all lab binaries.  Requires gcc (and gdb for the debugger section).
#   Ubuntu/WSL:  sudo apt-get install -y build-essential gdb
set -euo pipefail
cd "$(dirname "$0")"

CC="${CC:-gcc}"
FLAGS=(-O0 -g -Wall -Wextra)

echo "[*] building with $CC ${FLAGS[*]}"
for src in target mem_peek vm_readv vm_writev; do
    echo "    - $src"
    "$CC" "${FLAGS[@]}" -o "$src" "src/$src.c"
done
echo "[+] done. Binaries: target mem_peek vm_readv vm_writev"
echo "    (gdb comes from your distro package; core tools above need only gcc)"