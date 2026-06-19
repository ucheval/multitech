document.getElementById("registrationForm").addEventListener("submit", function (e) {
    const submitBtn = document.getElementById("submitBtn");
    const username = document.getElementById("id_username").value.trim();
    const firstName = document.getElementById("id_first_name").value.trim();
    const lastName = document.getElementById("id_last_name").value.trim();
    const email = document.getElementById("id_email").value.trim();
    const password = document.getElementById("id_password1").value;
    const password2 = document.getElementById("id_password2").value;
    const localNumber = document.getElementById("id_local_number").value.trim();
    const countryCode = document.getElementById("id_country_code").value;

    const errors = [];
    
    // Clear previous client-side errors
    document.querySelectorAll('.text-danger').forEach(el => el.textContent = '');

    // Validation
    if (username === "") {
        errors.push("Username cannot be empty.");
        document.querySelector("#id_username").nextElementSibling.textContent = "Username cannot be empty.";
    } else if (username.length < 3) {
        errors.push("Username too short");
        document.querySelector("#id_username").nextElementSibling.textContent = "Username must be at least 3 characters.";
    }
    
    if (firstName === "") {
        errors.push("First name is required");
        document.querySelector("#id_first_name").nextElementSibling.textContent = "First name cannot be empty.";
    }
    
    if (lastName === "") {
        errors.push("Last name is required");
        document.querySelector("#id_last_name").nextElementSibling.textContent = "Last name cannot be empty.";
    }
    
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        errors.push("Invalid email format");
        document.querySelector("#id_email").nextElementSibling.textContent = "Please enter a valid email address.";
    }
    
    if (password.length < 6 || password.length > 9) {
        errors.push("Invalid password length");
        document.querySelector("#id_password1").nextElementSibling.nextElementSibling.textContent = "Password must be between 6 and 9 characters.";
    } else if (!/[a-zA-Z]/.test(password) || !/\d/.test(password)) {
        errors.push("Password must contain letters and numbers");
        document.querySelector("#id_password1").nextElementSibling.nextElementSibling.textContent = "Password must contain both letters and numbers.";
    }
    
    if (password !== password2) {
        errors.push("Passwords don't match");
        document.querySelector("#id_password2").nextElementSibling.textContent = "Passwords do not match.";
    }
    
    if (!/^\d{7,15}$/.test(localNumber)) {
        errors.push("Invalid phone number");
        document.querySelector("#id_local_number").parentElement.nextElementSibling.nextElementSibling.textContent = "Phone number must be 7–15 digits.";
    }
    
    if (!countryCode) {
        errors.push("Country code required");
        document.querySelector("#id_country_code").parentElement.nextElementSibling.nextElementSibling.textContent = "Please select a country code.";
    }

    if (errors.length > 0) {
        e.preventDefault();
        const messagesDiv = document.getElementById("messages") || document.createElement("div");
        messagesDiv.id = "messages";
        messagesDiv.innerHTML = `
            <div class="alert alert-danger alert-dismissible fade show" role="alert">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Please fix ${errors.length} error${errors.length > 1 ? 's' : ''} before submitting.
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
        if (!document.getElementById("messages")) {
            document.querySelector(".register-container").insertBefore(messagesDiv, document.getElementById("registrationForm"));
        }
        submitBtn.classList.remove('loading');
        submitBtn.disabled = false;
        submitBtn.textContent = 'Create Account';
        return;
    }

    submitBtn.classList.add('loading');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Creating Account...';
});

// Sync country and country_code
const countrySelect = document.getElementById("id_country");
const countryCodeSelect = document.getElementById("id_country_code");
if (countrySelect && countryCodeSelect) {
    countrySelect.addEventListener("change", function () {
        countryCodeSelect.value = this.value;
    });
    countryCodeSelect.addEventListener("change", function () {
        countrySelect.value = this.value;
    });
}

// Password strength indicator
const passwordInput = document.getElementById('id_password1');
if (passwordInput) {
    passwordInput.addEventListener('input', function() {
        const password = this.value;
        const strengthText = this.nextElementSibling;
        
        if (password.length === 0) {
            strengthText.textContent = 'Password must be 6-9 characters with letters and numbers';
            strengthText.style.color = 'var(--text-muted)';
        } else if (password.length < 6) {
            strengthText.textContent = 'Password too short';
            strengthText.style.color = 'var(--error)';
        } else if (password.length > 9) {
            strengthText.textContent = 'Password too long';
            strengthText.style.color = 'var(--error)';
        } else if (!/[a-zA-Z]/.test(password) || !/\d/.test(password)) {
            strengthText.textContent = 'Password needs both letters and numbers';
            strengthText.style.color = 'var(--warning)';
        } else {
            strengthText.textContent = 'Password looks good!';
            strengthText.style.color = 'var(--success)';
        }
    });
}