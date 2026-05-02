from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import datetime
import pycountry
from django.db.models import Avg, Count
from .models import EvaluationRecord, CustomUser
from .ml_utils import feature_columns
from .services.evaluation_service import EvaluationService
from .forms import EvaluationForm 
from django import forms
from django.shortcuts import render, redirect , get_object_or_404
from .forms import SignupForm,LoginForm
import matplotlib
matplotlib.use('Agg')   # 🔥 FIX: no GUI backend

from django.contrib.auth import login
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
import matplotlib.pyplot as plt
import os
from django.conf import settings
import uuid
from urllib.parse import urlparse, urljoin
from django.utils.http import url_has_allowed_host_and_scheme

def home(request):
    return render(request, "predictor/home.html")


# ================= DASHBOARD =================
@login_required(login_url='login')
def dashboard(request):

    records = EvaluationRecord.objects.filter(
        user=request.user
    ).order_by("created_at")

    total = records.count()

    average_score = records.aggregate(avg=Avg("probability"))["avg"] or 0

    for r in records:
        if r.probability >= 70:
            r.rating_label = "Strong"
            r.badge_class = "success"
        elif r.probability >= 50:
            r.rating_label = "Moderate"
            r.badge_class = "warning"
        else:
            r.rating_label = "High Risk"
            r.badge_class = "danger"

    chart_labels = [r.created_at.strftime("%Y-%m-%d") for r in records]
    chart_values = [float(r.probability) for r in records]

    return render(request, "predictor/dashboard.html", {
        "records": records,
        "total": total,
        "average_score": round(average_score, 2),
        "chart_labels": chart_labels,
        "chart_values": chart_values
    })


# ================= UTIL =================
def get_country_name(code):
    country = pycountry.countries.get(alpha_3=code)
    return country.name if country else code


# -------------- Evaluate----------------------
FREE_LIMIT = 3

def evaluate(request):

    # ================= COUNTRY DATA =================
    country_data = []

    for col in feature_columns:
        if isinstance(col, str) and col.startswith("country_code_"):
            code = col.replace("country_code_", "")
            name = get_country_name(code)
            country_data.append((code, name))

    country_data = sorted(country_data, key=lambda x: x[1])

    # ================= CATEGORY DATA =================
    categories = sorted([
        col.replace("main_category_", "")
        for col in feature_columns
        if isinstance(col, str) and col.startswith("main_category_")
    ])

    # ================= YEAR + ROUNDS =================
    current_year = datetime.now().year
    years = list(range(current_year, 1980, -1))
    rounds = list(range(0, 11))

    # ================= FREE LIMIT =================
    remaining_attempts = None

    if not request.user.is_authenticated:
        count = request.session.get("free_evaluations_count", 0)
        remaining_attempts = max(0, FREE_LIMIT - count)

    # ================= POST =================
    if request.method == "POST":
        try:
            if not request.user.is_authenticated:
                count = request.session.get("free_evaluations_count", 0)

                if count >= FREE_LIMIT:
                    messages.warning(request, "Free limit reached. Please login.")
                    return redirect("login")

                request.session["free_evaluations_count"] = count + 1

            # 🔥 ML PROCESS
            result = EvaluationService.process_evaluation(request.POST)

            if not result:
                raise ValueError("Evaluation failed.")

            # ================= SAVE =================
            if request.user.is_authenticated:
                record = EvaluationRecord.objects.create(
                    user=request.user,
                    funding=result["funding"],
                    rounds=result["rounds"],
                    founded_year=result["founded_year"],
                    country=result["country"],
                    category=result["category"],
                    competition_level=result["competition_level"],
                    probability=result["probability"],
                    rating=result["rating"],
                    model_version=result["model_version"]
                )

                request.session["last_evaluation_id"] = record.id

            request.session["evaluation_result"] = result

            return redirect("result")

        except ValueError as e:
            messages.error(request, str(e))

        except Exception as e:
            print("ERROR:", e)
            messages.error(request, "Internal error. Try again.")

    # ================= RENDER =================
    return render(request, "predictor/evaluate.html", {
        "countries": country_data,
        "categories": categories,
        "years": years,
        "rounds": rounds,
        "remaining_attempts": remaining_attempts
    })


# ================= RESULT =================
def result(request):

    evaluation_id = request.session.get("last_evaluation_id")

    if request.user.is_authenticated and evaluation_id:
        try:
            record = EvaluationRecord.objects.get(
                id=evaluation_id,
                user=request.user
            )

            industry_average = EvaluationService.INDUSTRY_BASELINE

            return render(request, "predictor/result.html", {
                "funding": record.funding,
                "rounds": record.rounds,
                "founded_year": record.founded_year,
                "country": record.country,
                "category": record.category,
                "competition_level": record.competition_level,
                "probability": record.probability,
                "rating": record.rating,
                "industry_average": industry_average,
                "difference": round(record.probability - industry_average, 2),
                "model_version": record.model_version,
                "explanation": request.session.get("evaluation_result", {}).get("explanation"),
                "top_features": request.session.get("evaluation_result", {}).get("top_features", [])
            })

        except EvaluationRecord.DoesNotExist:
            pass

    result = request.session.get("evaluation_result")

    if not result:
        return redirect("evaluate")

    industry_average = EvaluationService.INDUSTRY_BASELINE

    return render(request, "predictor/result.html", {
        **result,
        "industry_average": industry_average,
        "difference": round(result["probability"] - industry_average, 2)
    })



