from django import forms
from datetime import datetime
import logging
from .ml_utils import feature_columns
from django.contrib.auth import authenticate
from .models import CustomUser
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password



class SignupForm(forms.ModelForm):

    password = forms.CharField(
        widget=forms.PasswordInput,
        help_text="Minimum 8 characters, not too common, not entirely numeric"
    )

    confirm_password = forms.CharField(
        widget=forms.PasswordInput,
        label="Confirm Password"
    )

    class Meta:
        model = CustomUser
        fields = ["email", "password"]

    def clean_email(self):
        email = self.cleaned_data.get("email")

        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError("Email already exists.")

        return email

    def clean_password(self):
        password = self.cleaned_data.get("password")

        try:
            validate_password(password)
        except ValidationError as e:
            raise ValidationError(e.messages)

        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password:
            if password != confirm_password:
                raise ValidationError({
                    "confirm_password": "Passwords do not match."
                })

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = user.email
        user.set_password(self.cleaned_data["password"])

        if commit:
            user.save()

        return user

# ================= LOGIN FORM =================
class LoginForm(forms.Form):

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "Enter your email"
        })
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Enter your password"
        })
    )

    def clean_email(self):
        email = self.cleaned_data.get("email")

        if not CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("No account found with this email.")

        return email

    def clean(self):
        cleaned_data = super().clean()

        email = cleaned_data.get("email")
        password = cleaned_data.get("password")

        if email and password:
            user = authenticate(username=email, password=password)

            if not user:
                raise forms.ValidationError({
                    "password": "Incorrect password."
                })

            cleaned_data["user"] = user

        return cleaned_data



logger = logging.getLogger(__name__)

class EvaluationForm(forms.Form):

    # ---------------- Funding ----------------
    funding = forms.FloatField(
        min_value=0,
        max_value=10_000_000_000,
        required=True,
        label="Total Funding"
    )

    # ---------------- Rounds ----------------
    rounds = forms.IntegerField(
        min_value=0,
        max_value=50,
        required=True,
        label="Funding Rounds"
    )

    # ---------------- Founded Year ----------------
    founded_year = forms.IntegerField(
        required=True,
        label="Founded Year"
    )

    # ---------------- Country ----------------
    country = forms.ChoiceField(
        required=True,
        label="Country"
    )

    # ---------------- Category ----------------
    category = forms.ChoiceField(
        required=True,
        label="Industry Category"
    )

    # ---------------- Competition ----------------
    COMPETITION_CHOICES = [
        ("emerging", "Emerging Market"),
        ("competitive", "Competitive Market"),
        ("high", "Highly Competitive"),
        ("saturated", "Saturated Market"),
    ]

    competition_level = forms.ChoiceField(
        choices=COMPETITION_CHOICES,
        required=True,
        label="Competition Level"
    )

    # ==========================================================
    # INIT (SAFE DYNAMIC DROPDOWNS)
    # ==========================================================
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        try:
            from .your_ml_file import feature_columns   # 🔴 FIX IMPORT PATH

            # Extract from model columns
            country_choices = sorted([
                (col.replace("country_code_", ""), col.replace("country_code_", ""))
                for col in feature_columns
                if col.startswith("country_code_")
            ])

            category_choices = sorted([
                (col.replace("main_category_", ""), col.replace("main_category_", ""))
                for col in feature_columns
                if col.startswith("main_category_")
            ])

            # 🔥 SAFETY FALLBACK (VERY IMPORTANT)
            if not country_choices:
                logger.warning("Country list empty → using fallback")
                country_choices = [
                    ("India", "India"),
                    ("USA", "USA"),
                    ("UK", "UK")
                ]

            if not category_choices:
                logger.warning("Category list empty → using fallback")
                category_choices = [
                    ("AI", "AI"),
                    ("FinTech", "FinTech"),
                    ("Ecommerce", "Ecommerce")
                ]

        except Exception as e:
            logger.error(f"Dropdown generation failed: {e}")

            # HARD FAILSAFE (never break UI)
            country_choices = [
                ("India", "India"),
                ("USA", "USA")
            ]

            category_choices = [
                ("AI", "AI"),
                ("FinTech", "FinTech")
            ]

        self.fields["country"].choices = country_choices
        self.fields["category"].choices = category_choices

    # ==========================================================
    # VALIDATIONS
    # ==========================================================

    def clean_founded_year(self):
        year = self.cleaned_data["founded_year"]
        current_year = datetime.now().year

        if year < 1980:
            raise forms.ValidationError("Founded year is unrealistically old.")

        if year > current_year:
            raise forms.ValidationError("Founded year cannot be in the future.")

        return year

    def clean(self):
        cleaned_data = super().clean()

        funding = cleaned_data.get("funding")
        rounds = cleaned_data.get("rounds")

        if funding is not None and rounds is not None:
            if funding > 0 and rounds == 0:
                raise forms.ValidationError(
                    "Funding provided but rounds set to 0."
                )

        return cleaned_data