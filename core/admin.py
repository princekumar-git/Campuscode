from django.contrib import admin
from .models import User, Problem, Contest, ForumPost

# Register your models here.
admin.site.register(User)
admin.site.register(Problem)
admin.site.register(Contest)
admin.site.register(ForumPost)
