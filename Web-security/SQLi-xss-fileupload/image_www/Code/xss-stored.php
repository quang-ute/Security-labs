<h2>Stored XSS Demo</h2>
<?php
  if(isset($_POST['submit'])){
    $comment = $_POST['comment'];
    $file = fopen("comments.txt", "a");
    fwrite($file, $comment . PHP_EOL);
    fclose($file);
  }
  echo "Recent comments:<br>";
  $file = fopen("comments.txt", "r");
  if ($file) {
    while (($line = fgets($file)) !== false) {
      echo $line . "<br>";
    }
    fclose($file);
  }
  else {
      echo "File error!";
  }
?>

<form method="POST" action="">
  <hr>
  <label for="comment">Leave a comment:</label><br>
  <textarea name="comment" id="comment" style="width:500px; height:300px"></textarea><br>
  <input type="submit" name="submit" value="Submit">
</form>
