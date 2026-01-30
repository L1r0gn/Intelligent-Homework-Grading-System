from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from functools import wraps
from .models import className, User, ClassTeacher
from .forms import ClassForm, ClassTeacherForm, AddStudentToClassForm
import logging

logger = logging.getLogger(__name__)

@login_required
def search_students_api(request):
    """
    API: 搜索学生
    GET 参数: q (关键词)
    返回: {results: [{id: 1, text: "Name (username)"}, ...]}
    """
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'results': []})
    
    # 仅搜索学生 (user_attribute=1)
    students = User.objects.filter(user_attribute=1).filter(
        Q(username__icontains=query) | 
        Q(wx_nickName__icontains=query) | 
        Q(phone__icontains=query)
    )[:20] # 限制返回前20条
    
    results = []
    for s in students:
        display_name = s.wx_nickName if s.wx_nickName else s.username
        # 格式化显示文本
        text = f"{display_name} ({s.username})"
        if s.phone:
            text += f" - {s.phone}"
            
        results.append({'id': s.id, 'text': text})
        
    return JsonResponse({'results': results})

def teacher_required(view_func):
    """
    Ensure user is authenticated and is an teacher (user_attribute >= 2)
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.user_attribute < 2:
            messages.error(request, "您没有权限访问该页面。")
            return redirect('dashboard')  # Redirect to dashboard or appropriate page
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def admin_required(view_func):
    """
    Ensure user is authenticated and is an admin (user_attribute >= 3)
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.user_attribute < 3:
            messages.error(request, "您没有权限访问该页面。")
            return redirect('dashboard') # Redirect to dashboard or appropriate page
        return view_func(request, *args, **kwargs)
    return _wrapped_view

@login_required
def my_class_list_view(request):
    """
    显示当前用户所在的班级列表
    """
    query = request.GET.get('q', '')
    # 获取当前用户所在的班级
    my_classes = request.user.class_in.all().order_by('-created_at')

    if query:
        my_classes = my_classes.filter(
            Q(name__icontains=query) | 
            Q(code__icontains=query) |
            Q(grade__icontains=query)
        )

    paginator = Paginator(my_classes, 10) # 10 classes per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'my_class_list.html', {
        'page_obj': page_obj,
        'query': query
    })

@admin_required
def class_list_view(request):
    """
    Display list of all classes with pagination and search.
    """
    query = request.GET.get('q', '')
    classes = className.objects.all().order_by('-created_at')

    if query:
        classes = classes.filter(
            Q(name__icontains=query) | 
            Q(code__icontains=query) |
            Q(grade__icontains=query)
        )

    paginator = Paginator(classes, 10) # 10 classes per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'class_list.html', {
        'page_obj': page_obj,
        'query': query
    })

@teacher_required
def class_create_view(request):
    """
    Create a new class.
    """
    if request.method == 'POST':
        form = ClassForm(request.POST)
        if form.is_valid():
            new_class = form.save(commit=False)
            new_class.created_by = request.user
            new_class.save()
            messages.success(request, f'班级 "{new_class.name}" 创建成功。')
            return redirect('class_list_web')
    else:
        form = ClassForm()
    
    return render(request, 'class_form.html', {'form': form, 'title': '创建班级'})

@admin_required
def class_edit_view(request, class_id):
    """
    Edit an existing class.
    """
    class_obj = get_object_or_404(className, id=class_id)
    if request.method == 'POST':
        form = ClassForm(request.POST, instance=class_obj)
        if form.is_valid():
            form.save()
            messages.success(request, f'班级 "{class_obj.name}" 更新成功。')
            return redirect('class_list_web')
    else:
        form = ClassForm(instance=class_obj)
    
    return render(request, 'class_form.html', {'form': form, 'title': '编辑班级'})

