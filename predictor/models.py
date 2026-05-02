from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager


# ================= CUSTOM USER MANAGER =================
class CustomUserManager(BaseUserManager):

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")

        return self.create_user(email, password, **extra_fields)


# ================= CUSTOM USER =================
class CustomUser(AbstractUser):

    username = None  # ❗ REMOVE username completely
    email = models.EmailField(unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()  # ❗ VERY IMPORTANT

    def __str__(self):
        return self.email


# ================= EVALUATION MODEL =================
class EvaluationRecord(models.Model):

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    funding = models.FloatField()
    rounds = models.IntegerField()
    founded_year = models.IntegerField()

    country = models.CharField(max_length=10)
    category = models.CharField(max_length=100)
    competition_level = models.CharField(max_length=20)

    probability = models.FloatField()
    rating = models.CharField(max_length=100)

    model_version = models.CharField(max_length=50)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.category} - {self.probability}% ({self.created_at.date()})"