from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class User(AbstractUser):
    ROLE_CHOICES = [
        ('Student', 'Student'),
        ('Admin', 'Admin'),
    ]
    role = models.CharField(max_length=20, default='Student', choices=ROLE_CHOICES) 
    college = models.CharField(max_length=100, default='CampusCode Institute')
    streak = models.IntegerField(default=0)
    college_rank = models.IntegerField(default=0)
    global_rank = models.IntegerField(default=0)
    level = models.IntegerField(default=1)
    xp = models.IntegerField(default=0)

    @property
    def xp_percentage(self):
        # Cap at 100% to avoid CSS overflow errors in progress bars
        return min((self.xp / 2000) * 100, 100)
    
    def __str__(self):
        return self.username

class Problem(models.Model):
    DIFFICULTY_CHOICES = [
        ('Easy', 'Easy'),
        ('Medium', 'Medium'),
        ('Hard', 'Hard'),
    ]
    
    title = models.CharField(max_length=200)
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES)
    points = models.IntegerField(default=10)
    acceptance = models.CharField(max_length=10, default='0%')
    tags = models.CharField(max_length=200, blank=True)
    
    # Problem Description Fields
    statement = models.TextField()
    input_fmt = models.TextField(verbose_name="Input Format")
    output_fmt = models.TextField(verbose_name="Output Format")
    constraints = models.TextField()
    
    # Visible Sample Cases (Shown in description)
    sample_input = models.TextField(blank=True, null=True)
    sample_output = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.title

class TestCase(models.Model):
    """
    Hidden test cases used for grading code submissions via Piston.
    """
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='test_cases')
    input_data = models.TextField(help_text="The stdin input given to the code")
    expected_output = models.TextField(help_text="The expected stdout output from the code")
    is_hidden = models.BooleanField(default=True, help_text="If True, the user won't see the input/output on failure")

    def __str__(self):
        return f"TestCase for {self.problem.title} (Hidden: {self.is_hidden})"

class Submission(models.Model):
    """
    Tracks every code submission attempt.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions')
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    code = models.TextField()
    language = models.CharField(max_length=50, default='python')
    passed = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        status = "Passed" if self.passed else "Failed"
        return f"{self.user.username} - {self.problem.title} - {status}"

class Contest(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    rules = models.TextField(blank=True)
    prizes = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, default='Upcoming')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    participants = models.IntegerField(default=0)

    @property
    def duration(self):
        diff = self.end_time - self.start_time
        hours = diff.seconds // 3600
        return f"{hours} Hours"
    
    def __str__(self):
        return self.title

class ForumPost(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    date_posted = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.title