@admin_required
def class_delete_view(request, class_id):
    """
    Delete a class with confirmation.
    """
    class_obj = get_object_or_404(className, id=class_id)
    
    # Check for associated students and teachers
    student_count = class_obj.members.count()
    teacher_count = class_obj.teachers.count()

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'delete':
            if student_count > 0 or teacher_count > 0:
                 # Check if user confirmed force delete (unlink)
                if request.POST.get('confirm_unlink') == 'yes':
                     # Unlink students (M2M remove)
                    class_obj.members.clear()
                    # Teachers are linked via ClassTeacher (Cascade delete will handle it, but for safety/logic clarity)
                    # Actually ClassTeacher has on_delete=CASCADE so deleting class deletes these records.
                    # But students are M2M.
                    class_obj.delete()
                    messages.success(request, '班级已删除，相关关联已解除。')
                    return redirect('class_list_web')
                else:
                    messages.error(request, '该班级仍有成员，请确认解除关联后再删除。')
            else:
                class_obj.delete()
                messages.success(request, '班级已删除。')
                return redirect('class_list_web')
    
    return render(request, 'class_confirm_delete.html', {
        'class_obj': class_obj,
        'student_count': student_count,
        'teacher_count': teacher_count
    })

@admin_required
def class_detail_view(request, class_id):
    """
    Show class details, students, and teachers.
    """
    class_obj = get_object_or_404(className, id=class_id)
    students = class_obj.members.all()
    teachers = class_obj.teachers.all().select_related('teacher') # ClassTeacher objects

    add_student_form = AddStudentToClassForm()
    add_teacher_form = ClassTeacherForm()

    return render(request, 'class_detail.html', {
        'class_obj': class_obj,
        'students': students,
        'teachers': teachers,
        'add_student_form': add_student_form,
        'add_teacher_form': add_teacher_form
    })

@admin_required
def class_add_student_view(request, class_id):
    class_obj = get_object_or_404(className, id=class_id)
    if request.method == 'POST':
        form = AddStudentToClassForm(request.POST)
        if form.is_valid():
            student = form.cleaned_data['student']
            if student in class_obj.members.all():
                messages.warning(request, f'学生 {student.username} 已经在该班级中。')
            else:
                class_obj.members.add(student)
                messages.success(request, f'成功将学生 {student.username} 添加到班级。')
        else:
            messages.error(request, '添加学生失败，请检查输入。')
    return redirect('class_detail_web', class_id=class_id)

@admin_required
def class_remove_student_view(request, class_id, student_id):
    class_obj = get_object_or_404(className, id=class_id)
    student = get_object_or_404(User, id=student_id)
    if request.method == 'POST':
        class_obj.members.remove(student)
        messages.success(request, f'已将学生 {student.username} 从班级移除。')
    return redirect('class_detail_web', class_id=class_id)

@admin_required
def class_add_teacher_view(request, class_id):
    class_obj = get_object_or_404(className, id=class_id)
    if request.method == 'POST':
        form = ClassTeacherForm(request.POST)
        if form.is_valid():
            teacher = form.cleaned_data['teacher']
            subject = form.cleaned_data['subject']
            
            if ClassTeacher.objects.filter(class_obj=class_obj, teacher=teacher).exists():
                 messages.warning(request, f'教师 {teacher.username} 已经在该班级任教。')
            else:
                ClassTeacher.objects.create(class_obj=class_obj, teacher=teacher, subject=subject)
                messages.success(request, f'成功添加任课教师 {teacher.username}。')
        else:
             messages.error(request, '添加教师失败，请检查输入。')
    return redirect('class_detail_web', class_id=class_id)

@admin_required
def class_remove_teacher_view(request, class_id, teacher_id):
    class_obj = get_object_or_404(className, id=class_id)
    # teacher_id here refers to the ClassTeacher ID, or User ID? 
    # Usually easier to pass ClassTeacher ID (the relation ID) to be precise, 
    # but the prompt implies "remove teacher from class".
    # Let's assume we pass the ClassTeacher ID (relation ID) for uniqueness if a teacher teaches multiple subjects?
    # The model has unique_together('class_obj', 'teacher', 'subject'). 
    # But usually a teacher teaches one subject per class or we just remove the teacher entirely.
    # Let's use the ClassTeacher PK for removal to be safe.
    
    relation = get_object_or_404(ClassTeacher, id=teacher_id, class_obj=class_obj)
    if request.method == 'POST':
        relation.delete()
        messages.success(request, f'已移除任课教师。')
    return redirect('class_detail_web', class_id=class_id)