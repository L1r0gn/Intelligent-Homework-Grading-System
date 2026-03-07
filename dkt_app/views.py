import os
import torch
import json
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.conf import settings
from userManageModule.models import User
from questionManageModule.models import KnowledgePoint, Problem
from gradingModule.models import Submission
from .dkt_utils import Data_Loader, get_student_predictions, Item
from .models import DKT
import logging

logger = logging.getLogger(__name__)

# 内存中的模型缓存
_dkt_model_cache = None
_knowledge_dim_cache = None
_knowledge_point_map_reverse_cache = None

def _load_dkt_model():
    """
    加载训练好的DKT模型和知识点维度。
    缓存模型和知识点维度以提高性能。
    """
    global _dkt_model_cache, _knowledge_dim_cache, _knowledge_point_map_reverse_cache

    if _dkt_model_cache is not None and _knowledge_dim_cache is not None and _knowledge_point_map_reverse_cache is not None:
        return _dkt_model_cache, _knowledge_dim_cache, _knowledge_point_map_reverse_cache

    # 1. 加载 Data_Loader 以获取知识点维度和知识点映射
    data_loader = Data_Loader() # 这将从数据库加载数据并设置知识点维度
    knowledge_dim = data_loader.knowledge_dim
    
    all_knowledge_points = KnowledgePoint.objects.all().order_by('id')
    knowledge_point_map_reverse = {i: kp.name for i, kp in enumerate(all_knowledge_points)}


    # 2. 初始化 DKT 模型
    dkt_model = DKT(knowledge_dim)

    # 3. 加载训练好的权重
    model_path = os.path.join(settings.BASE_DIR, 'dkt_app', 'trained_models', 'dkt_model.pth')
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"未找到训练好的 DKT 模型：{model_path}。请先运行 `python manage.py train_dkt`。")

    dkt_model.load_state_dict(torch.load(model_path))
    dkt_model.eval() # 设置模型为评估模式

    _dkt_model_cache = dkt_model
    _knowledge_dim_cache = knowledge_dim
    _knowledge_point_map_reverse_cache = knowledge_point_map_reverse
    
    return _dkt_model_cache, _knowledge_dim_cache, _knowledge_point_map_reverse_cache

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

@login_required
def my_mastery_view(request):
    """
    显示当前登录用户的 DKT 知识掌握度预测。
    学生只能查看自己的，老师和管理员可以查看所有学生的
    """
    user = request.user
    
    # 检查用户权限
    is_teacher_or_admin = user.user_attribute in [2, 3, 4]  # 老师、管理员、超级管理员
    
    if is_teacher_or_admin:
        # 如果是老师或管理员，重定向到学生列表页面
        return student_list_view(request)
    else:
        # 学生只能查看自己的
        student_id = user.id
        response = get_student_mastery_view(request, student_id)
        
        if response.status_code == 200:
            data = json.loads(response.content)
            logger.info(f"user {request.user.id} request dkt data, data:{data}")
            return render(request, 'dkt_app/my_mastery.html', {'dkt_data': data})
        else:
            error_message = json.loads(response.content).get('error', '未知错误')
            return render(request, 'dkt_app/my_mastery.html', {'error': error_message})

@login_required
def student_list_view(request):
    """
    显示学生列表，供老师和管理员选择查看哪个学生的学习情况。
    """
    user = request.user
    
    # 验证权限
    if user.user_attribute not in [2, 3, 4]:  # 非老师、管理员、超级管理员
        return render(request, 'dkt_app/student_list.html', {
            'error': '您没有权限访问此页面，只有老师和管理员可以查看。'
        })
    
    # 获取所有学生（排除老师和管理员）
    students = User.objects.filter(user_attribute=1).order_by('username')
    
    # 如果有班级关联，优先显示同班级的学生
    if user.class_in.exists():
        user_classes = user.class_in.all()
        class_students = User.objects.filter(class_in__in=user_classes, user_attribute=1).distinct().order_by('username')
        other_students = students.exclude(id__in=class_students.values('id'))
    else:
        class_students = students
        other_students = User.objects.none()
    
    context = {
        'class_students': class_students,
        'other_students': other_students,
        'is_teacher_or_admin': True
    }
    
    return render(request, 'dkt_app/student_list.html', context)

@login_required
def view_student_mastery(request, student_id):
    """
    老师和管理员查看特定学生的学习情况。
    """
    user = request.user
    
    # 验证权限
    if user.user_attribute not in [2, 3, 4]:  # 非老师、管理员、超级管理员
        return render(request, 'dkt_app/my_mastery.html', {
            'error': '您没有权限查看其他学生的学习情况。'
        })
    
    # 调用现有的 API 视图逻辑来获取数据
    response = get_student_mastery_view(request, student_id)


    if response.status_code == 200:
        data = json.loads(response.content)

        # test - wrong
        logger.info(data)

        student = get_object_or_404(User, id=student_id)
        logger.info(f"teacher {user.wx_nickName} fetch student {student.wx_nickName} dkt data")

        return render(request, 'dkt_app/my_mastery.html', {
            'dkt_data': data,
            'is_teacher_viewing': True,
            'current_user': user
        })
    else:
        error_message = json.loads(response.content).get('error', '未知错误')
        return render(request, 'dkt_app/my_mastery.html', {'error': error_message})

