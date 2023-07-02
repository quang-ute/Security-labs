<?php
session_start();

  // Authenticate the user
  if (!isset($_SESSION['authenticated']) || !$_SESSION['authenticated']) {
    header('Location: login.php');
    exit();
  }
  else {
    echo "Welcome, " . $_SESSION['username'] . "!";
  }
 
  if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $amount = $_POST['amount'];
    $to = $_POST['to'];

  // Transfer the amount
  $balance = $_SESSION['balance'];
  if ($balance >= $amount) {
    $balance -= $amount;
    $_SESSION['balance'] = $balance;
    // perform transfer
    $transfer = "Transfer {$amount} to {$to}<br>";
    echo $transfer;
    echo "Amount left {$balance}<hr>";
  } else {
    die('Insufficient balance!');
  }
} 

?>

<form action="" method="POST">
  <label for="amount">Amount:</label>
  <input type="number" id="amount" name="amount" required>
  <br>
  <label for="to">To:</label>
  <input type="text" id="to" name="to" required>
  <br>
  <input type="submit" name="transfer" value="Transfer">
</form>
