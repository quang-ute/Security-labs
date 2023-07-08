<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>XSS Demo</title>
</head>
<body>
  <?php
    if (isset($_POST['submit'])) {
      //$name = htmlspecialchars($_POST['name']);
      $name = $_POST['name'];
      echo "<p>Hello, $name!</p>";    
    }
  ?>
  <form method="POST" action="">
    <label for="name">Enter your name:</label>
    <input type="text" name="name" id="name">
    <input type="submit" name="submit" value="Submit">
  </form>
</body>
</html>