def get_student_mastery_view(request, student_id):
    try:
        # 1. 获取学生基本信息
        student = get_object_or_404(User, id=student_id)

        # 2. 加载模型（建议确保此函数内部有缓存机制，不要每次 open 文件）
        dkt_model, knowledge_dim, knowledge_point_map_reverse = _load_dkt_model()

        # 3. 获取所有知识点并建立映射（0-indexed）
        all_knowledge_points = KnowledgePoint.objects.all().order_by('id')
        knowledge_point_map = {kp.id: i for i, kp in enumerate(all_knowledge_points)}

        # 确保 concept_labels 与 knowledge_dim 长度一致
        concept_labels = [knowledge_point_map_reverse.get(i, f"未知-{i}") for i in range(knowledge_dim)]

        # 4. 获取提交记录并构造模型输入
        submissions = Submission.objects.filter(student=student)\
            .select_related('problem')\
            .prefetch_related('problem__knowledge_points')\
            .order_by('submitted_time')

        student_items_list = []
        for sub in submissions:
            # 这里的 +1 是为了匹配你 Data_Loader 和 train 中的 1-indexed 逻辑
            problem_knowledge_codes = [
                knowledge_point_map[kp.id] + 1
                for kp in sub.problem.knowledge_points.all()
                if kp.id in knowledge_point_map
            ]

            # 这里的及格线建议与训练时保持一致 (0.6)
            binary_score = 1.0 if (sub.score is not None and sub.problem.points and (sub.score / sub.problem.points) >= 0.6) else 0.0

            student_items_list.append(Item(
                exer_id=sub.problem.id,
                score=binary_score,
                knowledge_code=problem_knowledge_codes
            ))

        if not student_items_list:
            return JsonResponse({
                'message': 'No submission data for this student.',
                'mastery_predictions': [],
                'exercise_sequence': []
            })

        # 5. 调用推理函数
        # 注意：这里的 pred_matrix 形状应为 (knowledge_dim, Time_steps)
        pred_matrix, exercise_seq = get_student_predictions(dkt_model, student_items_list, knowledge_dim)

        # --- 6. 修正后的过滤逻辑 ---

        # 核心修改：从 student_items_list 中提取所有题目涉及的所有知识点
        # 而不是只从 exercise_seq (只存了 main_k_idx) 中提取
        all_interacted_indices = []
        for item in student_items_list:
            for code in item.knowledge_code:
                # 转换回 0-indexed 索引
                idx = code - 1
                if 0 <= idx < knowledge_dim:
                    all_interacted_indices.append(idx)

        # 去重并排序，得到学生真正练习过的所有知识点
        interacted_concept_indices = sorted(list(set(all_interacted_indices)))

        # 调试：检查到底找出了多少个知识点
        # logger.info(f"Interacted concepts count: {len(interacted_concept_indices)}")

        filtered_concept_labels = [concept_labels[idx] for idx in interacted_concept_indices]

        # 重要：将矩阵转置为 (Time_steps, knowledge_dim) 以便按时间步处理
        time_steps_matrix = pred_matrix.T

        filtered_mastery_predictions = []
        avg_mastery_history = []
        concept_mastery_history = {label: [] for label in filtered_concept_labels}

        for step_idx in range(len(exercise_seq)):
            current_step_all = time_steps_matrix[step_idx]

            # 过滤：保留所有练习过的知识点的预测值
            current_filtered = [float(current_step_all[idx]) for idx in interacted_concept_indices]
            filtered_mastery_predictions.append(current_filtered)

            # 计算当前步练习过的知识点平均掌握度
            avg_val = sum(current_filtered) / len(current_filtered) if current_filtered else 0
            avg_mastery_history.append(round(avg_val, 4))

            # 填充历史曲线
            for i, label in enumerate(filtered_concept_labels):
                concept_mastery_history[label].append(round(current_filtered[i], 4))

        # 7. 计算汇总数据
        last_concept_mastery = {}
        if filtered_mastery_predictions:
            last_step_vals = filtered_mastery_predictions[-1]
            for i, label in enumerate(filtered_concept_labels):
                last_concept_mastery[label] = round(last_step_vals[i], 4)

        current_avg_mastery = avg_mastery_history[-1] if avg_mastery_history else 0.0
        exercise_times = [f'练习{i+1}' for i in range(len(exercise_seq))]

        # 8. 封装响应
        response_data = {
            'student_id': student_id,
            'student_name': student.username,
            'knowledge_dim': knowledge_dim,
            'mastery_predictions': filtered_mastery_predictions,
            'exercise_sequence': [{
                'score': item['score'],
                'concept_idx': item['concept_idx'],
                'problem_id': student_items_list[i].exer_id
            } for i, item in enumerate(exercise_seq)],
            'concept_labels': filtered_concept_labels,
            'avg_mastery_history': avg_mastery_history,
            'last_concept_mastery': last_concept_mastery,
            'current_avg_mastery': current_avg_mastery,
            'exercise_times': exercise_times,
            'concept_mastery_history': concept_mastery_history
        }

        return JsonResponse(response_data)

    except Exception as e:
        logger.error(f"DKT API Error: {str(e)}", exc_info=True)
        return JsonResponse({'error': f'Error getting predictions: {str(e)}'}, status=500)