def download_report(request):

    result = request.session.get("evaluation_result")

    if not result:
        return redirect("evaluate")

    industry_average = EvaluationService.INDUSTRY_BASELINE

    probability = result["probability"]
    difference = round(probability - industry_average, 2)

    # ================= CHART 1 (Performance) =================
    fig1, ax1 = plt.subplots()
    ax1.bar(["Your Startup", "Industry Avg"], [probability, industry_average])
    ax1.set_ylim(0, 100)
    ax1.set_ylabel("Score (%)")
    ax1.set_title("Performance Comparison")

    chart1_path = os.path.join(settings.MEDIA_ROOT, f"chart1_{uuid.uuid4()}.png")
    plt.savefig(chart1_path)
    plt.close(fig1)

    # ================= CHART 2 (Feature Importance) =================
    top_features = result.get("top_features", [])

    chart2_path = None

    if top_features:
        labels = [f for f, _ in top_features]
        values = [float(i) for _, i in top_features]

        fig2, ax2 = plt.subplots()
        ax2.barh(labels, values)
        ax2.set_title("Feature Importance")

        chart2_path = os.path.join(settings.MEDIA_ROOT, f"chart2_{uuid.uuid4()}.png")
        plt.savefig(chart2_path)
        plt.close(fig2)

    # ================= CONTEXT =================
    context = {
        **result,
        "industry_average": industry_average,
        "difference": difference,
        "chart1": chart1_path,
        "chart2": chart2_path
    }

    template = get_template("predictor/pdf_report.html")
    html = template.render(context)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="startup_report.pdf"'

    pisa.CreatePDF(html, dest=response)

    return response

# ================= AUTH =================



def signup_view(request):

    next_url = request.GET.get("next") or request.POST.get("next")

    if request.method == "POST":
        form = SignupForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created successfully!")

            if next_url and url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={request.get_host()}
            ):
                return redirect(next_url)

            return redirect("home")

    else:
        form = SignupForm()

    return render(request, "auth/signup.html", {
        "form": form,
        "next": next_url
    })



def is_safe_url(url, host):
    if not url:
        return False
    netloc = urlparse(url).netloc
    return netloc == "" or netloc == host



def login_view(request):

    next_url = request.GET.get("next") or request.POST.get("next")

    if request.method == "POST":
        form = LoginForm(request.POST)

        if form.is_valid():
            user = form.cleaned_data["user"]
            login(request, user)
            messages.success(request, "Welcome back!")

            # ✅ SAFE REDIRECT (CORRECT WAY)
            if next_url and url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={request.get_host()}
            ):
                return redirect(next_url)

            return redirect("home")

    else:
        form = LoginForm()

    return render(request, "auth/login.html", {
        "form": form,
        "next": next_url
    })

def logout_view(request):
    logout(request)
    return redirect("home")


# ================= REPORT =================
@login_required(login_url="login")
def evaluation_report(request, record_id):

    try:
        record = EvaluationRecord.objects.get(
            id=record_id,
            user=request.user
        )
    except EvaluationRecord.DoesNotExist:
        messages.error(request, "Evaluation not found.")
        return redirect("dashboard")

    industry_average = EvaluationService.INDUSTRY_BASELINE

    return render(request, "predictor/report.html", {
        "record": record,
        "industry_average": industry_average,
        "difference": round(record.probability - industry_average, 2)
    })



@staff_member_required(login_url="login")
def admin_dashboard(request):

    total_users = CustomUser.objects.count()
    total_evaluations = EvaluationRecord.objects.count()

    avg_score = EvaluationRecord.objects.aggregate(
        avg=Avg("probability")
    )["avg"] or 0

    # Latest records
    recent_records = EvaluationRecord.objects.order_by("-created_at")[:10]

    # Users list
    users = CustomUser.objects.all().order_by("-date_joined")

    # Category stats
    category_stats = (
        EvaluationRecord.objects
        .values("category")
        .annotate(count=Count("id"))
        .order_by("-count")[:5]
    )

    return render(request, "admin_panel/dashboard.html", {
        "total_users": total_users,
        "total_evaluations": total_evaluations,
        "avg_score": round(avg_score, 2),
        "recent_records": recent_records,
        "category_stats": category_stats,
        "users": users
    })

@staff_member_required(login_url="login")
def toggle_user_status(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)

    user.is_active = not user.is_active
    user.save()

    return redirect("admin_dashboard")


@staff_member_required(login_url="login")
def delete_user(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)

    if user.is_superuser:
        messages.error(request, "Cannot delete admin user.")
    else:
        user.delete()
        messages.success(request, "User deleted.")

    return redirect("admin_dashboard")