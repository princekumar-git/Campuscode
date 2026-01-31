import json
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from django.utils import timezone
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors

# Make sure to import TestCase and Submission explicitly
 
from .models import (
    User,
    Problem,
    Contest,
    TestCase,
    Submission,
    ForumCategory,
    ForumThread,
    ForumReply,
    ForumVote,
)


PISTON_API = "https://emkc.org/api/v2/piston/execute"


def compute_and_update_ranks():
    """Recalculate and persist global and college ranks for all Students.

    Ranking rules:
    - Higher XP -> better (lower) rank (1 is best).
    - Users with equal XP receive the same rank (dense ranking).
    """
    students = User.objects.filter(role='Student').order_by('-xp', 'username')

    to_update = []

    # Global ranks (dense ranking)
    prev_xp = None
    rank = 0
    for u in students:
        if u.xp != prev_xp:
            rank += 1
            prev_xp = u.xp
        if u.global_rank != rank:
            u.global_rank = rank
            to_update.append(u)

    # College ranks (per college)
    colleges = students.values_list('college', flat=True).distinct()
    for college in colleges:
        col_students = students.filter(college=college)
        prev_xp = None
        rank = 0
        for u in col_students:
            if u.xp != prev_xp:
                rank += 1
                prev_xp = u.xp
            if u.college_rank != rank:
                u.college_rank = rank
                if u not in to_update:
                    to_update.append(u)

    if to_update:
        User.objects.bulk_update(to_update, ['global_rank', 'college_rank'])

# =========================================
# 1. Authentication Views 
# =========================================

def index(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'index.html')

def signup_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        password = request.POST.get('password')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists.')
            return redirect('index')

        user = User.objects.create_user(username=email, email=email, password=password)
        user.first_name = name 
        user.role = 'Student'
        user.streak = 1
        highest_rank = User.objects.filter(role='Student').order_by('global_rank').first()
        user.global_rank = highest_rank.global_rank + 1 if highest_rank else 1
        user.college_rank = highest_rank.college_rank + 1 if highest_rank else 1
        user.xp = 0
        user.save()

        login(request, user)
        return redirect('dashboard')
    
    return redirect('index')

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        try:
            user_obj = User.objects.get(email=email)
            user = authenticate(request, username=user_obj.username, password=password)
            
            if user is not None:
                login(request, user)
                if getattr(user, 'role', 'Student') == 'Admin':
                    return redirect('admin_dashboard')
                return redirect('dashboard')
            else:
                messages.error(request, 'Invalid password.')
        
        except User.DoesNotExist:
            messages.error(request, 'No account found with this email.')
            
    return redirect('index')

def logout_view(request):
    logout(request)
    return redirect('index')

# =========================================
# 2. Main Platform Views
# =========================================

@login_required
def dashboard(request):
    # Ensure ranks reflect current XP before rendering dashboard
    compute_and_update_ranks()
    return render(request, 'dashboard.html', {'user': request.user})

@login_required
def problems(request):
    problems = Problem.objects.all()
    return render(request, 'problems.html', {'problems': problems})

@login_required
def solve_problem(request, id):
    problem = get_object_or_404(Problem, id=id)
    return render(request, 'problem_page.html', {'problem': problem})

@login_required
def contests(request):
    contests = Contest.objects.order_by('start_time')
    return render(request, 'contest.html', {'contests': contests})

@login_required
def contest_overview(request, id):
    contest = get_object_or_404(Contest, id=id)
    return render(request, 'contest_overview.html', {'contest': contest})

@login_required
def forum(request):
    threads = ForumThread.objects.select_related('author', 'category') \
        .annotate(reply_count=Count('replies')) \
        .order_by('-created_at')

    categories = ForumCategory.objects.all()

    return render(request, 'forum.html', {
        'threads': threads,
        'categories': categories,
    })

@login_required
def add_reply(request, thread_id):
    thread = get_object_or_404(ForumThread, id=thread_id)

    if request.method == 'POST':
        ForumReply.objects.create(
            thread=thread,
            content=request.POST.get('content'),
            author=request.user
        )

        # XP reward
        request.user.xp += 5
        request.user.save()

        # Update ranks since XP changed
        compute_and_update_ranks()

    return redirect('forum_thread_detail', thread_id=thread.id)

@login_required
def upvote_reply(request, reply_id):
    reply = get_object_or_404(ForumReply, id=reply_id)

    vote, created = ForumVote.objects.get_or_create(
        reply=reply,
        user=request.user,
        defaults={'value': 1}
    )

    if not created:
        vote.delete()  # toggle off
    else:
        reply.author.xp += 2
        reply.author.save()

        # Update ranks since XP changed
        compute_and_update_ranks()

    return redirect('forum_thread_detail', thread_id=reply.thread.id)

