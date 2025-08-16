// Function to get CSRF token from cookies
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

document.addEventListener('DOMContentLoaded', function() {
  const tabSignIn = document.getElementById('tabSignIn');
  const tabRegister = document.getElementById('tabRegister');
  const signinForm = document.getElementById('signinForm');
  const registerForm = document.getElementById('registerForm');
  const formTitle = document.getElementById('formTitle');
  const formSubtitle = document.getElementById('formSubtitle');
  const toggleText = document.getElementById('toggleText');
  const dobInput = document.getElementById('dob');
  const dobWarning = document.getElementById('dobWarning');

  // Debug: Log if elements are found
  console.log('Elements found:', {
    tabSignIn: !!tabSignIn,
    tabRegister: !!tabRegister,
    signinForm: !!signinForm,
    registerForm: !!registerForm,
    formTitle: !!formTitle,
    formSubtitle: !!formSubtitle,
    toggleText: !!toggleText
  });

  // Check if all required elements exist
  if (!tabSignIn || !tabRegister || !signinForm || !registerForm || !formTitle || !formSubtitle || !toggleText) {
    console.error('Some elements are missing. Please check your HTML IDs.');
    return;
  }

  // Set max date for DOB to ensure 18+ age
  if (dobInput) {
    const today = new Date();
    const eighteenYearsAgo = new Date(today.getFullYear() - 18, today.getMonth(), today.getDate());
    dobInput.max = eighteenYearsAgo.toISOString().split('T')[0];

    dobInput.addEventListener('change', function() {
      const selectedDate = new Date(this.value);
      const ageDiffMs = Date.now() - selectedDate.getTime();
      const ageDate = new Date(ageDiffMs);
      const age = Math.abs(ageDate.getUTCFullYear() - 1970);

      if (age < 18) {
        dobWarning.style.display = 'block';
      } else {
        dobWarning.style.display = 'none';
      }
    });
  }

  function switchForm(form) {
    if (form === 'signin') {
      signinForm.style.display = 'block';
      registerForm.style.display = 'none';
      tabSignIn.classList.add('active');
      tabRegister.classList.remove('active');
      formTitle.textContent = 'Welcome';
      formSubtitle.textContent = 'Welcome back, please login to your account.';
      toggleText.textContent = "Don't have an account? Create an Account";
    } else {
      signinForm.style.display = 'none';
      registerForm.style.display = 'block';
      tabSignIn.classList.remove('active');
      tabRegister.classList.add('active');
      formTitle.textContent = 'Create Account';
      formSubtitle.textContent = 'Please fill the form to create an account.';
      toggleText.textContent = "Already have an account? Sign In";
    }
  }

  // Add click handlers with explicit function references
  tabSignIn.onclick = function() {
    console.log('Sign In tab clicked');
    switchForm('signin');
  };

  tabRegister.onclick = function() {
    console.log('Register tab clicked');
    switchForm('register');
  };

  toggleText.onclick = function() {
    console.log('Toggle text clicked');
    if (signinForm.style.display === 'none' || signinForm.style.display === '') {
      switchForm('signin');
    } else {
      switchForm('register');
    }
  };

  // Force initial state
  console.log('Setting initial state to signin');
  signinForm.style.display = 'block';
  registerForm.style.display = 'none';

  // Handle login form submission with enhanced error handling
  signinForm.addEventListener('submit', function(e) {
    e.preventDefault();
    console.log('Login form submitted');
    
    // Get form elements - check both possible IDs for login form
    let voterIdInput = signinForm.querySelector('#voterId') || signinForm.querySelector('[name="voter_id"]') || signinForm.querySelector('input[type="text"]');
    let passwordInput = signinForm.querySelector('#password') || signinForm.querySelector('[name="password"]') || signinForm.querySelector('input[type="password"]');
    
    console.log('Found form elements:', {
      voterId: !!voterIdInput,
      password: !!passwordInput
    });

    if (!voterIdInput || !passwordInput) {
      console.error('Could not find login form inputs');
      alert('Form elements not found. Please refresh the page and try again.');
      return;
    }

    const voterId = voterIdInput.value.trim();
    const password = passwordInput.value.trim();
    
    console.log('Form values:', {
      voterId: voterId ? 'Has value' : 'Empty',
      password: password ? 'Has value' : 'Empty'
    });

    // Basic validation
    if (!voterId || !password) {
      alert('Please fill in all fields');
      return;
    }

    // Validate Voter ID format (3 letters followed by 7 digits)
    if (!/^[A-Z]{3}[0-9]{7}$/.test(voterId.toUpperCase())) {
      alert('Please enter a valid Voter ID (3 letters followed by 7 digits)');
      return;
    }

    // Show loading state
    const submitButton = signinForm.querySelector('button[type="submit"]') || signinForm.querySelector('input[type="submit"]');
    const originalButtonText = submitButton ? submitButton.textContent || submitButton.value : '';
    if (submitButton) {
      submitButton.disabled = true;
      if (submitButton.textContent !== undefined) {
        submitButton.textContent = 'Logging in...';
      } else {
        submitButton.value = 'Logging in...';
      }
    }

    // Create form data for submission
    const formData = new FormData();
    formData.append('voter_id', voterId.toUpperCase());
    formData.append('password', password);

    console.log('Sending login request...');

    // Send login request to the backend with enhanced error handling
    fetch('/do_login/', {
      method: 'POST',
      body: formData,
      credentials: 'same-origin',
      headers: {
        'X-CSRFToken': getCookie('csrftoken'),
        'X-Requested-With': 'XMLHttpRequest'
      },
    })
    .then(response => {
      console.log('Response status:', response.status);
      console.log('Response ok:', response.ok);
      
      // Handle different response types
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        return response.json().then(data => ({ data, status: response.status, ok: response.ok }));
      } else {
        return response.text().then(text => ({ text, status: response.status, ok: response.ok }));
      }
    })
    .then(result => {
      console.log('Response result:', result);
      
      // Reset button state
      if (submitButton) {
        submitButton.disabled = false;
        if (submitButton.textContent !== undefined) {
          submitButton.textContent = originalButtonText;
        } else {
          submitButton.value = originalButtonText;
        }
      }

      if (result.ok) {
        if (result.data) {
          // JSON response
          if (result.data.success) {
            console.log('Login successful, redirecting...');
            // Try multiple redirect methods
            setTimeout(() => {
              window.location.href = '/voter/';
            }, 100);
          } else {
            alert(result.data.message || 'Login failed. Please check your credentials.');
          }
        } else if (result.text) {
          // HTML response - might be a redirect or success page
          if (result.text.includes('voter') || result.text.includes('dashboard') || result.status === 200) {
            console.log('Login appears successful, redirecting...');
            window.location.href = '/voter/';
          } else {
            alert('Login failed. Please check your credentials.');
          }
        }
      } else {
        // Handle HTTP error status codes
        if (result.status === 403) {
          alert('Access denied. Please check your credentials.');
        } else if (result.status === 404) {
          alert('Login service not found. Please contact support.');
        } else if (result.status === 500) {
          alert('Server error. Please try again later.');
        } else {
          const errorMessage = result.data ? (result.data.message || 'Login failed') : 'Login failed';
          alert(errorMessage + '. Please check your credentials.');
        }
      }
    })
    .catch(error => {
      console.error('Login error:', error);
      
      // Reset button state
      if (submitButton) {
        submitButton.disabled = false;
        if (submitButton.textContent !== undefined) {
          submitButton.textContent = originalButtonText;
        } else {
          submitButton.value = originalButtonText;
        }
      }
      
      // Check if it's a network error or server error
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        alert('Network error. Please check your internet connection and try again.');
      } else {
        alert('Login failed. Please try again.');
      }
    });
  });

  // --- Enhanced registration form validation logic ---
  function isValidEmail(email) {
    const regex = /^[\w-.]+@([\w-]+\.)+[\w-]{2,4}$/;
    return regex.test(email);
  }

  // Create or get error message element
  function getOrCreateErrorElement(inputId) {
    let errorElement = document.getElementById(inputId + '-error');
    if (!errorElement) {
      errorElement = document.createElement('div');
      errorElement.id = inputId + '-error';
      errorElement.className = 'error-message';
      errorElement.style.color = '#dc3545';
      errorElement.style.fontSize = '12px';
      errorElement.style.marginTop = '5px';
      errorElement.style.display = 'none';
      
      const input = document.getElementById(inputId);
      if (input && input.parentNode) {
        input.parentNode.insertBefore(errorElement, input.nextSibling);
      }
    }
    return errorElement;
  }

  function markField(input, isValid, message = '') {
    const errorElement = getOrCreateErrorElement(input.id);
    
    input.classList.remove('is-valid', 'is-invalid');
    input.style.removeProperty('border-color');
    input.style.removeProperty('box-shadow');
    
    if (isValid) {
      input.classList.add('is-valid');
      input.style.borderColor = '#28a745';
      input.style.boxShadow = '0 0 0 0.2rem rgba(40, 167, 69, 0.25)';
      input.setCustomValidity('');
      errorElement.style.display = 'none';
      errorElement.textContent = '';
    } else {
      input.classList.add('is-invalid');
      input.style.borderColor = '#dc3545';
      input.style.boxShadow = '0 0 0 0.2rem rgba(220, 53, 69, 0.25)';
      input.setCustomValidity(message);
      errorElement.textContent = message;
      errorElement.style.display = 'block';
    }
  }

  // Real-time validation setup
  function setupRealTimeValidation() {
    const validations = [
      { id: 'firstName', test: val => /^[A-Za-z]{2,}$/.test(val), msg: 'First name must be at least 6 letters long and contain only alphabets.' },
      { id: 'lastName', test: val => val.trim() !== '', msg: 'Last name cannot be empty.' },
      { id: 'email', test: isValidEmail, msg: 'Enter a valid email (e.g. user@example.com).' },
      { id: 'mobile', test: val => /^[6-9]\d{9}$/.test(val), msg: 'Mobile must be 10 digits and start with 6/7/8/9.' },
      { id: 'dob', test: val => {
        if (!val) return false;
        const dob = new Date(val);
        const today = new Date();
        const age = today.getFullYear() - dob.getFullYear();
        return age > 18 || (age === 18 && today >= new Date(dob.setFullYear(dob.getFullYear() + 18)));
      }, msg: 'You must be at least 18 years old.' },
      { id: 'gender', test: val => val !== '', msg: 'Please select a gender.' },
      { id: 'parentSpouseName', test: val => val.trim() !== '', msg: 'This field cannot be empty.' },
      { id: 'streetAddress', test: val => val.trim() !== '', msg: 'Address cannot be empty.' },
      { id: 'city', test: val => val.trim() !== '', msg: 'City cannot be empty.' },
      { id: 'state', test: val => val !== '', msg: 'Please select a state.' },
      { id: 'pincode', test: val => /^[1-9][0-9]{5}$/.test(val), msg: 'Pincode must be 6 digits starting with non-zero.' },
      { id: 'placeOfBirth', test: val => val.trim() !== '', msg: 'Place of birth cannot be empty.' },
      { id: 'voterId', test: val => /^[A-Z]{3}[0-9]{7}$/.test(val), msg: 'Voter ID must be in format: 3 letters followed by 7 digits.' },
      { id: 'aadharNumber', test: val => /^\d{12}$/.test(val), msg: 'Aadhar must be a 12-digit number.' },
      { id: 'panNumber', test: val => /^[A-Z]{5}[0-9]{4}[A-Z]{1}$/.test(val), msg: 'PAN must be in format: 5 letters, 4 digits, 1 letter.' },
      { id: 'password', test: val => val.length >= 6, msg: 'Password must be at least 6 characters.' },
      { id: 'confirmPassword', test: val => {
        const password = document.getElementById('password').value;
        return val === password && val.length >= 6;
      }, msg: 'Passwords must match and be at least 6 characters.' }
    ];

    // Add event listeners for real-time validation
    validations.forEach(({ id, test, msg }) => {
      const input = document.getElementById(id);
      if (input) {
        // Validate on blur (when user leaves field)
        input.addEventListener('blur', function() {
          if (this.value.trim() !== '' || this.type === 'date') {
            const isValid = test(this.value.trim());
            markField(this, isValid, msg);
          }
        });

        // Validate on input for certain fields
        if (['password', 'confirmPassword'].includes(id)) {
          input.addEventListener('input', function() {
            if (this.value.trim() !== '') {
              const isValid = test(this.value.trim());
              markField(this, isValid, msg);
              
              // Also validate confirm password when password changes
              if (id === 'password') {
                const confirmPasswordInput = document.getElementById('confirmPassword');
                if (confirmPasswordInput && confirmPasswordInput.value.trim() !== '') {
                  const confirmValidation = validations.find(v => v.id === 'confirmPassword');
                  const confirmIsValid = confirmValidation.test(confirmPasswordInput.value.trim());
                  markField(confirmPasswordInput, confirmIsValid, confirmValidation.msg);
                }
              }
            }
          });
        }
      }
    });

    return validations;
  }

  const validations = setupRealTimeValidation();

  // Check if all fields are valid
  function isFormValid() {
    let isValid = true;
    validations.forEach(({ id, test, msg }) => {
      const input = document.getElementById(id);
      if (input) {
        const fieldValid = test(input.value.trim());
        if (!fieldValid) {
          isValid = false;
        }
      }
    });
    return isValid;
  }

  // Update submit button state
  function updateSubmitButton() {
    const submitButton = registerForm.querySelector('button[type="submit"]') || registerForm.querySelector('input[type="submit"]');
    if (submitButton) {
      const formValid = isFormValid();
      submitButton.disabled = !formValid;
      submitButton.style.opacity = formValid ? '1' : '0.6';
      submitButton.style.cursor = formValid ? 'pointer' : 'not-allowed';
    }
  }

  // Add input listeners to update submit button state
  validations.forEach(({ id }) => {
    const input = document.getElementById(id);
    if (input) {
      input.addEventListener('input', updateSubmitButton);
      input.addEventListener('change', updateSubmitButton);
    }
  });

  registerForm.addEventListener('submit', function (e) {
    e.preventDefault();
    let isFormValid = true;

    // Validate all fields one final time
    validations.forEach(({ id, test, msg }) => {
      const input = document.getElementById(id);
      if (input) {
        const isValid = test(input.value.trim());
        markField(input, isValid, msg);
        if (!isValid) isFormValid = false;
      }
    });

    if (isFormValid) {
      // All fields are valid, proceed with registration
      console.log('Form is valid, submitting...');
      
      // Create FormData object with all form fields
      const formData = new FormData();
      validations.forEach(({ id }) => {
        const input = document.getElementById(id);
        if (input) {
          formData.append(id, input.value.trim());
        }
      });

      // Show loading state
      const submitButton = registerForm.querySelector('button[type="submit"]') || registerForm.querySelector('input[type="submit"]');
      const originalButtonText = submitButton ? submitButton.textContent || submitButton.value : '';
      if (submitButton) {
        submitButton.disabled = true;
        if (submitButton.textContent !== undefined) {
          submitButton.textContent = 'Registering...';
        } else {
          submitButton.value = 'Registering...';
        }
      }

      // Send registration request to the backend
      fetch('/register/', {
        method: 'POST',
        body: formData,
        credentials: 'same-origin',
        headers: {
          'X-CSRFToken': getCookie('csrftoken'),
          'X-Requested-With': 'XMLHttpRequest'
        },
      })
      .then(response => {
        console.log('Registration response status:', response.status);
        return response.json();
      })
      .then(data => {
        // Reset button state
        if (submitButton) {
          submitButton.disabled = false;
          if (submitButton.textContent !== undefined) {
            submitButton.textContent = originalButtonText;
          } else {
            submitButton.value = originalButtonText;
          }
        }

        if (data.success) {
          alert('Registration successful! Please login with your credentials.');
          // Switch to login form
          switchForm('signin');
        } else {
          alert(data.message || 'Registration failed. Please try again.');
        }
      })
      .catch(error => {
        console.error('Registration error:', error);
        // Reset button state
        if (submitButton) {
          submitButton.disabled = false;
          if (submitButton.textContent !== undefined) {
            submitButton.textContent = originalButtonText;
          } else {
            submitButton.value = originalButtonText;
          }
        }
        alert('Registration failed. Please try again.');
      });
    } else {
      // Scroll to first invalid field
      const firstInvalidField = registerForm.querySelector('.is-invalid');
      if (firstInvalidField) {
        firstInvalidField.scrollIntoView({ behavior: 'smooth', block: 'center' });
        firstInvalidField.focus();
      }
    }
  });

  // Initial submit button state
  setTimeout(() => {
    updateSubmitButton();
  }, 100);
});