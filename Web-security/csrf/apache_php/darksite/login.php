<?php
session_start();
// csrf countermeasure
//$token = bin2hex(random_bytes(32));
//$_SESSION['csrf_token'] = $token;

// Check if the user has submitted the login form
if (isset($_POST['username']) && isset($_POST['password'])) {
  $username = $_POST['username'];
  $password = $_POST['password'];

  // Verify the user's credentials against a database or other storage mechanism
  if ($username === 'admin' && $password === 'password') {
    // Set the authenticated session variable to true
    $_SESSION['authenticated'] = true;
    // Set the user's balance in the session
    $_SESSION['balance'] = 1000;
    $_SESSION['username'] = $username;
    echo "login successful";
    // Redirect the user to the transfer page
    header('Location: transfer.php');
    exit();
  } else {
    // Display an error message
    echo 'Invalid username or password!';
  }
}
?>

<form action="" method="POST">
  <label for="username">Username:</label>
  <input type="text" id="username" name="username" required>
  <br>
  <label for="password">Password:</label>
  <input type="password" id="password" name="password" required>
  <br>
  <input type="submit">
</form>
