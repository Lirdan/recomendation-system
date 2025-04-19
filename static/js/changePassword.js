/**
 *
 * Simple form validation script for password confirmation fields.
 *
 * Purpose:
 * - Checks whether the "new password" and "confirm password" inputs match
 * - Alerts the user if they do not match
 * - Used in registration or password change forms
 *
 * Assumes input fields with the following IDs:
 * - #newpassword
 * - #cpassword
 *
 * Returns:
 * - true if passwords match
 * - false otherwise (with alert)
 */
function validate() {
    // Get values from the password and confirm password fields
    var pass = document.getElementById("newpassword").value;
    var cpass = document.getElementById("cpassword").value;
    // Check if both passwords match
    if (pass == cpass) {
        return true; // Allow form submission
    } else {
        alert("Паролі не співпадають!");
        return false; // Prevent form submission
    }
}

