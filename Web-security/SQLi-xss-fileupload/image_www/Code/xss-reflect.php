<h2>reflected XSS lab</h2>
<?php
  if(isset($_POST['search'])){
    $query = $_POST['search'];
    echo "You search for: " . $query; // This text will be displayed in browser
  }
?>
<form action="" method="POST">
  <input type="text" id="search" name="search" required>
  <input type="submit">
</form>