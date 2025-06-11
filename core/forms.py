from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from phonenumber_field.formfields import PhoneNumberField
from .models import Course, PaymentSlip, Portfolio, Profile, OnboardingQuizResponse
import re
import pycountry
import phonenumbers
from phonenumbers import PhoneNumberFormat, parse, format_number, is_valid_number, region_code_for_country_code
from .models import Course

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'description', 'duration', 'level', 'price']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'duration': forms.NumberInput(attrs={'min': 1}),
            'price': forms.NumberInput(attrs={'step': '0.01', 'min': '0.00'}),
        }

    def clean_duration(self):
        duration = self.cleaned_data['duration']
        if duration <= 0:
            raise forms.ValidationError('Duration must be a positive integer.')
        return duration

    def clean_price(self):
        price = self.cleaned_data['price']
        if price < 0:
            raise forms.ValidationError('Price cannot be negative.')
        return price
    
COUNTRY_CHOICES = [
    (country.alpha_2, country.name) for country in sorted(pycountry.countries, key=lambda c: c.name)
]

# Generate country code choices with international phone dialing codes
COUNTRY_CODE_CHOICES = []
for country in sorted(pycountry.countries, key=lambda c: c.name):
    region_code = country.alpha_2
    try:
        # Get an example phone number for the region to extract the country code
        example_number = phonenumbers.example_number(region_code)
        if example_number:
            phone_code = f"+{example_number.country_code}"
            COUNTRY_CODE_CHOICES.append((region_code, f"{country.name} ({phone_code})"))
    except phonenumbers.NumberParseException:
        # Skip countries without valid phone numbers
        continue

class CustomRegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=True)
    user_type = forms.ChoiceField(choices=Profile.USER_TYPES, required=True, label="Registering as")
    country = forms.ChoiceField(choices=COUNTRY_CHOICES, required=True, label="Country of Residence")
    country_code = forms.ChoiceField(choices=COUNTRY_CODE_CHOICES, required=True, label="Country Code")
    local_number = forms.CharField(max_length=15, required=True, label="Phone Number")
    course = forms.ModelChoiceField(queryset=Course.objects.all(), required=False, label="Course (optional)")
    profile_picture = forms.ImageField(required=False, label="Profile Picture (optional)")

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2', 'user_type', 'country', 'country_code', 'local_number', 'course', 'profile_picture']
        
        
    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
            raise forms.ValidationError("Password must contain both letters and numbers.")
        return password

    def clean(self):
        cleaned_data = super().clean()
        country = cleaned_data.get('country')
        country_code = cleaned_data.get('country_code')
        local_number = cleaned_data.get('local_number')

        # Ensure country and country_code match
        if country and country_code and country != country_code:
            raise forms.ValidationError("Country and country code must match.")

        # Validate phone number
        if country_code and local_number:
            # Find the phone code for the country_code
            phone_code = None
            for code, name in COUNTRY_CODE_CHOICES:
                if code == country_code:
                    phone_code = name.split('(')[1].strip(')')
                    break
            if phone_code:
                try:
                    phone_number = parse(f"{phone_code}{local_number}", None)
                    if not is_valid_number(phone_number):
                        raise forms.ValidationError("Invalid phone number.")
                    cleaned_data['mobile_number'] = format_number(phone_number, PhoneNumberFormat.E164)
                except phonenumbers.NumberParseException:
                    raise forms.ValidationError("Invalid phone number format.")
            else:
                raise forms.ValidationError("Invalid country code.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user

class PaymentSlipForm(forms.ModelForm):
    class Meta:
        model = PaymentSlip
        fields = ['slip']
        widgets = {
            'slip': forms.FileInput(attrs={'accept': 'image/*,application/pdf'}),
        }

class PortfolioForm(forms.ModelForm):
    class Meta:
        model = Portfolio
        fields = ['name', 'bio', 'github_url', 'skills', 'projects', 'certificates', 'is_public']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
            'skills': forms.Textarea(attrs={'rows': 2}),
            'projects': forms.Textarea(attrs={'rows': 4}),
            'certificates': forms.Textarea(attrs={'rows': 2}),
        }

class OnboardingQuizForm(forms.ModelForm):
    social_media_platforms = forms.MultipleChoiceField(
        choices=[
            ('facebook', 'Facebook'),
            ('twitter', 'Twitter'),
            ('instagram', 'Instagram'),
            ('linkedin', 'LinkedIn'),
        ],
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Which social media platforms did you follow?"
    )

    class Meta:
        model = OnboardingQuizResponse
        fields = ['has_laptop', 'occupation', 'bio']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.followed_social_media = bool(self.cleaned_data['social_media_platforms'])
        if commit:
            instance.save()
        return instance

class FacilitatorProfileForm(forms.ModelForm):
    course = forms.ModelChoiceField(queryset=Course.objects.all(), required=True)

    class Meta:
        model = Profile
        fields = ['linkedin_url', 'twitter_url', 'github_url', 'facebook_url', 'internship_available', 'course']
        widgets = {
            'linkedin_url': forms.URLInput(attrs={'placeholder': 'https://linkedin.com/in/username'}),
            'twitter_url': forms.URLInput(attrs={'placeholder': 'https://twitter.com/username'}),
            'github_url': forms.URLInput(attrs={'placeholder': 'https://github.com/username'}),
            'facebook_url': forms.URLInput(attrs={'placeholder': 'https://facebook.com/username'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['course'].required = True

class CourseChangeForm(forms.Form):
    course = forms.ModelChoiceField(
        queryset=Course.objects.all(),
        required=True,
        label="Select New Course",
        help_text="Choose the course you wish to enroll in."
    )

    def clean_course(self):
        course = self.cleaned_data.get('course')
        if not course:
            raise forms.ValidationError("Please select a valid course.")
        return course
    
    
class DiscussionPostForm(forms.Form):
    title = forms.CharField(max_length=255, required=True)
    content = forms.CharField(widget=forms.Textarea, required=True)