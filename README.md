# MultiTechSpace — Fix & OTP Setup Guide

## What was broken and what was fixed

### 1. Double Profile crash (critical — blocks all registrations)
**File:** `core/signals.py` → replaced  
**Problem:** `register()` in views.py manually called `Profile.objects.create()`, but `signals.py` also does this on every `User` post_save. First student to register would crash with `IntegrityError: UNIQUE constraint failed`.  
**Fix:** `register()` now only updates the profile the signal already created. Signal also fixed to create Portfolio via a `post_save` on Profile (so `user_type` is available).

---

### 2. Duplicate view functions (causes wrong view to run silently)
**File:** `core/views.py` — manual edit required  
**Problem:** `live_session()` is defined twice (lines ~513 and ~747). `join_session()` is defined twice (lines ~569 and ~802). Django uses the last definition, but the first ones still waste memory and hide bugs.  
**Fix:** Delete the first copy of each (lines 513–566 and 569–594). Keep the versions after `submit_salary()`.

---

### 3. Project-level urls.py syntax error
**File:** `tech_school/urls.py` → replaced as `project_urls.py`  
**Problem:** A comment (`1. The official...`) was placed inline inside the `urlpatterns` list, which is a Python syntax error.  
**Fix:** Moved comment above the `path()` call.

---

### 4. calculate_performance.py used non-existent `cohort` field
**File:** `management/commands/calculate_performance.py` → replaced  
**Problem:** `PerformanceRecord.objects.get_or_create(cohort=cohort, ...)` — but `PerformanceRecord` has no `cohort` field. Would crash every time the command ran.  
**Fix:** Removed `cohort` from the lookup. Used `user + month` as the unique key (which matches the model). Also fixed division-by-zero risk and added proper `exists()` checks.

---

### 5. OTP / 2FA wiring
**Files:** `two_factor_setup.html`, `two_factor_verify.html` (new templates)  
**What was missing:** The HTML templates for setup and verification. The views were already correct.  
**Fix:** Both templates provided. The `two_factor_setup` view was also updated to skip straight to verification if the device is already confirmed.

---

## Deployment steps (do these in order)

### Step 1 — Apply file changes

| Source file | Replace/edit |
|---|---|
| `core/signals.py` | Replace entirely with `signals.py` from this folder |
| `tech_school/urls.py` | Replace entirely with `project_urls.py` from this folder |
| `management/commands/calculate_performance.py` | Replace entirely |
| `core/views.py` | See Step 2 below for manual edits |
| `templates/core/two_factor_setup.html` | Copy from this folder (create if doesn't exist) |
| `templates/core/two_factor_verify.html` | Copy from this folder (create if doesn't exist) |

### Step 2 — Manual edits to views.py

Open `core/views.py` and make these 4 changes:

**a) Replace `register()` function**  
Copy the `register()` function from `views_auth_patch.py`.

**b) Replace `user_login()` function**  
Copy the `user_login()` function from `views_auth_patch.py`. The key addition: after a superuser logs in, they are redirected to `two_factor_setup` instead of the dashboard.

**c) Delete duplicate `live_session()` and `join_session()`**  
Search for `def live_session(request):` — there are two. Delete the first one (around line 513). Do the same for `def join_session(request, session_id):` — delete the first one (around line 569).

**d) Replace `two_factor_setup()` function**  
Copy from `views_auth_patch.py`. Key change: if device is already confirmed, redirects to `verify_admin_access` instead of showing the QR code again.

### Step 3 — Run migrations on Render

In your Render dashboard → Shell (or add a one-time job):
```bash
python manage.py migrate
```
No new migrations needed for these fixes — no model changes.

### Step 4 — Set up your admin OTP (one time)

1. Log in to your site as the superuser
2. You'll be redirected to `/two_factor_setup/`
3. Open Google Authenticator or Authy on your phone
4. Tap **+** → **Scan QR code** → point at the screen
5. Enter the 6-digit code shown in the app
6. Click **Verify & Activate 2FA**
7. Done — you'll be taken to the admin dashboard

From now on, every superuser login goes:  
**Login → OTP verify → Admin dashboard**

### Step 5 — Add required packages (if not already in requirements.txt)

```
django-otp
qrcode[pil]
```

Render will install from `requirements.txt` automatically on next deploy.

---

## Quick checklist before going live

- [ ] `signals.py` replaced
- [ ] `urls.py` (project level) syntax error fixed
- [ ] `calculate_performance.py` replaced
- [ ] Duplicate `live_session` / `join_session` deleted from views.py
- [ ] `register()` updated in views.py
- [ ] `user_login()` updated in views.py
- [ ] `two_factor_setup()` updated in views.py
- [ ] Both OTP templates in `templates/core/`
- [ ] OTP set up on your phone
- [ ] Students can register without crashing ✅