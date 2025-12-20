/**
 * Password strength validator
 * Returns validation result with strength level and feedback messages
 */

const commonPasswords = [
  "password", "123456", "password123", "admin", "letmein", "welcome",
  "monkey", "dragon", "master", "sunshine", "qwerty", "123123",
  "111111", "abc123", "123456789", "password1", "pass", "test",
  "guest", "hello", "world", "strawbay", "invoice", "scanner"
];

export function validatePasswordStrength(password) {
  const result = {
    isValid: false,
    strength: 0, // 0-5 scale
    feedback: [],
    errors: []
  };

  if (!password) {
    result.errors.push("Password is required");
    return result;
  }

  if (password.length < 8) {
    result.errors.push("Password must be at least 8 characters");
  }

  if (password.length < 12) {
    result.feedback.push("Longer passwords are more secure");
  }

  // Check for lowercase letters
  if (!/[a-z]/.test(password)) {
    result.errors.push("Password must contain lowercase letters");
  } else {
    result.strength++;
  }

  // Check for uppercase letters
  if (!/[A-Z]/.test(password)) {
    result.errors.push("Password must contain uppercase letters");
  } else {
    result.strength++;
  }

  // Check for numbers
  if (!/\d/.test(password)) {
    result.errors.push("Password must contain numbers");
  } else {
    result.strength++;
  }

  // Check for special characters
  if (!/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)) {
    result.feedback.push("Adding special characters makes password stronger");
  } else {
    result.strength++;
  }

  // Check for common passwords
  if (commonPasswords.includes(password.toLowerCase())) {
    result.errors.push("This password is too common");
  } else {
    result.strength++;
  }

  // Check for sequential patterns
  if (/(.)\1{2,}/.test(password)) {
    result.feedback.push("Avoid repeating characters");
  }

  // No common keyboard patterns
  if (/qwerty|asdfgh|zxcvbn|123456|654321/.test(password.toLowerCase())) {
    result.feedback.push("Avoid keyboard patterns");
  }

  // Determine if valid
  result.isValid = result.errors.length === 0;

  // Clamp strength to 0-5
  result.strength = Math.min(5, result.strength);

  return result;
}

export function getPasswordStrengthLabel(strength) {
  switch(strength) {
    case 0:
    case 1:
      return "Very Weak";
    case 2:
      return "Weak";
    case 3:
      return "Fair";
    case 4:
      return "Good";
    case 5:
      return "Strong";
    default:
      return "Unknown";
  }
}

export function getPasswordStrengthColor(strength) {
  switch(strength) {
    case 0:
    case 1:
      return "#ef4444"; // red
    case 2:
      return "#f97316"; // orange
    case 3:
      return "#eab308"; // yellow
    case 4:
      return "#84cc16"; // lime
    case 5:
      return "#10b981"; // green
    default:
      return "#ccc";
  }
}