@login_required
def download_report_pdf(request):
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = "attachment; filename=CampusCode_Report.pdf"

    c = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    user = request.user

    # ===== HEADER =====
    c.setFont("Helvetica-Bold", 22)
    c.setFillColor(HexColor("#1E4A7A"))
    c.drawString(40, height - 50, "CampusCode – Learning Report")
    c.line(40, height - 60, width - 40, height - 60)

    # ===== USER INFO =====
    c.setFont("Helvetica", 12)
    c.setFillColor(colors.black)
    y = height - 100
    c.drawString(40, y, f"Username: {user.username}")
    c.drawString(40, y - 20, f"XP: {user.xp}")
    c.drawString(40, y - 40, f"Level: {user.level}")

    # ===== FOOTER =====
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.grey)
    c.drawString(40, 30, "Generated by CampusCode")
    c.drawRightString(width - 40, 30, timezone.now().strftime("%d %b %Y"))

    c.showPage()
    c.save()
    return response

@login_required
def create_thread(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        category_id = request.POST.get('category')

        ForumThread.objects.create(
            title=title,
            content=content,
            author=request.user,
            category_id=category_id if category_id else None
        )

        # XP reward for asking a question
        request.user.xp += 10
        request.user.save()

        # Update ranks since XP changed
        compute_and_update_ranks()

        return redirect('forum')

    categories = ForumCategory.objects.all()
    return render(request, 'create_thread.html', {
        'categories': categories
    })

@login_required
def forum_thread_detail(request, thread_id):
    thread = get_object_or_404(ForumThread, id=thread_id)

    # Increment views safely
    thread.views += 1
    thread.save(update_fields=['views'])

    replies = ForumReply.objects.filter(thread=thread) \
        .select_related('author') \
        .annotate(vote_count=Count('votes'))

    return render(request, 'forum_thread_detail.html', {
        'thread': thread,
        'replies': replies,
    })


@login_required
def profile(request):
    if request.method == 'POST':
        user = request.user
        new_username = request.POST.get('username')
        
        if new_username and new_username != user.username:
            if User.objects.filter(username=new_username).exists():
                messages.error(request, 'That username is already taken.')
                return redirect('profile')
            user.username = new_username

        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.college = request.POST.get('college')
        user.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('profile')
        
    return render(request, 'profile.html')


@login_required
def delete_account(request):
    """Deletes the authenticated user's account.

    Requires a POST with a `confirm_username` field that matches the
    current `request.user.username` to prevent accidental deletions.
    """
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('profile')

    user = request.user
    confirm_username = request.POST.get('confirm_username', '')

    if confirm_username != user.username:
        messages.error(request, 'Username confirmation did not match. Account not deleted.')
        return redirect('profile')

    # Logout first then delete the user (cascades to related models)
    logout(request)
    user.delete()
    messages.success(request, 'Your account has been deleted.')
    return redirect('index')


@login_required
def stats(request):
    user = request.user

    total_submissions = Submission.objects.filter(user=user).count()
    solved_problems = Submission.objects.filter(
        user=user, passed=True
    ).values('problem').distinct().count()

    success_rate = (solved_problems / total_submissions * 100) if total_submissions else 0

    difficulty_stats = {
        'Easy': Submission.objects.filter(user=user, passed=True, problem__difficulty='Easy')
            .values('problem').distinct().count(),
        'Medium': Submission.objects.filter(user=user, passed=True, problem__difficulty='Medium')
            .values('problem').distinct().count(),
        'Hard': Submission.objects.filter(user=user, passed=True, problem__difficulty='Hard')
            .values('problem').distinct().count(),
    }

    # 📈 submissions per day (last 7 days)
    daily_submissions = (
        Submission.objects.filter(user=user)
        .annotate(day=TruncDate('submitted_at'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )

    return render(request, 'report.html', {
        'total_submissions': total_submissions,
        'solved_problems': solved_problems,
        'success_rate': round(success_rate, 1),
        'difficulty_stats': difficulty_stats,
        'daily_submissions': list(daily_submissions),
    })
   
# =========================================
# 3. Admin Views
# =========================================

@login_required
def admin_dashboard(request):
    if request.user.role != 'Admin': return redirect('dashboard')
    stats = {
        'users': User.objects.filter(role='Student').count(),
        'problems': Problem.objects.count(),
        'contests': Contest.objects.count()
    }
    return render(request, 'admin_dashboard.html', {'stats': stats})

@login_required
def add_problem(request):
    if request.user.role != 'Admin': return redirect('dashboard')
    if request.method == 'POST':
        problem = Problem.objects.create(
            title=request.POST.get('title'),
            difficulty=request.POST.get('difficulty'),
            points=request.POST.get('points'),
            tags=request.POST.get('tags'),
            statement=request.POST.get('statement'),
            input_fmt=request.POST.get('input_fmt'),
            output_fmt=request.POST.get('output_fmt'),
            constraints=request.POST.get('constraints'),
            sample_input=request.POST.get('sample_input'),
            sample_output=request.POST.get('sample_output')
        )
        # Create a default visible test case matching the sample
        TestCase.objects.create(
            problem=problem,
            input_data=request.POST.get('sample_input'),
            expected_output=request.POST.get('sample_output'),
            is_hidden=False
        )
        messages.success(request, 'Problem Added')
    return redirect('admin_dashboard')

@login_required
def add_contest(request):
    if request.user.role != 'Admin': return redirect('dashboard')
    if request.method == 'POST':
        Contest.objects.create(
            title=request.POST.get('title'),
            description=request.POST.get('description'),
            rules=request.POST.get('rules'),
            prizes=request.POST.get('prizes'),
            start_time=request.POST.get('start_time'),
            end_time=request.POST.get('end_time'),
            status='Upcoming'
        )
        messages.success(request, 'Contest Created')
    return redirect('admin_dashboard')

# =========================================
# 4. Code Execution & Grading Views
# =========================================

@csrf_exempt
@login_required
def run_code(request):
    """
    Executes code against Sample Input.
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST request required"}, status=400)

    try:
        data = json.loads(request.body)
        code = data.get("code")
        language = data.get("language", "python")
        user_input = data.get("stdin", "")

        payload = {
            "language": language,
            "version": "*",
            "files": [{"content": code}],
            "stdin": user_input
        }
        
        response = requests.post(PISTON_API, json=payload, timeout=5)
        result = response.json()
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@login_required
def submit_solution(request, id):
    """
    Grading Logic: Runs against ALL test cases.
    """
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body)
        code = data.get("code")
        language = data.get("language", "python")

        problem = get_object_or_404(Problem, id=id)
        
        # [FIX 1] Use explicit filter instead of reverse relation to satisfy Pylance
        test_cases = TestCase.objects.filter(problem=problem)

        if not test_cases.exists():
            # Create a dummy object to safely run loop
            class DummyTC:
                def __init__(self, i, o): self.input_data, self.expected_output, self.is_hidden = i, o, False
            test_cases = [DummyTC(problem.sample_input, problem.sample_output)]

        results = []
        all_passed = True

        for tc in test_cases:
            payload = {
                "language": language,
                "version": "*",
                "files": [{"content": code}],
                "stdin": tc.input_data
            }

            try:
                response = requests.post(PISTON_API, json=payload, timeout=5)
                api_result = response.json()

                if 'run' not in api_result or api_result['run']['code'] != 0:
                    err_msg = api_result.get('run', {}).get('stderr', 'Unknown Error') or api_result.get('message', 'Error')
                    return JsonResponse({
                        "status": "error", 
                        "message": "Runtime/Compilation Error",
                        "details": err_msg
                    })

                # [FIX 2] Handle NoneType for stdout/expected output using (var or "")
                actual_output = (api_result['run'].get('stdout') or "").strip()
                expected_output = (tc.expected_output or "").strip()

                if actual_output == expected_output:
                    results.append({"status": "Passed"})
                else:
                    all_passed = False
                    results.append({
                        "status": "Failed",
                        "input": "Hidden Test Case" if tc.is_hidden else tc.input_data,
                        "expected": "Hidden" if tc.is_hidden else expected_output,
                        "actual": actual_output
                    })
                    break 

            except Exception as e:
                return JsonResponse({"status": "error", "message": "Execution API Failed", "details": str(e)})

        if all_passed:
            has_solved = Submission.objects.filter(user=request.user, problem=problem, passed=True).exists()
            msg = "Correct Answer!"
            
            if not has_solved:
                request.user.xp += problem.points
                request.user.save()
                msg += f" You earned +{problem.points} XP."

                # Update ranks since XP changed
                compute_and_update_ranks()
            
            Submission.objects.create(user=request.user, problem=problem, code=code, passed=True)
            return JsonResponse({"status": "success", "message": msg})
        else:
            Submission.objects.create(user=request.user, problem=problem, code=code, passed=False)
            return JsonResponse({"status": "failed", "results": results})

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)