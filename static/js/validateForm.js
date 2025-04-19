/**
 * Validates password confirmation on registration form.
 *
 * - Compares the password and confirm password fields
 * - If they match, returns true to allow form submission
 * - Otherwise, shows an alert and prevents form submission
 *
 * @returns {boolean} Whether the password confirmation is valid
 */
function validate() {
    var pass = document.getElementById("password").value;
    var cpass = document.getElementById("cpassword").value;
    if (pass == cpass) {
        return true; // Passwords match
    } else {
        alert("Паролі не співпадають"); // Show mismatch alert
        return false; // Prevent form submission
    }
}


